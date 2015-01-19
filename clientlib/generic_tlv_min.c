/**
 * @file
 * @brief Implements minimal client-oriented Generic TLV capabilities.
 * @details This file implements minimal Generic TLV capabiliies for a client -
 * enough for it to be able to understand and validate a generic TLV packet structure,
 * iterate through these generic TLVs, and return any particular TLV.
 * For the most part, these TLVs correpond to our @ref Frame objects.
 * @see Frame
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

// #include <stdio.h>
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


/// Return the 'Type' of the given TLV <b>T</b>LV entry (first two bytes)
guint16
get_generic_tlv_type(gconstpointer tlv_vp,	///<[in] Pointer to beginning of TLV entry
		 gconstpointer pktend)  	///<[in] Pointer to one byte past end of packet
{
	return tlv_get_guint16(tlv_vp, pktend);
}

/// Set the 'Type' of the given TLV <b>T</b>LV entry (first two bytes)
void
set_generic_tlv_type(gpointer tlv_vp,	///<[in] Pointer to beginning of TLV entry
		 guint16 newtype,	///<[in] Type to stuff into TLV entry
		 gconstpointer pktend)	///<[in] Pointer to one byte past end of packet
{
	tlv_set_guint16(tlv_vp, newtype, pktend);
}

/// Return the 'Length' of the given generic T<b>L</b>V entry (first 3 bytes after type)
/// Note: return result is "tainted" and must be validated by other means
guint32
get_generic_tlv_len(gconstpointer tlv_vp,	///<[in] Pointer to beginning of TLV entry
		gconstpointer pktend)		///<[in] Pointer to one byte past end of packet
{
	const guint8 * tlvp = tlv_vp;
	guint32 tainted_len = tlv_get_guint24(tlvp+sizeof(guint16), pktend);
	g_return_val_if_fail((tlvp + tainted_len) <= (const guint8*)pktend, TLV_BAD24);
	return tainted_len;
}

/// Set the 'Length' of the given generic T<b>L</b>V entry (first 3 bytes after type)
void
set_generic_tlv_len(gpointer tlv_vp,	///<[in] Pointer to beginning of TLV entry
		 guint32 newsize,	///<[in] Length to stuff into TLV entry
		 gconstpointer pktend)	///<[in] Pointer to one byte past end of packet
{
	guint8 * tlvp = tlv_vp;
	tlv_set_guint24(tlvp+sizeof(guint16), newsize, pktend);
}

/// Return a const pointer to the 'Value' of the given generic TL<b>V</b> entry
gconstpointer
get_generic_tlv_value(gconstpointer tlv_vp,	///<[in] Pointer to beginning of TLV entry,
		 gconstpointer pktend)		///<[in] Pointer to one byte past end of packet
{
	const guint8*	tlvbytes = tlv_vp;
	const guint8*	ret = (tlvbytes + GENERICTLV_HDRSZ);
	if (ret == (const guint8*)pktend) {
		g_return_val_if_fail(get_generic_tlv_len(tlv_vp, pktend) == 0, TLV_BADPTR); // NULL
		return ret;
	}
	g_return_val_if_fail(ret < (const guint8*)pktend, TLV_BADPTR); // NULL
	return ret;
}

/// Return a non-const (mutable) pointer to the 'Value' of the given generic TL<b>V</b> entry
gpointer
get_generic_tlv_nonconst_value(gpointer tlv_vp,	///<[in] Pointer to beginning of TLV entry,
		 gconstpointer pktend)		///<[in] Pointer to one byte past end of packet
{
	guint8*	tlvbytes	= tlv_vp;
	guint8*	ret		= (tlvbytes + GENERICTLV_HDRSZ);
	g_return_val_if_fail(ret < (const guint8*)pktend, TLV_BADPTR); // NULL
	return (tlvbytes + GENERICTLV_HDRSZ);
}

/// Set the TLV data value to the given 'tlv_vp' pointer.
/// length must have already been set in the TLV
void
set_generic_tlv_value(gpointer tlv_vp,		///< pointer to TLV entry
		      void* srcdata,		///< pointer to source data
		      guint32 srcsize,		///< size of source object
		      gconstpointer pktend)	///<[in] Pointer to one byte past end of packet
{
	guint8*		tlvbytes = tlv_vp;
	g_return_if_fail((gpointer)(tlvbytes+srcsize) <= pktend);
	g_return_if_fail(srcsize == get_generic_tlv_len(tlv_vp, pktend));
	memcpy(tlvbytes + GENERICTLV_HDRSZ, srcdata, srcsize);
}

/// Return TRUE if this is a valid generic TLV packet.
gboolean
is_valid_generic_tlv_packet(gconstpointer tlv_vp,//<[in] pointer to beginning of TLV packet
                     gconstpointer pktend)	//<[in] pointer to first byte past the end of packet
{
	const guint16	reqtypes [] = {FRAMETYPE_SIG};
	unsigned	j = 0;
	//int		lasttype = -1;
	const guint8*	next;
	if (NULL == tlv_vp || ((const guint8*)tlv_vp+GENERICTLV_HDRSZ)  > (const guint8*)pktend) {
		g_warning("TLV Invalid because packet is too short");
		return FALSE;
	}
	for (tlv_vp = get_generic_tlv_first(tlv_vp, pktend)
	;	NULL != tlv_vp && tlv_vp < pktend
	;	tlv_vp = next) {

		guint16		ttype;
		guint32		length;

		if (tlv_vp >= pktend) {
			return FALSE;
		}
		ttype = get_generic_tlv_type(tlv_vp, pktend);
		//lasttype = ttype;
		length = get_generic_tlv_len(tlv_vp, pktend);
		next = (const guint8*)tlv_vp + (length+GENERICTLV_HDRSZ);
		if (next > (const guint8*) pktend) {
			g_warning("TLV Invalid because TLV entry extends past end");
			return FALSE;
		}
#if 0
		// This is no longer true - in the presence of compression and encryption
		// and any other kinds of frames we might want to invent that gobble up
		// the rest of the packet to the end...
		if (ttype == FRAMETYPE_END) {
			if (get_generic_tlv_value(tlv_vp, pktend) == pktend) {
				return length == 0;
			}else{
				g_warning("TLV Invalid because END item isn't at end of packet");
				return FALSE;
			}
		}
#endif
		if (j < DIMOF(reqtypes) && ttype != reqtypes[j]) {
			g_warning("TLV Invalid because required TLV types aren't present in right order");
			return FALSE;
		}
		j += 1;
	}
#if 0
	// See the note above...
	g_warning("TLV Invalid because final type wasn't FRAMETYPE_END (it was %d)"
	,	lasttype);
#endif
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
		return TLV_BADPTR; // NULL
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
		return TLV_BADPTR; // NULL
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
