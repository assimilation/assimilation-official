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
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
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

void fakecma_startup(AuthListener*, FrameSet* fs, NetAddr*);
gboolean timeout_agent(gpointer ignored);

ObeyFrameSetTypeMap cmalist [] = {
	{FRAMESETTYPE_STARTUP,		fakecma_startup},
	{0,				NULL},
};
	

FrameSet* create_sendexpecthb(ConfigContext*, NetAddr* addrs, int addrcount);
FrameSet* create_setconfig(ConfigContext * cfg);
ConfigContext*	nanoconfig;

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
		break;
	default:
		g_message("CMA Received a FrameSet of type %d over the 'wire'."
		,	  fs->fstype);
	}
	//g_message("DUMPING packet received over 'wire':");
	//frameset_dump(fs);
	//g_message("END of packet received over 'wire':");
	fs->unref(fs);
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

/**
 * Create a @ref FrameSet to send and expect heartbeats from the same sets of addresses.
 * Keep in mind the entire packet needs to fit in a UDP packet (< 64K).
 * The port, hbtime, deadtime, and warntime parameters apply to all given addresses.
 */
FrameSet*
create_sendexpecthb(ConfigContext* config	///<[in] Provides deadtime, port, etc.
		,   NetAddr* addrs		///<[in/out] Addresses to include
		,   int addrcount)		///<[in] Count of 'addrs' provided
{
	FrameSet* ret = frameset_new(FRAMESETTYPE_SENDEXPECTHB);
	int	count = 0;

	// Put the port in the message (if asked)
	if (config->getint(config, CONFIGNAME_HBPORT) > 0) {
		gint	port = config->getint(config, CONFIGNAME_HBPORT);
		IntFrame * intf = intframe_new(FRAMETYPE_PORTNUM, 2);
		intf->setint(intf, port);
		frameset_append_frame(ret, &intf->baseclass);
		intf->baseclass.baseclass.unref(intf); intf = NULL;
	}
	// Put the heartbeat interval in the message (if asked)
	if (config->getint(config, CONFIGNAME_HBTIME) > 0) {
		gint	hbtime = config->getint(config, CONFIGNAME_HBTIME);
		IntFrame * intf = intframe_new(FRAMETYPE_HBINTERVAL, 4);
		intf->setint(intf, hbtime);
		frameset_append_frame(ret, &intf->baseclass);
		intf->baseclass.baseclass.unref(intf); intf = NULL;
	}
	// Put the heartbeat deadtime in the message (if asked)
	if (config->getint(config, CONFIGNAME_DEADTIME) > 0) {
		gint deadtime = config->getint(config, CONFIGNAME_DEADTIME);
		IntFrame * intf = intframe_new(FRAMETYPE_HBDEADTIME, 4);
		intf->setint(intf, deadtime);
		frameset_append_frame(ret, &intf->baseclass);
		intf->baseclass.baseclass.unref(intf); intf = NULL;
	}
	// Put the heartbeat warntime in the message (if asked)
	if (config->getint(config, CONFIGNAME_WARNTIME) > 0) {
		gint warntime = config->getint(config, CONFIGNAME_WARNTIME);
		IntFrame * intf = intframe_new(FRAMETYPE_HBWARNTIME, 4);
		intf->setint(intf, warntime);
		frameset_append_frame(ret, &intf->baseclass);
		intf->baseclass.baseclass.unref(intf); intf = NULL;
	}

	// Put all the addresses we were given in the message.
	for (count=0; count < addrcount; ++count) {
		AddrFrame* hbaddr = addrframe_new(FRAMETYPE_IPADDR, 0);
		hbaddr->setnetaddr(hbaddr, &addrs[count]);
		frameset_append_frame(ret, &hbaddr->baseclass);
		hbaddr->baseclass.baseclass.unref(hbaddr); hbaddr = NULL;
	}
	return  ret;
}

/// Routine to pretend to be the initial CMA
void
fakecma_startup(AuthListener* auth, FrameSet* ifs, NetAddr* nanoaddr)
{
	FrameSet*	pkt;
	NetGSource*	netpkt = auth->baseclass.transport;
	char *		nanostr = nanoaddr->baseclass.toString(nanoaddr);

	(void)ifs;
	g_message("CMA received startup message from nanoprobe at address %s/%d!!"
	,	nanostr, nanoaddr->port(nanoaddr));
	g_free(nanostr); nanostr = NULL;

	// Send the configuration data to our new "client"
	pkt = create_setconfig(nanoconfig);
	netpkt->sendaframeset(netpkt, nanoaddr, pkt);
	pkt->unref(pkt); pkt = NULL;

	// Now tell them to send/expect heartbeats to various places
	pkt = create_sendexpecthb(auth->baseclass.config, destaddr, 1);
	netpkt->sendaframeset(netpkt, nanoaddr, pkt);
	pkt->unref(pkt); pkt = NULL;

	pkt = create_sendexpecthb(auth->baseclass.config, otheraddr, 1);
	netpkt->sendaframeset(netpkt, nanoaddr, pkt);
	pkt->unref(pkt); pkt = NULL;

	pkt = create_sendexpecthb(auth->baseclass.config, otheraddr2, 1);
	netpkt->sendaframeset(netpkt, nanoaddr, pkt);
	pkt->unref(pkt); pkt = NULL;
}

