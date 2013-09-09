/**
 * @file
 * @brief Defines interfaces for the NetAddr (network address) object.
 * @details These can be various kinds of network addresses - IPV4, IPv6,
 * MAC addresses, etc. as enumerated by IANA, and covered by RFC 3232.
 * This class implements a basic API on these objects.
 *
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

#include <stdlib.h>
#include <memory.h>
#include <ctype.h>
#include <projectcommon.h>
#include <netaddr.h>
#include <address_family_numbers.h>
#ifdef _MSC_VER
#	include <ws2tcpip.h>
#endif
#ifdef HAVE_SYS_TYPES_H
#	include <sys/types.h>
#endif
#ifdef HAVE_SYS_SOCKET_H
#	include <sys/socket.h>
#endif
#ifdef HAVE_NETDB_H
#	include <netdb.h>
#endif

FSTATIC struct sockaddr_in6 _netaddr_ipv6sockaddr(const NetAddr* self);
FSTATIC struct sockaddr_in _netaddr_ipv4sockaddr(const NetAddr* self);
FSTATIC void _netaddr_finalize(AssimObj* self);
FSTATIC guint16 _netaddr_port(const NetAddr* self);
FSTATIC void _netaddr_setport(NetAddr* self, guint16);
FSTATIC guint16 _netaddr_addrtype(const NetAddr* self);
FSTATIC gboolean _netaddr_ismcast(const NetAddr* self);
FSTATIC gboolean _netaddr_islocal(const NetAddr* self);
FSTATIC gboolean _netaddr_isanyaddr(const NetAddr* self);
FSTATIC gconstpointer _netaddr_addrinnetorder(gsize *addrlen);
FSTATIC gboolean _netaddr_equal(const NetAddr*, const NetAddr*);
FSTATIC guint _netaddr_hash(const NetAddr*);
FSTATIC gchar * _netaddr_toStringflex(const NetAddr*, gboolean canonformat);
FSTATIC gchar * _netaddr_toString(gconstpointer);
FSTATIC gchar * _netaddr_canonStr(const NetAddr*);
FSTATIC NetAddr* _netaddr_toIPv6(const NetAddr*);
FSTATIC gchar * _netaddr_toString_ipv6_ipv4(const NetAddr* self, gboolean ipv4format);
FSTATIC NetAddr* _netaddr_string_ipv4_new(const char* addrstr);
FSTATIC NetAddr* _netaddr_string_ipv6_new(const char* addrstr);
FSTATIC NetAddr* _netaddr_string_macaddr_new(const char* addrstr);

DEBUGDECLARATIONS

/// @defgroup NetAddr NetAddr class
///@{
/// @ingroup C_Classes
/// This is our basic NetAddr object.
/// It represents network addresses of any of a wide variety of well-known @ref AddressFamilyNumbers "well-known types".
/// It is a class from which we might eventually make subclasses,
/// and is managed by our @ref ProjectClass system.

static const guchar ipv6loop [16]		= CONST_IPV6_LOOPBACK;	
static const guchar ipv4loopversion2 [16]	= {CONST_IPV6_IPV4SPACE, 127, 0, 0, 1};
static const guchar ipv4loop [4]		= CONST_IPV4_LOOPBACK;

/// Convert this IPv6-encapsulated IPv4 NetAddr to a string
FSTATIC gchar *
_netaddr_toString_ipv6_ipv4(const NetAddr* self, gboolean ipv4format)
{
	const char *	prefix;
	const char *	suffix;
	if (self->_addrport) {
		prefix = (ipv4format ? ""  : "[::ffff:");
		suffix = (ipv4format ? ":" : "]:"      );
	}else{
		prefix = (ipv4format ? ""  : "::ffff:");
		suffix = ""; // Not used
	}
		
	if (self->_addrport) {
		return g_strdup_printf("%s%d.%d.%d.%d%s%d",
				       prefix,
				       ((const guchar*)self->_addrbody)[12],
				       ((const guchar*)self->_addrbody)[13],
				       ((const guchar*)self->_addrbody)[14],
				       ((const guchar*)self->_addrbody)[15],
				       suffix,
				       self->_addrport);
	}
	return g_strdup_printf("%s%d.%d.%d.%d",
			       prefix,
			       ((const guchar*)self->_addrbody)[12],
			       ((const guchar*)self->_addrbody)[13],
			       ((const guchar*)self->_addrbody)[14],
			       ((const guchar*)self->_addrbody)[15]);
}
/// Convert this IPv6-encapsulated IPv4 NetAddr to an IPv4 representation
/// Convert this NetAddr to a string
FSTATIC gchar *
_netaddr_toString(gconstpointer baseobj)
{
	const NetAddr*	self = CASTTOCONSTCLASS(NetAddr, baseobj);
	return _netaddr_toStringflex(self, FALSE);
}

FSTATIC gchar *
_netaddr_canonStr(const NetAddr* self)
{
	return _netaddr_toStringflex(self, TRUE);
}

/// Convert this IPv6-encapsulated IPv4 NetAddr to an IPv4 representation
NetAddr*
_netaddr_toIPv6(const NetAddr* self)
{
	
	switch (self->_addrtype) {
		case ADDR_FAMILY_IPV6:
			// Return a copy of this IPv6 address
			return netaddr_ipv6_new(self->_addrbody, self->_addrport);

		case ADDR_FAMILY_IPV4: {
			const int	ipv4prefixlen	= 12;
			guchar 		ipv6addr[16]	= {CONST_IPV6_IPV4SPACE, 0, 0, 0, 0};
			// We have an IPv4 address we want to convert to an IPv6 address
			if (memcmp(self->_addrbody, ipv4loop, sizeof(ipv4loop)) == 0) {
				// Convert loopback addresses from v4 to v6
				memcpy(ipv6addr, ipv6loop, sizeof(ipv6loop));
			}else{
				memcpy(ipv6addr+ipv4prefixlen, self->_addrbody, 4);
			}
			return netaddr_ipv6_new(ipv6addr, self->_addrport);
		}

		default:	// OOPS!
			break;
	}
	/// @todo Convert MAC addresses to IPv6 addresses??
	g_return_val_if_reached(NULL);
}


/// Convert this NetAddr to a string
FSTATIC gchar *
_netaddr_toStringflex(const NetAddr* self, gboolean canon_format)
{
	gchar *		ret = NULL;
	GString*	gsret = NULL;
	int		nbyte;
	if (self->_addrtype == ADDR_FAMILY_IPV4) {
		if (self->_addrport) {
			return g_strdup_printf("%d.%d.%d.%d:%d",
					      ((const guchar*)self->_addrbody)[0],
					      ((const guchar*)self->_addrbody)[1],
					      ((const guchar*)self->_addrbody)[2],
					      ((const guchar*)self->_addrbody)[3],
					      self->_addrport);
		}
		return g_strdup_printf("%d.%d.%d.%d",
				      ((const guchar*)self->_addrbody)[0],
				      ((const guchar*)self->_addrbody)[1],
				      ((const guchar*)self->_addrbody)[2],
				      ((const guchar*)self->_addrbody)[3]);
	}
	gsret = g_string_new("");
	if (self->_addrtype == ADDR_FAMILY_IPV6) {
		gboolean	doublecolonyet = FALSE;
		gboolean	justhaddoublecolon = FALSE;
		int		zerocount = 0;
		guchar		ipv4prefix[] = {0,0,0,0,0,0,0,0,0,0,0xff,0xff};
                if (self->_addrlen != 16) {
			g_string_free(gsret, TRUE); gsret = NULL;
			return g_strdup("{invalid ipv6}");
		}
		if (self->_addrport) {
			g_string_append(gsret, "[");
		}
		if (memcmp(self->_addrbody, ipv4prefix, sizeof(ipv4prefix)) == 0) {
			g_string_free(gsret, TRUE); gsret = NULL;
			return _netaddr_toString_ipv6_ipv4(self, canon_format);
		}
		for (nbyte = 0; nbyte < self->_addrlen; nbyte += 2) {
			guint16 byte0 = ((const guchar*)self->_addrbody)[nbyte];
			guint16 byte1 = ((const guchar*)self->_addrbody)[nbyte+1];
			guint16 word = (byte0 << 8 | byte1);
			if (!doublecolonyet && word == 0x00) {
				++zerocount;
				continue;
			}
			if (zerocount == 1) {
				g_string_append_printf(gsret, (nbyte == 2 ? "0" : ":0"));
				zerocount=0;
			}else if (zerocount > 1) {
				g_string_append_printf(gsret, "::");
				zerocount=0;
				doublecolonyet = TRUE;
				justhaddoublecolon = TRUE;
			}
			g_string_append_printf(gsret
			,	((nbyte == 0 || justhaddoublecolon) ? "%x" : ":%x"), word);
			justhaddoublecolon = FALSE;
		}
		if (zerocount == 1) {
			g_string_append_printf(gsret, ":00");
		}else if (zerocount > 1) {
			g_string_append_printf(gsret, "::");
		}
		if (self->_addrport) {
			g_string_append_printf(gsret, "]:%d", self->_addrport);
		}
		
	}else{
		for (nbyte = 0; nbyte < self->_addrlen; ++nbyte) {
			g_string_append_printf(gsret, (nbyte == 0 ? "%02x" : ":%02x"),
					       ((const guchar*)self->_addrbody)[nbyte]);
		}
	}
	ret = gsret->str;
	g_string_free(gsret, FALSE);
	return ret;
}

/// Return TRUE if these two addresses are "equal" (equivalent)
FSTATIC gboolean
_netaddr_equal(const NetAddr*self, const NetAddr*other)
{
	///@todo Perhaps we ought to eventually compare for MAC addresses and IPv6 equivalents ;-)
	const guchar	ipv6v4   [12] = {CONST_IPV6_IPV4SPACE};// Where IPv4 addrs are found inside IPv6 space
	gint		memcmprc;


	DEBUGMSG5("%s.%d: Comparing (type %d, length %d) vs (type %d, length %d)"
	,	__FUNCTION__, __LINE__, self->_addrtype, self->_addrlen, other->_addrtype, other->_addrlen)
	DEBUGMSG5("%s.%d: checking ports for equality (if v4/v6 addresses)", __FUNCTION__, __LINE__)
	if ((self->_addrtype  == ADDR_FAMILY_IPV6  || self->_addrtype  == ADDR_FAMILY_IPV4)
	&&  (other->_addrtype == ADDR_FAMILY_IPV6  || other->_addrtype == ADDR_FAMILY_IPV4)
	&&	self->_addrport != other->_addrport) {
		DEBUGMSG5("%s.%d: selfport:%d, otherport:%d", __FUNCTION__, __LINE__, self->_addrport, other->_addrport);
		return FALSE;
	}

	if (self->_addrtype == ADDR_FAMILY_IPV6) {
		DEBUGMSG5("%s.%d: self is IPv6", __FUNCTION__, __LINE__)
		if (other->_addrtype == ADDR_FAMILY_IPV4) {
			const guchar *selfabody = self->_addrbody;
			// Check for equivalent IPv4 and IPv6 addresses
			DEBUGMSG5("%s.%d: checking equivalent v6/v4 addresses", __FUNCTION__, __LINE__)
			if (memcmp(selfabody, ipv6v4, sizeof(ipv6v4)) == 0
			&&  memcmp(selfabody+12, other->_addrbody, 4) == 0) {
				DEBUGMSG5("%s.%d: v6/v4 addresses are equivalent", __FUNCTION__, __LINE__)
				return TRUE;
			}
			DEBUGMSG5("%s.%d: checking v6/v4 loopbacks", __FUNCTION__, __LINE__)
			// Check for the equivalent loopback addresses between IPv4 and IPv6
			/// @todo Not sure if it should treat the two loopbacks as the same...
			if (memcmp(self->_addrbody,  ipv6loop, sizeof(ipv6loop)) == 0
			&&  memcmp(other->_addrbody, ipv4loop, sizeof(ipv4loop)) == 0) {
				DEBUGMSG5("%s.%d: v6/v4 addresses are both loopbacks", __FUNCTION__, __LINE__)
				return TRUE;
			}
			DEBUGMSG5("%s.%d: v6/v4 addresses are not equivalent", __FUNCTION__, __LINE__)
			return FALSE;
		}else if (other->_addrtype == ADDR_FAMILY_IPV6) {
			// Well... Are we cross comparing the two types of ipv6 loopback addresses?
			// These are:   ::1 and ::ff:127.0.0.1		Kinda weird - but seems valid...
			DEBUGMSG5("%s.%d: other is IPv6 too", __FUNCTION__, __LINE__)
			if (memcmp(self->_addrbody, ipv6loop, sizeof(ipv6loop)) == 0) {
				DEBUGMSG5("%s.%d: comparing loopbacks", __FUNCTION__, __LINE__);
				if (memcmp(other->_addrbody, ipv4loopversion2, sizeof(ipv4loopversion2)) == 0) {
					return TRUE;
				}
			}else if (memcmp(self->_addrbody, ipv4loopversion2, sizeof(ipv4loopversion2)) == 0) {
				DEBUGMSG5("%s.%d: comparing loopbacks the other way", __FUNCTION__, __LINE__);
				if (memcmp(other->_addrbody, ipv6loop, sizeof(ipv6loop)) == 0) {
					return TRUE;
				}
			}
		}
	}
	
	DEBUGMSG5("%s.%d: checking to see if we need to reverse operands...", __FUNCTION__, __LINE__)
	
	if (self->_addrtype == ADDR_FAMILY_IPV4 && other->_addrtype == ADDR_FAMILY_IPV6) {
		gboolean	retval;
		// Switch the operands and try again...
		DEBUGMSG5("%s.%d: switching operands", __FUNCTION__, __LINE__)
		retval =  _netaddr_equal(other, self);
		DEBUGMSG5("%s.%d: returning %s after switching operands", __FUNCTION__, __LINE__
		,	(retval ? "True" : "False"));
		return retval;
	}
	DEBUGMSG5("%s.%d: checking type and length...", __FUNCTION__, __LINE__)
	// Other than ipv4 vs ipv6 (handled above) we require addresses to be of the same type
	if (self->_addrtype != other->_addrtype || self->_addrlen  != other->_addrlen) {
		DEBUGMSG5("%s.%d: self->addrtype:%d, other->addrtype:%d", __FUNCTION__, __LINE__, self->_addrtype, other->_addrtype);
		DEBUGMSG5("%s.%d: self->addrlen: %d, other->addrlen: %d", __FUNCTION__, __LINE__, self->_addrlen, other->_addrlen);
		return FALSE;
	}
	memcmprc = memcmp(self->_addrbody, other->_addrbody, self->_addrlen);
	DEBUGMSG5("%s.%d: memcmp(self, other, %d) returned %d", __FUNCTION__, __LINE__
	,	self->_addrlen, memcmprc);
	return memcmprc == 0;
}

#ifndef CHAR_BIT
#	define	CHAR_BIT	8
#endif
/// NetAddr hash function which worries about denial of service via hash collisions.
/// Note that this function will produce results unique to this process instance.
/// This is to avoid denial of service through has hash collisions
FSTATIC guint
_netaddr_hash(const NetAddr* self)
{
	// For an explanation of the random hash seed see https://lwn.net/Articles/474912/
	const	guint	shift	 = 7;
	static	guint	hashseed = 0;
	int		j;
	NetAddr*	v6addr = NULL;
	const NetAddr*	addrtouse = self;
	guint		result;
	const guchar v6loopback[16] =  CONST_IPV6_LOOPBACK;
	while (0 == hashseed) {
		hashseed = (guint)g_random_int();
	}


	DEBUGMSG5("%s.%d: %d/%d:%d NetAddr", __FUNCTION__, __LINE__
	,	self->_addrtype, self->_addrlen, self->_addrport);
	// Convert v4 addresses into v6 so that we match the compare operation's behavior
	if (self->_addrtype == ADDR_FAMILY_IPV4) {
		DEBUGMSG5("%s.%d: Hashing IPv6", __FUNCTION__, __LINE__);

		// This is kind of high overhead... Could be optimized if need be
		if (memcmp(self->_addrbody, ipv4loop, sizeof(ipv4loop))== 0) {
			DEBUGMSG5("%s.%d: Returning an IPv6 loopback value", __FUNCTION__, __LINE__);
			v6addr = netaddr_ipv6_new(v6loopback, self->_addrport);
		}else{
			DEBUGMSG5("%s.%d: Returning an IPv6 replacement value", __FUNCTION__, __LINE__);
			v6addr = _netaddr_toIPv6(self);
		}
		addrtouse = v6addr;
	}else if (self->_addrtype == ADDR_FAMILY_IPV6) {
		DEBUGMSG5("%s.%d: Hashing IPv6", __FUNCTION__, __LINE__);
		if (memcmp(self->_addrbody, ipv4loopversion2, sizeof(ipv4loopversion2)) == 0) {
			DEBUGMSG5("%s.%d: Returning an IPv6 loopback value", __FUNCTION__, __LINE__);
			v6addr = netaddr_ipv6_new(v6loopback, self->_addrport);
			addrtouse = v6addr;
		}
	}

	g_return_val_if_fail(addrtouse != NULL, 0);
	result = (guint)(addrtouse->_addrtype) ^ hashseed;
	if (addrtouse->_addrtype == ADDR_FAMILY_IPV6 || addrtouse->_addrtype == ADDR_FAMILY_IPV4) {
		result ^= addrtouse->_addrport;
	}
	for (j=0; j < addrtouse->_addrlen; ++j) {
		// Circular shift with addrbody xored in...
		// Addresses are typically either 4 bytes or 16 bytes (6 and 8 bytes are also possible)
		// So 4 bytes means the first byte gets shifted by 28 bits, and 16 means it 
		// all wraps around a lot ;-)
		result	=  ((result << shift) | (result >> (sizeof(result)*CHAR_BIT - shift)))
			^ ((guint)((guint8*)addrtouse->_addrbody)[j]);
	}
	if (v6addr) {
		UNREF(v6addr);
		addrtouse = NULL;
	}
	return result;
}

/// g_hash_table equal comparator for a NetAddr
WINEXPORT gboolean
netaddr_g_hash_equal(gconstpointer lhs, gconstpointer rhs)
{
	const NetAddr* a_lhs = CASTTOCONSTCLASS(NetAddr, lhs);
	const NetAddr* a_rhs = CASTTOCONSTCLASS(NetAddr, rhs);
	return a_lhs->equal(a_lhs, a_rhs);
}

/// g_hash_table hash function for a NetAddr
WINEXPORT guint
netaddr_g_hash_hash(gconstpointer addrptr)
{
	const NetAddr* self = CASTTOCONSTCLASS(NetAddr, addrptr);
	return self->hash(self);
}

/// Finalize (free) this object
FSTATIC void
_netaddr_finalize(AssimObj* base)
{
	NetAddr*	self = CASTTOCLASS(NetAddr, base);
	if (self->_addrbody) {
		FREE(self->_addrbody);
		self->_addrbody = NULL;
	}
	FREECLASSOBJ(self);
	self = NULL;
}


/// Return the port of this NetAddr
FSTATIC guint16
_netaddr_port(const NetAddr* self)
{
	return self->_addrport;
}


/// Set the port of this NetAddr
FSTATIC void
_netaddr_setport(NetAddr* self, guint16 port)
{
	self->_addrport = port;
}


/// Return the address type of this NetAddr
FSTATIC guint16
_netaddr_addrtype(const NetAddr* self)
{
	return self->_addrtype;
}

/// Return TRUE if this is a multicast address
FSTATIC gboolean
_netaddr_ismcast(const NetAddr* self)
{
	if (self->_addrbody == NULL) {
		return FALSE;
	}
	/// @todo recognize IPv6 multicast addresses too...
	switch (self->_addrtype) {
		case ADDR_FAMILY_IPV4: {
			guint8 byte0 = ((guint8*)self->_addrbody)[0];
			return (byte0 >= 224 && byte0 <= 239);
		}
		break;;
	}
	return	FALSE;
}
/// Return TRUE if this is a multicast address
FSTATIC gboolean
_netaddr_islocal(const NetAddr* self)
{
	switch (self->_addrtype) {
		case ADDR_FAMILY_IPV4: {
			guint8 byte0 = ((guint8*)self->_addrbody)[0];
			return byte0 == 127;;
		}
		case ADDR_FAMILY_IPV6: {
			const guint8	ipv6local[16] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1};
			const guint8	ipv4localprefix[13] = {0,0,0,0,0,0,0,0,0,0,0xff,0xff, 127};
			if (memcmp(self->_addrbody, ipv6local, sizeof(ipv6local)) == 0) {
				return TRUE;
			}
			if (memcmp(self->_addrbody, ipv4localprefix, sizeof(ipv4localprefix)) == 0) {
				return TRUE;
			}
			break;
		}

		default:
			break;
	}
	return	FALSE;
}

FSTATIC gboolean
_netaddr_isanyaddr(const NetAddr* self)
{
	const guint8	anyaddr[16] =		{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
	const guint8    v6v4anyaddr[16] =	{CONST_IPV6_IPV4SPACE, 0, 0, 0, 0};
	if (self->_addrtype != ADDR_FAMILY_IPV4 && self->_addrtype != ADDR_FAMILY_IPV6) {
		return FALSE;
	}
	if (memcmp(self->_addrbody, anyaddr, self->_addrlen) == 0) {
		return TRUE;
	}
	return memcmp(self->_addrbody, v6v4anyaddr, self->_addrlen) == 0;
}
	

/// Generic NetAddr constructor.
NetAddr*
netaddr_new(gsize objsize,				///<[in] Size of object to construct
	    guint16 port,				///<[in] Port (if applicable)
	    guint16 addrtype,				///<[in] IETF/IANA address type
	    gconstpointer addrbody,			///<[in] Pointer to address body
	    guint16 addrlen)				///<[in] Length of address
{
	AssimObj*	baseobj;
	NetAddr*	self;

	
	BINDDEBUG(NetAddr);
	if (objsize < sizeof(NetAddr)) {
		objsize = sizeof(NetAddr);
	}
	g_return_val_if_fail(addrbody != NULL, NULL);
	g_return_val_if_fail(addrlen >= 4, NULL);

	

	baseobj = assimobj_new(objsize);
	proj_class_register_subclassed(baseobj, "NetAddr");
	self = CASTTOCLASS(NetAddr, baseobj);
	g_return_val_if_fail(self != NULL, NULL);

	baseobj->_finalize = _netaddr_finalize;
	baseobj->toString = _netaddr_toString;
	self->canonStr = _netaddr_canonStr;
	self->toIPv6 = _netaddr_toIPv6;
	self->_addrport = port;
	self->_addrtype = addrtype;
	self->_addrlen = addrlen;
	self->ipv6sockaddr = _netaddr_ipv6sockaddr;
	self->ipv4sockaddr = _netaddr_ipv4sockaddr;
	self->_addrbody = g_memdup(addrbody, addrlen);
	self->port = _netaddr_port;
	self->setport = _netaddr_setport;
	self->addrtype = _netaddr_addrtype;
	self->ismcast = _netaddr_ismcast;
	self->islocal = _netaddr_islocal;
	self->isanyaddr = _netaddr_isanyaddr;
	self->equal = _netaddr_equal;
	self->hash = _netaddr_hash;

	return self;

}

/// Convert a string to an IPv4 NetAddr
FSTATIC NetAddr*
_netaddr_string_ipv4_new(const char* addrstr)
{
	// Must have four numbers [0-255] in decimal - optionally followed by : port number...
	int		dotpositions[3];
	int		colonpos = -1;
	guint8		addresses[4];
	guint8		stack_protector_dummy[8];
	guint		whichdot = 0;
	int		byte;
	NetAddr*	ret;
	int		port = 0;
	
	guint	j;
	int	debug = FALSE;
	int	lastpos = 0;

	(void)stack_protector_dummy;
	//debug = g_ascii_isdigit(addrstr[0]);

	if (debug) {
		g_debug("CHECKING [%s]", addrstr);
	}

	// Scruffy IPv4 string format verification
	for (j=0; addrstr[j]; ++j) {
		if (debug) {
			g_debug("Looking at '%c'", addrstr[j]);
		}
		switch(addrstr[j]) {
			case '0': case '1': case '2': case '3': case '4':
			case '5': case '6': case '7': case '8': case '9':
			continue;

			case '.':
				if (whichdot >= DIMOF(dotpositions)
				||	colonpos >= 0) {
					return NULL;
				}
				dotpositions[whichdot] = j;
				whichdot += 1;
				continue;

			case '\0':
				break;
			case ':':
				if (colonpos >= 0) {
					return NULL;
				}
				colonpos = j;
				break;

			default:
				if (debug) {
					g_debug("Illegal character [%c]", addrstr[j]);
				}
					
				return NULL;
		}
		if (j > 21) {
			return NULL;
		}
	}
	lastpos = j;
	if (debug) {
            g_debug("whichdot = %d", whichdot);
	}
	if (whichdot != 3) {
		return NULL;
	}
	byte = atoi(addrstr);
	if (debug) {
	    g_debug("byte %d = %d", 0, byte);
	}
	if (byte < 0 || byte > 255) {
		return NULL;
	}
	addresses[0] = byte;


	for (j=0; j < DIMOF(dotpositions); ++j) {
		byte = atoi(addrstr+dotpositions[j]+1);
		if (debug) {
		    g_debug("byte %d = %d", j, byte);
		}
		if (byte < 0 || byte > 255) {
			return NULL;
		}
		addresses[j+1] = (guint8)byte;
	}
	if (colonpos >= 0) {
		if (colonpos > (lastpos - 2)) {
			return NULL;
		}
		port = atoi(addrstr+colonpos+1);
		if (port > 65535) {
			g_debug("found bad (%s) IPV4 port", addrstr+colonpos+1);
			return NULL;
		}
		if (debug) {
			g_debug("found good IPV4 port [%d]", port);
		}
	}
	if (debug) {
		g_debug("Returning good IPV4 address!");
	}
	ret =  netaddr_ipv4_new(addresses, port);
	if (debug) {
		g_debug("Returning good IPV4 address [%p]!", ret);
	}
	return ret;
}

/// Convert a string into an IPv6 address - possibly including a port as per RFC 4291.
/// Format is either abcd:efab:cdab:cdef:abcd:efab:cdab:cdef with :: standing in for missing zeroes - 
/// or [abcd:efab:cdab:cdef:abcd:efab:cdab:cdef]:port-in-decimal - as per standard convention and the RFC.
FSTATIC NetAddr*
_netaddr_string_ipv6_new(const char* addrstr)
{
/*
 *	ipv6
 *  OR
 *	[ipv6]:decimal-port
 *
 *	The 'IPv6' part is described by RFC 4291
 *
 *
 *	It consists of a sequence of 0-8 collections of 1-4 hexadecimal digits separated by
 *	colon characters.
 *	If there are fewer than 8 collections of digits, then there must be exactly one :: string
 *	in the address string.  This :: tag represents a variable-length sequence of zeros in the address.
 *
 *	There is also another variant on the format of the IPv6 portion:
 *
 *	It can be "::ffff:" followed by an IPv4 address in typical IPv4 dotted decimal notation.
 *	@todo make _netaddr_string_ipv6_new() support the special format used for
 *	      IPv6-encapsulated IPv4 addresses.
 *
 */
	int		len = strlen(addrstr);
	const char *	firstaddrdigit = addrstr;
	const char *	lastaddrdigit = addrstr+len-1;
	const char *	curaddrdigit;
	unsigned	j;
	long		port = 0;
	guint16		addrchunks[8];
	guint8		addrbytes[16];
	guint8*		addrptr;
	guint		chunkindex = 0;
	int		coloncolonindex = -1;
	guint		coloncolonlength = 0;
	char*		firstbadhexchar = NULL;
	NetAddr*	retval;
	const char	v4prefix[] = "ffff:";
	const guint	v4prefixlen = sizeof(v4prefix)-1;
	gboolean	v4encapsulated = FALSE;
	guint		conversionbase = 16;
	char		delimchar = ':';
	guint		maxchunkindex = DIMOF(addrchunks);
	long		maxchunkvalue = 65535;

	DEBUGMSG5("%s.%d(\"%s\")", __FUNCTION__, __LINE__, addrstr);
	memset(addrchunks, 0, sizeof(addrchunks));

	if (*addrstr == '[') {
		// Then we have a port number - look for ']' and ':'
		char *	rbracketpos = strchr(addrstr+1, ']');
		char *	firstbadchar = rbracketpos;

		if (rbracketpos == NULL || rbracketpos[1] != ':') {
			return NULL;
		}
		firstaddrdigit += 1;
		lastaddrdigit = rbracketpos - 1;
		port = strtol(rbracketpos+2, &firstbadchar, 10);
		if (*firstbadchar != '\0' || port <= 0 || port >= 65536) {
			DEBUGMSG5("%s.%d: Not IPv6 format due to bad port number syntax"
			,	__FUNCTION__, __LINE__);
			return NULL;
		}
	}
	// Now, we know where the collection of address characters starts and ends
	if (firstaddrdigit[0] == ':' && firstaddrdigit[1] == ':') {
		coloncolonindex = 0;
		firstaddrdigit += 2;
		// Let's see if it might be an ipv4 address encapsulated as ipv6...
		DEBUGMSG5("%s.%d: LOOKING to see if we have an encapsulated IPv4 address. [%s] [%s]"
		,	__FUNCTION__, __LINE__, firstaddrdigit, v4prefix);
		if (strncmp(firstaddrdigit, v4prefix, v4prefixlen) == 0) {
			DEBUGMSG5("%s.%d: May have an encapsulated IPv4 address. [%s]"
			,	__FUNCTION__, __LINE__, firstaddrdigit);
			if (strchr(firstaddrdigit + v4prefixlen, '.') != NULL) {
				// We have '.'s but no more ':'s...
				DEBUGMSG5("%s.%d: Appear to have an encapsulated IPv4 address."
				,	__FUNCTION__, __LINE__);
				v4encapsulated = TRUE;
				conversionbase = 10;	// IPv4 addresses are decimal
				delimchar = '.';	// IPv4 addresses use . delimiters
				maxchunkindex = 4;	// IPv4 addresses have exactly 4 parts
				maxchunkvalue = 255;	// IPv4 address elements are single bytes
				firstaddrdigit += v4prefixlen;
			}
		}
	}
	curaddrdigit = firstaddrdigit;
	// Loop over the characters, breaking them into a series of hexadecimal (or decimal) chunks
	for (chunkindex=0; chunkindex < maxchunkindex && curaddrdigit <= lastaddrdigit; ++chunkindex) {
		long	chunk = strtol(curaddrdigit, &firstbadhexchar, conversionbase);
		DEBUGMSG5("%s.%d: chunk %d begins [%s] converts to 0x%lx", __FUNCTION__, __LINE__
		,	chunkindex, curaddrdigit, (unsigned long)chunk);
		if (chunk < 0 || chunk > maxchunkvalue) {
			DEBUGMSG5("%s.%d: Not IPv6 format due to invalid chunk value [%ld]"
			,	__FUNCTION__, __LINE__, chunk);
			return NULL;
		}
		// Remember the value of this chunk...
		addrchunks[chunkindex] = (guint16)chunk;

		// Was the ending delimiter what we expected?
		if (firstbadhexchar <= lastaddrdigit && *firstbadhexchar != delimchar) {
			DEBUGMSG5("%s.%d: Not IPv6 format due to invalid character [%c]"
			,	__FUNCTION__, __LINE__, *firstbadhexchar);
			return NULL;
		}
		curaddrdigit = firstbadhexchar;
		if (v4encapsulated && *firstbadhexchar == delimchar) {
			curaddrdigit += 1;
		// Is there a :: in this position in the address?
		}else if (!v4encapsulated && firstbadhexchar[0] == ':') {
			if (firstbadhexchar[1] == ':') {
				if (coloncolonindex >= 0) {
					// :: can only appear once in the address
					DEBUGMSG5("%s.%d: Not IPv6 format due to multiple ::'s"
					,	__FUNCTION__, __LINE__);
					return NULL;
				}
				coloncolonindex = chunkindex + 1;
				curaddrdigit += 2;
			}else{
				curaddrdigit += 1;
			}
		}else if (*firstbadhexchar != ']' && *firstbadhexchar != '\0') {
			DEBUGMSG5("%s.%d: Not IPv6 format due to illegal char [%c]"
			,	__FUNCTION__, __LINE__,	*firstbadhexchar);
			return NULL;
		}
			
		if (firstbadhexchar >= lastaddrdigit + 1) {
			break;
		}
	}
	if (firstbadhexchar != NULL && firstbadhexchar != lastaddrdigit + 1) {
		DEBUGMSG5("%s.%d: Not IPv6 format due to excess length.", __FUNCTION__, __LINE__);
		DEBUGMSG5("%s.%d: firstbadhexchar = %p, lastaddrdigit = %p, diff=%ld"
		,	__FUNCTION__, __LINE__, firstbadhexchar, lastaddrdigit
		,	(long)(lastaddrdigit-firstbadhexchar));
		return NULL;
	}
	if (coloncolonindex >= 0 && chunkindex == DIMOF(addrchunks)-1) {
		DEBUGMSG5("%s.%d: Not IPv6 format due to full length with :: present"
		,	__FUNCTION__, __LINE__);
		return NULL;
	}
	if (coloncolonindex < 0 && chunkindex != DIMOF(addrchunks)-1) {
		DEBUGMSG5("%s.%d: Not IPv6 format due to too few digits."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}
	// OK --- now we have something that looks a lot like a legit IPv6 address.
	// let's see if we can make a NetAddr out of it...
	if (coloncolonindex >= 0) {
		coloncolonlength = (DIMOF(addrchunks)-1) - chunkindex;
		DEBUGMSG5("%s.%d: coloncolonlength is %d, index is %d", __FUNCTION__, __LINE__
		,	coloncolonlength, coloncolonindex);
	}
	DEBUGMSG5("%s.%d: chunkindex is %d", __FUNCTION__, __LINE__, chunkindex);

	addrptr = addrbytes;


	if (v4encapsulated) {
		// Take care of the encapsulated IPv4 special case...
		const	guint8	v4prefix[] = {CONST_IPV6_IPV4SPACE};
		const	guint	offset = sizeof(v4prefix);
		if (chunkindex != 3) {
			DEBUGMSG5("%s.%d: Not IPv4 encapsulated as IPv6 format due to too few digits."
			,	__FUNCTION__, __LINE__);
			return NULL;
		}
		memcpy(addrbytes, v4prefix, sizeof(v4prefix));
		addrbytes[offset+0] =  (guint8)addrchunks[0];
		addrbytes[offset+1] =  (guint8)addrchunks[1];
		addrbytes[offset+2] =  (guint8)addrchunks[2];
		addrbytes[offset+3] =  (guint8)addrchunks[3];
	}else{
		// Otherwise we have a more normal IPv6 address
		memset(addrbytes, 0, DIMOF(addrbytes));
		// Make our set of chunks into an IPv6 address in binary
		for (j=0; j <= chunkindex; ++j) {
			// Is this where the :: goes?
			if (((gint)j) == coloncolonindex) {
				// Insert the right number of zeros
				memset(addrptr, 0, coloncolonlength*2);
				addrptr += 2*coloncolonlength;
			}
			// Copy the next bit of data
			addrptr[0] = (((addrchunks[j]) >> 8) & 0xff);
			addrptr[1] = addrchunks[j] & 0xff;
			addrptr += 2;
		}
		// Did the :: appear at the end of the address - weird but legal...
		if (coloncolonindex == (gint)chunkindex + 1) {
			DEBUGMSG5("%s.%d: Appending %d zeros to the end of the address"
			,	__FUNCTION__, __LINE__, coloncolonlength*2);
			memset(addrptr, 0, coloncolonlength*2);
			addrptr += 2*coloncolonlength;
		}
		DEBUGMSG5("%s.%d: addrptr == addrbytes+%ld",	__FUNCTION__, __LINE__
		,	(long)(addrptr-addrbytes));
		g_return_val_if_fail(addrptr == addrbytes+DIMOF(addrbytes), NULL);
	}
	retval = netaddr_ipv6_new(addrbytes, port);
	DUMP5(addrstr, &retval->baseclass, " Converted the former into the latter...(ignore the extra ':')");
	return retval;
}

