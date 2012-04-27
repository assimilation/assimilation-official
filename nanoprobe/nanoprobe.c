/**
 * @file 
 * @brief nanoprobe main program.
 * Starts up a nanoprobe and does nanoprobie things - deferring most of the work to others.
 *
 *
 *
 * @author &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 *
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
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

#define	DEFAULT_PORT	1984

gint64		pktcount = 0;
GMainLoop*	loop = NULL;
NetIO*		nettransport;
NetGSource*	netpkt;
NetAddr*	destaddr;
NetAddr*	localbindaddr;
int		heartbeatcount = 0;
int		errcount = 0;
int		pcapcount = 0;
int		wirepktcount = 0;

//		Signals...
gboolean	sigint	= FALSE;
gboolean	sigterm = FALSE;
gboolean	sighup	= FALSE;
gboolean	sigusr1 = FALSE;
gboolean	sigusr2 = FALSE;

const char *	procname = "nanoprobe";

void catch_a_signal(int signum);
gboolean check_for_signals(gpointer ignored);
gboolean gotnetpkt(Listener*, FrameSet* fs, NetAddr* srcaddr);


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
		case FRAMESETTYPE_HBBACKALIVE:
			g_message("Received back alive notification (type %d) over the 'wire'."
			,	  fs->fstype);
			break;

		default:
			if (fs->fstype >= FRAMESETTYPE_STARTUP && fs->fstype < FRAMESETTYPE_SENDHB) {
				g_message("Received a FrameSet of type %d over the 'wire' (OOPS!)."
				,	  fs->fstype);
			}else{
				g_message("Received a FrameSet of type %d over the 'wire'."
				,	  fs->fstype);
			}
	}
	//g_message("DUMPING packet received over 'wire':");
	//frameset_dump(fs);
	//g_message("END of packet received over 'wire':");
	fs->unref(fs);
	return TRUE;
}

/// Signal reception function - signals stop by here...
void
catch_a_signal(int signum)
{
	switch(signum) {
		case SIGINT:
			sigint = TRUE;
			break;
		case SIGTERM:
			sigterm = TRUE;
			break;
		case SIGHUP:
			sighup = TRUE;
			break;
		case SIGUSR1:
			proj_class_incr_debug(NULL);
			sigusr1 = TRUE;
			break;
		case SIGUSR2:
			proj_class_decr_debug(NULL);
			sigusr2 = TRUE;
			break;
	}
}

/// Check for signals periodically
gboolean
check_for_signals(gpointer ignored)
{
	(void)ignored;
	if (sigterm || sigint) {
		g_message("%s: exiting on %s.", procname, (sigterm ? "SIGTERM" : "SIGINT"));
		g_main_loop_quit(loop);
		return FALSE;
	}
	if (sigusr1) {
		sigusr1 = FALSE;
	}
	if (sigusr2) {
		sigusr2 = FALSE;
	}
	return TRUE;
}

/**
 * Nanoprobe main program.
 *
 * It leaves most of the work of starting up the nanoprobe code to nano_start_full()
 */
int
main(int argc, char **argv)
{
	//const guint8		loopback[] = CONST_IPV6_LOOPBACK;
	//const guint8		defaultCMAaddr[] = CONST_ASSIM_DEFAULT_V4_MCAST;
	const guint8		defaultCMAaddr[] = {10,10,10,4};
	//const guint8		anyv6addrstring[] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
	const guint8		localv4address[] = {10,10,10,5};
	guint16			testport = DEFAULT_PORT;
	SignFrame*		signature = signframe_new(G_CHECKSUM_SHA256, 0);
	Listener*		otherlistener;
	ConfigContext*		config = configcontext_new(0);
	PacketDecoder*		decoder = nano_packet_decoder();
	struct sigaction	sigact;

	/// @todo initialize from a setup file - initial IP address, port, debug - anything else?


	(void)argc;
	(void)argv;
	g_log_set_fatal_mask (NULL, G_LOG_LEVEL_ERROR|G_LOG_LEVEL_CRITICAL);

	if (!netio_is_dual_ipv4v6_stack()) {
		g_warning("This OS DOES NOT support dual ipv4/v6 sockets - this may not work!!");
	}
	memset(&sigact, 0,  sizeof(sigact));
	sigact.sa_handler = catch_a_signal;
	sigaction(SIGTERM, &sigact, NULL);
	sigaction(SIGINT,  &sigact, NULL); // Need to check to see if it's already blocked.
	sigaction(SIGUSR1, &sigact, NULL);
	sigaction(SIGUSR2, &sigact, NULL);

	config->setframe(config, CONFIGNAME_OUTSIG, &signature->baseclass);

	// Create a network transport object for normal UDP packets
	nettransport = &(netioudp_new(0, config, decoder)->baseclass);
	g_return_val_if_fail(NULL != nettransport, 2);


	// Construct the NetAddr we'll talk to (it will default to be mcast when we get that working)
	destaddr =  netaddr_ipv4_new(defaultCMAaddr, testport);
	g_return_val_if_fail(NULL != destaddr, 3);
	config->setaddr(config, CONFIGNAME_CMAINIT, destaddr);
	if (destaddr->ismcast(destaddr)) {
		nettransport->mcastjoin(nettransport, destaddr, NULL);	// Broken!
	}

	// Construct a NetAddr to bind to (listen from) (normally ANY address)
	//localbindaddr =  netaddr_ipv6_new(anyv6addrstring, testport);
	localbindaddr =  netaddr_ipv4_new(localv4address, testport);
	g_return_val_if_fail(NULL != destaddr, 5);

	// Bind to ANY address (as noted above)
	g_return_val_if_fail(nettransport->bindaddr(nettransport, localbindaddr),16);
        localbindaddr->  baseclass.unref(localbindaddr);
	localbindaddr = NULL;
	//g_return_val_if_fail(nettransport->bindaddr(nettransport, destaddr),16);

	// Connect up our network transport into the g_main_loop paradigm
	// so we get dispatched when packets arrive
	netpkt = netgsource_new(nettransport, NULL, G_PRIORITY_HIGH, FALSE, NULL, 0, NULL);

	// Observe all unclaimed packets
	otherlistener = listener_new(config, 0);
	otherlistener->got_frameset = gotnetpkt;
	netpkt->addListener(netpkt, 0, otherlistener);
	otherlistener->associate(otherlistener,netpkt);
	g_timeout_add_seconds(1, check_for_signals, NULL);

	// Unref the "other" listener - netpkt et al holds references to it
	otherlistener->baseclass.unref(otherlistener); otherlistener = NULL;

	// Free signature frame
	signature->baseclass.baseclass.unref(signature); signature = NULL;

	// Free misc addresses
        destaddr-> baseclass.unref(destaddr); destaddr = NULL;

	nano_start_full("/home/alanr/monitor/src/discovery_agents/netconfig"
	,	900, netpkt, config);

	// Free config object
	config->baseclass.unref(config); config = NULL;

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

	g_source_unref(&netpkt->baseclass); netpkt = NULL;

	// This guy needs to be last - or nearly so...
	g_main_context_unref(g_main_context_default());

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
