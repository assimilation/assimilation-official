/**
 * @file
 * @brief Defines interfaces for the NetAddr (network address) object.
 * @details These can be various kinds of network addresses - IPV4, IPv6,
 * MAC addresses, etc. as enumerated by IANA, and covered by RFC 3232 and defined
 * in our @ref AddressFamilyNumbers "IETF/IANA Address Family Numbers".
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

#ifndef _NETADDR_H
#define _NETADDR_H
#include <projectcommon.h>
#include <assimobj.h>
#ifdef _MSC_VER
#	include <winsock2.h>
	typedef int socklen_t;
#else
#	include <netinet/in.h>
#endif
typedef struct _NetAddr NetAddr;

/// The @ref NetAddr class represents a general network address - whether IP, MAC, or @ref AddressFamilyNumbers "any other type of address".
/// It is a class from which we <i>might</i> eventually make subclasses,
/// and is managed by our @ref ProjectClass system.
///@{
/// @ingroup NetAddr
struct _NetAddr {
	AssimObj	baseclass;
	void		(*setport)(NetAddr*, guint16);          ///< Set port for this NetAddr
	guint16		(*port)(const NetAddr* self);		///< Return port from this address
	guint16		(*addrtype)(const NetAddr* self);	///< Return @ref AddressFamilyNumbers address type
	gboolean	(*ismcast)(const NetAddr* self);	///< Return TRUE if this address is a multicast address
	gboolean	(*islocal)(const NetAddr* self);	///< Return TRUE if this address is a local address
	gboolean	(*isanyaddr)(const NetAddr* self);	///< Return TRUE if this address is an 'ANY' address
	struct sockaddr_in6(*ipv6sockaddr)(const NetAddr* self);///< Return the ipv6 sockaddr corresponding to this address
	struct sockaddr_in(*ipv4sockaddr)(const NetAddr* self);///< Return the ipv4 sockaddr corresponding to this address
	gboolean	(*equal)(const NetAddr*,const NetAddr*);///< Compare NetAddrs
	guint		(*hash)(const NetAddr*);		///< Compute hash of the NetAddr
	char *		(*canonStr)(const NetAddr*);		///< Canonical form toString
	NetAddr*	(*toIPv6)(const NetAddr*);		///< Convert this NetAddr to the IPv6 equivalent
	NetAddr*	(*toIPv4)(const NetAddr*);		///< Convert this NetAddr to the IPv4 equivalent if possible
								///< It always returns a new object
	gpointer	_addrbody;		///< private: Address body
	guint16		_addrtype;		///< private: Address type
	guint16		_addrlen;		///< private: Length of _addrbody
	guint16		_addrport;		///< private: Address port (if applicable)

};
WINEXPORT NetAddr*	netaddr_new(gsize objsize, guint16 port, guint16 addrtype, gconstpointer addrbody, guint16 addrlen);
WINEXPORT NetAddr*	netaddr_sockaddr_new(const struct sockaddr_in6 *, socklen_t);
WINEXPORT NetAddr*	netaddr_macaddr_new(gconstpointer macbuf, guint16 maclen);
WINEXPORT NetAddr*	netaddr_mac48_new(gconstpointer macbuf);
WINEXPORT NetAddr*	netaddr_mac64_new(gconstpointer macbuf);
WINEXPORT NetAddr*	netaddr_ipv4_new(gconstpointer	ipbuf, guint16	port);
WINEXPORT NetAddr*	netaddr_ipv6_new(gconstpointer ipbuf, guint16	port);
WINEXPORT NetAddr*	netaddr_string_new(const char* addrstr);
WINEXPORT NetAddr*	netaddr_dns_new(const char* addrstr);
WINEXPORT gboolean	netaddr_g_hash_equal(gconstpointer lhs, gconstpointer rhs);
WINEXPORT guint		netaddr_g_hash_hash(gconstpointer addrptr);

#define	CONST_IPV6_LOOPBACK		{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1}
#define	CONST_IPV4_LOOPBACK		{127,0,0,1}
#define	CONST_IPV6_IPV4SPACE		0,0,0,0,0,0,0,0,0,0,0xff,0xff
#define	CONST_IPV6_IPV4START		{CONST_IPV6_IPV4SPACE, 0, 0, 0, 0}
#define	CONST_IPV6_MACSPACE		0xFE, 0x80, 0, 0, 0, 0, 0, 0x02
#define	CONST_IPV6_MACSTART		{CONST_IPV6_MACSPACE, 0, 0, 0, 0, 0, 0, 0, 0}


#define	CONST_ASSIM_DEFAULT_V4_MCAST	{224,0,2,5}	///< This is our reserved multicast address

///@}

#endif /* _NETADDR_H */
