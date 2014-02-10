/**
 * @file
 * @brief Implements minimal client-oriented LLDP capabilities
 * @details This file contains the minimal LLDP capability for a client - enough for it to be able to
 * understand and validate a CDP packet's structure, return any particular TLV
 * and specifically to be able to locate the chassis id and port id (which the client needs).
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

#include <stdio.h>
#include <string.h>
#include <lldp.h>
#include <tlvhelper.h>
#define	DIMOF(a)	(sizeof(a)/sizeof(a[0]))
/** @defgroup lldp_format Layout of LLDP packets
 *  @ingroup WireDataFormats
 * The Link Layer Discovery Protocol is a layer two discovery protocol which we receive and interpret, but do not send.
 * The LLDP protocol is defined by the 802.1AB specification, described in IEEE document entitled
 * Station and Media Access Control Connectivity Discovery.
 * This information is mostly derived
 * from that specification.
 *
 * All LLDP packets consist of a set of Type/Length/Value entries, ending in a
 * zero (LLDP_TLV_END) entry with zero bytes.  It appears that some implementations
 * may omit this final terminator entry, even though it's required by the spec...
 *
 * The format of the LLDP TLV entries is shown below:
 * <PRE>
 * +------------------------------------------------------------+
 * | Type (7-bits) | Length (9 bits) | Value (arbitrary length) |
 * +------------------------------------------------------------+
 * </PRE>
 * Note that the TLV header (Type + Length) is two bytes with the low-order bit
 * in the first byte serving as the high-order bit of the length field.
 * The TLV types are defined in @ref lldp_type_fields "lldp.h".
 *
 * For TLVs of type @c LLDP_TLV_ORG_SPECIFIC (127) additional fields are defined
 * for the purpose of extending the format by specific organizations.
 * Those packets look like this:
 * <PRE>
 * +--------+----------+-------------------------------+------------+
 * |  Type  |  Length |   OUI   | org-defined subtype | org-defined |
 * | 7 bits |  9 bits | 3 bytes |      1 byte         | info string |
 * +--------+---------+---------+---------------------+-------------+
 * </PRE>
 * The OUI == Organizational Unique Identifier - which is IEEE's way
 * of giving each organization their own name space.  The entire list
 * is <i>very</i> long, but a few of them are defined in the 802.1AB spec.
 * These are:
 * - 00-80-C2 @ref lldp_oui_802_1 "IEEE 802.1"
 * - 00-12-0F @ref lldp_oui_802_3 "IEEE 802.3"
 */

/** @defgroup lldp_pkt_offsets LLDP: offsets for LLDP packets
 *  @{ 
 *  @ingroup lldp_format
 */
#define		NETTLV_INITPKTOFFSET	14
#define		NETTLV_HDRSZ	2
/// @} 



/// Return the 'Type' of the given LLDP <b>T</b>LV entry
/// The Type is the high order 7 bits from the zeroth byte in the TLV entry.
guint8
get_lldptlv_type(const void* tlv_vp,  ///<[in] Pointer to beginning of TLV entry
		 const void* pktend)  ///<[in] Pointer to one byte past end of packet
{
	return (guint8)((tlv_get_guint8(tlv_vp, pktend)>>1) & 0x7F);
}

/// Return the 'Length' of the given LLDP T<b>L</b>V entry.
/// The length is the low order bit from the zeroth byte
/// plus all 8 bits of the second byte
gsize
get_lldptlv_len(const void* tlv_vp,	///<[in] Pointer to beginning of TLV entry
		const void* pktend)	///<[in] Pointer to one byte past end of packet
{
	const unsigned char * tlvp = tlv_vp;
	guint8 byte0 = tlv_get_guint8(tlvp, pktend);
	guint8 byte1 = tlv_get_guint8(tlvp+1, pktend);

	return ((((gsize)(byte0&0x1)) << 8) & (gsize)0x1FF)
	       |	((gsize)byte1) ;
}

/// Return the 'Value' of the given LLDP TL<b>V</b> entry
const void *
get_lldptlv_body(const void * tlv_vp,	///<[in] Pointer to beginning of TLV entry,
		 const void* pktend)	///<[in] Pointer to one byte past end of packet
{
	(void)pktend;
	return ((const guint8*)tlv_vp + NETTLV_HDRSZ);
}

