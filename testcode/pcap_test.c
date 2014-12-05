/**
 * @file
 * @brief Simple pcap testing code.
 * Reads a few packets from pcap capture files, and then listens for LLDP packets on the network.
 * Also does a few other basic unit tests that don't require a network.
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
#include <ctype.h>
#include <cdp.h>
#include <lldp.h>
#include <address_family_numbers.h>
#include <server_dump.h>
#include <pcap_min.h>
#include <frameset.h>
#include <frame.h>
#include <addrframe.h>
#include <cstringframe.h>
#include <netio.h>
#include <intframe.h>
#include <frametypes.h>
#include <tlvhelper.h>

#define DIMOF(a)	(sizeof(a)/sizeof(a[0]))

FSTATIC void frameset_tests(void);
FSTATIC void cast_frameset_tests(void);
FSTATIC void address_tests(void);


/// Basic tests of our Class system, and for good measure testing of some Frame and FrameSet objects.
FSTATIC void
cast_frameset_tests(void)
{
	Frame*		f = frame_new(10, 0);
	CstringFrame*	csf	= cstringframe_new(11,0);
	AddrFrame*	af = addrframe_new(12,0);
	IntFrame*	intf = intframe_new(13,sizeof(long));
	SignFrame*	sigf = signframe_glib_new(G_CHECKSUM_SHA256, 0);
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
	(void)stackprotectionstuff;

	g_message("Performing c-class cast tests");
	fcast = CASTTOCLASS(Frame, f);
	(void)fcast;
	fcast = CASTTOCLASS(Frame, csf);
	(void)fcast;
	fcast = CASTTOCLASS(Frame, af);
	(void)fcast;
	fcast = CASTTOCLASS(Frame, intf);
	(void)fcast;
	fcast = CASTTOCLASS(Frame, sigf);
	(void)fcast;
	cscast = CASTTOCLASS(CstringFrame, csf);
	(void)cscast;
	afcast = CASTTOCLASS(AddrFrame, af);
	(void)afcast;
	intfcast = CASTTOCLASS(IntFrame, intf);
	(void)intfcast;
	sigf = CASTTOCLASS(SignFrame, sigf);
	(void)sigf;


	f->setvalue(f, fred, strlen(fred), NULL);
	csf->baseclass.setvalue(CASTTOCLASS(Frame,csf), george, sizeof(george), NULL);
	intf->setint(intf, 42);
	tlv_set_guint16(address, 1, address + DIMOF(address));
	af->setaddr(af, ADDR_FAMILY_IPV4, address, sizeof(address));
	frameset_append_frame(fs, CASTTOCLASS(Frame,f));
	UNREF(f);
	frameset_append_frame(fs, CASTTOCLASS(Frame, csf));
	UNREF2(csf);
	frameset_append_frame(fs, CASTTOCLASS(Frame, af));
	UNREF2(af);
	frameset_append_frame(fs, CASTTOCLASS(Frame, intf));
	UNREF2(intf);
	frameset_construct_packet(fs, sigf, NULL, NULL);
	UNREF2(sigf);
	proj_class_dump_live_objects();
	g_message("finalizing the FrameSet (and presumably frames)");
	UNREF(fs);
	proj_class_dump_live_objects();
	g_message("C-class cast tests complete! - please check the output for errors.");
}

/// Basic tests of a few different kinds of @ref AddrFrame objects
FSTATIC void
address_tests(void)
{
	const guint8	addr_ipv4_localhost[4] = CONST_IPV4_LOOPBACK;
	const guint8	addr_ipv4_other[4] = {10, 10, 10, 5};
	const guint8	addr_ipv6_localhost[16] =  CONST_IPV6_LOOPBACK;
	const guint8	addr_ipv46_localhost[16] = {0,0,0,0,0,0,0,0,0,0,0xff,0xff,127,0,0,1};
	const guint8	addr_macaddr48 [6]= {0x00, 0x1b, 0xfc, 0x1b, 0xa8, 0x73};
	const guint8	addr_macaddr64 [8]= {0x00, 0x1b, 0xfc, 0x1b, 0xa8, 0x73, 0x42, 0x42};
	const guint8	addr_ipv6_other[16] = {0xfe, 0x80, 0,0,0,0,0,0, 0x2, 0x1b, 0xfc, 0xff, 0xfe, 0x1b, 0xa8, 0x73};
	AddrFrame*	ipv4_localhost = addrframe_ipv4_new(FRAMETYPE_IPADDR, addr_ipv4_localhost);
	AddrFrame*	ipv6_localhost = addrframe_ipv6_new(FRAMETYPE_IPADDR, addr_ipv6_localhost);
	AddrFrame*	ipv46_localhost = addrframe_ipv6_new(FRAMETYPE_IPADDR, addr_ipv46_localhost);
	AddrFrame*	macaddr48 = addrframe_mac48_new(FRAMETYPE_IPADDR, addr_macaddr48);
	AddrFrame*	macaddr64 = addrframe_mac64_new(FRAMETYPE_IPADDR, addr_macaddr64);
	AddrFrame*	ipv6_other = addrframe_ipv6_new(FRAMETYPE_IPADDR, addr_ipv6_other);
	AddrFrame*	ipv4_other = addrframe_ipv4_new(FRAMETYPE_IPADDR, addr_ipv4_other);
	AddrFrame*	bframeipv4_1 = addrframe_new(FRAMETYPE_IPADDR, 0);
	AddrFrame*	bframeipv4_2 = addrframe_new(FRAMETYPE_IPADDR, 0);
	AddrFrame*	bframeipv6_1 = addrframe_new(FRAMETYPE_IPADDR, 0);
	AddrFrame*	bframeipv6_2 = addrframe_new(FRAMETYPE_IPADDR, 0);
	AddrFrame*	bframemac_1 = addrframe_new(FRAMETYPE_MACADDR, 0);
	AddrFrame*	bframemac_2 = addrframe_new(FRAMETYPE_MACADDR, 0);
	AddrFrame*	bframemac_3 = addrframe_new(FRAMETYPE_MACADDR, 0);
	AddrFrame*	gframes[] = {ipv4_localhost, ipv6_localhost, ipv46_localhost, macaddr48, macaddr64, ipv6_other, ipv4_other};
	AddrFrame*	bframes[] = {bframeipv4_1, bframeipv4_2, bframeipv6_1, bframeipv6_2, bframemac_1, bframemac_2, bframemac_3};
	AddrFrame*	af;
	SignFrame*	gsigf = signframe_glib_new(G_CHECKSUM_SHA256, 0);
	unsigned	j;
	FrameSet*	gfs = frameset_new(42);


	g_message("Starting Known Good AddressFrame tests.");
	for (j=0; j < DIMOF(gframes); ++j) {
                Frame * faf;
		af = gframes[j];
                faf = CASTTOCLASS(Frame, af);
		if (!af->baseclass.isvalid(faf, NULL, NULL)) {
			g_critical("OOPS Good AddressFrame %d is NOT valid!", j);
		}
		frameset_append_frame(gfs, faf);
		UNREF2(af);
	}
	frameset_construct_packet(gfs, gsigf, NULL, NULL);
	UNREF2(gsigf);
	UNREF(gfs);


	bframeipv4_1->setaddr(bframeipv4_1, ADDR_FAMILY_IPV4, addr_ipv46_localhost, 3);
	bframeipv4_1->setaddr(bframeipv4_2, ADDR_FAMILY_IPV4, addr_ipv46_localhost, 5);
	bframeipv6_1->setaddr(bframeipv6_1, ADDR_FAMILY_IPV6, addr_ipv46_localhost, 15);
	bframeipv6_2->setaddr(bframeipv6_2, ADDR_FAMILY_IPV6, addr_ipv46_localhost, 17);
	bframemac_1->setaddr(bframemac_1, ADDR_FAMILY_802,  addr_ipv46_localhost, 5);
	bframemac_2->setaddr(bframemac_2, ADDR_FAMILY_802,  addr_ipv46_localhost, 7);
	bframemac_3->setaddr(bframemac_3, ADDR_FAMILY_802,  addr_ipv46_localhost, 9);

	g_message("Starting Known Bad AddressFrame tests.");
	for (j=0; j < DIMOF(bframes); ++j) {
		af = bframes[j];
		if (af->baseclass.isvalid(CASTTOCLASS(Frame, af), NULL, NULL)) {
			g_critical("Bad AddressFrame %d SHOULD NOT BE valid!", j);
		}
		UNREF2(af);
		bframes[j] = NULL;
	}

	proj_class_dump_live_objects();
	g_message("End of AddressFrame tests.");
}




#define PCAP	"../pcap/"

/// Main program for performing tests that don't need a network.
int
main(int argc, char **argv)
{
	char			errbuf[PCAP_ERRBUF_SIZE];
	struct pcap_pkthdr 	hdr;
	const	guchar*		packet;
	unsigned		j;
	const char * lldpfilenames []	= {PCAP "lldp.detailed.pcap", PCAP "procurve.lldp.pcap", PCAP "lldpmed_civicloc.pcap"};
	const char * cdpfilenames  []	= {PCAP "cdp.pcap", PCAP "n0.eth2.cdp.pcap"};
	
	(void)argc; (void)argv;
	// make CRITICAL messages terminate the program too...
	g_log_set_fatal_mask (NULL, G_LOG_LEVEL_ERROR|G_LOG_LEVEL_CRITICAL);
	cast_frameset_tests();
	address_tests();

	// Parse some existing CDP files
	for (j=0; j < DIMOF(cdpfilenames); ++j) {
		pcap_t*	handle;
		const char * filename = cdpfilenames[j];
		int	count = 0;
		if (NULL == (handle = pcap_open_offline(filename, errbuf))) {
			g_error("open_offline failed.../: %s", errbuf);
			exit(1);
		}
		while (NULL != (packet = pcap_next(handle, &hdr))) {
			const guchar *	pend = packet + hdr.caplen;
			++count;
			g_message("Found a %d/%d byte CDP packet!", hdr.caplen, hdr.len);
			if (is_valid_cdp_packet(packet, pend)) {
				dump_cdp_packet(packet, pend);
			}else{
				g_warning("ERROR: %d byte CDP packet %d in [%s] is NOT valid!\n",
                                        (int)(pend-packet), count, filename);
			}
			dump_mem(packet, packet+hdr.caplen);
			g_message("%s", "");
		}
		pcap_close(handle);
	}

	// Parse some existing LLDP files
	for (j=0; j < DIMOF(lldpfilenames); ++j) {
		pcap_t*	handle;
		const char * filename = lldpfilenames[j];
		if (NULL == (handle = pcap_open_offline(filename, errbuf))) {
			g_error("open_offline failed.../: %s\n", errbuf);
		}
		while (NULL != (packet = pcap_next(handle, &hdr))) {
			const guchar *	pend = packet + hdr.caplen;
			g_message("Found a %d/%d byte LLDP packet!\n", hdr.caplen, hdr.len);
			dump_lldp_packet(packet, pend);
			dump_mem(packet, packet+hdr.caplen);
			g_message("%s", "");
		}
		pcap_close(handle);
	}
	return(0);
}
