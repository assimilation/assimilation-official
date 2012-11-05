/**
 * @file
 * @brief Implements server-side CDP capabilities - things the client side won't need.
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
#include <stdio.h>
#ifdef _MSC_VER
#include <winsock2.h>
#else
#include <netinet/in.h>
#endif
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

		fprintf(stdout, "CDP TLV type: %s, length: %"G_GSIZE_FORMAT", values: "
		,	get_cdp_type_string(ttype), tlen);
		dump_mem(tbody, tbody+tlen);
		fprintf(stdout, "\n");
	}
}
