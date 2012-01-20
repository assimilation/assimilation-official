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
#include <frameset.h>
#include <ctype.h>
#include <cdp.h>
#include <lldp.h>
#include <server_dump.h>
#include <pcap_GSource.h>
#include <decode_packet.h>
#include <netgsource.h>
#include <netioudp.h>
#include <netaddr.h>
#include <hblistener.h>
#include <hbsender.h>

gint64		maxpkts  = G_MAXINT64;
gint64		pktcount = 0;
GMainLoop*	loop = NULL;
NetIO*		transport;
NetAddr*	destaddr;
HbSender*	sender = NULL;
int		wirepktcount = 0;
int		heartbeatcount = 0;
int		errcount = 0;
int		pcapcount = 0;
void send_encapsulated_packet(gconstpointer, gconstpointer, const struct pcap_pkthdr *, const char *);
gboolean gotapcappacket(GSource_pcap_t*, pcap_t *, gconstpointer, gconstpointer, const struct pcap_pkthdr *, const char *, gpointer);
gboolean gotnetpkt(Listener*, FrameSet* fs, NetAddr* srcaddr);
void real_deadtime_agent(HbListener* who);
void initial_deadtime_agent(HbListener* who);
void got_heartbeat(HbListener* who);

/// Test routine for sending an encapsulated Pcap packet.
void
send_encapsulated_packet(gconstpointer packet,			///<[in] pcap packet data
		   gconstpointer pktend,			///<[in] one byte past end of pkt
           	   const struct pcap_pkthdr *hdr,	///<[in] pcap header
		   const char * dev)			///<[in] capture device
{
	FrameSet *	fs = construct_pcap_frameset(FRAMESETTYPE_SWDISCOVER, packet, pktend, hdr, dev);
	//g_message("Sending a frameset containing an encapsulated capture packet.");
	transport->sendaframeset(transport, destaddr, fs);
	fs->unref(fs); fs = NULL;
}

/// Routine called when a packet is received from the g_main_loop() mechanisms.
gboolean
gotapcappacket(GSource_pcap_t* srcobj,		///<[in]GSource object causing this call
	   pcap_t *capfd,			///<[in]pcap capture object
           gconstpointer pkt,			///<[in]captured packet
           gconstpointer pend,			///<[in]end of captured packet
           const struct pcap_pkthdr *hdr,	///<[in]pcap header
           const char *dev,			///<[in]name of capture device
	   gpointer userdatanotused)		///<[unused] unused userdata pointer
{
	FrameSet *	fs;
	SignFrame*	signature;
	(void)srcobj; (void)capfd; (void)userdatanotused;
	++pcapcount;
	if (is_valid_lldp_packet(pkt, pend)) {
		g_message("Found a %d/%d byte LLDP packet!", hdr->caplen, hdr->len);
		//dump_lldp_packet(pkt, pend);
	}else if (is_valid_cdp_packet(pkt, pend)) {
		g_message("Found a %d/%d byte CDP packet!", hdr->caplen, hdr->len);
		//dump_cdp_packet(pkt, pend);
	}else{
		g_warning("Found a %d/%d byte INVALID packet!", hdr->caplen, hdr->len);
		++errcount;
	}
	signature = signframe_new(G_CHECKSUM_SHA256, 0);
	//g_message("Constructing a frameset for this %d byte captured packet.", hdr->caplen);
	fs = construct_pcap_frameset(0xfeed, pkt, pend, hdr, dev);
	//g_message("Constructing a capture packet packet from the constructed frameset.");
	frameset_construct_packet(fs, signature, NULL, NULL);
	signature->baseclass.unref(CASTTOCLASS(Frame, signature)); signature = NULL;
	if (!fs->packet) {
		g_critical("fs is NULL!");
		++errcount;
	}else{
		GSList*		fslist;
		int	size = (guint8*)fs->pktend - (guint8*) fs->packet;
		g_message("Constructed packet is %d bytes", size);
		fslist = pktdata_to_frameset_list(fs->packet, fs->pktend);
		if (fslist == NULL) {
			g_warning("fslist is NULL!");
			++errcount;
		}else{
			FrameSet*	copyfs = CASTTOCLASS(FrameSet, fslist->data);
			SignFrame*	newsig = signframe_new(G_CHECKSUM_SHA256, 0);
			frameset_construct_packet(copyfs, newsig, NULL, NULL);
			newsig->baseclass.unref(CASTTOCLASS(Frame, newsig));
			newsig = NULL;
			if (!copyfs->packet) {
				g_warning("copyfs->packet is NULL!");
				++errcount;
			}else{
				int	cpsize = (guint8*)copyfs->pktend - (guint8*) copyfs->packet;
				//g_message("Second Constructed packet is %d bytes", cpsize);
				//frameset_dump(fs);
				//frameset_dump(copyfs);
				if (size == cpsize) {
					if (memcmp(fs->packet, copyfs->packet, size) == 0) {
						g_message("Packets are identical!");
					}else{
						g_warning("Packets are different :-(");
						++errcount;
					}
				}else{
					g_warning("Packets are different sizes:-(");
					++errcount;
				}
			}
			//g_message("Frameset for copy packet - freed!");
			copyfs->unref(copyfs);
			copyfs = NULL;
			g_slist_free(fslist);
		}
	}
	fs->unref(fs);
	fs = NULL;
	//g_message("Frameset for constructed packet - freed!");
	send_encapsulated_packet(pkt, pend, hdr, dev);
	++pktcount;
	return TRUE;
}

