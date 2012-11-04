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
	struct sockaddr_in6(*ipv6sockaddr)(const NetAddr* self);///< Return the ipv6 sockaddr corresponding to this address
	struct sockaddr_in(*ipv4sockaddr)(const NetAddr* self);///< Return the ipv4 sockaddr corresponding to this address
	gboolean	(*equal)(const NetAddr*,const NetAddr*);///< Compare NetAddrs
	char *		(*canonStr)(const NetAddr*);		///< Canonical form toString
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


#define	CONST_IPV6_LOOPBACK		{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1}
#define	CONST_IPV4_LOOPBACK		{127,0,0,1}
#define	CONST_IPV6_IPV4SPACE		0,0,0,0,0,0,0,0,0,0,0xff,0xff
#define	CONST_IPV6_IPV4START		{IPV4SPACE, 0, 0, 0, 0}
#define	CONST_IPV6_MACSPACE		0xFE, 0x80, 0, 0, 0, 0, 0, 0x02
#define	CONST_IPV6_MACSTART		{CONST_IPV6_MACSPACE, 0, 0, 0, 0, 0, 0, 0, 0}


#define	CONST_ASSIM_DEFAULT_V4_MCAST	{224,0,2,5}	///< This is our reserved multicast address

///@}

#endif /* _NETADDR_H */
