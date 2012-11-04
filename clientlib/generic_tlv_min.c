/**
 * @file
 * @brief Implements minimal client-oriented Generic TLV capabilities.
 * @details This file implements minimal Generic TLV capabiliies for a client -
 * enough for it to be able to understand and validate a generic TLV packet structure,
 * iterate through these generic TLVs, and return any particular TLV.
 * For the most part, these TLVs correpond to our @ref Frame objects.
 * @see Frame
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <stdio.h>
#include <string.h>
#include <tlvhelper.h>
#include <frametypes.h>
#include <generic_tlv_min.h>

///@defgroup GenericTLV Generic TLV capabilities
///@{
///@brief Implements a set of client-oriented TLV (Type, Length, Value) capabilities.
///@details These capabilities are the core of our packet assembly/disassembly infrastructure.
///Everything we send is wrapped in a @ref Frame, or a @ref FrameSet, and those both make extensive
///use of the capabilties defined here.

/// Size of Generic TLV header -  ((type + length) == 4)
#define	GENERICTLV_HDRSZ	(sizeof(guint16)+sizeof(guint16))

/// Return the 'Type' of the given TLV <b>T</b>LV entry (first two bytes)
guint16
get_generic_tlv_type(gconstpointer tlv_vp,  ///<[in] Pointer to beginning of TLV entry
		 gconstpointer pktend)  ///<[in] Pointer to one byte past end of packet
{
	return tlv_get_guint16(tlv_vp, pktend);
}

/// Set the 'Type' of the given TLV <b>T</b>LV entry (first two bytes)
void
set_generic_tlv_type(gpointer tlv_vp,	///<[in] Pointer to beginning of TLV entry
		 guint16 newtype,		///<[in] Type to stuff into TLV entry
		 gconstpointer pktend)		///<[in] Pointer to one byte past end of packet
{
	tlv_set_guint16(tlv_vp, newtype, pktend);
}

/// Return the 'Length' of the given generic T<b>L</b>V entry (second short in packet)
guint16
get_generic_tlv_len(gconstpointer tlv_vp,	///<[in] Pointer to beginning of TLV entry
		gconstpointer pktend)	///<[in] Pointer to one byte past end of packet
{
	const guint8 * tlvp = tlv_vp;
	return tlv_get_guint16(tlvp+sizeof(guint16), pktend);
}

/// Set the 'Length' of the given generic T<b>L</b>V entry (second short in packet)
void
set_generic_tlv_len(gpointer tlv_vp,	///<[in] Pointer to beginning of TLV entry
		 guint16 newsize,		///<[in] Type to stuff into TLV entry
		 gconstpointer pktend)		///<[in] Pointer to one byte past end of packet
{
	guint8 * tlvp = tlv_vp;
	tlv_set_guint16(tlvp+sizeof(guint16), newsize, pktend);
}

/// Return a const pointer to the 'Value' of the given generic TL<b>V</b> entry
gconstpointer
get_generic_tlv_value(gconstpointer tlv_vp,	///<[in] Pointer to beginning of TLV entry,
		 gconstpointer pktend)		///<[in] Pointer to one byte past end of packet
{
	const guint8*	tlvbytes = tlv_vp;
	(void)pktend;
	return (tlvbytes + GENERICTLV_HDRSZ);
}

/// Return a non-const (mutable) pointer to the 'Value' of the given generic TL<b>V</b> entry
gpointer
get_generic_tlv_nonconst_value(gpointer tlv_vp,	///<[in] Pointer to beginning of TLV entry,
		 gconstpointer pktend)		///<[in] Pointer to one byte past end of packet
{
	guint8*	tlvbytes = tlv_vp;
	(void)pktend;
	return (tlvbytes + GENERICTLV_HDRSZ);
}

/// Set the TLV data value to the given 'tlv_vp' pointer.
/// @pre length must have already been set in the TLV
void
set_generic_tlv_value(gpointer tlv_vp,		///< pointer to TLV entry
		      void* srcdata,		///< pointer to source data
		      guint16 srcsize,		///< size of source object
		      gconstpointer pktend)	///<[in] Pointer to one byte past end of packet
{
	guint8*		tlvbytes = tlv_vp;
	g_return_if_fail((gpointer)(tlvbytes+srcsize) <= pktend);
	g_return_if_fail(srcsize == get_generic_tlv_len(tlv_vp, pktend));
	memcpy(tlvbytes + GENERICTLV_HDRSZ, srcdata, srcsize);
}

/// Return TRUE if this is a valid generic TLV packet.
gboolean
is_valid_generic_tlv_packet(gconstpointer tlv_vp,	//<[in] pointer to beginning of generic TLV packet
                     gconstpointer pktend)	//<[in] pointer to first byte past the end of the packet
{
	const guint16	reqtypes [] = {FRAMETYPE_SIG};
	unsigned	j = 0;
	int		lasttype = -1;
	if (NULL == tlv_vp || ((const guint8*)tlv_vp+GENERICTLV_HDRSZ)  > (const guint8*)pktend) {
		fprintf(stderr, "TLV Invalid because packet is too short\n");
		return FALSE;
	}
	for (tlv_vp = get_generic_tlv_first(tlv_vp, pktend)
	;	NULL != tlv_vp
	;	tlv_vp = get_generic_tlv_next(tlv_vp, pktend)) {

		guint16		ttype;
		guint16		length;
		const guint8*	next;

		if (tlv_vp >= pktend) {
			return FALSE;
		}
		ttype = get_generic_tlv_type(tlv_vp, pktend);
		lasttype = ttype;
		length = get_generic_tlv_len(tlv_vp, pktend);
		next = (const guint8*)tlv_vp + (length+GENERICTLV_HDRSZ);
		if (next > (const guint8*) pktend) {
			fprintf(stderr, "TLV Invalid because TLV entry extends past end\n");
			return FALSE;
		}
		if (ttype == FRAMETYPE_END) {
			if (get_generic_tlv_value(tlv_vp, pktend) == pktend) {
				return length == 0;
			}else{
				fprintf(stderr, "TLV Invalid because END item isn't at end of packet\n");
				return FALSE;
			}
		}
		if (j < DIMOF(reqtypes) && ttype != reqtypes[j]) {
			fprintf(stderr, "TLV Invalid because required TLV types aren't present in right order\n");
			return FALSE;
		}
		j += 1;
	}
	if (lasttype != FRAMETYPE_END) {
		fprintf(stderr, "TLV Invalid because final type wasn't FRAMETYPE_END (it was %d)\n"
		,	lasttype);
		return FALSE;
	}
	return TRUE;
}

gconstpointer
get_generic_tlv_first(gconstpointer packet,	///<[in] Pointer to beginning of TLV packet
                      gconstpointer pktend)	///<[in] Pointer to first byte after the end of the TLV packet
{
	const guint8*	inittlv = packet;
	if (packet == NULL
	||	(inittlv + GENERICTLV_HDRSZ) > (const guint8*)pktend
	||	(inittlv + GENERICTLV_HDRSZ + get_generic_tlv_len(inittlv, pktend)) > (const guint8*)pktend) {
		return NULL;
	}
	return inittlv;
}

/// Return pointer to the next generic TLV entry after the current location
gconstpointer
get_generic_tlv_next(gconstpointer tlv_vp,		///<[in] Pointer to  current TLV entry
                  gconstpointer pktend)	///<[in] Pointer to first byte after the end of the TLV packet
{
	const guint8*	nexttlv;
	const guint8*	nextend;
	if (tlv_vp == NULL
        ||  ((const guint8*)tlv_vp+GENERICTLV_HDRSZ) > (const guint8*)pktend
        ||  get_generic_tlv_type(tlv_vp, pktend) == FRAMETYPE_END) {
		return NULL;
	}
	nexttlv = (const guint8*)tlv_vp  + GENERICTLV_HDRSZ + get_generic_tlv_len(tlv_vp, pktend);
	/* Watch out for malformed packets! (BLACKHAT, PARANOIA) */
	nextend = nexttlv + GENERICTLV_HDRSZ + get_generic_tlv_len(nexttlv, pktend);
	/* fprintf(stderr, "LOOK: cur:%p, next: %p, nextend: %p, vpend: %p\n"
	,	tlv_vp, nexttlv, nextend, pktend); */
	return nextend > (const guint8*)pktend ? NULL : nexttlv;
}

/// Return pointer to the next TLV entry of the given type at or after the current location
gconstpointer
find_next_generic_tlv_type(gconstpointer tlv_vp,///< [in] Pointer to the current TLV
                       guint16 tlvtype,		///< [in] Type of TLV we're looking for
                       gconstpointer pktend)	///< [in] Pointer to first byte beyond the packet.
{
	while (NULL != tlv_vp && ((const guint8*)tlv_vp+GENERICTLV_HDRSZ) <= (const guint8*)pktend) {
		if (get_generic_tlv_type(tlv_vp, pktend) == tlvtype) {
			return tlv_vp;
		}
		tlv_vp = get_generic_tlv_next(tlv_vp, pktend);
	}
	return NULL;
}
//@}
