/**
 * @file
 * @brief Implements minimal client-oriented CDP capabilities
 * @details This file contains the minimal CDP capability for a client - enough for it to be able to
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
 *  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/.
 */
#include <stdio.h>

#ifdef _MSC_VER
#	include <winsock.h>
#else
#	include <netinet/in.h>
#endif

#include <cdp.h>
#include <tlvhelper.h>
/**
 * @defgroup cdp_format Layout of CDP Packets
 * @ingroup WireDataFormats
 * CDP is the Cisco Discovery Protocol - which we receive and interpret, but don't send.
 * CDP packets consist of a 4-byte initial header, followed by any number of Type/Length/Value (TLV)
 * sections.  A CDP packet should never exceed 1500 bytes,
 * because they are restricted to single ethernet-level frames.
 * The initial header portion (after ethernet and SNAP headers) is laid out as shown below:
 * <PRE>
 * +----------------------+------------------------+---------------+
 * | CDP Protocol Version | CDP Time To Live (TTL) | CDP Checksum  |
 * |       1 byte         |        1 byte          |    2 bytes    |
 * +----------------------+------------------------+---------------+
 * </PRE>
 */
/** @defgroup  cdp_prelude_offsets CDP: Offsets of initial non-TLV items in a CDP packet.
 *  The initial items are a checksum, protocol version, and the time to live of the packet.
 *  These all come before the TLV portion of the CDP packet.
 *
 *  CDP packets are encoded with SNAP (Subnet Access Protocol) headers
 *  @see get_cdptlv_first
 *  @{ 
 *  @ingroup cdp_format
 */
/// Number of bytes before the CDP packet itself starts
#define		CDP_OVERHEAD		22
/// Size of the CDP version object in a CDP packet
#define		CDP_VERSSZ		1
/// Size of the Time to Live (TTL) object in a CDP packet
#define		CDP_TTLSZ		1
/// Size of the checksum object in a CDP packet
#define		CDP_CKSUMSZ		2
/// Start of the TLV (type, length, value) portion of a CDP packet
#define		CDPINITHDRSZ		(CDP_OVERHEAD+CDP_VERSSZ+CDP_TTLSZ+CDP_CKSUMSZ) /* 26 */
/// @}
/** @defgroup  cdp_tlv_offsets CDP: Sizes of the type and length portion of a CDP TLV entry.

 *  Offsets of things that occur at the beginning of each TLV entry 
 *  @see get_cdptlv_type, get_cdptlv_len, get_cdptlv_vlen, cdptlv_body
 *  @{ 
 *  @ingroup cdp_format
 */
///		Size of the type element in the CDP TLV triple
#define		CDPTLV_TYPESZ		2
///		Size of the length element in a CDP TLV
#define		CDPTLV_LENSZ		2
///		Overhead - offset to the beginning of the CDP TLV Value
#define		CDPTLV_TYPELENSZ	(CDPTLV_TYPESZ+CDPTLV_LENSZ) /* 4 */
/// @}


/// Check to see if this is a valid CDP packet.
/// We validate that it is completely well-formed, and not dangerous to process
/// to the best of our knowledge - watching especially for buffer-overrun type
/// issues in the structure of the packet.
/// @return TRUE if this is a valid CDP packet, FALSE otherwise.
/// @todo validate dest MAC address (01:00:0c:cc:cc:cc) before looking at anything else...
WINEXPORT gboolean
is_valid_cdp_packet(const void* packet,		///< [in]Start of CDP packet
                    const void* pktend)	///< [in]First byte after the last CDP packet byte
{
	const unsigned	reqtypes [] = {1};	// The set of required initial TLV types
						// The LLDP list is slighly more impressive ;-)
	unsigned	j = 0;
	const void*	tlv_vp;			// Pointer to a TLV entry in the CDP packet.
	const void*	next = NULL;
	unsigned	vers;


	fprintf(stderr, "Validating CDP packet: %p,  pktend: %p\n", packet, pktend);
	if ((const void *)((const unsigned char *)packet+CDPTLV_TYPELENSZ)  > pktend || packet == NULL) {
                fprintf(stderr, "BAD1 packet: %p,  pktend: %p\n", packet, pktend);
		return FALSE;
	}
	/* Heuristic - at this writing, version could be 1 or 2 - Cisco currently defaults to 2 ... */
	if ((vers=get_cdp_vers(packet, pktend)) < 1 || vers > 4
	||  get_cdp_ttl(packet, pktend) < 3) {
                fprintf(stderr, "BAD2 packet: %p,  pktend: %p [vers=%d, ttl=%d]\n", packet, pktend
		,	get_cdp_vers(packet, pktend), get_cdp_ttl(packet, pktend));
		return FALSE;
	}

	for (tlv_vp = get_cdptlv_first(packet, pktend)
	;    NULL != tlv_vp && tlv_vp < pktend
	;    tlv_vp = next) {
		unsigned	ttype;
		unsigned	length;

		ttype  = get_cdptlv_type(tlv_vp, pktend);
		length = get_cdptlv_len (tlv_vp, pktend);
		next = (const void *)((const unsigned char *)tlv_vp + length);
		if ((const void *)((const unsigned char *)tlv_vp+CDPTLV_TYPELENSZ) > pktend) {
			fprintf(stderr, "BAD3 tlv_vp: %p,  pktend: %p j=%d [vers=%d, ttl=%d]\n"
			,	tlv_vp, pktend, j
			,	get_cdp_vers(packet, pktend), get_cdp_ttl(packet, pktend));
			return FALSE;
		}
		if (next > pktend
		||	length < CDPTLV_TYPELENSZ
		||	(j < DIMOF(reqtypes) && ttype != reqtypes[j])) {
                	fprintf(stderr, "BAD4 packet: %p,  pktend: %p, next %p, frame %d, type %d\n"
			,	packet, pktend, next, j, ttype);
			return FALSE;
		}
		j += 1;
	}
	// The only way to exit that loop without returning FALSE is if tlp_vp == pktend
	return TRUE;
}

