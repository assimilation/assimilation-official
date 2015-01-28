/**
 * @file
 * @brief Implements the @ref AddrFrame class - A frame for generic network addresses
 * @details AddrFrames consist of a two-byte IANA address family number plus the address.
 * These fields are generally stored in network byte order.
 * We have explicit support for three types, and the rest hopefully can come along for the ride...
 * @see Frame, FrameSet, GenericTLV
 * @see http://www.iana.org/assignments/address-family-numbers/address-family-numbers.xhtml
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
#include <string.h>
#include <projectcommon.h>
#include <frameset.h>
#include <addrframe.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>
#include <address_family_numbers.h>

FSTATIC gboolean _addrframe_default_isvalid(const Frame *, gconstpointer, gconstpointer);
FSTATIC void _addrframe_setaddr(AddrFrame* self, guint16 frametype, gconstpointer addr, gsize addrlen);
FSTATIC NetAddr* _addrframe_getnetaddr(AddrFrame* self);
FSTATIC void _addrframe_setnetaddr(AddrFrame* self, NetAddr*netaddr);
FSTATIC void _addrframe_setport(AddrFrame *, guint16 port);
FSTATIC void _addrframe_finalize(AssimObj*);
FSTATIC char* _addrframe_toString(gconstpointer);
///@}

/**
 * @defgroup AddrFrameFormats C-Class AddrFrame wire format
 * @{
 * @ingroup FrameFormats
 * Here is the format we use for packaging an @ref AddrFrame for the wire.
 * Note that different types of addresses are different lengths.
 * The address types are as per the @ref AddressFamilyNumbers "IANA Address Family" numbering scheme.
<PRE>
+-------------+----------------+------------------+--------------------+
| frametype   |    f_length    | Address Type     |    address-data    |
|  16 bits)   |    (16-bits)   |    2 bytes       | (f_length-2 bytes) |
+-------------+----------------+------------------+--------------------+
</PRE>
*@}
*/

///@defgroup AddrFrame AddrFrame class
/// Class for holding/storing various kinds of @ref NetAddr network addresses. We're a subclass of @ref Frame.
/// @{
/// @ingroup Frame

/// @ref AddrFrame 'isvalid' member function - checks address type and length.
/// Note that this checking is more thorough for IPV4, IPV5 and MAC addresses than for
/// any other types.
/// Right now it <i>does</i> allow other address types, but perhaps they should be disallowed?
/// Each of the classes that use this class should make sure that the address held in an @ref AddrFrame
/// is suitable to the purpose at hand.
/// We need to support MAC addresses, but they can't be used in a context that requires
/// some kind of IP address.  So, <i>caveat emptor</i> has to be the rule of the day anyway.
FSTATIC gboolean
_addrframe_default_isvalid(const Frame * self,	///<[in/out] AddrFrame object ('this')
		       gconstpointer tlvptr,	///<[in] Pointer to the TLV for this AddrFrame
		       gconstpointer pktend)	///<[in] Pointer to one byte past the end of the packet
{
	guint32		tlvlen = 0;
	guint16		address_family = 0;
	gconstpointer	valueptr = NULL;
	guint32		addrlen;

	if (tlvptr == NULL) {
		// Validate the local copy instead of the TLV version.
		tlvptr = self->value;
		g_return_val_if_fail(tlvptr != NULL, FALSE);
		pktend = (const guint8*)tlvptr + self->length;
		address_family = tlv_get_guint16(tlvptr, pktend);
		addrlen = self->length - sizeof(guint16);;
	}else{
		tlvlen = get_generic_tlv_len(tlvptr, pktend);
		if (tlvlen <= sizeof(guint16)) {
			return FALSE;
		}
		addrlen = tlvlen - sizeof(guint16);

		valueptr = get_generic_tlv_value(tlvptr, pktend);
		if (valueptr == NULL) {
			return FALSE;
		}
		
		address_family = tlv_get_guint16(valueptr, pktend);
	}

	switch(address_family) {
		case ADDR_FAMILY_IPV4:		// IPv4
			return (4 == addrlen);

		case ADDR_FAMILY_IPV6:		// IPv6
			return (16 == addrlen);

		case ADDR_FAMILY_802:		// IEEE 802 MAC addresses
			// MAC-48/EUI-48 OR EUI-64
			// See http://en.wikipedia.org/wiki/MAC_address
			return (6 == addrlen || 8 == addrlen);
	}
	if (address_family < ADDR_FAMILY_IPV4 || address_family >= 32) {
		// Probably a mangled address type -- could be changed if we need
		// to support some odd protocol in the future...
		return FALSE;
	}
	// WAG...
	return (addrlen >= 4 && addrlen <= 32);	// Or we could just disallow them...
}

