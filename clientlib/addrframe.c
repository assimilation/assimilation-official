/**
 * @file
 * @brief Implements the @ref AddrFrame class - A frame for generic network addresses
 * @details AddrFrames consist of a two-byte IANA address family number plus the address.
 * These fields are generally stored in network byte order.
 * We have explicit support for three types, and the rest just come along for the ride...
 * @see Frame, FrameSet, GenericTLV
 * @see http://www.iana.org/assignments/address-family-numbers/address-family-numbers.xhtml
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <string.h>
#include <projectcommon.h>
#include <frameset.h>
#include <addrframe.h>
#include <frameformats.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>
#include <address_family_numbers.h>

FSTATIC gboolean _addrframe_default_isvalid(Frame *, gconstpointer, gconstpointer);
FSTATIC void _addrframe_setaddr(AddrFrame* f, guint16 frametype, gpointer addr, gsize addrlen);
FSTATIC void _addrframe_addr_finalize(void * addr);
///@}



///@defgroup AddrFrame AddrFrame class
/// Class for holding/storing various kinds of self-identifying network addresses.
/// @{
/// @ingroup C_Classes

/// Default @ref AddrFrame 'isvalid' member function (always returns TRUE)
FSTATIC gboolean
_addrframe_default_isvalid(Frame * self,	///< AddrFrame object ('this')
		       gconstpointer tlvptr,	///< Pointer to the TLV for this AddrFrame
		       gconstpointer pktend)	///< Pointer to one byte past the end of the packet
{
	guint16		tlvlen = 0;
	guint16		address_family = 0;
	gconstpointer	valueptr = NULL;

	tlvlen = get_generic_tlv_len(tlvptr, pktend);
	if (tlvlen <= sizeof(guint16)) {
		return FALSE;
	}

	valueptr = get_generic_tlv_value(tlvptr, pktend);
	if (valueptr == NULL) {
		return FALSE;
	}
	
	address_family = tlv_get_guint16(valueptr, pktend);

	if (address_family < ADDR_FAMILY_IPV4 || address_family > 32) {
		return FALSE;
	}

	switch(address_family) {
		case ADDR_FAMILY_IPV4:
			return (tlvlen == (4+sizeof(guint16)));

		case ADDR_FAMILY_IPV6:
			return (tlvlen == (16+ sizeof(guint16)));

		case ADDR_FAMILY_802:		// MAC addresses
			return (tlvlen == (6+sizeof(guint16)));	// Not really sure what all kinds of 802
								//  addresses there are...
	}
	// WAG...
	return (tlvlen >= 6 && tlvlen <= 34);	// Or we could just disallow them...
}

/// Set the address for this AddrFrame @ref Frame
FSTATIC void
_addrframe_setaddr(AddrFrame* f,	// Frame to set the address type for 
		  guint16 addrtype,	// IANA address type
		  gpointer addr,	// Address blob
		  gsize addrlen)	// size of address
{
	gsize		blobsize = addrlen +  sizeof(guint16);
	guint8*		blob = MALLOC0(blobsize);

	g_return_if_fail(blob != NULL);

	tlv_set_guint16(blob, addrtype, blob+blobsize);
	memcpy(blob+sizeof(guint16), addr, addrlen);
	f->baseclass.length = blobsize;
	f->baseclass.value = blob;
}

/// Finalize address blob
FSTATIC void
_addrframe_addr_finalize(void * addr) ///< Address object to free (FREE)
{
	FREE(addr);
}

/// Construct a new frame - allowing for "derived" frame types...
/// This can be used directly for creating AddrFrame frames, or by derived classes.
AddrFrame*
addrframe_new(guint16 frame_type,	///< TLV type of AddrFrame
	      gsize framesize)		///< size of frame structure (or zero for sizeof(AddrFrame))
{
	Frame*		baseframe;
	AddrFrame*	aframe;

	if (framesize < sizeof(AddrFrame)){
		framesize = sizeof(AddrFrame);
	}

	baseframe = frame_new(frame_type, framesize);
	baseframe->isvalid = _addrframe_default_isvalid;
	proj_class_register_subclassed (baseframe, "AddrFrame");
	baseframe->valuefinalize = _addrframe_addr_finalize;
	aframe = CASTTOCLASS(AddrFrame, baseframe);
	
	aframe->setaddr = _addrframe_setaddr;
	return aframe;
}

///@}
