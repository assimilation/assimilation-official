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

#include <stdlib.h>
#include <memory.h>
#include <projectcommon.h>
#include <netaddr.h>
#include <address_family_numbers.h>
#ifdef _MSC_VER
#	include <ws2tcpip.h>
#endif

FSTATIC struct sockaddr_in6 _netaddr_ipv6sockaddr(const NetAddr* self);
FSTATIC struct sockaddr_in _netaddr_ipv4sockaddr(const NetAddr* self);
FSTATIC void _netaddr_finalize(AssimObj* self);
FSTATIC guint16 _netaddr_port(const NetAddr* self);
FSTATIC void _netaddr_setport(NetAddr* self, guint16);
FSTATIC guint16 _netaddr_addrtype(const NetAddr* self);
FSTATIC gboolean _netaddr_ismcast(const NetAddr* self);
FSTATIC gconstpointer _netaddr_addrinnetorder(gsize *addrlen);
FSTATIC gboolean _netaddr_equal(const NetAddr*, const NetAddr*);
FSTATIC gchar * _netaddr_toStringflex(const NetAddr*, gboolean canonformat);
FSTATIC gchar * _netaddr_toString(gconstpointer);
FSTATIC gchar * _netaddr_canonStr(const NetAddr*);
FSTATIC gchar * _netaddr_toString_ipv6_ipv4(const NetAddr* self, gboolean ipv4format);
FSTATIC NetAddr* _netaddr_string_ipv4_new(const char* addrstr);

DEBUGDECLARATIONS

/// @defgroup NetAddr NetAddr class
///@{
/// @ingroup C_Classes
/// This is our basic NetAddr object.
/// It represents network addresses of any of a wide variety of well-known @ref AddressFamilyNumbers "well-known types".
/// It is a class from which we might eventually make subclasses,
/// and is managed by our @ref ProjectClass system.

///@todo Figure out the byte order issues so that we store them in a consistent
///	 format - ipv4, ipv6 and MAC addresses...