/// Return the CDP protocol version for this packet.  This is normally 2.
/// The CDP protocol version is not part of the TLVs in a CDP packet.
WINEXPORT guint8
get_cdp_vers(const void* pktptr, ///<[in] Pointer to beginning of the CDP packet
             const void* pktend) ///<[in]Pointer of first byte past end of CDP packet
{
	const unsigned char *	pkt_uc = pktptr;
	return tlv_get_guint8(pkt_uc+CDP_OVERHEAD, pktend);
}

/// Return the time to live for this CDP packet.
/// The TTL is not part of the TLVs in a CDP packet.
/// @return time to live (TTL) in seconds
WINEXPORT guint8
get_cdp_ttl(const void* pktptr, ///< [in]Pointer to beginning of the CDP packet
            const void* pktend) ///<[in]Pointer of first byte past end of CDP packet
{
	const unsigned char *	pkt_uc = pktptr;
	return tlv_get_guint8(pkt_uc+CDP_OVERHEAD+1, pktend);
}
/// Return the 16-bit checksum for this CDP packet.
/// The checksum is not part of the TLVs, so the input pointer is to the CDP packet
/// not the first TLV in the packet.
WINEXPORT guint16
get_cdp_cksum(const void* pktptr, ///< [in]Pointer to beginning of CDP packet
              const void* pktend) ///<[in]Pointer of first byte past end of CDP packet
{
	const unsigned char *	pkt_uc = pktptr;
	return tlv_get_guint16(pkt_uc+CDP_OVERHEAD+2, pktend);
}

/// Return type from the given TLV triplet in a CDP packet.
/// @return type value from CDP TLV triple
WINEXPORT guint16
get_cdptlv_type(const void* tlv_vp,  ///< [in]Should be the a CDP TLV object from get_cdbtlv_first
				     ///< or get_cdp_tlv_next, etc.
              const void* pktend)    ///<[in]Pointer of first byte past end of CDP packet
{
	return tlv_get_guint16(tlv_vp, pktend);
}

/// Return size of the given TLV triplet.
/// @return size of the entire TLV triplet - including size of T and L as well as V.
WINEXPORT gsize
get_cdptlv_len(const void* tlv_vp,   ///< [in]Should be the a CDP TLV object from get_cdbtlv_first
				     ///< or get_cdp_tlv_next, etc.
               const void* pktend)    ///<[in]Pointer of first byte past end of CDP packet
{
	const unsigned char* tlv_uc = tlv_vp;
	return tlv_get_guint16(tlv_uc+2, pktend);
}
/// Return length of the value blob int a given TLV triplet in a CDP packet - value size only.
/// @return number of bytes in the Value portion of the CDP TLV pointed to in the input
/// @see get_cdptlv_body
WINEXPORT gsize
get_cdptlv_vlen(const void* tlv_vp,  ///< [in]Should be the a CDP TLV object from get_cdbtlv_first(),
				     ///< or get_cdp_tlv_next(), etc.
                const void* pktend)  ///<[in]Pointer of first byte past end of CDP packet
{
	return (unsigned)(get_cdptlv_len(tlv_vp, pktend) - CDPTLV_TYPELENSZ);
}

