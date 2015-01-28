/**
 * @file
 * @brief Implements the @ref IpPortFrame class - A frame for generic network addresses
 * @details IpPortFrames consist of a 2-byte port number followed by a 2-byte IANA
 * address family number plus the address.
 * These fields are stored in network byte order.
 * We only support IPv4 and IPv6 addresses - as the port is mandatory for this object.
 * @see Frame, FrameSet, GenericTLV, AddrFrame
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
 *  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
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
FSTATIC gchar* _ipportframe_toString(gconstpointer aself);
///@}

/**
 * @defgroup IpPortFrameFormats C-Class IpPortFrame wire format (including port number)
 * @{
 * @ingroup FrameFormats
 * Here is the format we use for packaging an @ref IpPortFrame for the wire.
 * Note that different types of addresses are different lengths.
 * The address types are either 1 for IPv4 or 2 for IPv6.  This is the same
 * as a NetAddr, and the same as RFC 3232 and is defined/described here:
 * http://www.iana.org/assignments/address-family-numbers/address-family-numbers.xhtml
<PRE>
+-------------+----------------+-------------+---------------+--------------------+
| frametype   |    f_length    | Port Number | Address Type  |    address-data    |
|  16 bits)   |    (16-bits)   |   2 bytes   |   2 bytes     | (f_length-4 bytes) |
+-------------+----------------+-------------+---------------+--------------------+
</PRE>
*@}
*/
#define	TLVOVERHEAD	(sizeof(guint16)+sizeof(guint16))	///< Two bytes for port number, and two for the address type
#define	TLVIPV4SIZE	(TLVOVERHEAD+4)				///< IPv4 addresses are 4 bytes
#define	TLVIPV6SIZE	(TLVOVERHEAD+16)			///< IPv4 addresses are 16 bytes

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
	guint16		portnumber;
	const guint16*	int16ptr;
	guint16		pktsize;

	if (tlvptr == NULL) {
		// Validate the local copy instead of the TLV version.
		tlvptr = self->value;
		g_return_val_if_fail(tlvptr != NULL, FALSE);
		pktend = (const guint8*)tlvptr + self->length;
		int16ptr = (const guint16*)self->value;
		pktsize = self->length;
	}else{
		pktsize = get_generic_tlv_len(tlvptr, pktend);
		int16ptr = (const guint16*)get_generic_tlv_value(tlvptr, pktend);
	}
	
	if (pktsize < TLVIPV4SIZE || int16ptr == NULL) {
		return FALSE;
	}

	// First field -- port number: 16-bit unsigned integer - network byte order
	portnumber = tlv_get_guint16(int16ptr, pktend);
	if (portnumber == 0) {
		g_warning("%s.%d: Port is zero", __FUNCTION__, __LINE__);
		return FALSE;
	}
	
	// Second field -- address family: 16-bit unsigned integer - network byte order
	address_family = tlv_get_guint16(int16ptr+1, pktend);

	switch(address_family) {
		case ADDR_FAMILY_IPV4:		// IPv4
			return (TLVIPV4SIZE == pktsize);

		case ADDR_FAMILY_IPV6:		// IPv6
			return (TLVIPV6SIZE == pktsize);

		default:
			break;

	}
	return FALSE;
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

	tlv_set_guint16(blob, port, blobend);
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


/// Finalize an IpPortFrame
FSTATIC void
_ipportframe_finalize(AssimObj*obj)
{
	IpPortFrame*	self = CASTTOCLASS(IpPortFrame, obj);
	if (self->_addr) {
		UNREF(self->_addr);
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
	        gsize framesize)	///<[in] size of frame structure (or zero for sizeof(IpPortFrame))
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
	aframe->baseclass.baseclass.toString = _ipportframe_toString;
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
	if (port == 0) {
		return NULL;
	}
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
	if (port == 0) {
		return NULL;
	}
	ret = ipportframe_new(frame_type, 0);
	g_return_val_if_fail(ret != NULL, NULL);
	_ipportframe_setaddr(ret, ADDR_FAMILY_IPV6, port, addr, 16);
	return ret;
}

/// Construct and initialize an @ref IpPortFrame from a IP @ref NetAddr
WINEXPORT IpPortFrame*
ipportframe_netaddr_new(guint16 frame_type, NetAddr* addr)
{
	guint16		port = addr->port(addr);
	gpointer	body = addr->_addrbody;

	if (port == 0) {
		return NULL;
	}

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
ipportframe_tlvconstructor(gpointer tlvstart,		///<[in] pointer to start of where to find our TLV
			   gconstpointer pktend,	///<[in] pointer to the first invalid address past tlvstart
			   gpointer* ignorednewpkt,	///<[ignored] replacement packet if any
			   gpointer* ignoredpktend)	///<[ignored] end of replaement packet

{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint32		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	IpPortFrame *	ret;
	guint16		addr_family;
	guint16		port;

// +-------------+----------------+-------------+---------------+--------------------+
// | frametype   |    f_length    | Port Number | Address Type  |    address-data    |
// |  16 bits)   |    (24-bits)   |   2 bytes   |   2 bytes     | (f_length-4 bytes) |
// +-------------+----------------+-------------+---------------+--------------------+
	(void)ignorednewpkt;	(void)ignoredpktend;
	port = tlv_get_guint16(framevalue, pktend);
	if (port == 0) {
		return NULL;
	}

	addr_family = tlv_get_guint16(framevalue+sizeof(guint16), pktend);

	switch (addr_family) {
		case ADDR_FAMILY_IPV4:
			g_return_val_if_fail(framelength == TLVIPV4SIZE, NULL);
			break;
		case ADDR_FAMILY_IPV6:
			g_return_val_if_fail(framelength == TLVIPV6SIZE, NULL);
			break;
		default:
			g_return_val_if_reached(NULL);
			break;
	}

	ret = ipportframe_new(frametype, 0);
	ret->baseclass.length = framelength;
	_ipportframe_setaddr(ret, addr_family, port, framevalue+TLVOVERHEAD
	,		     framelength-TLVOVERHEAD);
	if (!_ipportframe_default_isvalid(&ret->baseclass, tlvstart, pktend)) {
		UNREF2(ret);
		g_return_val_if_reached(NULL);
	}
	return &ret->baseclass;
}
/// Convert IPaddrPortFrame object into a printable string
FSTATIC gchar*
_ipportframe_toString(gconstpointer aself)
{
	const IpPortFrame*	self = CASTTOCONSTCLASS(IpPortFrame, aself);
	char *			selfstr = self->_addr->baseclass.toString(&self->_addr->baseclass);
	char *			ret;

	ret = g_strdup_printf("IpPortFrame(%d, %s)", self->baseclass.type, selfstr);
	g_free(selfstr);
	return ret;
}
///@}
