/**
 * @file
 * @brief Defines interfaces for the NetAddr (network address) object.
 * @details These can be various kinds of network addresses - IPV4, IPv6,
 * MAC addresses, etc. as enumerated by IANA, and covered by RFC 3232.
 * This class implements a basic API on these objects.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#include <memory.h>
#include <netaddr.h>
#include <address_family_numbers.h>

/// @defgroup NetAddr NetAddr class
///@{
/// @ingroup C_Classes
/// This is our basic NetAddr object.
/// It represents network addresses of any of a wide variety of well-known @ref AddressFamilyNumbers "well-known types".
/// It is a class from which we might eventually make subclasses,
/// and is managed by our @ref ProjectClass system.

///@todo Figure out the byte order issues so that we store them in a consistent
///	 format - ipv4, ipv6 and MAC addresses...
FSTATIC struct sockaddr_in6 _netaddr_ipv6sockaddr(const NetAddr* self);

/// Generic NetAddr constructor.
NetAddr*
netaddr_new(gsize objsize,				///<[in] Size of object to construct
	    guint16 port,				///<[in] Port (if applicable)
	    guint16 addrtype,				///<[in] IETF/IANA address type
	    gconstpointer addrbody,			///<[in] Pointer to address body
	    guint16 addrlen)				///<[in] Length of address
{
	NetAddr*	self;

	if (objsize < sizeof(NetAddr)) {
		objsize = sizeof(NetAddr);
	}
	g_return_val_if_fail(addrbody != NULL, NULL);
	g_return_val_if_fail(addrlen >= 4, NULL);

	self = MALLOCCLASS(NetAddr, objsize);
	g_return_val_if_fail(self != NULL, NULL);

	self->_addrport = port;
	self->_addrtype = addrtype;
	self->_addrlen = addrlen;
	self->ipv6sockaddr = _netaddr_ipv6sockaddr;
	self->_addrbody = g_memdup(addrbody, addrlen);

	return self;

}
/// Create new NetAddr from a MAC address
NetAddr*
netaddr_macaddr_new(gconstpointer macbuf,	///<[in] Pointer to physical (MAC) address
			 guint16 maclen)	///<[in] length of 'macbuf'
{
	
	g_return_val_if_fail(maclen == 6 || maclen == 8, NULL);
	return netaddr_new(0, 0, ADDR_FAMILY_802, macbuf, maclen);
}

/// Create new NetAddr from a MAC48 address
NetAddr*
netaddr_mac48_new(gconstpointer macbuf)	///<[in] Pointer to physical (MAC) address
{
	return netaddr_macaddr_new(macbuf, 6);
}

/// Create new NetAddr from a MAC64 address
NetAddr*
netaddr_mac64_new(gconstpointer macbuf)	///<[in] Pointer to physical (MAC) address
{
	return netaddr_macaddr_new(macbuf, 6);
}

/// Create new NetAddr from a IPv4 address
NetAddr*
netaddr_ipv4_new(gconstpointer	ipbuf,	///<[in] Pointer to 4-byte IPv4 address
		 guint16	port)	///<[in] Port (or zero for non-port-specific IP address)
{
	return	netaddr_new(0, port, ADDR_FAMILY_IPV4, ipbuf, 4);
}

/// Create new NetAddr from a IPv6 address
NetAddr*
netaddr_ipv6_new(gconstpointer ipbuf,	///<[in] Pointer to 8-byte IPv6 address
		 guint16	port)	///<[in] Port (or zero for non-port-specific IP address)
{
	return	netaddr_new(0, port, ADDR_FAMILY_IPV6, ipbuf, 8);
}




/// Create new NetAddr from a <b>struct sockaddr</b>
NetAddr*
netaddr_sockaddr_new(const struct sockaddr *sa,	///<[in] struct sockaddr to construct address from
			  socklen_t length)	///<[in] number of bytes in 'sa'
{
	const struct sockaddr_in*	sa_in = (const struct sockaddr_in*)sa;
	const struct sockaddr_in6*	sa_in6 = (const struct sockaddr_in6*)sa;

	switch(sa_in->sin_family) {
		case AF_INET:
			return netaddr_new(0, sa_in->sin_port, 
					   ADDR_FAMILY_IPV4, &sa_in->sin_addr, 4);
			break;

		case AF_INET6:
			/// @todo convert IPv4 encapsulated addresses to real IPv4 addresses??
			return netaddr_new(0, sa_in6->sin6_port, 
					   ADDR_FAMILY_IPV6, &sa_in6->sin6_addr, 16);
			break;
	}
	g_return_val_if_reached(NULL);
}
///@}

FSTATIC struct sockaddr_in6
_netaddr_ipv6sockaddr(const NetAddr* self)	//<[in] NetAddr object to convert to ipv6 sockaddr
{
	struct sockaddr_in6	saddr;

	memset(&saddr, 0x00, sizeof(saddr));

	switch (self->_addrtype) {
		case ADDR_FAMILY_IPV4:
			g_return_val_if_fail(4 == self->_addrlen, saddr);
			saddr.sin6_family = AF_INET6;
			saddr.sin6_port = self->_addrport;
			/// @todo May need to account for the "any" ipv4 address here and
			/// translate it into the "any" ipv6 address...
			// (this works because saddr is initialized to zero)
			saddr.sin6_addr.s6_addr[10] =  0xff;
			saddr.sin6_addr.s6_addr[11] =  0xff;
			memcpy(saddr.sin6_addr.s6_addr+12, self->_addrbody, self->_addrlen);
			break;

		case ADDR_FAMILY_IPV6:
			g_return_val_if_fail(16 == self->_addrlen, saddr);
			saddr.sin6_family = AF_INET6;
			saddr.sin6_port = self->_addrport;
			memcpy(&saddr.sin6_addr, self->_addrbody, self->_addrlen);
			break;

		default:
			g_return_val_if_reached(saddr);
	}
	return saddr;
}
