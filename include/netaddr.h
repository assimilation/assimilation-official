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

/// The @ref NetAddr class represents a general network address - whether IP, MAC, or @ref AddressFamilyNumbers "any other type of address".
/// It is a class from which we <i>might</i> eventually make subclasses,
/// and is managed by our @ref ProjectClass system.
///@{
/// @ingroup NetAddr
struct _NetAddr {
	guint16		(*port)(const NetAddr* self);		///< Return port from this address
	guint16		(*addrtype)(const NetAddr* self);	///< Return @ref AddressFamilyNumbers address type
	struct sockaddr_in6(*ipv6sockaddr)(const NetAddr* self);///< Return the ipv6 address corresponding to this address
	gboolean	(*equal)(const NetAddr*,const NetAddr*);///< Compare NetAddrs
	gchar *		(*toString)(const NetAddr* self);	///< Convert to g_malloced (!) string
	void		(*ref)(NetAddr* self);			///< Add a reference to this object
	void		(*unref)(NetAddr* self);		///< Add a reference to this object
	void		(*_finalize)(NetAddr* self);		///< Finalize this object.
	gpointer	_addrbody;				///< private: Address body
	guint16		_addrtype;				///< private: Address type
	guint16		_addrlen;				///< private: Length of _addrbody
	guint16		_addrport;				///< private: Address port (if applicable)
	guint16		_refcount;				///< private: Reference count
};
NetAddr*	netaddr_new(gsize objsize, guint16 port, guint16 addrtype, gconstpointer addrbody, guint16 addrlen);
NetAddr*	netaddr_sockaddr_new(const struct sockaddr_in6 *, socklen_t);
NetAddr*	netaddr_macaddr_new(gconstpointer macbuf, guint16 maclen);
NetAddr*	netaddr_mac48_new(gconstpointer macbuf);
NetAddr*	netaddr_mac64_new(gconstpointer macbuf);
NetAddr*	netaddr_ipv4_new(gconstpointer	ipbuf, guint16	port);
NetAddr*	netaddr_ipv6_new(gconstpointer ipbuf, guint16	port);


#define	CONST_IPV6_LOOPBACK	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1}
#define	CONST_IPV4_LOOPBACK	{127,0,0,1}
#define	CONST_IPV6_IPV4SPACE	0,0,0,0,0,0,0,0,0,0,0xff,0xff
#define	CONST_IPV6_IPV4START	{IPV4SPACE, 0, 0, 0, 0}
#define	CONST_IPV6_MACSPACE	0xFE, 0x80, 0, 0, 0, 0, 0, 0x02
#define	CONST_IPV6_MACSTART	{CONST_IPV6_MACSPACE, 0, 0, 0, 0, 0, 0, 0, 0}

///@}

#endif /* _NETADDR_H */
