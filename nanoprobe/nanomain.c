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

#include <projectcommon.h>
#include <stdlib.h>
#ifdef HAVE_UNISTD_H
#	include <unistd.h>
#endif
#include <string.h>
#include <signal.h>
#include <errno.h>
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

#undef	DEBUGSHUTDOWN
#define	DEBUGSHUTDOWN	1

DEBUGDECLARATIONS

#ifdef WIN32
#define SEP "\\"
#	undef HAS_FORK
WINIMPORT int errcount;
WINIMPORT GMainLoop*		mainloop;
WINEXPORT void		remove_pid_file(const char * pidfile);
WINEXPORT void daemonize_me(gboolean stay_in_foreground, const char * dirtorunin, char* pidfile);
WINEXPORT PidRunningStat are_we_already_running(const char * pidfile, int* pid);
WINEXPORT int		kill_pid_service(const char * pidfile, int signal);
#else
#define SEP "/"
#	define	HAS_FORK
#endif

const char *		localaddr = NULL;
const char *		cmaaddr = NULL;
const char *		procname = "nanoprobe";

gint64		pktcount = 0;
NetIO*		nettransport;
NetGSource*	netpkt;
NetAddr*	destaddr;
NetAddr*	localbindaddr;
int		heartbeatcount = 0;
int		pcapcount = 0;
int		wirepktcount = 0;


//		Signals...
gboolean	sigint	= FALSE;
gboolean	sigterm = FALSE;
gboolean	sighup	= FALSE;
gboolean	sigusr1 = FALSE;
gboolean	sigusr2 = FALSE;


FSTATIC void catch_a_signal(int signum);
FSTATIC gboolean check_for_signals(gpointer ignored);
FSTATIC gboolean gotnetpkt(Listener*, FrameSet* fs, NetAddr* srcaddr);
FSTATIC void usage(const char * cmdname);


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
				DEBUGMSG3("%s.%d: Received a FrameSet of type %d over the 'wire'."
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
#ifndef WIN32
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
#endif
	}
}

// If our output is all ACKed, then go ahead and shutdown

