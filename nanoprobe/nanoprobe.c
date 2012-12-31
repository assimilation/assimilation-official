/**
 * @file 
 * @brief nanoprobe main program.
 * Starts up a nanoprobe and does nanoprobie things - deferring most of the work to others.
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
 */

#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <signal.h>
#include <errno.h>
#include <getopt.h>
#include <sys/utsname.h>
#include <projectcommon.h>
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
#include <misc.h>
#include <nanoprobe.h>

DEBUGDECLARATIONS

#ifdef WIN32
#	undef HAS_FORK
#else
#	define	HAS_FORK
#endif

gint64		pktcount = 0;
GMainLoop*	mainloop = NULL;
NetIO*		nettransport;
NetGSource*	netpkt;
NetAddr*	destaddr;
NetAddr*	localbindaddr;
int		heartbeatcount = 0;
int		errcount = 0;
int		pcapcount = 0;
int		wirepktcount = 0;

guint		idle_shutdown_event = 0;
guint		shutdown_timer = 0;

//		Signals...
gboolean	sigint	= FALSE;
gboolean	sigterm = FALSE;
gboolean	sighup	= FALSE;
gboolean	sigusr1 = FALSE;
gboolean	sigusr2 = FALSE;

const char *	procname = "nanoprobe";

FSTATIC void catch_a_signal(int signum);
FSTATIC gboolean check_for_signals(gpointer ignored);
FSTATIC gboolean gotnetpkt(Listener*, FrameSet* fs, NetAddr* srcaddr);
FSTATIC void usage(const char * cmdname);
FSTATIC gboolean final_shutdown(gpointer unused);
FSTATIC gboolean shutdown_when_outdone(gpointer unused);


/// Test routine called when an otherwise-unclaimed NetIO packet is received.
FSTATIC gboolean
gotnetpkt(Listener* l,		///<[in/out] Input GSource
	  FrameSet* fs,		///<[in/out] @ref FrameSet "FrameSet"s received
	  NetAddr* srcaddr	///<[in] Source address of this packet
	  )
{
	(void)l; (void)srcaddr;
	++wirepktcount;
	switch(fs->fstype) {
		case FRAMESETTYPE_HBBACKALIVE:
			g_message("%s.%d: Received back alive notification (type %d) over the 'wire'."
			,	  __FUNCTION__, __LINE__, fs->fstype);
			break;

		default:
			if (fs->fstype >= FRAMESETTYPE_STARTUP && fs->fstype < FRAMESETTYPE_SENDHB) {
				g_warning("%s.%d: Received a FrameSet of type %d over the 'wire' (OOPS!)."
				,	  __FUNCTION__, __LINE__, fs->fstype);
			}else{
				DEBUGMSG("%s.%d: Received a FrameSet of type %d over the 'wire'."
				,	  __FUNCTION__, __LINE__, fs->fstype);
			}
	}
	DUMP3(__FUNCTION__, &srcaddr->baseclass, " Was address received from.");
	DUMP3(__FUNCTION__, &fs->baseclass, " Was the frameset received.");
	UNREF(fs);
	return TRUE;
}

/// Signal reception function - signals stop by here...
FSTATIC void
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

// If our output is all ACKed, then go ahead and shutdown
FSTATIC gboolean
shutdown_when_outdone(gpointer unused)
{
	(void)unused;
	// Wait for the CMA to ACK our shutdown message - if we've heard anything from them...
	if (!nano_connected || !nettransport->outputpending(nettransport)){
		g_source_remove(shutdown_timer);
		g_main_quit(mainloop);
		return FALSE;
	}
	return TRUE;
}
// Final Shutdown -- a contingency timer to make sure we eventually shut down
FSTATIC gboolean
final_shutdown(gpointer unused)
{
	(void)unused;
	if (idle_shutdown_event) {
		g_source_remove(idle_shutdown_event);
	}
	g_main_quit(mainloop);
	return FALSE;
}