/// Create a NetAddr from a 48-bit or 64-bit-format MAC address string
/// - either : or - are permitted as the delimter between bytes (octets)
NetAddr*
_netaddr_string_macaddr_new(const char *addrstr)
{
	guint8		hexvals[8];
	unsigned	hexindex = 0;

	const char *	cp;
	char *		nextcp;

	for (cp = addrstr; *cp; hexindex++, cp=nextcp) {
		long	hexvalue;
		if (hexindex >= DIMOF(hexvals)) {
			return NULL;
		}
		hexvalue = strtol(cp, &nextcp, 16);
		if (hexvalue < 0 || hexvalue > 255 || nextcp == cp) {
			return NULL;
		}
		hexvals[hexindex] = hexvalue;
		if (*nextcp == '-' || *nextcp == ':') {
			nextcp++;
			// Disallow a final : or -
			if (*nextcp == '\0') {
				return NULL;
			}
		}
	}
	if (hexindex == 6) {
		return netaddr_mac48_new(hexvals);
	}
	if (hexindex == 8) {
		return netaddr_mac64_new(hexvals);
	}
	return NULL;
}

/// Create a NetAddr from an ipv4, ipv6 or MAC address string 
NetAddr*
netaddr_string_new(const char* addrstr)
{
	NetAddr*	retval = NULL;
	char		addr0 = addrstr[0];

	if (addr0 == '[' || addr0 == ':') {
		return _netaddr_string_ipv6_new(addrstr);
	}

	if (isdigit(addr0)) {
		retval = _netaddr_string_ipv4_new(addrstr);
		if (!retval) {
			retval = _netaddr_string_ipv6_new(addrstr);
			if (!retval) {
				retval = _netaddr_string_macaddr_new(addrstr);
			}
		}
	}else if (isxdigit(addr0)) {
		retval = _netaddr_string_ipv6_new(addrstr);
		if (!retval) {
			retval = _netaddr_string_macaddr_new(addrstr);
		}
	}
	return retval;
}