/// Create a FRAMESETTYPE_SETCONFIG @ref FrameSet.
/// We create it from a ConfigContext containing <i>only</i> values we want to go into
/// the SETCONFIG message.  We ignore frames in the ConfigContext (shouldn't be any).
/// We are effectively a "friend" function to the ConfigContext object - either that
/// or we cheated in order to iterate through its hash tables ;-)
FrameSet*
create_setconfig(ConfigContext * cfg)
{
	FrameSet*	fs = frameset_new(FRAMESETTYPE_SETCONFIG);
	GHashTableIter	iter;
	gpointer	key;
	gpointer	data;

	// First we go through the integer values (if any)
	// Next we go through the string values (if any)
	// Lastly we go through the NetAddr values (if any)

	// Integer values
	if (cfg->_intvalues) {
		g_hash_table_iter_init(&iter, cfg->_intvalues);
		while (g_hash_table_iter_next(&iter, &key, &data)) {
			char *		name = key;
			int		value = GPOINTER_TO_INT(data);
			CstringFrame*	n = cstringframe_new(FRAMETYPE_PARAMNAME, 0);
			IntFrame*	v = intframe_new(FRAMETYPE_CINTVAL, 4);
			n->baseclass.setvalue(&n->baseclass, strdup(name), strlen(name)+1
			,		      frame_default_valuefinalize);
			v->setint(v, value);
			frameset_append_frame(fs, &n->baseclass);
			frameset_append_frame(fs, &v->baseclass);
			n->baseclass.baseclass.unref(n);
			v->baseclass.baseclass.unref(v);
		}
	}
	
	// String values
	if (cfg->_strvalues) {
		g_hash_table_iter_init(&iter, cfg->_strvalues);
		while (g_hash_table_iter_next(&iter, &key, &data)) {
			char *		name = key;
			char *		value = data;
			CstringFrame*	n = cstringframe_new(FRAMETYPE_PARAMNAME, 0);
			CstringFrame*	v = cstringframe_new(FRAMETYPE_CSTRINGVAL, 0);
			n->baseclass.setvalue(&n->baseclass, strdup(name), strlen(name)+1
			,		      frame_default_valuefinalize);
			v->baseclass.setvalue(&v->baseclass, strdup(value), strlen(value)+1
			,		      frame_default_valuefinalize);
			frameset_append_frame(fs, &n->baseclass);
			frameset_append_frame(fs, &v->baseclass);
			n->baseclass.baseclass.unref(n);
			v->baseclass.baseclass.unref(v);
		}
	}

	// NetAddr values
	if (cfg->_addrvalues) {
		g_hash_table_iter_init(&iter, cfg->_addrvalues);
		while (g_hash_table_iter_next(&iter, &key, &data)) {
			char *		name = key;
			NetAddr*	value = data;
			CstringFrame*	n = cstringframe_new(FRAMETYPE_PARAMNAME, 0);
			AddrFrame*	v = addrframe_new(FRAMETYPE_IPADDR, 0);
			n->baseclass.setvalue(&n->baseclass, strdup(name), strlen(name)+1
			,		      frame_default_valuefinalize);
			frameset_append_frame(fs, &n->baseclass);
			// The port doesn't come through when going across the wire
			if (value->port(value) != 0) {
				IntFrame*	p = intframe_new(FRAMETYPE_PORTNUM, 4);
				p->setint(p, value->port(value));
				frameset_append_frame(fs, &p->baseclass);
				p->baseclass.baseclass.unref(p);
			}
			v->setnetaddr(v, value);
			frameset_append_frame(fs, &v->baseclass);
			n->baseclass.baseclass.unref(n);
			v->baseclass.baseclass.unref(v);
		}
	}

	return fs;
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
	if (argc > 1) {
		maxpkts = atol(argv[1]);
                g_debug("Max packet count is %lld", maxpkts);
	}

	if (netio_is_dual_ipv4v6_stack()) {
		g_message("Our OS supports dual ipv4/v6 sockets. Hurray!");
	}else{
		g_warning("Our OS DOES NOT support dual ipv4/v6 sockets - this may not work!!");
	}
	

	config->setframe(config, CONFIGNAME_OUTSIG, &signature->baseclass);

	// Set up the parameters the 'CMA' is going to send to our 'nanoprobe'
	// in response to their request for configuration data.
	nanoconfig = configcontext_new(0);
	nanoconfig->setint(nanoconfig, CONFIGNAME_HBPORT, testport);
	nanoconfig->setint(nanoconfig, CONFIGNAME_HBTIME, 1000000);
	nanoconfig->setint(nanoconfig, CONFIGNAME_DEADTIME, 3*1000000);
	nanoconfig->setint(nanoconfig, CONFIGNAME_CMAPORT, testport);

	// Create a network transport object for normal UDP packets
	nettransport = &(netioudp_new(0, config, decoder)->baseclass);
	g_return_val_if_fail(NULL != nettransport, 2);


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
	g_return_val_if_fail(nettransport->bindaddr(nettransport, anyaddr),16);
	//g_return_val_if_fail(nettransport->bindaddr(nettransport, destaddr),16);

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

	nano_start_full("/home/alanr/monitor/src/discovery_agents/netconfig"
	,	900, netpkt, config);

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

	nettransport->finalize(nettransport); nettransport = NULL;

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
        anyaddr->  baseclass.unref(anyaddr);

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
        proj_class_finalize_sys(); /// Shut down object system to make valgrind happy :-D
	return(errcount <= 127 ? errcount : 127);
}
