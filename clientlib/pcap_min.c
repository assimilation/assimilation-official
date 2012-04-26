/**
 * @file
 * @brief Simple pcap interface code.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 *
 *  @todo In general, need to exclude sent packets from received packets even on those platforms
 *  (like Linux) where libpcap won't filter that for us.  This will probably involve filtering by source
 *  MAC address.
 *
 *  @todo To figure out what the MAC address of an interface on Windows is, 
 *  use the GetAdapterAddresses function - http://msdn.microsoft.com/en-us/library/aa365915(v=vs.85).aspx
 * @todo convert all the messaging over to use the various glib logging functions.
 *
 */
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <projectcommon.h>
#include <cdp.h>
#include <lldp.h>
#include <pcap_min.h>
#include <addrframe.h>
#include <proj_classes.h>

#define DIMOF(a)	(sizeof(a)/sizeof(a[0]))


/// Structure mapping @ref pcap_protocols bits to the corresponding pcap filter expressions.
static struct pcap_filter_info {
	const unsigned	filterbit;
	const char *	filter;
}filterinfo[] = {
	{ENABLE_LLDP,	"(ether dst 01:80:c2:00:00:0e and ether proto 0x88cc)"},
	{ENABLE_CDP,	"(ether dst 01:00:0c:cc:cc:cc and ether[20:2] = 0x2000 and ether[12:2] <= 1500 and "
                         "ether[14:2] = 0xAAAA and ether[16:1] = 0x03 and ether[17:2] = 0x0000 and ether[19:1] = 0x0C)"},

};

DEBUGDECLARATIONS

/**
 *  Set up pcap listener for the given interfaces and protocols.
 *  @return a properly configured pcap_t* object for listening for the given protocols - NULL on error
 *  @see pcap_protocols
 */
pcap_t*
create_pcap_listener(const char * dev		///<[in] Device name to listen on
,		     gboolean blocking		///<[in] TRUE if this is a blocking connection
,		     unsigned listenmask	///<[in] Bit mask of protocols to listen for
						///< (see @ref pcap_protocols "list of valid bits")
,		     struct bpf_program*prog)	///<[out] Compiled PCAP program
{
	pcap_t*			pcdescr;
	bpf_u_int32		maskp;
	bpf_u_int32		netp;
	char			errbuf[PCAP_ERRBUF_SIZE];
	char *			expr;
	int			filterlen = 1;
	unsigned		j;
	int			cnt=0;
	int			rc;
	const char ORWORD [] = " or ";

	BINDDEBUG(pcap_t);
//	setbuf(stdout, NULL);
	setvbuf(stdout, NULL, _IONBF, 0);
	errbuf[0] = '\0';

	// Search the list of valid bits so we can construct the libpcap filter
	// for the given set of protocols on the fly...
	// On this pass we just compute the amount of memory we'll need...
	for (j = 0, cnt = 0; j < DIMOF(filterinfo); ++j) {
		if (listenmask & filterinfo[j].filterbit) {
			++cnt;
			if (cnt > 1) {
				filterlen += sizeof(ORWORD);
			}
			filterlen += strlen(filterinfo[j].filter);
		}
	}
	
	if (filterlen < 2) {
		g_warning("Constructed filter is too short - invalid mask argument.");
		return NULL;
	}
	if (NULL == (expr = malloc(filterlen))) {
		g_error("Out of memory!");
		return NULL;
	}
	// Same song, different verse...
	// This time around, we construct the filter
	expr[0] = '\0';
	for (j = 0, cnt = 0; j < DIMOF(filterinfo); ++j) {
		if (listenmask & filterinfo[j].filterbit) {
			++cnt;
			if (cnt > 1) {
				g_strlcat(expr, ORWORD, filterlen);
			}
			g_strlcat(expr, filterinfo[j].filter, filterlen);
		}
	}
	if (pcap_lookupnet(dev, &netp, &maskp, errbuf) != 0) {
		g_warning("pcap_lookupnet failed: [%s]", errbuf);
		return NULL;
	}
	
	if (NULL == (pcdescr = pcap_create(dev, errbuf))) {
		g_warning("pcap_create failed: [%s]", errbuf);
		return NULL;
	}
	//pcap_set_promisc(pcdescr, FALSE);
	pcap_set_promisc(pcdescr, TRUE);	/// @todo: figure out why we need promiscuous mode.
#ifdef HAVE_PCAP_SET_RFMON
	pcap_set_rfmon(pcdescr, FALSE);
#endif
	pcap_setdirection(pcdescr, PCAP_D_IN);
	// Weird bug - returns -3 and doesn't show an error message...
	// And pcap_getnonblock also returns -3... Neither should happen AFAIK...
	if ((rc = pcap_setnonblock(pcdescr, !blocking, errbuf)) < 0 && errbuf[0] != '\0') {
		g_warning("pcap_setnonblock(%d) failed: [%s] [rc=%d]", !blocking, errbuf, rc);
		g_warning("Have no idea why this happens - current blocking state is: %d."
		,	pcap_getnonblock(pcdescr, errbuf));
	}
	pcap_set_snaplen(pcdescr, 1500);
	/// @todo deal with pcap_set_timeout() call here.
	if (blocking) {
		pcap_set_timeout(pcdescr, 240*1000);
	}else{
		pcap_set_timeout(pcdescr, 1);
	}
	//pcap_set_buffer_size(pcdescr, 1500);
      
	if (pcap_activate(pcdescr) != 0) {
		g_warning("pcap_activate failed: [%s]", pcap_geterr(pcdescr));
		return(NULL);
	}
	if (pcap_compile(pcdescr, prog, expr, FALSE, maskp) < 0) {
		g_warning("pcap_compile of [%s] failed: [%s]", expr, pcap_geterr(pcdescr));
		return(NULL);
	}
	if (pcap_setfilter(pcdescr, prog) < 0) {
		g_warning("pcap_setfilter on [%s] failed: [%s]", expr, pcap_geterr(pcdescr));
		return(NULL);
	}
	DEBUGMSG1("Compile of [%s] worked!\n", expr);
	free(expr); expr = NULL;
	return(pcdescr);
}