///
/// Test routine called when a NetIO packet is received.
gboolean
gotnetpkt(Listener* l,		///<[in/out] Input GSource
	  FrameSet* fs,		///<[in/out] Framesets received
	  NetAddr* srcaddr	///<[in] Source address of this packet
	  )
{
	(void)l; (void)srcaddr;
	++wirepktcount;
	g_message("Received a packet over the 'wire'!");
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

void
real_deadtime_agent(HbListener* who)
{
	(void)who;
	g_warning("Subsequent (unexpected) deadtime event occurred.");
	++errcount;
}
void
got_heartbeat(HbListener* who)
{
	(void)who;
	++heartbeatcount;
	//g_debug("Got heartbeat()");
}
void
initial_deadtime_agent(HbListener* who)
{
	(void)who;
	g_message("Expected deadtime event occurred (once)");
	sender = hbsender_new(destaddr, transport, 1,  0);
	who->set_deadtime_callback(who, real_deadtime_agent);
	
}

/// Test program looping and reading LLDP/CDP packets.
int
main(int argc, char **argv)
{
	char *		dev;					// Device to listen on
	GSource*	pcapsource;				// GSource for packets
	unsigned	protocols = ENABLE_LLDP|ENABLE_CDP;	// Protocols to watch for...
	char		errbuf[PCAP_ERRBUF_SIZE];		// Error buffer...
	const guint8	loopback[] = CONST_IPV6_LOOPBACK;
	guint16		testport = 1984;
	SignFrame*	signature = signframe_new(G_CHECKSUM_SHA256, 0);
	NetGSource*	netpkt;
	HbListener*	hblisten;
	Listener*	otherlistener;


	g_log_set_fatal_mask (NULL, G_LOG_LEVEL_ERROR|G_LOG_LEVEL_CRITICAL);
	if (argc > 1) {
		maxpkts = atol(argv[1]);
                g_debug("Max LLDP/CDP packet count is %lld", maxpkts);
	}
	
	dev = pcap_lookupdev(errbuf);	// Find name of default network device...
	if (dev == NULL) {
		g_critical("Couldn't find default device: %s", errbuf);
		++errcount;
		return(2);
	}
	g_message("PCAP capture device is: %s", dev);


	// Create a pcap packet Gsource for the g_main_loop environment,
	// and connect it up to run in the default context

	pcapsource = g_source_pcap_new(dev, protocols, gotapcappacket, NULL,
                                      G_PRIORITY_DEFAULT, FALSE, NULL, 0, NULL);
	g_return_val_if_fail(NULL != pcapsource, 1);

	// Create a network transport object (UDP packets)
	transport = CASTTOCLASS(NetIO, netioudp_new(0));
	g_return_val_if_fail(NULL != transport, 2);
	transport->set_signframe(transport, signature);

	// Construct the NetAddr we'll talk to (i.e., ourselves) and listen from
	destaddr =  netaddr_ipv6_new(loopback, testport);
	g_return_val_if_fail(NULL != destaddr, 3);

	// Listen for our own packets...
	g_return_val_if_fail(transport->bindaddr(transport, destaddr),16);

	// Connect up our network transport into the g_main_loop paradigm
	// so we get dispatched when packets arrive
	netpkt = netgsource_new(transport, NULL, G_PRIORITY_HIGH, FALSE, NULL, 0, NULL);
	otherlistener = listener_new(0);
	otherlistener->got_frameset = gotnetpkt;
	netpkt->addListener(netpkt, 0, otherlistener);	// Get all unclaimed packets...
	// Unref the "other" listener
	otherlistener->unref(otherlistener); otherlistener = NULL;

	// Create a heartbeat listener
	hblisten = hblistener_new(destaddr, 0);
	hblisten->set_deadtime(hblisten, 10*1000000);
	hblisten->set_heartbeat_callback(hblisten, got_heartbeat);
	hblisten->set_deadtime_callback(hblisten, initial_deadtime_agent);

	// Intercept incoming heartbeat packets - direct them to heartbeat listener
	netpkt->addListener(netpkt, FRAMESETTYPE_HEARTBEAT, CASTTOCLASS(Listener, hblisten));
	// Unref the heartbeat listener
	hblisten->baseclass.unref(CASTTOCLASS(Listener, hblisten)); hblisten = NULL;

	loop = g_main_loop_new(g_main_context_default(), TRUE);

	// Start up the main loop - run the program...
	g_main_loop_run(loop);

	transport->finalize(transport); transport = NULL;
	if (sender) {
		sender->unref(sender); sender = NULL;
	}
	g_source_pcap_finalize((GSource*)pcapsource);

	// g_main_loop_unref() calls g_source_unref() - so we should not call it directly.
	g_main_context_unref(g_main_context_default());

	// Main loop is over - shut everything down, free everything...
	g_main_loop_unref(loop); loop=NULL; pcapsource=NULL;

	// Unlink heartbeat dispatcher - this should NOT be necessary...
	netpkt->addListener(netpkt, FRAMESETTYPE_HEARTBEAT, NULL);

	// Unlink misc dispatcher - this should NOT be necessary...
	netpkt->addListener(netpkt, 0, NULL);

	// Free signature frame
	signature->baseclass.unref(CASTTOCLASS(Frame, signature)); signature = NULL;

	// Free destination address
        destaddr->unref(destaddr);


	// At this point - nothing should show up - we should have freed everything
	proj_class_dump_live_objects();
	if (proj_class_live_object_count() > 2) {
		g_warning("Too many objects (%d) alive at end of test.", 
			proj_class_live_object_count());
		++errcount;
	}
	g_message("Count of pcap packets received:\t%d", pcapcount);
	g_message("Count of pkts received over wire:\t%d", wirepktcount);
	g_message("Count of heartbeats received:\t%d", heartbeatcount);
	g_message("Count of errors:\t\t\t%d", errcount);
	return(errcount <= 127 ? errcount : 127);
}
