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

#include <netaddr.h>
#include <address_family_numbers.h>

/// This is our basic NetAddr object.
/// It represents network addresses of a variety of types.
/// It is a class from which we might eventually make subclasses,
/// and is managed by our @ref ProjectClass system.
///@{
/// @ingroup NetADDR

///@todo Figure out the byte order issues so that we store them in a consistent
///	 format - ipv4, ipv6 and MAC addresses...

/// Generic NetAddr constructor.
NetAddr*
netaddr_new(gsize objsize, guint16 port, guint16 addrtype, gconstpointer addrbody, guint16 addrlen)
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

	self->_addrbody = g_memdup(addrbody, addrlen);

	return self;

}
/// Create new NetAddr from a MAC address
NetAddr*
netaddr_new_from_macaddr(gconstpointer macbuf, guint16 maclen)
{
	
	g_return_val_if_fail(maclen >= 6, NULL);
	g_return_val_if_fail(maclen <= 32, NULL);
	return netaddr_new(0, 0, ADDR_FAMILY_802, macbuf, maclen);
}

/// Create new NetAddr from a <b>struct sockaddr</b>
NetAddr*
netaddr_new_from_sockaddr(struct sockaddr *sa, socklen_t length)
{
	struct sockaddr_in*	sa_in = (struct sockaddr_in*)sa;
	struct sockaddr_in6*	sa_in6 = (struct sockaddr_in6*)sa;

	switch(sa_in->sin_family) {
		case AF_INET:
			return netaddr_new(0, sa_in->sin_port, 
					   ADDR_FAMILY_IPV4, &sa_in->sin_addr, 4);
			break;

		case AF_INET6:
			/// @todo convert IPv4 encapsulated addresses to real IPv4 addresses
			return netaddr_new(0, sa_in6->sin6_port, 
					   ADDR_FAMILY_IPV6, &sa_in6->sin6_addr, 16);
			break;
	}
	g_return_val_if_reached(NULL);
}
///@}

