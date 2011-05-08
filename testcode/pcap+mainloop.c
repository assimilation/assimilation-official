/**
 * @file
 * @brief Simple pcap testing code using 'mainloop'.
 * Listens for CDP or LLDP packets on the network - all using the mainloop dispatch code.
 * Probably a short-lived piece of test code.
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

gint64		maxpkts  = G_MAXINT64;
gint64		pktcount = 0;
GMainLoop*	loop = NULL;
NetIO*		transport;
NetAddr*	destaddr;
void encapsulate_packet(gconstpointer, gconstpointer, const struct pcap_pkthdr *, const char *);
gboolean gotapcappacket(GSource_pcap_t*, pcap_t *, gconstpointer, gconstpointer, const struct pcap_pkthdr *, const char *, gpointer);
gboolean gotnetpkt(NetGSource* gs, FrameSet* fs, NetAddr* srcaddr, gpointer ignored);

/// Test routine for encapsulating a packet in a FrameSet
/// Eventually this will include the packet data, the interface information, and the source address
/// of the packet.  These can be a Frame and a CstringFrame.  But I think I already have a function
/// which does most of this...  Better look into that...
/// The name is "construct_pcap_frameset".
void
encapsulate_packet(gconstpointer packet,			///<[in] pcap packet data
		   gconstpointer pktend,			///<[in] one byte past end of pkt
           	   const struct pcap_pkthdr *hdr,	///<[in] pcap header
		   const char * dev)			///<[in] capture device
{
	FrameSet *	fs;
	GSList*		list;
	fs = construct_pcap_frameset(FRAMESETTYPE_SWDISCOVER, packet, pktend, hdr, dev);
	list = g_slist_append(NULL, fs);
	fprintf(stderr, "Forwarding a frameset containing a capture packet packet.\n");
	transport->sendframesets(transport, destaddr, list);
	fs->unref(fs);
	list->data = NULL;
	g_slist_free(list);
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
	SignFrame*	signature = signframe_new(G_CHECKSUM_SHA256, 0);
	if (is_valid_lldp_packet(pkt, pend)) {
		fprintf(stderr, "Found a %d/%d byte LLDP packet!\n", hdr->caplen, hdr->len);
		dump_lldp_packet(pkt, pend);
	}else if (is_valid_cdp_packet(pkt, pend)) {
		fprintf(stderr, "Found a %d/%d byte CDP packet!\n", hdr->caplen, hdr->len);
		dump_cdp_packet(pkt, pend);
	}else{
		fprintf(stderr, "Found a %d/%d byte INVALID packet!\n", hdr->caplen, hdr->len);
	}
	fprintf(stderr, "Constructing a frameset for this %d byte captured packet.\n", hdr->caplen);
	fs = construct_pcap_frameset(0xfeed, pkt, pend, hdr, dev);
	fprintf(stderr, "Constructing a capture packet packet from the constructed frameset.\n");
	frameset_construct_packet(fs, signature, NULL, NULL);
	signature->baseclass.unref(CASTTOCLASS(Frame, signature)); signature = NULL;
	if (!fs->packet) {
		fprintf(stderr, "fs is NULL!\n");
	}else{
		GSList*		fslist;
		int	size = (guint8*)fs->pktend - (guint8*) fs->packet;
		fprintf(stderr, "Constructed packet is %d bytes\n", size);
		fslist = pktdata_to_frameset_list(fs->packet, fs->pktend);
		if (fslist == NULL) {
			fprintf(stderr, "fslist is NULL!\n");
		}else{
			FrameSet*	copyfs = CASTTOCLASS(FrameSet, fslist->data);
			SignFrame*	newsig = signframe_new(G_CHECKSUM_SHA256, 0);
			frameset_construct_packet(copyfs, newsig, NULL, NULL);
			newsig->baseclass.unref(CASTTOCLASS(Frame, newsig));
			newsig = NULL;
			if (!copyfs->packet) {
				fprintf(stderr, "copyfs->packet is NULL!\n");
			}else{
				int	cpsize = (guint8*)copyfs->pktend - (guint8*) copyfs->packet;
				fprintf(stderr, "Second Constructed packet is %d bytes\n", cpsize);
				frameset_dump(fs);
				frameset_dump(copyfs);
				if (size == cpsize) {
					if (memcmp(fs->packet, copyfs->packet, size) == 0) {
						fprintf(stderr, "Packets are identical!\n");
					}else{
						fprintf(stderr, "Packets are different :-(\n");
					}
				}
			}
			fprintf(stderr, "Frameset for copy packet - freed!\n");
			copyfs->unref(copyfs);
			copyfs = NULL;
		}
	}
	fs->unref(fs);
	fs = NULL;
	fprintf(stderr, "Frameset for constructed packet - freed!\n");
	encapsulate_packet(pkt, pend, hdr, dev);
	++pktcount;
	if (pktcount >= maxpkts) {
		fprintf(stderr, "QUITTING NOW!\n");
		g_main_loop_quit(loop);
		return FALSE;
	}
	return TRUE;
}

///
/// Test routine called when a NetIO packet is received.
gboolean
gotnetpkt(NetGSource* gs,	///<[in/out] Input GSource
	  FrameSet* fs,	///<[in/out] Framesets received
	  NetAddr* srcaddr,	///<[in] Source address of this packet
	  gpointer ignored	///<[ignored] User data (ignored)
	  )
{
	g_message("Received a packet over the 'wire'!");
	g_message("DUMPING packet received over 'wire':");
	frameset_dump(fs);
	fs->unref(fs);
	g_message("END of packet received over 'wire':");
	return TRUE;
}

/// Test program looping and reading LLDP/CDP packets.
int
main(int argc, char **argv)
{
	char *		dev;					// Device to listen on
	GSource*	pktsource;				// GSource for packets
	unsigned	protocols = ENABLE_LLDP|ENABLE_CDP;	// Protocols to watch for...
	char		errbuf[PCAP_ERRBUF_SIZE];		// Error buffer...
	const guint8	loopback[] = CONST_IPV4_LOOPBACK;
	guint16		testport = 1984;
	SignFrame*	signature = signframe_new(G_CHECKSUM_SHA256, 0);
	NetGSource*	netpkt;

	g_log_set_fatal_mask (NULL, G_LOG_LEVEL_ERROR|G_LOG_LEVEL_CRITICAL);
	if (argc > 1) {
		maxpkts = atol(argv[1]);
	}
	
	dev = pcap_lookupdev(errbuf);	// Find name of default network device...
	if (dev == NULL) {
		fprintf(stderr, "Couldn't find default device: %s\n", errbuf);
		return(2);
	}
	printf("PCAP capture device is: %s\n", dev);


	/// Create a packet source, and connect it up to run in the default context
	pktsource = g_source_pcap_new(dev, protocols, gotapcappacket, NULL,
                                      G_PRIORITY_DEFAULT, FALSE, NULL, 0, NULL);
	g_return_val_if_fail(NULL != pktsource, 1);

	transport = CASTTOCLASS(NetIO, netioudp_new(0));
	g_return_val_if_fail(NULL != transport, 2);
	transport->set_signframe(transport, signature);

	destaddr =  netaddr_ipv4_new(loopback, testport);
	g_return_val_if_fail(NULL != destaddr, 3);

	// Listen for our own packets...
	g_return_val_if_fail(transport->bindaddr(transport, destaddr),4);
	netpkt = netgsource_new(transport, NULL, G_PRIORITY_HIGH, FALSE, NULL, 0, NULL);
	netpkt->addDispatch(netpkt, 0, gotnetpkt);	// Get all unclaimed packets...

	loop = g_main_loop_new(g_main_context_default(), TRUE);
	g_main_loop_run(loop);
	g_main_loop_unref(loop); loop=NULL; pktsource=NULL;
	transport->finalize(transport); transport = NULL;
	// g_main_loop_unref() calls g_source_unref() - so we should not call it directly.
	g_main_context_unref(g_main_context_default());
	g_source_unref(CASTTOCLASS(GSource, netpkt));
	FREECLASSOBJ(destaddr); destaddr = NULL;
	signature->baseclass.unref(CASTTOCLASS(Frame, signature)); signature = NULL;
	proj_class_dump_live_objects();
	return(0);
}
