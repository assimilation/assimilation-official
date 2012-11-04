/**
 * @file
 * @brief Implements the @ref IpPortFrame class - A frame for generic network addresses
 * @details IpPortFrames consist of a 2-byte port number followed by a 2-byte IANA
 * address family number plus the address.
 * These fields are generally stored in network byte order.
 * We have explicit support for three types, and the rest hopefully can come along for the ride...
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
#include <ipportframe.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>
#include <address_family_numbers.h>

FSTATIC gboolean _ipportframe_default_isvalid(const Frame *, gconstpointer, gconstpointer);
FSTATIC void _ipportframe_setaddr(IpPortFrame* self, guint16 frametype, guint16 port, gconstpointer addr, gsize addrlen);
FSTATIC NetAddr* _ipportframe_getnetaddr(IpPortFrame* self);
FSTATIC void _ipportframe_setnetaddr(IpPortFrame* self, NetAddr*netaddr);
FSTATIC void _ipportframe_finalize(AssimObj*);
FSTATIC IpPortFrame* ipportframe_new(guint16 frame_type, gsize framesize);
///@}

/**
 * @defgroup IpPortFrameFormats C-Class IpPortFrame wire format (including port number)
 * @{
 * @ingroup FrameFormats
 * Here is the format we use for packaging an @ref IpPortFrame for the wire.
 * Note that different types of addresses are different lengths.
 * The address types are either 1 for IPv4 or 2 for IPv6 which is the same as for
 * a NetAddr, and the same as RFC 3232 and is defined/described here:
 * http://www.iana.org/assignments/address-family-numbers/address-family-numbers.xhtml
<PRE>
+-------------+----------------+-------------+---------------+--------------------+
| frametype   |    f_length    | Port Number | Address Type  |    address-data    |
|  16 bits)   |    (16-bits)   |   2 bytes   |   2 bytes     | (f_length-4 bytes) |
+-------------+----------------+-------------+---------------+--------------------+
</PRE>
*@}
*/

///@defgroup IpPortFrame IpPortFrame class
/// Class for holding/storing various kinds of @ref NetAddr network addresses. We're a subclass of @ref Frame.
/// @{
/// @ingroup Frame

/// @ref IpPortFrame 'isvalid' member function - checks address type and length.
/// It only allows IPv4 and IPv6 address types.
FSTATIC gboolean
_ipportframe_default_isvalid(const Frame * self,///<[in/out] IpPortFrame object ('this')
		       gconstpointer tlvptr,	///<[in] Pointer to the TLV for this IpPortFrame
		       gconstpointer pktend)	///<[in] Pointer to one byte past the end of the packet
{
	guint16		address_family = 0;
	guint16		addrlen;
	guint16		portnumber;
	const guint16	ipv4size = 4;
	const guint16	ipv6size = 16;
	const guint16*	int16ptr;

	if (tlvptr == NULL) {
		// Validate the local copy instead of the TLV version.
		tlvptr = self->value;
		g_return_val_if_fail(tlvptr != NULL, FALSE);
		pktend = (const guint8*)tlvptr + self->length;
		addrlen = self->length - (2*sizeof(guint16));
		int16ptr = (const guint16*)self->value;
	}else{
		guint16		pktsize;
		pktsize = get_generic_tlv_len(tlvptr, pktend);
		addrlen = pktsize - (2*sizeof(guint16));
		int16ptr = (const guint16*)get_generic_tlv_value(tlvptr, pktend);
	}
	
	g_return_val_if_fail(int16ptr != NULL, FALSE);
	// If this is true, then the packet is big enough to look at the other fields...
	g_return_val_if_fail(addrlen == ipv4size || addrlen == ipv6size, FALSE);

	// First field -- port number: 16-bit unsigned integer - network byte order
	portnumber = tlv_get_guint16(int16ptr, pktend);
	g_return_val_if_fail(portnumber != 0, FALSE);
	
	// Second field -- address family: 16-bit unsigned integer - network byte order
	address_family = tlv_get_guint16(int16ptr+1, pktend);
	g_return_val_if_fail(address_family == ADDR_FAMILY_IPV4 || address_family == ADDR_FAMILY_IPV6, FALSE);

	switch(address_family) {
		case ADDR_FAMILY_IPV4:		// IPv4
			return (4 == addrlen);

		case ADDR_FAMILY_IPV6:		// IPv6
			return (16 == addrlen);

	}
	g_return_val_if_reached(FALSE);
}

FSTATIC void
_ipportframe_setaddr(IpPortFrame* f,	//<[in/out] Frame to set the address type for 
		     guint16 addrtype,	//<[in] IANA address type
		     guint16 port,	//<[in] port		  
		     gconstpointer addr,//<[in] Address blob
		     gsize addrlen)	//<[in] size of address
{
	gsize		blobsize = addrlen +  (2*sizeof(guint16));
	guint8*		blob = MALLOC(blobsize);
	guint8*		blobend = blob + blobsize;

	g_return_if_fail(blob != NULL);

	if (f->baseclass.value != NULL) {
		FREE(f->baseclass.value);
		f->baseclass.value = NULL;
	}

	tlv_set_guint16(blob, addrtype, blobend);
	tlv_set_guint16(blob+sizeof(guint16), addrtype, blobend);
	memcpy(blob+sizeof(guint16)+sizeof(guint16), addr, addrlen);
	f->baseclass.length = blobsize;
	f->baseclass.value = blob;
	f->port = port;
	f->_addr = netaddr_new(0, 0, addrtype, addr, addrlen);
	f->_addr->setport(f->_addr, port);
}


