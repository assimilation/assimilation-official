/**
 * @file
 * @brief Simple pcap testing code.
 * Reads a few packets from pcap capture files, and then listens for LLDP packets on the network.
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
#include <ctype.h>
#include <projectcommon.h>
#include <cdp.h>
#include <lldp.h>
#include <server_dump.h>
#include <pcap_min.h>
#include <frameset.h>
#include <frame.h>
#include <addrframe.h>
#include <cstringframe.h>
#include <intframe.h>
#include <frameformats.h>
#include <tlvhelper.h>

#define DIMOF(a)	(sizeof(a)/sizeof(a[0]))

FSTATIC void cast_tests(void);
FSTATIC void frameset_tests(void);
FSTATIC void cast_tests(void);
pcap_t* create_pcap_listener(const char * dev, unsigned listenmask);


FSTATIC void
cast_tests(void)
{
	Frame*		f = frame_new(10, 0);
	CstringFrame*	csf	= cstringframe_new(11,0);
	AddrFrame*	af = addrframe_new(12,0);
	IntFrame*	intf = intframe_new(13,sizeof(long));
	SignFrame*	sigf = signframe_new(G_CHECKSUM_SHA256, 0);
	guint8		address[] = {127, 0, 0, 1};
	gchar		fred[]  = "fred";
	gchar		george[]  = "george";
	char		stackprotectionstuff[8];

	Frame*		fcast;
	AddrFrame*	afcast;
	CstringFrame*	cscast;
	IntFrame*	intfcast;
	FrameSet*	fs = frameset_new(42);

	stackprotectionstuff[0] = '\0';	// Make it think we need stackprotection stuff...

	printf("Performing c-class cast tests\n");
	fcast = CASTTOCLASS(Frame, f);
	fcast = CASTTOCLASS(Frame, csf);
	fcast = CASTTOCLASS(Frame, af);
	fcast = CASTTOCLASS(Frame, intf);
	fcast = CASTTOCLASS(Frame, sigf);
	cscast = CASTTOCLASS(CstringFrame, csf);
	afcast = CASTTOCLASS(AddrFrame, af);
	intfcast = CASTTOCLASS(IntFrame, intf);
	sigf = CASTTOCLASS(SignFrame, sigf);


	f->setvalue(f, fred, strlen(fred), NULL);
	csf->baseclass.setvalue(CASTTOCLASS(Frame,csf), george, sizeof(george), NULL);
	intf->setint(intf, 42);
	tlv_set_guint16(address, 1, address + DIMOF(address));
	af->setaddr(af, 1, address, sizeof(address));
	frameset_append_frame(fs, CASTTOCLASS(Frame,f));
	frameset_append_frame(fs, CASTTOCLASS(Frame, csf));
	frameset_append_frame(fs, CASTTOCLASS(Frame, af));
	frameset_append_frame(fs, CASTTOCLASS(Frame, intf));
	frameset_construct_packet(fs, sigf, NULL, NULL);
	proj_class_dump_live_objects();
	printf("finalizing the FrameSet (and presumably frames)\n");
	fs->finalize(fs);
	fs = NULL;
	proj_class_dump_live_objects();
	printf("C-class cast tests complete! - check output for errors.\n");
}





#define PCAP	"pcap/"

int
main(int argc, char **argv)
{
	char			errbuf[PCAP_ERRBUF_SIZE];
	struct pcap_pkthdr 	hdr;
	const	guchar*		packet;
	int			j;
	const char * lldpfilenames []	= {PCAP "lldp.detailed.pcap", PCAP "procurve.lldp.pcap", PCAP "lldpmed_civicloc.pcap"};
	const char * cdpfilenames  []	= {PCAP "cdp.pcap", PCAP "n0.eth2.cdp.pcap"};
	
	// make CRITICAL errors terminate the program too...
	g_log_set_fatal_mask (NULL, G_LOG_LEVEL_ERROR|G_LOG_LEVEL_CRITICAL);
	cast_tests();

	// Parse some existing CDP files
	for (j=0; j < DIMOF(cdpfilenames); ++j) {
		pcap_t*	handle;
		const char * filename = cdpfilenames[j];
		int	count = 0;
		if (NULL == (handle = pcap_open_offline(filename, errbuf))) {
			fprintf(stderr, "open_offline failed.../: %s\n", errbuf);
			exit(1);
		}
		while (NULL != (packet = pcap_next(handle, &hdr))) {
			const guchar *	pend = packet + hdr.caplen;
			++count;
			fprintf(stderr, "Found a %d/%d byte CDP packet!\n", hdr.caplen, hdr.len);
			if (is_valid_cdp_packet(packet, pend)) {
				dump_cdp_packet(packet, pend);
			}else{
				fprintf(stderr,
				        "\nERROR: %d byte CDP packet %d in [%s] is NOT valid!\n\n",
                                        (int)(pend-packet), count, filename);
			}
			dump_mem(packet, packet+hdr.caplen);
			printf("\n");
		}
		pcap_close(handle);
	}

	// Parse some existing LLDP files
	for (j=0; j < DIMOF(lldpfilenames); ++j) {
		pcap_t*	handle;
		const char * filename = lldpfilenames[j];
		if (NULL == (handle = pcap_open_offline(filename, errbuf))) {
			fprintf(stderr, "open_offline failed.../: %s\n", errbuf);
			exit(1);
		}
		while (NULL != (packet = pcap_next(handle, &hdr))) {
			const guchar *	pend = packet + hdr.caplen;
			fprintf(stdout, "Found a %d/%d byte LLDP packet!\n", hdr.caplen, hdr.len);
			dump_lldp_packet(packet, pend);
			dump_mem(packet, packet+hdr.caplen);
			printf("\n");
		}
		pcap_close(handle);
	}
	return(0);
}
