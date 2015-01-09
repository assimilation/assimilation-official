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

#include <projectcommon.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#ifdef HAVE_MCHECK_H
#	include <mcheck.h>
#endif
#include <framesettypes.h>
#include <frameset.h>
#include <ctype.h>
#include <netgsource.h>
#include <reliableudp.h>
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
#include <resourcecmd.h>
#include <cmalib.h>
#include <cryptcurve25519.h>


#define		TESTPORT	1984
#define		CRYPTO_KEYID	CMA_KEY_PREFIX "999999b"

#ifdef WIN32
WINIMPORT int errcount;
WINIMPORT NanoHbStats nano_hbstats;
WINIMPORT GMainLoop*		mainloop;
#else
extern int errcount;
extern NanoHbStats nano_hbstats;
GMainLoop*		mainloop;
#endif

int		expected_dead_count = 1;
gint64		maxpkts  = G_MAXINT64;
gint64		pktcount = 0;
GMainLoop*	mainloop;
NetIO*		nettransport;
NetGSource*	netpkt;
NetAddr*	destaddr;
NetAddr*	otheraddr;
NetAddr*	otheraddr2;
NetAddr*	anyaddr;
int		wirepktcount = 0;

gboolean gotnetpkt(Listener*, FrameSet* fs, NetAddr* srcaddr);
void got_heartbeat(HbListener* who);
void got_heartbeat2(HbListener* who);
void check_JSON(FrameSet* fs);
FSTATIC gboolean test_cma_authentication(const FrameSet*fs);

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

	//g_debug("Frameset type is: %d", fs->fstype);
	for (fptr=fs->framelist; fptr; fptr=fptr->next) {
		Frame*	frame = CASTTOCLASS(Frame, fptr->data);
		CstringFrame*	csf;
		ConfigContext *	config;
		//g_debug("Frame type is: %d", frame->type);
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
			UNREF(config);
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
	default:{
			char *	fsstr = fs->baseclass.toString(&fs->baseclass);
			g_message("CMA Received a FrameSet of type %d [%s] over the 'wire'."
			,	  fs->fstype, fsstr);
			FREE(fsstr); fsstr = NULL;
		}
	}
	
	l->transport->_netio->ackmessage(l->transport->_netio, srcaddr, fs);
	UNREF(fs);
	if (wirepktcount >= maxpkts) {
		g_message("QUITTING NOW - wirepktcount!");
		nano_initiate_shutdown();
		return FALSE;
	}
	return TRUE;
}

/// Called every second during tests
gboolean
timeout_agent(gpointer ignored)
{
	ReliableUDP*	io = CASTTOCLASS(ReliableUDP, nettransport);

	(void)ignored;
	if (nano_hbstats.heartbeat_count > (unsigned)maxpkts) {
		g_message("QUITTING NOW! (heartbeat count)");
		io->_protocol->closeall(io->_protocol);
		nano_initiate_shutdown();
		return FALSE;
	}
	return TRUE;
}

#define	OCFCLASS	"\"" REQCLASSNAMEFIELD		"\": \"ocf\""
#define	HBPROVIDER	"\"" REQPROVIDERNAMEFIELD	"\": \"heartbeat\""
#define	DUMMYTYPE	"\"" CONFIGNAME_TYPE		"\": \"Dummy\""
#define	STARTOP		"\"" REQOPERATIONNAMEFIELD	"\": \"start\""
#define	STOPOP		"\"" REQOPERATIONNAMEFIELD	"\": \"stop\""
#define	MONITOROP	"\"" REQOPERATIONNAMEFIELD	"\": \"monitor\""
#define	METADATAOP	"\"" REQOPERATIONNAMEFIELD	"\": \"meta-data\""
#define	RESOURCENAME	"\"" CONFIGNAME_INSTANCE	"\": \"DummyTestGTest01\""
#define	NULLPARAMS	"\"" REQENVIRONNAMEFIELD	"\": {}"
#define	C ","
#define REQID(id)	"\"" REQIDENTIFIERNAMEFIELD	"\": " #id
#define REPEAT(repeat)	"\"" REQREPEATNAMEFIELD	"\": " #repeat
#define INITDELAY(delay)	"\"" CONFIGNAME_INITDELAY	"\": " #delay
#define	COMMREQUEST	OCFCLASS C HBPROVIDER C DUMMYTYPE C RESOURCENAME C NULLPARAMS
#define REQUEST(type,id, repeat,delay)	\
	"{" COMMREQUEST C type C REQID(id) C REPEAT(repeat) C INITDELAY(delay)"}"