FSTATIC NetAddr*
_ipportframe_getnetaddr(IpPortFrame* self)
{
	return self->_addr;
}




FSTATIC void
_ipportframe_finalize(AssimObj*obj)
{
	IpPortFrame*	self = CASTTOCLASS(IpPortFrame, obj);
	if (self->_addr) {
		self->_addr->baseclass.unref(self->_addr);
		self->_addr = NULL;
	}
	if (self->baseclass.value) {
		FREE(self->baseclass.value);
		self->baseclass.value = NULL;
	}
	self->_basefinal(CASTTOCLASS(AssimObj, self)); self = NULL;
}

/// Construct a new @ref IpPortFrame - allowing for "derived" frame types...
/// This can be used directly for creating @ref IpPortFrame frames, or by derived classes.
FSTATIC IpPortFrame*
ipportframe_new(guint16 frame_type,	///<[in] TLV type of the @ref IpPortFrame (not address type) frame
	      gsize framesize)		///<[in] size of frame structure (or zero for sizeof(IpPortFrame))
{
	IpPortFrame*	aframe;

	if (framesize < sizeof(IpPortFrame)){
		framesize = sizeof(IpPortFrame);
	}

	aframe = NEWSUBCLASS(IpPortFrame, frame_new(frame_type, framesize));
	aframe->baseclass.isvalid = _ipportframe_default_isvalid;
	
	aframe->getnetaddr = _ipportframe_getnetaddr;
	aframe->_basefinal = aframe->baseclass.baseclass._finalize;
	aframe->baseclass.baseclass._finalize = _ipportframe_finalize;
	return aframe;
}

/// Construct and initialize an IPv4 @ref IpPortFrame
WINEXPORT IpPortFrame*
ipportframe_ipv4_new(guint16 frame_type,	///<[in] TLV type of the @ref IpPortFrame
						///<     (not address type) frame
		     guint16 port,		///<[in] port number
		     gconstpointer addr)	///<[in] pointer to the (binary) IPv4 address data
{
	IpPortFrame*	ret;
	g_return_val_if_fail(addr != NULL, NULL);
	ret = ipportframe_new(frame_type, 0);
	g_return_val_if_fail(ret != NULL, NULL);
	_ipportframe_setaddr(ret, ADDR_FAMILY_IPV4, port, addr, 4);
	return ret;
}

/// Construct and initialize an IPv6 @ref IpPortFrame
WINEXPORT IpPortFrame*
ipportframe_ipv6_new(guint16 frame_type,	///<[in] TLV type of the @ref IpPortFrame (not address type) frame
		     guint16 port,		///<[in] port number
		   gconstpointer addr)	///<[in] pointer to the (binary) IPv6 address data
{
	IpPortFrame*	ret;
	g_return_val_if_fail(addr != NULL, NULL);
	ret = ipportframe_new(frame_type, 0);
	g_return_val_if_fail(ret != NULL, NULL);
	_ipportframe_setaddr(ret, ADDR_FAMILY_IPV6, port, addr, 16);
	return ret;
}

/// Construct and initialize an @ref IpPortFrame from a IP @ref NetAddr
IpPortFrame*
ipportframe_netaddr_new(guint16 frame_type, NetAddr* addr)
{
	guint16		port = addr->port(addr);
	gpointer	body = addr->_addrbody;

	switch(addr->addrtype(addr)) {
		case ADDR_FAMILY_IPV4:
			return ipportframe_ipv4_new(frame_type, port, body);
			break;
		case ADDR_FAMILY_IPV6:
			return ipportframe_ipv6_new(frame_type, port, body);
			break;
	}
	return NULL;
}


/// Given marshalled packet data corresponding to an IpPortFrame (address), return the corresponding @ref Frame
/// In other words, un-marshall the data...
/// Note that this always returns an @ref IpPortFrame (a subclass of @ref Frame)
WINEXPORT Frame*
ipportframe_tlvconstructor(gconstpointer tlvstart,	///<[in] pointer to start of where to find our TLV
			 gconstpointer pktend)		///<[in] pointer to the first invalid address past tlvstart

{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint16		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	IpPortFrame *	ret;
	guint16		addr_family;
	guint16		port;
	const guint16	headerlen = (sizeof(guint16) + sizeof(guint16));

	port = tlv_get_guint16(framevalue, pktend);
	g_return_val_if_fail(port != 0, NULL);

	addr_family = tlv_get_guint16(framevalue+sizeof(guint16), pktend);
	if (addr_family == ADDR_FAMILY_IPV4) {
		g_return_val_if_fail(framelength == 4+headerlen, NULL);
	}else if (addr_family == ADDR_FAMILY_IPV6) {
		g_return_val_if_fail(framelength == 16+headerlen, NULL);
	}else{
		g_return_val_if_reached(NULL);
	}

	ret = ipportframe_new(frametype, 0);
	ret->baseclass.length = framelength;
	_ipportframe_setaddr(ret, addr_family, port, framevalue+headerlen
	,		     framelength-headerlen);
	if (!_ipportframe_default_isvalid(&ret->baseclass, tlvstart, pktend)) {
		ret->baseclass.baseclass.unref(ret);	ret = NULL;
		g_return_val_if_reached(NULL);
	}
	return &ret->baseclass;
}
///@}
