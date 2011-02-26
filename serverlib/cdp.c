/**
 * @file
 * @brief Implements server-side CDP capabilities - things the client side won't need.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <projectcommon.h>
#include <stdio.h>
#include <netinet/in.h>
#include "cdp.h"
#include <server_dump.h>

/**
 * Map of CDP types into strings...
 */
static const char*	cdptypenames[] = 
{	"*INVALIDCDPTYPE-0*"
,	"chassis_id"
,	"mgmt_address"
,	"port_id"
,	"capabilities"
,	"version"
,	"platform"
,	"ipprefix"
,	"hello_protocol"
,	"vtp_domain"
,	"native_vlan"
,	"duplex"
,	"appliance_id"
,	"power_consumption"
,	"*UNKNOWNCDPTYPE-15*"
,	"*UNKNOWNCDPTYPE-16*"
,	"*UNKNOWNCDPTYPE-17*"
,	"*UNKNOWNCDPTYPE-18*"
,	"*UNKNOWNCDPTYPE-19*"	///< Have actually seen these -- Wonder what they are...
,	"*UNKNOWNCDPTYPE-20*"	///< Have actually seen these -- Wonder what they are...
,	"*UNKNOWNCDPTYPE-21*"
,	"*UNKNOWNCDPTYPE-22*"	///< Others report seeing these...
,	"*UNKNOWNCDPTYPE-23*"
,	"*UNKNOWNCDPTYPE-24*"
,	"*UNKNOWNCDPTYPE-25*"
,	"*UNKNOWNCDPTYPE-26*"
,	"*UNKNOWNCDPTYPE-27*"
,	"*UNKNOWNCDPTYPE-28*"
,	"*UNKNOWNCDPTYPE-29*"
,	"*UNKNOWNCDPTYPE-30*"
,	"*UNKNOWNCDPTYPE-31*"
,	"*UNKNOWNCDPTYPE-32*"
,	"*UNKNOWNCDPTYPE-33*"
};

const char * get_cdp_type_string(unsigned);
void dump_cdp_packet(const void*, const void*);

/// Translate a CDP TLV type into a string.
/// @return pointer to a constant/static string describing the type of this TLV.
const char *
get_cdp_type_string(unsigned cdptype) ///< [in] CDP TLV type
{
	if (cdptype < DIMOF(cdptypenames)) {
		return cdptypenames[cdptype];
	}
        return "UNKNOWN";
}

/// Dump out a CDP packet - not very intelligently
void
dump_cdp_packet(const void* vpacket,	///< [in]Pointer to a the start of a CDP packet
                const void* vpktend)	///< [in]Pointer of first byte past end of CDP packet
{
	const guchar*	packet = vpacket;
	const guchar*	pktend = vpktend;
	const guchar*	tlv_vp;

	if (NULL == packet
	||  !is_valid_cdp_packet(packet, pktend)) {
		fprintf(stderr, "%ld byte packet at address %p is not a valid CDP packet.\n"
		,	(long)(pktend-packet), packet);
		return;
	}
	fprintf(stdout, "{CDP vers: %d, cksum: 0x%04x, ttl: %d}\n"
	,	get_cdp_vers(packet, pktend), get_cdp_cksum(packet, pktend), get_cdp_ttl(packet, pktend));

	for (tlv_vp = get_cdptlv_first(packet, pktend)
	;	tlv_vp != NULL
	;	tlv_vp = get_cdptlv_next(tlv_vp, pktend)) {
		unsigned		ttype	= get_cdptlv_type(tlv_vp, pktend);
		gsize			tlen	= get_cdptlv_vlen(tlv_vp, pktend);
		const unsigned char*	tbody	= get_cdptlv_body(tlv_vp, pktend);

		fprintf(stdout, "CDP TLV type: %s, length: %zd, values: "
		,	get_cdp_type_string(ttype), tlen);
		dump_mem(tbody, tbody+tlen);
		fprintf(stdout, "\n");
	}
}