#define START REQUEST(STARTOP,		1, 0, 0)	// One shot - no delay
#define MONITOR REQUEST(MONITOROP,	2, 0, 0)	// Repeat every second - no delay
#define STOP REQUEST(STOPOP,		3, 0, 5)	// No repeat - 5 second delay

/// Routine to pretend to be the initial CMA
void
fakecma_startup(AuthListener* auth, FrameSet* ifs, NetAddr* nanoaddr)
{
	FrameSet*	pkt;
	NetGSource*	netpkt = auth->baseclass.transport;
	char *		nanostr = nanoaddr->baseclass.toString(nanoaddr);
	GSList*		thisgsf;
	const char *	keyid = NULL;

	(void)ifs;
	g_message("CMA received startup message from nanoprobe at address %s/%d."
	,	nanostr, nanoaddr->port(nanoaddr));
	g_free(nanostr); nanostr = NULL;
	check_JSON(ifs);

	netpkt->_netio->addalias(netpkt->_netio, nanoaddr, destaddr);
	
	// Set up our crypto...
	cryptframe_set_dest_public_key_id(nanoaddr, cryptframe_get_signing_key_id());
	cryptframe_set_dest_public_key_id(destaddr, cryptframe_get_signing_key_id());
	cryptframe_associate_identity(CMA_IDENTITY_NAME, cryptframe_get_signing_key_id());
	cryptframe_set_encryption_method(cryptcurve25519_new_generic);
	for (thisgsf = ifs->framelist; thisgsf; thisgsf=thisgsf->next) {
		Frame*	thisframe = CASTTOCLASS(Frame, thisgsf->data);
		if (thisframe->type == FRAMETYPE_KEYID) {
			CstringFrame* csf = CASTTOCLASS(CstringFrame, thisframe);
			keyid = (const char *)csf->baseclass.value;
		}else if (keyid && thisframe->type == FRAMETYPE_PUBKEYCURVE25519) {
			cryptcurve25519_save_public_key(keyid, thisframe->value
			,	thisframe->length);
		}
	}

	// Send the configuration data to our new "client"
	pkt = create_setconfig(nanoconfig);
	netpkt->_netio->sendareliablefs(netpkt->_netio, nanoaddr, DEFAULT_FSP_QID, pkt);
	UNREF(pkt);

	// Now tell them to send/expect heartbeats to various places
	pkt = create_sendexpecthb(auth->baseclass.config, FRAMESETTYPE_SENDEXPECTHB, destaddr, 1);
	netpkt->_netio->sendareliablefs(netpkt->_netio, nanoaddr, DEFAULT_FSP_QID, pkt);
	UNREF(pkt);

	{
		const char *	json[] = { START, MONITOR, STOP};
		unsigned	j;
		// Create a frameset for a few resource operations
		pkt = frameset_new(FRAMESETTYPE_DORSCOP);
		for (j=0; j < DIMOF(json); j++) {
			CstringFrame*	csf = cstringframe_new(FRAMETYPE_RSCJSON,0);
			csf->baseclass.setvalue(&csf->baseclass, g_strdup(json[j])
			,	strlen(json[j])+1, g_free);
			frameset_append_frame(pkt, &csf->baseclass);
			UNREF2(csf);
		}
		netpkt->_netio->sendareliablefs(netpkt->_netio, nanoaddr, DEFAULT_FSP_QID, pkt);
		UNREF(pkt);
	}
}