/// Assign an address to this @ref AddrFrame object
FSTATIC void
_addrframe_setaddr(AddrFrame* f,	//<[in/out] Frame to set the address type for 
		  guint16 addrtype,	//<[in] IANA address type
		  gconstpointer addr,	//<[in] Address blob
		  gsize addrlen)	//<[in] size of address
{
	gsize		blobsize = addrlen +  sizeof(guint16);
	guint8*		blob = MALLOC(blobsize);

	g_return_if_fail(blob != NULL);

	if (f->baseclass.value != NULL) {
		FREE(f->baseclass.value);
		f->baseclass.value = NULL;
	}

	tlv_set_guint16(blob, addrtype, blob+blobsize);
	memcpy(blob+sizeof(guint16), addr, addrlen);
	f->baseclass.length = blobsize;
	f->baseclass.value = blob;
	f->_addr = netaddr_new(0, 0, addrtype, addr, addrlen);
}

FSTATIC void
_addrframe_setport(AddrFrame* self, guint16 port)
{
	if (self && self->_addr) {
		self->_addr->_addrport = port;
	}
	
}


FSTATIC NetAddr*
_addrframe_getnetaddr(AddrFrame* self)
{
	return self->_addr;
}

/// Assign a NetAddr to this @ref AddrFrame object
FSTATIC void
_addrframe_setnetaddr(AddrFrame* self,	///<[in/out] AddrFrame whose address we're setting...
                   NetAddr* naddr)	///<[in] NetAddr value to set it to.
					///< We hold a reference to it.
{
        if (self->_addr) {
		UNREF(self->_addr);
	}
	self->setaddr(self, naddr->addrtype(naddr), naddr->_addrbody, naddr->_addrlen);
	if (!_addrframe_default_isvalid((Frame*)self, NULL, NULL)) {
		g_error("supplied netaddr for addrframe is invalid");
	}
}



FSTATIC void
_addrframe_finalize(AssimObj*obj)
{
	AddrFrame*	self = CASTTOCLASS(AddrFrame, obj);
	if (self->_addr) {
		UNREF(self->_addr);
	}
	if (self->baseclass.value) {
		FREE(self->baseclass.value);
		self->baseclass.value = NULL;
	}
	self->_basefinal(CASTTOCLASS(AssimObj, self)); self = NULL;
}

/// Construct a new @ref AddrFrame - allowing for "derived" frame types...
/// This can be used directly for creating @ref AddrFrame frames, or by derived classes.
WINEXPORT AddrFrame*
addrframe_new(guint16 frame_type,	///<[in] TLV type of the @ref AddrFrame (not address type) frame
	      gsize framesize)		///<[in] size of frame structure (or zero for sizeof(AddrFrame))
{
	Frame*		baseframe;
	AddrFrame*	aframe;

	if (framesize < sizeof(AddrFrame)){
		framesize = sizeof(AddrFrame);
	}

	baseframe = frame_new(frame_type, framesize);
	baseframe->isvalid = _addrframe_default_isvalid;
	proj_class_register_subclassed (baseframe, "AddrFrame");
	aframe = CASTTOCLASS(AddrFrame, baseframe);
	
	aframe->setaddr = _addrframe_setaddr;
	aframe->setnetaddr = _addrframe_setnetaddr;
	aframe->getnetaddr = _addrframe_getnetaddr;
	aframe->setport = _addrframe_setport;
	aframe->_basefinal = baseframe->baseclass._finalize;
	baseframe->baseclass._finalize = _addrframe_finalize;
	baseframe->baseclass.toString = _addrframe_toString;
	aframe->_addr = NULL;
	return aframe;
}

