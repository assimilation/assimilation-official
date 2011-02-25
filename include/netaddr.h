/**
 * @file
 * @brief Defines interfaces for the NetAddr (network address) object.
 * @details These can be various kinds of network addresses - IPV4, IPv6,
 * MAC addresses, etc. as enumerated by IANA, and covered by RFC 3232 and defined
 * in our @ref AddressFamilyNumbers "IETF/IANA Address Family Numbers".
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _NETADDR_H
#define _NETADDR_H
#include <projectcommon.h>
#include <netinet/in.h>
typedef struct _NetAddr NetAddr;

/// This is our basic NetAddr object.
/// It represents network addresses
/// It is a class from which we might eventually make subclasses,
/// and is managed by our @ref ProjectClass system.
///@{
/// @ingroup NetADDR
struct _NetAddr {
	guint16		(*port)(const NetAddr* self);		///< Return port from this address
	guint16		(*addrtype)(const NetAddr* self);	///< Return @ref AddressFamilyNumbers address type
	gconstpointer	(*addrinnetorder)(const NetAddr* self, gsize* addrlen);///< Return the address in network byte order
	struct sockaddr_in6(*ipv6addr)(const NetAddr* self);	///< Return the ipv6 address corresponding to this address
	void		(*finalize)(gpointer self);		///< Finalize this object.
	gpointer	_addrbody;				///< private: Address body
	guint16		_addrtype;				///< private: Address type
	guint16		_addrlen;				///< private: Length of _addrbody
	guint16		_addrport;				///< privaet: Address port (if applicable)
};
NetAddr*	netaddr_new(gsize objsize, guint16 port, guint16 addrtype, gconstpointer addrbody, guint16 addrlen);
NetAddr*	netaddr_new_from_sockaddr(const struct sockaddr *, socklen_t);
NetAddr*	netaddr_new_from_macaddr(gconstpointer addrbody, guint16 maclen);
///@}

#endif /* _NETADDR_H */