/// Convert this ipv6-encapsulated ipv4 NetAddr to a string
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
				       ((const gchar*)self->_addrbody)[12],
				       ((const gchar*)self->_addrbody)[13],
				       ((const gchar*)self->_addrbody)[14],
				       ((const gchar*)self->_addrbody)[15],
				       suffix,
				       self->_addrport);
	}
	return g_strdup_printf("%s%d.%d.%d.%d",
			       prefix,
			       ((const gchar*)self->_addrbody)[12],
			       ((const gchar*)self->_addrbody)[13],
			       ((const gchar*)self->_addrbody)[14],
			       ((const gchar*)self->_addrbody)[15]);
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
					      ((const gchar*)self->_addrbody)[0],
					      ((const gchar*)self->_addrbody)[1],
					      ((const gchar*)self->_addrbody)[2],
					      ((const gchar*)self->_addrbody)[3],
					      self->_addrport);
		}
		return g_strdup_printf("%d.%d.%d.%d",
				      ((const gchar*)self->_addrbody)[0],
				      ((const gchar*)self->_addrbody)[1],
				      ((const gchar*)self->_addrbody)[2],
				      ((const gchar*)self->_addrbody)[3]);
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
					       ((const gchar*)self->_addrbody)[nbyte]);
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
	/// Perhaps we ought to eventually maybe compare for MAC addresses and ipv6 equivalents ;-)
	const guchar ipv6v4   [] = {CONST_IPV6_IPV4SPACE};
	const guchar ipv6loop [] = CONST_IPV6_LOOPBACK;
	const guchar ipv4loop [] = CONST_IPV4_LOOPBACK;

	DEBUGMSG5("Place 1: self:%p, other:%p", self, other);

	if (self->_addrtype == ADDR_FAMILY_IPV6 && other->_addrtype == ADDR_FAMILY_IPV4) {
		const guchar *selfabody = self->_addrbody;
		// Check for equivalent ipv4 and ipv6 addresses
		if (memcmp(selfabody, ipv6v4, sizeof(ipv6v4)) == 0
	        &&  memcmp(selfabody+12, other->_addrbody, 4) == 0) {
			return TRUE;
		}
		// Check for the equivalent *any* addresses between ipv4 and ipv6
		if (memcmp(self->_addrbody,  ipv6loop, sizeof(ipv6loop)) == 0
		&&  memcmp(other->_addrbody, ipv4loop, sizeof(ipv4loop)) == 0) {
			return TRUE;
		}
		return FALSE;
	}else if (self->_addrtype == ADDR_FAMILY_IPV4 && other->_addrtype == ADDR_FAMILY_IPV6) {
		// Switch the operands and try again...
		return _netaddr_equal(other, self);
	}
	DEBUGMSG5("Place 2: self:%p, other:%p", self, other);
	DEBUGMSG5("Place 3: self->addrtype:%d, other->addrtype:%d", self->_addrtype, other->_addrtype);
	DEBUGMSG5("Place 4: self->addrlen:%d, other->addrlen:%d", self->_addrlen, other->_addrlen);
	if (self->_addrtype != other->_addrtype || self->_addrlen  != other->_addrlen) {
		return FALSE;
	}
	DEBUGMSG5("Place 5: self:%p, other:%p", self, other);
	DEBUGMSG5("Place 6: self->_addrbody:%p, other->_addrbody:%p", self->_addrbody, other->_addrbody);
	return (memcmp(self->_addrbody, other->_addrbody, self->_addrlen) == 0);
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
	switch (self->_addrtype) {
		case ADDR_FAMILY_IPV4: {
			guint8 byte0 = ((guint8*)self->_addrbody)[0];
			return (byte0 >= 224 && byte0 <= 239);
		}
		break;;
	}
	return	FALSE;
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
	self->equal = _netaddr_equal;

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
	guint		whichdot = 0;
	int		byte;
	NetAddr*	ret;
	int		port = 0;
	
	guint	j;
	int	debug = FALSE;
	int	lastpos = 0;

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
		if (port == 0 || port > 65535) {
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

NetAddr*
netaddr_string_new(const char* addrstr)
{
	/// FIXME: Need to write _netaddr_string_ipv6_new (with provisions for port numbers!)
	return _netaddr_string_ipv4_new(addrstr);
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
_netaddr_ipv6sockaddr(const NetAddr* self)	//<[in] NetAddr object to convert to ipv6 sockaddr
{
	struct sockaddr_in6	saddr;

	memset(&saddr, 0x00, sizeof(saddr));
	if (self->_addrport == 0) {
		char *	addrstr = self->baseclass.toString(self);
		g_warning("%s: IP address %s has port == 0", __FUNCTION__, addrstr);
		g_free(addrstr);	addrstr = NULL;
		return saddr;
	}

	switch (self->_addrtype) {
		case ADDR_FAMILY_IPV4:
			g_return_val_if_fail(4 == self->_addrlen, saddr);
			saddr.sin6_family = AF_INET6;
			saddr.sin6_port = htons(self->_addrport);
			/// @todo May need to account for the "any" ipv4 address here and
			/// translate it into the "any" ipv6 address...
			// (this works because saddr is initialized to zero)
			saddr.sin6_addr.s6_addr[10] =  0xff;
			saddr.sin6_addr.s6_addr[11] =  0xff;
			memcpy(saddr.sin6_addr.s6_addr+12, self->_addrbody, self->_addrlen);
			DEBUGMSG2("%s:%s: sin6_family 0x%x, sin6_port %d"
			,	__FILE__, __FUNCTION__
			,	saddr.sin6_family, ntohs(saddr.sin6_port));
			DEBUGMSG2("%s:%s:s6_addr(v4): %02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x"
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
_netaddr_ipv4sockaddr(const NetAddr* self)	//<[in] NetAddr object to convert to ipv4 sockaddr
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