/// Construct and initialize an IPv4 @ref AddrFrame
WINEXPORT AddrFrame*
addrframe_ipv4_new(guint16 frame_type,	///<[in] TLV type of the @ref AddrFrame (not address type) frame
		   gconstpointer addr)	///<[in] pointer to the (binary) IPv4 address data
{
	AddrFrame*	ret;
	ret = addrframe_new(frame_type, 0);
	g_return_val_if_fail(ret != NULL, NULL);
	ret->setaddr(ret, ADDR_FAMILY_IPV4, addr, 4);
	return ret;
}

/// Construct and initialize an IPv6 @ref AddrFrame
WINEXPORT AddrFrame*
addrframe_ipv6_new(guint16 frame_type,	///<[in] TLV type of the @ref AddrFrame (not address type) frame
		   gconstpointer addr)	///<[in] pointer to the (binary) IPv6 address data
{
	AddrFrame*	ret;
	ret = addrframe_new(frame_type, 0);
	g_return_val_if_fail(ret != NULL, NULL);
	ret->setaddr(ret, ADDR_FAMILY_IPV6, addr, 16);
	return ret;
}

/// Construct and initialize a 48-bit MAC address @ref AddrFrame
WINEXPORT AddrFrame*
addrframe_mac48_new(guint16 frame_type,	///<[in] TLV type of the @ref AddrFrame (not address type) frame
                    gconstpointer addr)	///<[in] pointer to the (binary) MAC address data
{
	AddrFrame*	ret;
	ret = addrframe_new(frame_type, 0);
	g_return_val_if_fail(ret != NULL, NULL);
	ret->setaddr(ret, ADDR_FAMILY_802, addr, 6);
	return ret;
}
/// Construct and initialize a 64-bit MAC address @ref AddrFrame
WINEXPORT AddrFrame*
addrframe_mac64_new(guint16 frame_type,	///<[in] TLV type of the @ref AddrFrame (not address type) frame
		    gconstpointer addr)	///<[in] pointer to the (binary) MAC address data
{
	AddrFrame*	ret;
	ret = addrframe_new(frame_type, 0);
	g_return_val_if_fail(ret != NULL, NULL);
	ret->setaddr(ret, ADDR_FAMILY_802, addr, 8);
	return ret;
}

/// Given marshalled packet data corresponding to an AddrFrame (address), return the corresponding @ref Frame
/// In other words, un-marshall the data...
/// Note that this always returns an @ref AddrFrame (a subclass of @ref Frame)
WINEXPORT Frame*
addrframe_tlvconstructor(gpointer tlvstart,		///<[in] pointer to start of where to find our TLV
			 gconstpointer pktend,		///<[in] pointer to the first invalid address past tlvstart
		         gpointer* ignorednewpkt,	///<[ignored] replacement packet
		         gpointer* ignoredpktend)	///<[ignored] end of replacement packet

{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint16		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	AddrFrame *	ret = addrframe_new(frametype, 0);
	guint16		address_family;

	(void)ignorednewpkt;	(void)ignoredpktend;
	g_return_val_if_fail(ret != NULL, NULL);

	address_family = tlv_get_guint16(framevalue, pktend);

	ret->baseclass.length = framelength;
	ret->setaddr(ret, address_family, framevalue+sizeof(guint16), framelength-sizeof(guint16));
	if (!_addrframe_default_isvalid(&ret->baseclass, tlvstart, pktend)) {
		UNREF2(ret);
		g_return_val_if_reached(NULL);
	}
	return &ret->baseclass;
}


/// Convert AddrFrame object into a printable string
FSTATIC gchar*
_addrframe_toString(gconstpointer aself)
{
	const AddrFrame*	self = CASTTOCONSTCLASS(AddrFrame, aself);
	char *			selfstr = self->_addr->baseclass.toString(&self->_addr->baseclass);
	char *			ret;

	ret = g_strdup_printf("AddrFrame(type=%d, %s)", self->baseclass.type, selfstr);
	g_free(selfstr);
	return ret;
}
///@}