/// Check for signals periodically
FSTATIC gboolean
check_for_signals(gpointer ignored)
{
	(void)ignored;
	if (sigterm || sigint) {
		g_message("%s: exiting on %s.", procname, (sigterm ? "SIGTERM" : "SIGINT"));
#ifdef DEBUGSHUTDOWN
		// Crank up protocol debugging
		proj_class_incr_debug("FsProtocol");
		proj_class_incr_debug("FsProtocol");
		proj_class_incr_debug("FsProtocol");
		proj_class_incr_debug("FsProtocol");
		proj_class_incr_debug("FsProtocol");
		// And reliable UDP, etc. debugging too.
		proj_class_incr_debug("NetIO");
		proj_class_incr_debug("NetIO");
		proj_class_incr_debug("NetIO");
		proj_class_incr_debug("NetIO");
		proj_class_incr_debug("NetIO");
		proj_class_incr_debug("FsQueue");
		proj_class_incr_debug("FsQueue");
		proj_class_incr_debug("FsQueue");
		proj_class_incr_debug("FsQueue");
		proj_class_incr_debug("FsQueue");
#endif
		return nano_initiate_shutdown();
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
	fprintf(stderr, "\t-c --cmaaddr <address:port-of-CMA>\n");
	fprintf(stderr, "\t-b --bind <address:port-to-listen-on-locally>\n");
	fprintf(stderr, "\t-t --ttl  <multi cast ttl (default == 31)>\n");
#ifndef WIN32
#ifdef HAS_FORK
	fprintf(stderr, "\t-f --foreground (stay in foreground.)\n");
#endif
	fprintf(stderr, "\t-k --kill (send SIGTERM to the running service.)\n");
	fprintf(stderr, "\t-p --pidfile <pid-file-pathname>.\n");
	fprintf(stderr, "\t-s --status (report nanoprobe status)\n");
#endif
	fprintf(stderr, "\t-d --debug <debug-level (0-5)>\n");
	fprintf(stderr, "\t-D --dynamic (use ephemeral/dynamic port number)\n");
}

/**
 * Nanoprobe main program.
 *
 * It leaves most of the work of starting up the nanoprobe code to nano_start_full()
 */
int
main(int argc, char **argv)
{
	static char		defaultCMAaddr[] = CMAADDR;
	static char		defaultlocaladdress [] = NANOLISTENADDR;
	SignFrame*		signature = signframe_glib_new(G_CHECKSUM_SHA256, 0);
	CompressFrame*		compression = compressframe_new(FRAMETYPE_COMPRESS, COMPRESS_ZLIB);
	Listener*		otherlistener;
	ConfigContext*		config = configcontext_new(0);
	PacketDecoder*		decoder = nano_packet_decoder();
#ifdef HAVE_SIGACTION
	struct sigaction	sigact;
#endif
	static char *		localaddr = defaultlocaladdress;
	static char *		cmaaddr = defaultCMAaddr;
	static int debug = 0;
	gboolean		anyportpermitted = TRUE;
	static int			mcast_ttl = 31;
	static gboolean		stay_in_foreground = FALSE;
	static gboolean		dostatusonly = FALSE;
	static gboolean		dokillonly = FALSE;
	static gboolean		dynamicport = FALSE;
	static char*		pidfile = NULL;
	gboolean		bindret = FALSE;
	PidRunningStat rstat;
	int ret;

	GError *error = NULL;
	static GOptionEntry 	long_options[] = {
		{"bind",	'b', 0,	G_OPTION_ARG_STRING, &localaddr, "<address:port-to-listen-on-locally>", NULL},
		{"cmaaddr",	'c', 0, G_OPTION_ARG_STRING, &cmaaddr,	 "<address:port-of-CMA>", NULL},
		{"debug",	'd', 0, G_OPTION_ARG_INT,   &debug,      "set debug level", NULL},
		{"dynamic",	'D', 0, G_OPTION_ARG_NONE,  &dynamicport," force dynamic port", NULL},
		{"ttl",		't', 0, G_OPTION_ARG_INT, &mcast_ttl,    "<multicast-ttl> (default is 31)",	NULL},
		{"kill",    'k', 0, G_OPTION_ARG_NONE, &dokillonly, "send SIGTERM to the running service", NULL},
		{"pidfile", 'p', 0, G_OPTION_ARG_STRING, &pidfile, "<pid-file-pathname>", NULL},
		{"status",  's', 0, G_OPTION_ARG_NONE, &dostatusonly, "report nanoprobe status", NULL},
#ifdef HAS_FORK
		{"foreground", 'f', 0, G_OPTION_ARG_NONE, &stay_in_foreground, "stay in foreground", NULL},
#endif
		{NULL, 0, 0, G_OPTION_ARG_NONE, NULL, NULL, NULL}
	};

	GOptionContext *context = g_option_context_new("- start nanoprobe");
	g_option_context_add_main_entries(context, long_options, NULL);
	/// @todo initialize from a setup file - initial IP address:port, debug - anything else?


	if(!(g_option_context_parse(context, &argc, &argv, &error))) {
		g_print("option parsing failed %s\n", error->message);
		usage(argv[0]);
		exit(1);
	}
	
	BINDDEBUG(NanoprobeMain);

	if (debug > 0 && debug <= 5) {
		DEBUGMSG("DEBUG IS SET TO %d", debug);
		while(debug > 0) {
			proj_class_incr_debug(NULL);
			debug -= 1;
		}
	}


	if (pidfile == NULL) {
		pidfile = get_default_pid_fileName(procname);
	}

	if (dostatusonly) {
		rstat = are_we_already_running(pidfile, NULL);
		ret = pidrunningstat_to_status(rstat);
		g_free(pidfile);
		exit(ret);
	}
	if (dokillonly) {
		int rc = kill_pid_service(pidfile, SIGTERM);
		if (rc != 0) {
			fprintf(stderr, "%s: could not stop service [%s]\n", "nanoprobe", g_strerror(errno));
			g_warning("%s: could not stop service [%s]\n", "nanoprobe", g_strerror(errno));
			g_free(pidfile);
			exit(1);
		}
		while (are_we_already_running(pidfile, NULL) == PID_RUNNING) {
			usleep(100000);	// 1/10 second
		}
		g_free(pidfile);
		exit(0);
	}
	daemonize_me(stay_in_foreground, SEP, pidfile);

	assimilation_openlog(argv[0]);

	if (!netio_is_dual_ipv4v6_stack()) {
		g_warning("This OS DOES NOT support dual ipv4/v6 sockets - this may not work!!");
	}
#ifndef HAVE_SIGACTION
	signal(SIGTERM, catch_a_signal);
	if (stay_in_foreground) {
		if (signal(SIGINT, catch_a_signal) == SIG_IGN) {
			signal(SIGINT, SIG_IGN);
		}
	}else{
		signal(SIGINT, SIG_IGN);
	}
#else
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
#endif

	config->setframe(config, CONFIGNAME_OUTSIG, &signature->baseclass);
	config->setframe(config, CONFIGNAME_COMPRESS, &compression->baseclass);

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


	if (dynamicport) {
		anyportpermitted = TRUE;
	}else{
		// Construct a NetAddr to bind to (listen from) (normally ANY address)
		localbindaddr =  netaddr_string_new(localaddr);
		g_return_val_if_fail(NULL != localbindaddr, 5);

		// Bind to the requested address (defaults to ANY as noted above)
		bindret = nettransport->bindaddr(nettransport, localbindaddr, anyportpermitted);
		UNREF(localbindaddr);
	}
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
			g_warning("Cannot bind to local address [%s] and cannot use any free port."
			,	localaddr);
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
	// Free compression frame
	UNREF2(compression);

	// Free misc addresses
	UNREF(destaddr);

	nano_start_full("netconfig", 900, netpkt, config, NULL);
	g_info("Starting version %s: licensed under %s", VERSION_STRING, LONG_LICENSE_STRING);

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

	remove_pid_file(pidfile);
	g_free(pidfile);

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