FSTATIC gboolean
test_cma_authentication(const FrameSet*fs)
{
	gpointer	maybecrypt = g_slist_nth_data(fs->framelist, 1);
	Frame*		mightbecrypt;
	/// For our purposes, we don't much care how it's encrypted...
	g_return_val_if_fail(maybecrypt != NULL, FALSE);
	mightbecrypt = CASTTOCLASS(Frame, maybecrypt);
	if (mightbecrypt->type != FRAMETYPE_CRYPTCURVE25519) {
		DUMP("test_cma_authentication: ", &fs->baseclass, " was BAD");
		return FALSE;
	}
	return TRUE;
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
	//const guint8	mcastaddrstring[] = CONST_ASSIM_DEFAULT_V4_MCAST;
	//NetAddr*	mcastaddr;
	const guint8	otheradstring[] = {127,0,0,1};
	const guint8	otheradstring2[] = {10,10,10,4};
	const guint8	anyadstring[] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
	guint16		testport = TESTPORT;
	SignFrame*	signature = signframe_glib_new(G_CHECKSUM_SHA256, 0);
	Listener*	otherlistener;
	ConfigContext*	config = configcontext_new(0);
	PacketDecoder*	decoder = nano_packet_decoder();
	AuthListener*	listentonanoprobes;

#if 0
#	ifdef HAVE_MCHECK_PEDANTIC
	g_assert(mcheck_pedantic(NULL) == 0);
#	else
#		ifdef HAVE_MCHECK
	g_assert(mcheck(NULL) == 0);
#		endif
#	endif
#endif
	g_setenv("G_MESSAGES_DEBUG", "all", TRUE);
#if 0
	proj_class_incr_debug(NULL);
	proj_class_incr_debug(NULL);
	proj_class_incr_debug(NULL);
	proj_class_incr_debug(NULL);
#endif
	g_log_set_fatal_mask(NULL, G_LOG_LEVEL_ERROR);

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
	nettransport = &(reliableudp_new(0, config, decoder, 0)->baseclass.baseclass);
	g_return_val_if_fail(NULL != nettransport, 2);

	// Set up the parameters the 'CMA' is going to send to our 'nanoprobe'
	// in response to their request for configuration data.
	nanoconfig = configcontext_new(0);
	nanoconfig->setint(nanoconfig, CONFIGNAME_INTERVAL, 1);
	nanoconfig->setint(nanoconfig, CONFIGNAME_TIMEOUT, 3);
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

	g_message("NOT Joining multicast address.");
#if 0
	// We can't do this because of encryption and we will likely screw up
	// others on our network even if that weren't a problem...
	mcastaddr =  netaddr_ipv4_new(mcastaddrstring, testport);
	g_return_val_if_fail(nettransport->mcastjoin(nettransport, mcastaddr, NULL), 17);
	UNREF(mcastaddr);
	g_message("multicast join succeeded.");
#endif

	// Connect up our network transport into the g_main_loop paradigm
	// so we get dispatched when packets arrive
	netpkt = netgsource_new(nettransport, NULL, G_PRIORITY_HIGH, FALSE, NULL, 0, NULL);

	// Set up so that we can observe all unclaimed packets
	otherlistener = listener_new(config, 0);
	otherlistener->got_frameset = gotnetpkt;
	netpkt->addListener(netpkt, 0, otherlistener);
	otherlistener->associate(otherlistener,netpkt);

	// Unref the "other" listener - we hold other references to it
	UNREF(otherlistener);

	// Pretend to be the CMA...
	// Listen for packets from our nanoprobes - scattered throughout space...
	listentonanoprobes = authlistener_new(0, cmalist, config, TRUE, NULL);
	listentonanoprobes->baseclass.associate(&listentonanoprobes->baseclass, netpkt);

	nano_start_full("netconfig", 900, netpkt, config, test_cma_authentication);

	g_timeout_add_seconds(1, timeout_agent, NULL);
	mainloop = g_main_loop_new(g_main_context_default(), TRUE);

	/********************************************************************
	 *	Start up the main loop - run our test program...
	 *	(the one pretending to be both the nanoprobe and the CMA)
	 ********************************************************************/
	g_main_loop_run(mainloop);

	/********************************************************************
	 *	We exited the main loop.  Shut things down.
	 ********************************************************************/

	nano_shutdown(TRUE);	// Tell it to shutdown and print stats
	g_message("Count of 'other' pkts received:\t%d", wirepktcount);

	UNREF(nettransport);

	// Main loop is over - shut everything down, free everything...
	g_main_loop_unref(mainloop); mainloop=NULL;


	// Unlink misc dispatcher - this should NOT be necessary...
	netpkt->addListener(netpkt, 0, NULL);

	// Dissociate packet actions from the packet source.
	listentonanoprobes->baseclass.dissociate(&listentonanoprobes->baseclass);

	// Unref the AuthListener object
	UNREF2(listentonanoprobes);

	g_source_destroy(&netpkt->baseclass);
	g_source_unref(&netpkt->baseclass);
	//g_main_context_unref(g_main_context_default());

	// Free signature frame
	UNREF2(signature);

	// Free misc addresses
	UNREF(destaddr);
	UNREF(otheraddr);
	UNREF(otheraddr2);
	UNREF(anyaddr);

	// Free config object
	UNREF(config);
	UNREF(nanoconfig);


	// At this point - nothing should show up - we should have freed everything
	if (proj_class_live_object_count() > 0) {
		g_warning("Too many objects (%d) alive at end of test.", 
			proj_class_live_object_count());
		proj_class_dump_live_objects();
		++errcount;
	}else{
		g_message("No objects left alive.  Awesome!");
	}
        proj_class_finalize_sys(); // Shut down object system to make valgrind happy :-D
	return(errcount <= 127 ? errcount : 127);
}
