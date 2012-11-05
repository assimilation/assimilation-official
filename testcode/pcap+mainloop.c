/**
 * @file
 * @brief Simple pcap testing code using 'mainloop'.
 * Listens for CDP or LLDP packets on the network - all using the mainloop dispatch code.
 * Probably a short-lived piece of test code.  Well... Maybe not so short-lived, but definitely
 * basic testing.
 *
 * Here's what it does at the moment:
 *	+ listen for LLDP or CDP packets and:
 *		demarshall them and remarshall them to see if they're the same
 *	+ listen for heartbeats - and there won't be any at first
 *		When we have declared ourself dead, we begin to send ourselves heartbeats.
 *		The first one will be declared late, but the remaining ones should be on time.
 *	The software is built to expect this behavior from itself and print info messages when
 *	things go as they should, and warning messages when things deviate from expectations.
 *
 *
 * This file is part of the Assimilation Project.
 *
 * @author Copyright &copy; 2011, 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 *  The Assimilation software is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  The Assimilation software is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
 *
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <projectcommon.h>
#include <framesettypes.h>
#include <frameset.h>
#include <ctype.h>
#include <netgsource.h>
#include <netioudp.h>
#include <netaddr.h>
#include <authlistener.h>
#include <signframe.h>
#include <cryptframe.h>
#include <compressframe.h>
#include <intframe.h>
#include <addrframe.h>
#include <cstringframe.h>
#include <frametypes.h>
#include <nanoprobe.h>
#include <cmalib.h>


#define		TESTPORT	1984

int		expected_dead_count = 1;
gint64		maxpkts  = G_MAXINT64;
gint64		pktcount = 0;
GMainLoop*	loop = NULL;
NetIO*		nettransport;
NetGSource*	netpkt;
NetAddr*	destaddr;
NetAddr*	otheraddr;
NetAddr*	otheraddr2;
NetAddr*	anyaddr;
int		wirepktcount = 0;
int		heartbeatcount = 0;
int		errcount = 0;
int		pcapcount = 0;
gboolean gotnetpkt(Listener*, FrameSet* fs, NetAddr* srcaddr);
void got_heartbeat(HbListener* who);
void got_heartbeat2(HbListener* who);
void check_JSON(FrameSet* fs);

void fakecma_startup(AuthListener*, FrameSet* fs, NetAddr*);
gboolean timeout_agent(gpointer ignored);

ObeyFrameSetTypeMap cmalist [] = {
	{FRAMESETTYPE_STARTUP,		fakecma_startup},
	{0,				NULL},
};
	

ConfigContext*	nanoconfig;

void
check_JSON(FrameSet* fs)
{
	GSList*	fptr;
	int	jsoncount = 0;
	int	errcount = 0;

	g_debug("Frameset type is: %d", fs->fstype);
	for (fptr=fs->framelist; fptr; fptr=fptr->next) {
		Frame*	frame = CASTTOCLASS(Frame, fptr->data);
		CstringFrame*	csf;
		ConfigContext *	config;
		g_debug("Frame type is: %d", frame->type);
		if (frame->type != FRAMETYPE_JSDISCOVER) {
			continue;
		}
		++jsoncount;
		// Ahh!  JSON data.  Let's parse it!
		csf = CASTTOCLASS(CstringFrame, frame);
		config = configcontext_new_JSON_string(csf->baseclass.value);
		if (config == NULL) {
			g_warning("JSON text did not parse correctly [%s]"
			,	(char*)csf->baseclass.value);
			++errcount;
		}else{
			char *	tostr = config->baseclass.toString(config);
			g_message("PARSED JSON: %s", tostr);
			g_free(tostr); tostr = NULL;
			config->baseclass.unref(config); config = NULL;
		}
	}
	g_message("%d JSON strings parsed.  %d errors.", jsoncount, errcount);
}

/// Test routine called when an otherwise-unclaimed NetIO packet is received.
gboolean
gotnetpkt(Listener* l,		///<[in/out] Input GSource
	  FrameSet* fs,		///<[in/out] @ref FrameSet "FrameSet"s received
	  NetAddr* srcaddr	///<[in] Source address of this packet
	  )
{
	(void)l; (void)srcaddr;
	++wirepktcount;
	switch(fs->fstype) {
	case FRAMESETTYPE_HBDEAD:
		g_message("CMA Received dead host notification (type %d) over the 'wire'."
		,	  fs->fstype);
		break;
	case FRAMESETTYPE_SWDISCOVER:
		g_message("CMA Received switch discovery data (type %d) over the 'wire'."
		,	  fs->fstype);
		break;
	case FRAMESETTYPE_JSDISCOVERY:
		g_message("CMA Received JSON discovery data (type %d) over the 'wire'."
		,	  fs->fstype);
		check_JSON(fs);
		break;
	default:
		g_message("CMA Received a FrameSet of type %d over the 'wire'."
		,	  fs->fstype);
	}
	//g_message("DUMPING packet received over 'wire':");
	//frameset_dump(fs);
	//g_message("END of packet received over 'wire':");
	fs->baseclass.unref(&fs->baseclass);
	if (wirepktcount >= maxpkts) {
		g_message("QUITTING NOW!");
		g_main_loop_quit(loop);
		return FALSE;
	}
	return TRUE;
}

/// Called every second during tests
gboolean
timeout_agent(gpointer ignored)
{
	(void)ignored;
	if (nano_hbstats.heartbeat_count > (unsigned)maxpkts) {
		g_message("QUITTING NOW! (heartbeat count)");
		g_main_loop_quit(loop);
		return FALSE;
		
	}
	return TRUE;
}

/// Routine to pretend to be the initial CMA
void
fakecma_startup(AuthListener* auth, FrameSet* ifs, NetAddr* nanoaddr)
{
	FrameSet*	pkt;
	NetGSource*	netpkt = auth->baseclass.transport;
	char *		nanostr = nanoaddr->baseclass.toString(nanoaddr);

	(void)ifs;
	g_message("CMA received startup message from nanoprobe at address %s/%d."
	,	nanostr, nanoaddr->port(nanoaddr));
	g_free(nanostr); nanostr = NULL;
	check_JSON(ifs);

	// Send the configuration data to our new "client"
	pkt = create_setconfig(nanoconfig);
	netpkt->sendaframeset(netpkt, nanoaddr, pkt);
	pkt->baseclass.unref(&pkt->baseclass); pkt = NULL;

	// Now tell them to send/expect heartbeats to various places
	pkt = create_sendexpecthb(auth->baseclass.config,FRAMESETTYPE_SENDEXPECTHB, destaddr, 1);
	netpkt->sendaframeset(netpkt, nanoaddr, pkt);
	pkt->baseclass.unref(&pkt->baseclass); pkt = NULL;

	pkt = create_sendexpecthb(auth->baseclass.config, FRAMESETTYPE_SENDEXPECTHB,otheraddr, 1);
	netpkt->sendaframeset(netpkt, nanoaddr, pkt);
	pkt->baseclass.unref(&pkt->baseclass); pkt = NULL;

	pkt = create_sendexpecthb(auth->baseclass.config, FRAMESETTYPE_SENDEXPECTHB,otheraddr2, 1);
	netpkt->sendaframeset(netpkt, nanoaddr, pkt);
	pkt->baseclass.unref(&pkt->baseclass); pkt = NULL;
}

/**
 * Test program looping and reading LLDP/CDP packets and exercising most of the packet
 * send/receive mechanism and a good bit of nanoprobe and CMA basic infrastructure.
 *
 * It plays both sides of the game - the CMA and the nanoprobe.
 *
 * It leaves most of the work of starting up the nanoprobe code to nano_start_full()
 */