/// Return the body (value) blob of a CDP TLV triplet
/// @return pointer to the value blob of a CDP TLV triplet.
/// Length of this blob is given by get_cdptlv_vlen().
/// @see get_cdptlv_vlen
WINEXPORT const void *
get_cdptlv_body(const void* tlv_vp,	///< [in]Should be the a CDP TLV object from get_cdbtlv_first()
					///< or get_cdp_tlv_next(), etc.
                const void* pktend)     ///<[in]Pointer of first byte past end of CDP packet
{
	g_return_val_if_fail(tlv_vp < pktend, NULL);
	return (const void*)((const unsigned char *)tlv_vp + CDPTLV_TYPELENSZ);
}
/// Return the first CDP TLV triple in a CDP packet.
/// @return pointer to the first CDP TLV triple in the packet - or NULL if none.
/// Note that this will <B>never</B> return a pointer to a TLV which extends past tlv_vpend.
WINEXPORT const void *
get_cdptlv_first(const void* pkt,	///< [in]Pointer to start of CDP packet
                 const void* pktend)	///< [in]First byte after the last CDP packet byte
{
	gsize			len = (const char *)pktend - (const char *)pkt;
	const unsigned char*	ret = (const unsigned char*)pkt;
	unsigned		vers;
	/*fprintf(stderr, "%s.%d: pkt %p, pktend %p, len %d\n", __FUNCTION__, __LINE__
	,	pkt, pktend, (int)len);*/
	if (ret == NULL || len < (CDPINITHDRSZ + CDPTLV_TYPELENSZ)
	/* Note that these version and ttl constraints are heuristics, not absolutes */
	||  (vers=get_cdp_vers(ret, pktend)) < 1 || vers > 5
	||  get_cdp_ttl(ret, pktend) < 2) {
		/*fprintf(stderr, "%s.%d: pkt %p, pktend %p, len %d vers %d ttl %d\n"
		,	__FUNCTION__, __LINE__
		,	pkt, pktend, (int)len, vers, get_cdp_ttl(ret, pktend));*/
		return NULL;
	}
	ret += CDPINITHDRSZ;
	if ((ret + get_cdptlv_len(ret, pktend)) > (const unsigned char *)pktend) {
		/*fprintf(stderr, "%s.%d: pkt %p, pktend %p, tlvlen %d\n"
		,	__FUNCTION__, __LINE__,	pkt, pktend, (int)get_cdptlv_len(ret, pktend));*/
		return NULL;
	}
	/*fprintf(stderr, "%s.%d: pkt %p, pktend %p, returning %p\n"
	,	__FUNCTION__, __LINE__,	pkt, pktend, ret);*/
	return (const void *)ret;
}
/// Locate the next CDP TLV triple (iterator).
/// @return pointer to the next CDP TLV triple in the sequence - or NULL if none.
/// Note that this will <B>never</B> return a pointer to a TLV which extends past tlv_vpend.
WINEXPORT const void *
get_cdptlv_next(const void* tlv_vp, 	///< [in]Pointer to first byte of current TLV triple
                const void* tlv_vpend)	///< [in]First byte after the last CDP packet byte
{
	const unsigned char*	nexttlv;
	const unsigned char*	nextend;
	if (tlv_vp == NULL) {
		return NULL;
	}
	nexttlv = (const unsigned char*)tlv_vp  + get_cdptlv_len(tlv_vp, tlv_vpend);
	if ((const void *)(nexttlv + CDPTLV_TYPELENSZ) > tlv_vpend) {
		// In an ideal world nexttlv would exactly equal tlv_vpend...
		return NULL;
	}
	/* Watch out for malformed packets! (BLACKHAT, PARANOIA) */
	nextend = nexttlv + get_cdptlv_len(nexttlv, tlv_vpend);
	return ((const void *)nextend > tlv_vpend) ? NULL : nexttlv;
}


/// Get the chassis ID associated with this CDP packet.
/// @return pointer to chassis ID memory area and also length of the chassis ID
WINEXPORT const void*
get_cdp_chassis_id(gconstpointer packet,		///< [in]Pointer to a the start of a CDP packet
                   gssize*     idlength,	///< [out]length of chassis id
                   gconstpointer pktend)		///< [in]Pointer of first byte past end of CDP packet
{
	const void *	tlv_vp;
	for (tlv_vp=get_cdptlv_first(packet, pktend);
	     tlv_vp != NULL;
	     tlv_vp = get_cdptlv_next(tlv_vp, pktend)) {
		if (get_cdptlv_type(tlv_vp, pktend) == CDP_TLV_DEVID) {
			*idlength = get_cdptlv_vlen(tlv_vp, pktend);
			return get_cdptlv_body(tlv_vp, pktend);
		}
		tlv_vp = get_cdptlv_next(tlv_vp, pktend);
	}
	return NULL;
}


/// get the port ID associated with this CDP packet
/// @return pointer to port ID memory area and also length of the port ID
WINEXPORT const void*
get_cdp_port_id(gconstpointer packet,	///< [in]Pointer to a the start of a CDP packet
                gssize*     idlength,	///< [out]length of chassis id
                gconstpointer pktend)	///< [in]Pointer of first byte past end of CDP packet
{
	const void *	tlv_vp;
	for (tlv_vp=get_cdptlv_first(packet, pktend);
	     tlv_vp != NULL;
	     tlv_vp = get_cdptlv_next(tlv_vp, pktend)) {
		if (get_cdptlv_type(tlv_vp, pktend) == CDP_TLV_PORTID) {
			*idlength = get_cdptlv_vlen(tlv_vp, pktend);
			return get_cdptlv_body(tlv_vp, pktend);
		}
		tlv_vp = get_cdptlv_next(tlv_vp, pktend);
	}
	return NULL;
}