/// Create a NetAddr from a DNS name or an ipv4 or ipv6 constant string
NetAddr*
netaddr_dns_new(const char * sysname_or_addr)	//< System name/address
{
#ifdef HAVE_GETADDRINFO
	NetAddr*	ret = NULL;
	const char*	digits = ":[0123456789ABCDEFabcdef";
	const char *	colonpos;
	char*		sysname;
	int		rc;
	const char*	service = NULL;
	struct addrinfo	hints;
	struct addrinfo*sysinfo;

	// See if it _could_ be a numeric address...
	if (strchr(digits, sysname_or_addr[0]) != NULL) {
		ret = netaddr_string_new(sysname_or_addr);
		if (NULL != ret) {
			return ret;
		}
		// Who knows, maybe they gave a symbolic port and a constant IP address...
		// In any case, give it another shot...
	}

	// See if they specified a port...
	colonpos = strchr(sysname_or_addr, ':');

	if (NULL == colonpos) {
		service = "0";
		sysname = g_strdup(sysname_or_addr);
	}else{
		service = colonpos + 1;
		if (strlen(service) < 1 || atol(service) < 0 || atol(service) > 65535) {
			return NULL;
		}
		sysname = g_strndup(sysname_or_addr, colonpos-sysname_or_addr);
	}
	memset(&hints, 0, sizeof(hints));
	hints.ai_family = AF_UNSPEC;
	hints.ai_socktype = SOCK_DGRAM;
	rc =  getaddrinfo(sysname, service, &hints, &sysinfo);
	if (0 != rc) {
		DEBUGMSG("%s.%d: Could not resolve %s - reason: %s"
		,	__FUNCTION__, __LINE__, sysname, gai_strerror(rc));
	}else{
		ret = netaddr_sockaddr_new((struct sockaddr_in6*)sysinfo[0].ai_addr
		,	sysinfo[0].ai_addrlen);
		freeaddrinfo(sysinfo);
	}
	g_free(sysname); sysname = NULL;
#else
#	error "Must have a replacement for getaddrinfo(3)"
#endif
	return ret;
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
	return netaddr_macaddr_new(macbuf, 8);
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
netaddr_ipv6_new(gconstpointer ipbuf,	///<[in] Pointer to 16-byte IPv6 address
		 guint16	port)	///<[in] Port (or zero for non-port-specific IP address)
{
	return	netaddr_new(0, port, ADDR_FAMILY_IPV6, ipbuf, 16);
}




/// Create new NetAddr from a <b>struct sockaddr</b>
NetAddr*
netaddr_sockaddr_new(const struct sockaddr_in6 *sa_in6,	///<[in] struct sockaddr to construct address from
			  socklen_t length)	///<[in] number of bytes in 'sa'
{
	const struct sockaddr_in*	sa_in = (const struct sockaddr_in*)sa_in6;

	(void)length;
	switch(sa_in->sin_family) {
		case AF_INET:
			return netaddr_new(0, ntohs(sa_in->sin_port), 
					   ADDR_FAMILY_IPV4, &sa_in->sin_addr, 4);
			break;

		case AF_INET6:
			/// @todo convert IPv4 encapsulated addresses to real IPv4 addresses??
			return netaddr_new(0, ntohs(sa_in6->sin6_port), 
					   ADDR_FAMILY_IPV6, &sa_in6->sin6_addr, 16);
			break;
	}
	g_return_val_if_reached(NULL);
}

FSTATIC struct sockaddr_in6
_netaddr_ipv6sockaddr(const NetAddr* self)	//<[in] NetAddr object to convert to IPv6 sockaddr
{
	struct sockaddr_in6	saddr;

	memset(&saddr, 0x00, sizeof(saddr));

	switch (self->_addrtype) {
		case ADDR_FAMILY_IPV4:
			g_return_val_if_fail(4 == self->_addrlen, saddr);
			saddr.sin6_family = AF_INET6;
			saddr.sin6_port = htons(self->_addrport);
			/// @todo May need to account for the "any" IPv4 address here and
			/// translate it into the "any" IPv6 address...
			// (this works because saddr is initialized to zero)
			saddr.sin6_addr.s6_addr[10] =  0xff;
			saddr.sin6_addr.s6_addr[11] =  0xff;
			memcpy(saddr.sin6_addr.s6_addr+12, self->_addrbody, self->_addrlen);
			DEBUGMSG3("%s:%s: sin6_family 0x%x, sin6_port %d"
			,	__FILE__, __FUNCTION__
			,	saddr.sin6_family, ntohs(saddr.sin6_port));
			DEBUGMSG3("%s:%s:s6_addr(v4): %02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x"
			,	__FILE__, __FUNCTION__
			,	saddr.sin6_addr.s6_addr[0],saddr.sin6_addr.s6_addr[1]
			,	saddr.sin6_addr.s6_addr[2],saddr.sin6_addr.s6_addr[3]
			,	saddr.sin6_addr.s6_addr[4],saddr.sin6_addr.s6_addr[5]
			,	saddr.sin6_addr.s6_addr[6],saddr.sin6_addr.s6_addr[7]
			,	saddr.sin6_addr.s6_addr[8],saddr.sin6_addr.s6_addr[8]
			,	saddr.sin6_addr.s6_addr[10],saddr.sin6_addr.s6_addr[11]
			,	saddr.sin6_addr.s6_addr[12],saddr.sin6_addr.s6_addr[13]
			,	saddr.sin6_addr.s6_addr[14],saddr.sin6_addr.s6_addr[15]);
			
			break;

		case ADDR_FAMILY_IPV6:
			g_return_val_if_fail(16 == self->_addrlen, saddr);
			saddr.sin6_family = AF_INET6;
			saddr.sin6_port = htons(self->_addrport);
			memcpy(&saddr.sin6_addr, self->_addrbody, self->_addrlen);
			break;

		default:
			g_return_val_if_reached(saddr);
	}
	return saddr;
}

FSTATIC struct sockaddr_in
_netaddr_ipv4sockaddr(const NetAddr* self)	//<[in] NetAddr object to convert to IPv4 sockaddr
{
	struct sockaddr_in	saddr;

	memset(&saddr, 0x00, sizeof(saddr));

	switch (self->_addrtype) {
		case ADDR_FAMILY_IPV4:
			g_return_val_if_fail(4 == self->_addrlen, saddr);
			saddr.sin_family = AF_INET;
			saddr.sin_port = htons(self->_addrport);
			memcpy(&saddr.sin_addr, self->_addrbody, 4);
			break;

		default:
			g_return_val_if_reached(saddr);
	}
	return saddr;
}
///@}