/// Check for signals periodically
FSTATIC gboolean
check_for_signals(gpointer ignored)
{
	(void)ignored;
	if (sigterm || sigint) {
		g_message("%s: exiting on %s.", procname, (sigterm ? "SIGTERM" : "SIGINT"));
		if (nano_connected) {
			struct utsname	un;	// System name, etc.
			uname(&un);
			nanoprobe_report_upstream(FRAMESETTYPE_HBSHUTDOWN, NULL, un.nodename, 0);
			// Wait for an ACK before shutting down...
			idle_shutdown_event = g_idle_add(shutdown_when_outdone, NULL);
			// But just in case... Shut down in 10 seconds anyway...
			shutdown_timer = g_timeout_add_seconds(10, final_shutdown, NULL);
		}else{
			g_warning("%s: Never connected to CMA - no notification sent.", procname);
			++errcount;  // Trigger non-zero exit code...
			return final_shutdown(NULL);
		}
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

FSTATIC void
usage(const char * cmdname)
{
	fprintf(stderr, "usage: %s [arguments...]\n", cmdname);
	fprintf(stderr, "Legal arguments are:\n");
	fprintf(stderr, "\t-c --cmaaddr address:port-of-CMA\n");
	fprintf(stderr, "\t-b --bind address:port-to-listen-on-locally\n");
#ifdef HAS_FORK
	fprintf(stderr, "\t-f --foreground stay in foreground.\n");
#endif
	fprintf(stderr, "\t-d --debug (increment debug level)\n");
}

/**
 * Nanoprobe main program.
 *
 * It leaves most of the work of starting up the nanoprobe code to nano_start_full()
 */
int
main(int argc, char **argv)
{
	const char		defaultCMAaddr[] = CMAADDR;
	const char		defaultlocaladdress [] = NANOLISTENADDR;
	SignFrame*		signature = signframe_new(G_CHECKSUM_SHA256, 0);
	Listener*		otherlistener;
	ConfigContext*		config = configcontext_new(0);
	PacketDecoder*		decoder = nano_packet_decoder();
	struct sigaction	sigact;
	const char *		cmaaddr = defaultCMAaddr;
	const char *		localaddr = defaultlocaladdress;
	gboolean		anyportpermitted = TRUE;
	int			c;
	int			mcast_ttl = 31;
	gboolean		stay_in_foreground = FALSE;
	static struct option 	long_options[] = {
		{"cmaaddr",	required_argument,	0,	'c'},
		{"bind",	required_argument,	0,	'b'},
		{"ttl",		required_argument,	0,	't'},
		{"debug",	no_argument,		0,	'd'},
#ifdef HAS_FORK
		{"foreground",	no_argument,		0,	'f'},
#endif
		{NULL, 		no_argument,		0,	0}
	};
	gboolean		moreopts = TRUE;
	gboolean		optionerror = FALSE;
	int			option_index = 0;
	gboolean		bindret;
	/// @todo initialize from a setup file - initial IP address:port, debug - anything else?


	BINDDEBUG(NanoprobeMain);
	while (moreopts) {
		c = getopt_long(argc, argv, "b:c:dfl:t:", long_options, &option_index);
		switch(c) {
			case -1:
				moreopts = FALSE;
				break;
			case  0:	// It already set a flag
				break;

			case 'b':
				localaddr = optarg;
				anyportpermitted = FALSE;
				break;

			case 'c':
				cmaaddr = optarg;
				break;

			case 'd':
				proj_class_incr_debug(NULL);
				break;

#ifdef HAS_FORK
			case 'f':
				stay_in_foreground = TRUE;
				break;
#endif

			case 't':
				mcast_ttl = atoi(optarg);
				break;

			case '?':	// Already printed an error message
				optionerror = TRUE;
				break;

			default:
				g_error("OOPS! Default case in getopt_long(%c)", c);
				optionerror = TRUE;
				break;
		}
	}

	if (optionerror) {
		usage(argv[0]);
		exit(1);
	}


	daemonize_me(stay_in_foreground, "/");
	assimilation_openlog(argv[0]);

	if (!netio_is_dual_ipv4v6_stack()) {
		g_warning("This OS DOES NOT support dual ipv4/v6 sockets - this may not work!!");
	}
	memset(&sigact, 0,  sizeof(sigact));
	sigact.sa_handler = catch_a_signal;
	sigaction(SIGTERM, &sigact, NULL);
	if (stay_in_foreground) {
		struct sigaction	oldact;
		sigaction(SIGINT,  &sigact, &oldact); // Need to check to see if it's already blocked.
		if (oldact.sa_handler == SIG_IGN) {
			// OOPS - put it back like it was
			sigaction(SIGINT, &oldact, NULL);
		}
	}else{
		// Always ignore SIGINT when in the background
		struct sigaction	ignoreme;
		memset(&ignoreme, 0,  sizeof(ignoreme));
		ignoreme.sa_handler = SIG_IGN;
		sigaction(SIGINT, &ignoreme, NULL);
	}
	sigaction(SIGUSR1, &sigact, NULL);
	sigaction(SIGUSR2, &sigact, NULL);

	config->setframe(config, CONFIGNAME_OUTSIG, &signature->baseclass);

	// Create a network transport object for normal UDP packets
	nettransport = &(reliableudp_new(0, config, decoder, 0)->baseclass.baseclass);
	g_return_val_if_fail(NULL != nettransport, 2);


	// Construct the NetAddr we'll talk to (it defaults to a mcast address nowadays)
	destaddr =  netaddr_string_new(cmaaddr);
	g_info("CMA address: %s", cmaaddr);
	if (destaddr->ismcast(destaddr)) {
		if (!nettransport->setmcast_ttl(nettransport, mcast_ttl)) {
			g_warning("Unable to set multicast TTL to %d [%s %d]", mcast_ttl
			,	g_strerror(errno), errno);
		}
	}

	g_return_val_if_fail(NULL != destaddr, 3);
	g_return_val_if_fail(destaddr->port(destaddr) != 0, 4);
	config->setaddr(config, CONFIGNAME_CMAINIT, destaddr);


	// Construct a NetAddr to bind to (listen from) (normally ANY address)
	localbindaddr =  netaddr_string_new(localaddr);
	g_return_val_if_fail(NULL != localbindaddr, 5);


	// Bind to the requested address (defaults to ANY as noted above)
	bindret = nettransport->bindaddr(nettransport, localbindaddr, anyportpermitted);
	UNREF(localbindaddr);
	if (!bindret) {
		// OOPS! Address:Port already busy...
		if (anyportpermitted) {
			guint8 anyaddr[16] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
			localbindaddr =  netaddr_ipv6_new(anyaddr, 0);
			g_return_val_if_fail(NULL != localbindaddr, 5);
			bindret = nettransport->bindaddr(nettransport, localbindaddr, FALSE);
			UNREF(localbindaddr);
			localbindaddr = NULL;
			g_return_val_if_fail(bindret, 6);
		}else{
			g_warning("Cannot bind to local address [%s] and cannot use any free port.", localaddr);
			return(5);
		}
	}
	{
		NetAddr*	boundaddr = nettransport->boundaddr(nettransport);
		if (boundaddr) {
			char *		boundstr = boundaddr->baseclass.toString(&boundaddr->baseclass);
			g_info("Local address: %s", boundstr);
			g_free(boundstr);
			UNREF(boundaddr);
		}else{
			g_warning("Unable to determine local address!");
		}
	}

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
	UNREF(otherlistener);

	// Free signature frame
	UNREF2(signature);

	// Free misc addresses
	UNREF(destaddr);

	nano_start_full("netconfig", 900, netpkt, config);

	// Free config object
	UNREF(config);

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
	g_info("%-35s %8d", "Count of 'other' pkts received:", wirepktcount);

	UNREF(nettransport);

	// This two calls need to be last - and in this order...
	// (I wish the documentation on this stuff was clearer... Sigh...)
	//g_main_context_unref(g_main_context_default());
	g_main_loop_unref(mainloop);
	g_source_unref(&netpkt->baseclass);	// Not sure why this is needed...
	g_source_destroy(&netpkt->baseclass);	// Not sure why this is needed...
	mainloop = NULL; netpkt = NULL;


	// At this point - nothing should show up - we should have freed everything
	if (proj_class_live_object_count() > 0) {
		proj_class_dump_live_objects();
		g_warning("Too many objects (%d) alive at end of test.", 
			proj_class_live_object_count());
		++errcount;
	}else{
		g_info("No objects left alive.  Awesome!");
	}
        proj_class_finalize_sys(); /// Shut down object system to make valgrind happy :-D
	return(errcount <= 127 ? errcount : 127);
}
