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

#define PCAP	"pcap/"

gint64 maxpkts  = G_MAXINT64;
gint64 pktcount = 0;
GMainLoop*	loop = NULL;
FrameSet* encapsulate_packet(gpointer, gpointer, const char *);
gboolean gotapcappacket(GSource_pcap_t*, pcap_t *, gconstpointer, gconstpointer, const struct pcap_pkthdr *, const char *, gpointer);

/// Test routine for encapsulating a packet in a FrameSet
/// Eventually this will include the packet data, the interface information, and the source address
/// of the packet.  These can be a Frame, CstringFrame, and an AddrFrame respectively.
/// In this case, the AddrFrame will be for the MAC address - since there is no higher level
/// protocol for these link level discovery protocols.
FrameSet*
encapsulate_packet(gpointer packet,
		   gpointer pktend,
		   const char * dev)
{
	///@todo finish encapsulate_packet
	return NULL;

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
			copyfs->finalize(copyfs);
			copyfs = NULL;
		}
	}

	fs->finalize(fs);
	fs = NULL;
	fprintf(stderr, "Frameset for constructed packet - freed!\n");
	++pktcount;
	if (pktcount >= maxpkts) {
		fprintf(stderr, "QUITTING NOW!\n");
		g_main_loop_quit(loop);
		return FALSE;
	}
	return TRUE;
}

/// Test program looping and reading LLDP/CDP packets.
int
main(int argc, char **argv)
{
	char *			dev;					// Device to listen on
	GSource*		pktsource;				// GSource for packets
	unsigned		protocols = ENABLE_LLDP|ENABLE_CDP;	// Protocols to watch for...
	char			errbuf[PCAP_ERRBUF_SIZE];		// Error buffer...

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

	if (NULL == pktsource) {
		fprintf(stderr, "Cannot create new packet source!\n");
	}
	loop = g_main_loop_new(g_main_context_default(), TRUE);
	g_main_loop_run(loop);
	g_main_loop_unref(loop); loop=NULL; pktsource=NULL;
	// g_main_loop_unref() calls g_source_unref() - so we should not call it ourselves.
	proj_class_dump_live_objects();
	return(0);
}