/// @todo validate destination MAC 01:80:c2:00:00:0e and Ethernet protocol 0x88cc.
/// Return TRUE if this is a valid LLDP packet.
gboolean
is_valid_lldp_packet(const void* tlv_vp,	//<[in] pointer to beginning pf LLDP packet
                     const void* pktend)	//<[in] pointer to first byte past the end of the packet
{
	const unsigned	reqtypes [] = {LLDP_TLV_CHID,LLDP_TLV_PID, LLDP_TLV_TTL};
	unsigned	j = 0;
#ifdef PEDANTIC_LLDP_NERD
	int		lasttype = -1;
#endif
	if (NULL == tlv_vp || ((const guint8*)tlv_vp+NETTLV_HDRSZ)  > (const guint8*)pktend) {
		g_warning("LLDP Invalid because packet is too short\n");
		return FALSE;
	}
	for (tlv_vp = get_lldptlv_first(tlv_vp, pktend)
	;	NULL != tlv_vp
	;	tlv_vp = get_lldptlv_next(tlv_vp, pktend)) {
		unsigned	ttype;
		unsigned	length;
		const guint8*	next;

		if (tlv_vp >= pktend) {
			return FALSE;
		}
		ttype = get_lldptlv_type(tlv_vp, pktend);
#ifdef PEDANTIC_LLDP_NERD
		lasttype = ttype;
#endif
		length = get_lldptlv_len(tlv_vp, pktend);
		next = (const guint8*)tlv_vp + (length+NETTLV_HDRSZ);
		if (next > (const guint8*)pktend) {
			g_warning("LLDP Invalid because TLV entry extends past end\n");
			return FALSE;
		}
		if (ttype == LLDP_TLV_END) {
			if (get_lldptlv_body(tlv_vp, pktend) == pktend) {
				return length == 0;
			}else{
				g_warning("LLDP Invalid because END item isn't at end of packet\n");
				return FALSE;
			}
		}
		if (j < DIMOF(reqtypes) && ttype != reqtypes[j]) {
			g_warning("LLDP Invalid because required TLV type [%d] isn't present in right position (%d)\n"
			,	reqtypes[j], j);
			return FALSE;
		}
		j += 1;
	}
#ifdef PEDANTIC_LLDP_NERD
	if (lasttype != LLDP_TLV_END) {
		g_warning("LLDP Invalid because final type wasn't LLDP_TLV_END (it was %d)\n"
		,	lasttype);
		return FALSE;
	}
#endif
	return TRUE;
}

const void *
get_lldptlv_first(const void* packet,	///<[in] Pointer to beginning of LLDP packet
                  const void* pktend)	///<[in] Pointer to first byte after the end of the LLDP packet
{
	const guint8*	inittlv = (const guint8*)packet + NETTLV_INITPKTOFFSET;
	if (packet == NULL
	||	(inittlv + NETTLV_HDRSZ) > (const guint8*)pktend
	||	(inittlv + NETTLV_HDRSZ + get_lldptlv_len(inittlv, pktend)) > (const guint8*)pktend) {
		return NULL;
	}
	return inittlv;
}

/// Return pointer to the next LLDP TLV entry after the current location
const void *
get_lldptlv_next(const void* tlv_vp,		///<[in] Pointer to  current LLDP TLV entry
                  const void* pktend)	///<[in] Pointer to first byte after the end of the LLDP packet
{
	const guint8 *	nexttlv;
	const void*	nextend;
	if (tlv_vp == NULL
        ||  ((const guint8*)tlv_vp+NETTLV_HDRSZ) > (const guint8*)pktend
        ||  get_lldptlv_type(tlv_vp, pktend) == LLDP_TLV_END) {
		return NULL;
	}
	nexttlv = (const guint8*)tlv_vp  + NETTLV_HDRSZ + get_lldptlv_len(tlv_vp, pktend);
	/* Watch out for malformed packets! (BLACKHAT, PARANOIA) */
	nextend = nexttlv + NETTLV_HDRSZ + get_lldptlv_len(nexttlv, pktend);
	/* fprintf(stderr, "LOOK: cur:%p, next: %p, nextend: %p, vpend: %p\n"
	,	tlv_vp, nexttlv, nextend, pktend); */
	return nextend > pktend ? NULL : nexttlv;
}

/// Return pointer to the next LLDP entry of the given type at or after the current location
const void *
find_next_lldptlv_type(const void* tlv_vp,	///< [in] Pointer to the current TLV
                       unsigned tlvtype,	///< [in] Type of TLV we're looking for
                       const void* pktend)	///< [in] Pointer to first byte beyond the packet.
{
	while (NULL != tlv_vp && ((const guint8*)tlv_vp+NETTLV_HDRSZ) <= (const guint8*)pktend) {
		if (get_lldptlv_type(tlv_vp, pktend) == tlvtype) {
			return tlv_vp;
		}
		tlv_vp = get_lldptlv_next(tlv_vp, pktend);
	}
	return NULL;
}

/// Return a pointer to the chassis id Value entry, and its length.
///@return pointer to the chassis ID value, and its length.
const void *
get_lldp_chassis_id(gconstpointer	tlv_vp,		///<[in] Pointer to beginning of LLDP packet
                    gssize*		idlength,	///<[out] Length of the chassis id
                    gconstpointer	pktend)		///<[in] Pointer to first byte beyond packet.
{
	const void *	tlventry;
	tlv_vp = get_lldptlv_first(tlv_vp, pktend);
	tlventry = find_next_lldptlv_type(tlv_vp, LLDP_TLV_CHID, pktend);
	if (tlventry == NULL) {
		return NULL;
	}
	*idlength = get_lldptlv_len(tlv_vp, pktend);
	return get_lldptlv_body(tlv_vp, pktend);
}

/// Return a pointer to the port id Value entry, and its length.
///@return pointer to the port ID value, and its length.
const void *
get_lldp_port_id(gconstpointer tlv_vp,	///<[in] Pointer to beginning of LLDP packet
                 gssize* idlength,	///<[out] Length of the port id value
                 gconstpointer pktend)	///<[in] Pointer to first byte beyond packet.
{
	const void *	tlventry;
	tlv_vp = get_lldptlv_first(tlv_vp, pktend);
	tlventry = find_next_lldptlv_type(tlv_vp, LLDP_TLV_PID, pktend);
	if (tlventry == NULL) {
		return NULL;
	}
	*idlength = get_lldptlv_len(tlv_vp, pktend);
	return get_lldptlv_body(tlv_vp, pktend);
}