int
main(int argc, char **argv)
{
	const guint8	loopback[] = CONST_IPV6_LOOPBACK;
	const guint8	mcastaddrstring[] = CONST_ASSIM_DEFAULT_V4_MCAST;
	NetAddr*	mcastaddr;
	const guint8	otheradstring[] = {10,10,10,5};
	const guint8	otheradstring2[] = {10,10,10,4};
	const guint8	anyadstring[] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
	guint16		testport = TESTPORT;
	SignFrame*	signature = signframe_new(G_CHECKSUM_SHA256, 0);
	Listener*	otherlistener;
	ConfigContext*	config = configcontext_new(0);
	PacketDecoder*	decoder = nano_packet_decoder();
	AuthListener*	listentonanoprobes;


	g_log_set_fatal_mask (NULL, G_LOG_LEVEL_ERROR|G_LOG_LEVEL_CRITICAL);
	//proj_class_incr_debug(NULL);
	if (argc > 1) {
		maxpkts = atol(argv[1]);
                g_debug("Max packet count is "FMT_64BIT"d", maxpkts);
	}

	if (netio_is_dual_ipv4v6_stack()) {
		g_message("Our OS supports dual ipv4/v6 sockets. Hurray!");
	}else{
		g_warning("Our OS DOES NOT support dual ipv4/v6 sockets - this may not work!!");
	}
	

	config->setframe(config, CONFIGNAME_OUTSIG, &signature->baseclass);

	// Create a network transport object for normal UDP packets
	nettransport = &(netioudp_new(0, config, decoder)->baseclass);
	g_return_val_if_fail(NULL != nettransport, 2);

	// Set up the parameters the 'CMA' is going to send to our 'nanoprobe'
	// in response to their request for configuration data.
	nanoconfig = configcontext_new(0);
	nanoconfig->setint(nanoconfig, CONFIGNAME_HBPORT, testport);
	nanoconfig->setint(nanoconfig, CONFIGNAME_HBTIME, 1000000);
	nanoconfig->setint(nanoconfig, CONFIGNAME_DEADTIME, 3*1000000);
	nanoconfig->setint(nanoconfig, CONFIGNAME_CMAPORT, testport);


	// Construct the NetAddr we'll talk to (i.e., ourselves) and listen from
	destaddr =  netaddr_ipv6_new(loopback, testport);
	g_return_val_if_fail(NULL != destaddr, 3);
	config->setaddr(config, CONFIGNAME_CMAINIT, destaddr);
	nanoconfig->setaddr(nanoconfig, CONFIGNAME_CMAADDR, destaddr);
	nanoconfig->setaddr(nanoconfig, CONFIGNAME_CMAFAIL, destaddr);
	nanoconfig->setaddr(nanoconfig, CONFIGNAME_CMADISCOVER, destaddr);


	// Construct another couple of NetAddrs to talk to and listen from
	// for good measure...
	otheraddr =  netaddr_ipv4_new(otheradstring, testport);
	g_return_val_if_fail(NULL != otheraddr, 4);
	otheraddr2 =  netaddr_ipv4_new(otheradstring2, testport);
	g_return_val_if_fail(NULL != otheraddr2, 4);

	// Construct another NetAddr to bind to (anything)
	anyaddr =  netaddr_ipv6_new(anyadstring, testport);
	g_return_val_if_fail(NULL != destaddr, 5);

	// Bind to ANY address (as noted above)
	g_return_val_if_fail(nettransport->bindaddr(nettransport, anyaddr, FALSE),16);
	//g_return_val_if_fail(nettransport->bindaddr(nettransport, destaddr),16);

	g_message("Joining multicast address.");
	mcastaddr =  netaddr_ipv4_new(mcastaddrstring, testport);
	g_return_val_if_fail(nettransport->mcastjoin(nettransport, mcastaddr, NULL), 17);
	mcastaddr->baseclass.unref(mcastaddr); mcastaddr = NULL;
	g_message("multicast join succeeded.");

	// Connect up our network transport into the g_main_loop paradigm
	// so we get dispatched when packets arrive
	netpkt = netgsource_new(nettransport, NULL, G_PRIORITY_HIGH, FALSE, NULL, 0, NULL);

	// Set up so that we can observe all unclaimed packets
	otherlistener = listener_new(config, 0);
	otherlistener->got_frameset = gotnetpkt;
	netpkt->addListener(netpkt, 0, otherlistener);
	otherlistener->associate(otherlistener,netpkt);

	// Unref the "other" listener - we hold other references to it
	otherlistener->baseclass.unref(otherlistener); otherlistener = NULL;

	// Pretend to be the CMA...
	// Listen for packets from our nanoprobes - scattered throughout space...
	listentonanoprobes = authlistener_new(cmalist, config, 0);
	listentonanoprobes->baseclass.associate(&listentonanoprobes->baseclass, netpkt);

	nano_start_full("netconfig", 900, netpkt, config);

	g_timeout_add_seconds(1, timeout_agent, NULL);
	loop = g_main_loop_new(g_main_context_default(), TRUE);

	/********************************************************************
	 *	Start up the main loop - run our test program...
	 *	(the one pretending to be both the nanoprobe and the CMA)
	 ********************************************************************/
	g_main_loop_run(loop);

	/********************************************************************
	 *	We exited the main loop.  Shut things down.
	 ********************************************************************/

	nano_shutdown(TRUE);	// Tell it to shutdown and print stats
	g_message("Count of 'other' pkts received:\t%d", wirepktcount);

	nettransport->baseclass.unref(nettransport); nettransport = NULL;

	// Main loop is over - shut everything down, free everything...
	g_main_loop_unref(loop); loop=NULL;




	// Unlink misc dispatcher - this should NOT be necessary...
	netpkt->addListener(netpkt, 0, NULL);

	// Dissociate packet actions from the packet source.
	listentonanoprobes->baseclass.dissociate(&listentonanoprobes->baseclass);

	// Unref the AuthListener object
	listentonanoprobes->baseclass.baseclass.unref(listentonanoprobes);
	listentonanoprobes = NULL;

	g_source_unref(CASTTOCLASS(GSource, netpkt));
	// g_main_loop_unref() calls g_source_unref() - so we should not call it directly.
	g_main_context_unref(g_main_context_default());

	// Free signature frame
	signature->baseclass.baseclass.unref(signature); signature = NULL;

	// Free misc addresses
        destaddr-> baseclass.unref(destaddr);
        otheraddr->baseclass.unref(otheraddr);
        otheraddr2->baseclass.unref(otheraddr2);
        anyaddr->baseclass.unref(anyaddr); anyaddr = NULL;

	// Free config object
	config->baseclass.unref(config);
	nanoconfig->baseclass.unref(nanoconfig);

	// At this point - nothing should show up - we should have freed everything
	if (proj_class_live_object_count() > 0) {
		proj_class_dump_live_objects();
		g_warning("Too many objects (%d) alive at end of test.", 
			proj_class_live_object_count());
		++errcount;
	}else{
		g_message("No objects left alive.  Awesome!");
	}
        proj_class_finalize_sys(); // Shut down object system to make valgrind happy :-D
	return(errcount <= 127 ? errcount : 127);
}
