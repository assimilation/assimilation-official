/**
 * @file
 * @brief Implements network I/O class (@ref NetIO)
 * @details This file contains the code to support the @ref NetIO objects for doing network I/O.
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

#include <projectcommon.h>
#include <errno.h>
#include <memory.h>
#ifdef	HAVE_UNISTD_H
#	include <unistd.h>
#endif
#include <stdlib.h>
#include <fcntl.h>
#include <sys/types.h>
#ifdef _MSC_VER
#	include <winsock2.h>
#	include <ws2tcpip.h>
#include <ws2ipdef.h>
#define ip_mreqn ip_mreq
#define imr_address imr_multiaddr
#define s6_addr16 u.Word
#define close closesocket
#else
#	include <sys/socket.h>
#	include <netinet/in.h>
#endif
#include <glib.h>
#include <packetdecoder.h>
#include <address_family_numbers.h>
#include <proj_classes.h>
#include <netio.h>
#include <frameset.h>
#include <frametypes.h>
#include <misc.h>
FSTATIC gint _netio_getfd(const NetIO* self);
FSTATIC void _netio_setblockio(const NetIO* self, gboolean blocking);
FSTATIC gboolean _netio_bindaddr(NetIO* self, const NetAddr* src, gboolean silent);
FSTATIC gboolean _netio_input_queued(const NetIO* self);
FSTATIC NetAddr* _netio_boundaddr(const NetIO* self);
FSTATIC void _netio_sendframesets(NetIO* self, const NetAddr* destaddr, GSList* framesets);
FSTATIC void _netio_sendaframeset(NetIO* self, const NetAddr* destaddr, FrameSet* frameset);
FSTATIC void _netio_finalize(AssimObj* self);
FSTATIC void _netio_sendapacket(NetIO* self, gconstpointer packet, gconstpointer pktend, const NetAddr* destaddr);
FSTATIC gpointer _netio_recvapacket(NetIO*, gpointer*, struct sockaddr_in6*, socklen_t*addrlen);
FSTATIC gsize _netio_getmaxpktsize(const NetIO* self);
FSTATIC gsize _netio_setmaxpktsize(NetIO* self, gsize maxpktsize);
FSTATIC GSList* _netio_recvframesets(NetIO*self , NetAddr** src);
FSTATIC SignFrame* _netio_signframe (NetIO *self);
FSTATIC CompressFrame* _netio_compressframe (NetIO *self);
FSTATIC gboolean _netio_mcastjoin(NetIO* self, const NetAddr* src, const NetAddr*localaddr);
FSTATIC gboolean _netio_setmcast_ttl(NetIO* self, guint8 ttl);
FSTATIC void _netio_enablepktloss(NetIO* self, gboolean enable);
FSTATIC void _netio_setpktloss(NetIO* self, double rcvloss, double xmitloss);
FSTATIC gboolean _netio_sendareliablefs(NetIO*self, NetAddr*dest, guint16 queueid, FrameSet* frameset);
FSTATIC gboolean _netio_sendreliablefs(NetIO*self, NetAddr* dest, guint16 queueid, GSList* fslist);
FSTATIC gboolean _netio_ackmessage(NetIO* self, NetAddr* dest, FrameSet* frameset);
FSTATIC gboolean _netio_supportsreliable(NetIO* self); 
FSTATIC void  _netio_closeconn(NetIO* self, guint16 qid, const NetAddr* destaddr);
FSTATIC void _netio_netaddr_destroy(gpointer addrptr);
FSTATIC void _netio_addalias(NetIO* self, NetAddr * fromaddr, NetAddr* toaddr);

DEBUGDECLARATIONS

/// @defgroup NetIO NetIO class
///@{
///@ingroup C_Classes
/// (Abstract) NetIO objects are able to perform network writes and reads.
/// It is a class from which we <i>must</i> make subclasses,
/// and is managed by our @ref ProjectClass system.

/// Member function to return the file descriptor underlying this NetIO object
FSTATIC gint
_netio_getfd(const NetIO* self)	///< [in] The object whose file descriptor is being returned
{
	g_return_val_if_fail(NULL != self, -1);
	g_return_val_if_fail(NULL != self->giosock, -1);
	return g_io_channel_unix_get_fd(self->giosock);
}

/// Member function to set blocking/non-blocking mode on our sockets
FSTATIC void
_netio_setblockio(const NetIO* self, gboolean blocking)
{
	int	chanflags = g_io_channel_get_flags(self->giosock);
#ifndef WIN32
	int fcntlflags = fcntl (self->getfd(self), F_GETFL, 0);
	if (blocking) {
		fcntlflags |= O_NONBLOCK;
	}else{
		fcntlflags &= ~O_NONBLOCK;
	}
	if (fcntl(self->getfd(self), F_SETFL, fcntlflags) < 0) {
		g_critical("%s.%d: fcntl(F_SETFL, 0x%x) failed: %s", __FUNCTION__, __LINE__
		,	fcntlflags, g_strerror(errno));
		return;
	}
#endif
	if (blocking) {
		chanflags |= G_IO_FLAG_NONBLOCK;
	}else{
		chanflags &= ~G_IO_FLAG_NONBLOCK;
	}
	g_io_channel_set_flags(self->giosock, chanflags, NULL);
}


/// Set up a NetIO object to listen to (join) a particular multicast group.
FSTATIC gboolean
_netio_mcastjoin(NetIO* self, const NetAddr* src, const NetAddr*localaddr)
{
	int			rc = -1;
	NetAddr*		genlocal = NULL;


	errno = 0;

	if (!src->ismcast(src)) {
		g_warning("%s: Cannot join multicast group with non-multicast address"
		,	__FUNCTION__);
		goto getout;
	}
	if (localaddr != NULL && src->_addrtype != localaddr->_addrtype) {
		g_warning("%s: Cannot join multicast group with differing address types"
		,	__FUNCTION__);
		goto getout;
	}

	if (ADDR_FAMILY_IPV6 == src->_addrtype ) {
		struct ipv6_mreq	multicast_request;
		struct sockaddr_in6	saddr;
		saddr = src->ipv6sockaddr(src);
		memset(&multicast_request, 0, sizeof(multicast_request));
		memcpy(&multicast_request.ipv6mr_multiaddr, &saddr
		,	sizeof(multicast_request.ipv6mr_multiaddr));

		if (localaddr == NULL) {
			genlocal = self->boundaddr(self);
			localaddr = genlocal;
			if (localaddr->addrtype(localaddr) != ADDR_FAMILY_IPV6) {
				localaddr = NULL;
			}
		}

		if (localaddr != NULL) {
			struct sockaddr_in6	laddr;
			laddr = localaddr->ipv6sockaddr(localaddr);
			memcpy(&multicast_request.ipv6mr_interface, &laddr.sin6_addr
			,	sizeof(multicast_request.ipv6mr_interface));
		}
		if (localaddr && localaddr->addrtype(localaddr) != ADDR_FAMILY_IPV6) {
			g_warning("%s: Cannot join v6 multicast group - local address not IPv6"
			,	__FUNCTION__);
			goto getout;
		}

		rc = setsockopt(self->getfd(self), IPPROTO_IPV6, IPV6_JOIN_GROUP
		,	(gpointer)&multicast_request, sizeof(multicast_request));
		if (rc != 0) {
			g_warning("%s: Cannot join v6 multicast group [%s (errno:%d)]"
			,	__FUNCTION__, g_strerror(errno), errno);
		}
	}else if (ADDR_FAMILY_IPV4 == src->_addrtype) {
		struct ip_mreqn	multicast_request;
		struct sockaddr_in	saddr;
		memset(&multicast_request, 0, sizeof(multicast_request));
		saddr = src->ipv4sockaddr(src);
		memcpy(&multicast_request.imr_multiaddr, &saddr.sin_addr
		,	sizeof(multicast_request.imr_multiaddr));

		if (localaddr == NULL) {
			genlocal = self->boundaddr(self);
			localaddr = genlocal;
			if (localaddr->addrtype(localaddr) != ADDR_FAMILY_IPV4) {
				localaddr = NULL;
			}
		}
		if (localaddr && localaddr->addrtype(localaddr) != ADDR_FAMILY_IPV4) {
			g_warning("%s: Cannot join v4 multicast group - local address not IPv4"
			,	__FUNCTION__);
			goto getout;
		}

		if (localaddr != NULL) {
			struct sockaddr_in	laddr;
			laddr = localaddr->ipv4sockaddr(localaddr);
			memcpy(&multicast_request.imr_address, &laddr.sin_addr
			,	sizeof(multicast_request.imr_address));
		}

		rc = setsockopt(self->getfd(self), IPPROTO_IP, IP_ADD_MEMBERSHIP
		,	(gpointer)&multicast_request, sizeof(multicast_request));
		if (rc != 0) {
			g_warning("%s: Cannot join v4 multicast group [%s (errno:%d)]"
			,	__FUNCTION__, g_strerror(errno), errno);
		}else{
			// Default to the largest organizational scope defined...
			self->setmcast_ttl(self, 31);
		}
	}
getout:
	if (genlocal) {
		UNREF(genlocal);
		genlocal = NULL;
	}

	return (rc == 0);
}

/// Set up the multicast TTL for this NetIO object
gboolean
_netio_setmcast_ttl(NetIO*	self,		///<[in/out] netIO object to set the TTL of
		     guint8	ttlin)		///<[in] multicast TTL
///<  TTL     Scope
///<    0    Restricted to the same host. Won't be output by any interface.
///<    1    Restricted to the same subnet. Won't be forwarded by a router.
///<  <32    Restricted to the same site, organization or department.
///<  <64    Restricted to the same region.
///< <128    Restricted to the same continent.
///< <255    Unrestricted in scope. Global.
{
	int	ttl = ttlin;
        return setsockopt(self->getfd(self), IPPROTO_IP, IP_MULTICAST_TTL, (char *)&ttl, sizeof(ttl) == 0);
}

/// Member function that returns TRUE if input is ready to be read
FSTATIC gboolean
_netio_input_queued(const NetIO* self)		///<[in] The NetIO object being queried
{
	(void)self;
	return FALSE;	// By default we don't have any input queues
}

/// Member function to bind this NewIO object to a NetAddr address
FSTATIC gboolean
_netio_bindaddr(NetIO* self,		///<[in/out] The object being bound
		const NetAddr* src,	///<[in] The address to bind it to
		gboolean silent)	///<[in] TRUE if no message on error
{
	gint			sockfd;
	struct sockaddr_in6	saddr;
	int			rc;
	g_return_val_if_fail(NULL != self, FALSE);
	g_return_val_if_fail(NULL != self->giosock, FALSE);
	sockfd = self->getfd(self);

	if (src->ismcast(src)) {
		g_warning("%s: Attempt to bind to multicast address.", __FUNCTION__);
		return FALSE;
	}
	memset(&saddr, 0x00, sizeof(saddr));
	saddr.sin6_family = AF_INET6;
	saddr.sin6_port = src->port(src);
	g_return_val_if_fail(src->addrtype(src) == ADDR_FAMILY_IPV4 || src->addrtype(src) == ADDR_FAMILY_IPV6, FALSE);

	saddr = src->ipv6sockaddr(src);
	rc = bind(sockfd, (struct sockaddr*)&saddr, sizeof(saddr));
	if (rc != 0 && !silent) {
		g_warning("%s: Cannot bind to address [%s (errno:%d)]"
		,	__FUNCTION__, g_strerror(errno), errno);
	}
	return rc == 0;
}
/// Member function to return the bound NetAddr (with port) of this NetIO object
FSTATIC NetAddr*
_netio_boundaddr(const NetIO* self)		///<[in] The object being examined
{
	gint			sockfd = self->getfd(self);
	struct sockaddr_in6	saddr;
	socklen_t		saddrlen = sizeof(saddr);
	socklen_t		retsize = saddrlen;


	if (getsockname(sockfd, (struct sockaddr*)&saddr, &retsize) < 0) {
		g_warning("%s: Cannot retrieve bound address [%s]", __FUNCTION__, g_strerror(errno));
		return NULL;
	}
	if (retsize != saddrlen) {
		g_warning("%s: Truncated getsockname() return [%d/%d bytes]", __FUNCTION__, retsize, saddrlen);
		return NULL;
	}
	return netaddr_sockaddr_new(&saddr, saddrlen);

}

/// Member function to free this NetIO object.
FSTATIC void
_netio_finalize(AssimObj* aself)	///<[in/out] The object being freed
{
	NetIO*	self = CASTTOCLASS(NetIO, aself);
	if (self->giosock) {
		g_io_channel_shutdown(self->giosock, TRUE, NULL);
		g_io_channel_unref(self->giosock);
		self->giosock = NULL;
	}
	if (self->_signframe) {
		UNREF2(self->_signframe);
	}
	if (self->_compressframe) {
		UNREF2(self->_compressframe);
	}
	if (self->_decoder) {
		UNREF(self->_decoder);
	}

	// Free up our hash table of aliases
	if (self->aliases) {
		g_hash_table_destroy(self->aliases);	// It will free the NetAddrs contained therein
		self->aliases = NULL;
	}
	_assimobj_finalize(aself); self = NULL; aself = NULL;
}

/// Get the max packet size for this NetIO transport
FSTATIC gsize
_netio_getmaxpktsize(const NetIO* self)	///<[in] The object whose max pkt size is being returned
{
	return self->_maxpktsize;
}

/// Set the max packet size for this NetIO transport
FSTATIC gsize
_netio_setmaxpktsize(NetIO* self,	///<[in/out] The object whose max packet size to set
		    gsize maxpktsize)	///<[in] Size to set the max packet size to.
{
	self->_maxpktsize = maxpktsize;
	return self->getmaxpktsize(self);
}
FSTATIC CompressFrame*
_netio_compressframe (NetIO *self)
{
	return self->_compressframe;
}

FSTATIC SignFrame*
_netio_signframe (NetIO *self)
{
	return self->_signframe;
}

/// NetIO constructor.
NetIO*
netio_new(gsize objsize			///<[in] The size of the object to construct (or zero)
	, ConfigContext* config		///<[in] Configuration Information
	, PacketDecoder*decoder)	///<[in] Packet decoder
{
	NetIO* ret;
	Frame*	f;

	BINDDEBUG(NetIO);
	if (objsize < sizeof(NetIO)) {
		objsize = sizeof(NetIO);
	}
	ret = NEWSUBCLASS(NetIO, assimobj_new(objsize));
	ret->baseclass._finalize = _netio_finalize;
	ret->getfd = _netio_getfd;
	ret->setblockio = _netio_setblockio;
	ret->input_queued = _netio_input_queued;
	ret->bindaddr = _netio_bindaddr;
	ret->sendframesets = _netio_sendframesets;
	ret->sendaframeset = _netio_sendaframeset;
	ret->getmaxpktsize = _netio_getmaxpktsize;
	ret->setmaxpktsize = _netio_setmaxpktsize;
	ret->recvframesets = _netio_recvframesets;
	ret->boundaddr = _netio_boundaddr;
	ret->mcastjoin = _netio_mcastjoin;
	ret->setmcast_ttl = _netio_setmcast_ttl;
	ret->signframe = _netio_signframe;
	ret->compressframe = _netio_compressframe;
	ret->setpktloss = _netio_setpktloss;
	ret->enablepktloss = _netio_enablepktloss;
	ret->sendareliablefs = _netio_sendareliablefs;
	ret->sendreliablefs = _netio_sendreliablefs;
	ret->ackmessage = _netio_ackmessage;
	ret->supportsreliable  = _netio_supportsreliable;	// It just returns FALSE
	ret->outputpending  = _netio_supportsreliable;		// It just returns FALSE
	ret->addalias = _netio_addalias;
	ret->closeconn = _netio_closeconn;
	ret->_maxpktsize = 65300;
	ret->_configinfo = config;
	ret->_decoder = decoder;
	REF(decoder);
	f =  config->getframe(config, CONFIGNAME_OUTSIG);
	g_return_val_if_fail(f != NULL, NULL);
	REF(f);
	ret->_signframe = CASTTOCLASS(SignFrame, f);
	ret->_compressframe = CASTTOCLASS(CompressFrame,config->getframe(config, CONFIGNAME_COMPRESS));
	if (ret->_compressframe) {
		REF2(ret->_compressframe);
	}
	ret->aliases = g_hash_table_new_full(netaddr_g_hash_hash, netaddr_g_hash_equal
        ,		_netio_netaddr_destroy, _netio_netaddr_destroy);  // Keys and data are same type...
	memset(&ret->stats, 0, sizeof(ret->stats));
	return ret;
}

/// NetIO internal function to send a packet (datagram)
FSTATIC void
_netio_sendapacket(NetIO* self,			///<[in] Object doing the sending
		   gconstpointer packet,	///<[in] Packet to send
		   gconstpointer pktend,	///<[in] one byte past end of packet
		   const NetAddr* destaddr)	///<[in] where to send it
{
	struct sockaddr_in6 v6addr = destaddr->ipv6sockaddr(destaddr);
	gssize length = (const guint8*)pktend - (const guint8*)packet;
	gssize rc;
	guint flags = 0x00;
	g_return_if_fail(length > 0);

	DUMP3(__FUNCTION__, &destaddr->baseclass, " is destination address");
	DUMP3(__FUNCTION__, &self->baseclass, " is NetIO object");
	if (self->_shouldlosepkts) {
		if (g_random_double() < self->_xmitloss) {
			g_message("%s.%d: Threw away %"G_GSSIZE_FORMAT" byte output packet"
			,	__FUNCTION__, __LINE__, length);
			return;
		}
	}

	rc = sendto(self->getfd(self),  packet, (size_t)length, flags, (const struct sockaddr*)&v6addr, sizeof(v6addr));
	DEBUGMSG3("%s.%d: sendto(%d, %ld, [%04x:%04x:%04x:%04x:%04x:%04x:%04x:%04x], port=%d) returned %ld"
	,	__FUNCTION__, __LINE__, self->getfd(self), (long)length
	,	ntohs(v6addr.sin6_addr.s6_addr16[0])
	,	ntohs(v6addr.sin6_addr.s6_addr16[1])
	,	ntohs(v6addr.sin6_addr.s6_addr16[2])
	,	ntohs(v6addr.sin6_addr.s6_addr16[3])
	,	ntohs(v6addr.sin6_addr.s6_addr16[4])
	,	ntohs(v6addr.sin6_addr.s6_addr16[5])
	,	ntohs(v6addr.sin6_addr.s6_addr16[6])
	,	ntohs(v6addr.sin6_addr.s6_addr16[7])
	,	ntohs(v6addr.sin6_port)
	,	(long)rc);
	self->stats.sendcalls ++;
	self->stats.pktswritten ++;
	if (rc == -1 && errno == EPERM) {
		g_info("%s.%d: Got a weird sendto EPERM error for %"G_GSSIZE_FORMAT" byte packet."
		,	__FUNCTION__, __LINE__, (gssize)length);
		g_info("%s.%d: This only seems to happen under Docker..."
		,	__FUNCTION__, __LINE__);
		return;
	}
        if (rc != length) {
		char *	tostring = destaddr->baseclass.toString(destaddr);
		g_warning(
		"%s: sendto returned %"G_GSSIZE_FORMAT " vs %"G_GSSIZE_FORMAT" with errno %s"
		,	__FUNCTION__, rc, (gssize)length, g_strerror(errno));
		g_warning("%s: destaddr:[%s] ", __FUNCTION__, tostring);
		g_free(tostring); tostring = NULL;
	}
	//g_return_if_fail(rc == length);
	g_warn_if_fail(rc == length);
}

/// NetIO member function to send a GSList of FrameSets.
/// @todo consider optimizing this code to send multiple FrameSets in a single datagram -
/// using sendmsg(2) assuming we start constructing GSLists with more than one FrameSet
/// in it on a regular basis.
FSTATIC void
_netio_sendframesets(NetIO* self,		///< [in/out] The NetIO object doing the sending
		     const NetAddr* destaddr,	///< [in] Where to send the FrameSets
		     GSList* framesets)		///< [in] The framesets being sent
{
	GSList*	curfsl;
	g_return_if_fail(self != NULL);
	g_return_if_fail(framesets != NULL);
	g_return_if_fail(destaddr != NULL);
	g_return_if_fail(self->_signframe != NULL);

	/// @todo change netio_sendframesets to use sendmsg(2) instead of sendto(2)...
	/// This loop would then be to set up a <b>struct iovec</b>,
	/// and would be followed by a sendmsg(2) call - eliminating sendapacket() above.
	for (curfsl=framesets; curfsl != NULL; curfsl=curfsl->next) {
		FrameSet* curfs		= CASTTOCLASS(FrameSet, curfsl->data);
		SignFrame* signframe	= self->signframe(self);
		CryptFrame*	cryptframe	= NULL;
		CompressFrame*	compressframe	= self->compressframe(self);
		if (compressframe) {
			REF2(compressframe);
		}
		cryptframe = cryptframe_new_by_destaddr(destaddr);
		DEBUGMSG3("%s.%d: cryptframe: %p", __FUNCTION__, __LINE__, cryptframe);
		frameset_construct_packet(curfs, signframe, cryptframe, compressframe);
		if (cryptframe) {
			DEBUGMSG3("%s.%d: Sending encrypted packet.", __FUNCTION__, __LINE__);
			UNREF2(cryptframe);
		}
		DUMP3(__FUNCTION__, &curfs->baseclass, "is the frameset being sent");
		_netio_sendapacket(self, curfs->packet, curfs->pktend, destaddr);
		self->stats.fswritten++;
	}
}
FSTATIC void
_netio_sendaframeset(NetIO* self,		///< [in/out] The NetIO object doing the sending
		     const NetAddr* destaddr,	///< [in] Where to send the FrameSets
		     FrameSet* frameset)	///< [in] The framesets being sent
{
	SignFrame* signframe		= self->signframe(self);
	CryptFrame*	cryptframe;
	CompressFrame*	compressframe	= self->compressframe(self);
	g_return_if_fail(self != NULL);
	g_return_if_fail(self->_signframe != NULL);
	g_return_if_fail(frameset != NULL);
	g_return_if_fail(destaddr != NULL);

	cryptframe = cryptframe_new_by_destaddr(destaddr);
	DEBUGMSG3("%s.%d: cryptframe: %p", __FUNCTION__, __LINE__, cryptframe);
	frameset_construct_packet(frameset, signframe, cryptframe, compressframe);
	DEBUGMSG3("%s.%d: packet constructed (marshalled)", __FUNCTION__, __LINE__);
	if (cryptframe) {
		DEBUGMSG3("%s.%d: Sending encrypted packet.", __FUNCTION__, __LINE__);
		UNREF2(cryptframe);
	}
	DEBUGMSG3("%s.%d: sending %ld byte packet", __FUNCTION__, __LINE__
	,	(long)(((guint8*)frameset->pktend-(guint8*)frameset->packet)));
	DUMP3(__FUNCTION__, &frameset->baseclass, "is the frameset being sent");
	_netio_sendapacket(self, frameset->packet, frameset->pktend, destaddr);
}

/// Internal function to receive a packet from our NetIO object
/// General method:
/// - use MSG_PEEK to get message length
/// - malloc the amount of memory indicated by MSG_PEEK
/// - receive message into malloced buffer
/// - check for errors
/// - return received message, length, etc.
#include <stdlib.h>
#include <memory.h>
FSTATIC gpointer
_netio_recvapacket(NetIO* self,			///<[in/out] Transport to receive packet from
		   gpointer* pktend,		///<[out] Pointer to one past end of packet
		   struct sockaddr_in6* srcaddr,///<[*out] Pointer to source address as sockaddr
		   socklen_t* addrlen)		///<[out] length of address in 'srcaddr'
{
	char		dummy[8]; // Make GCC stack protection happy...
#ifndef __FUNCTION__
#	define __FUNCTION__ "_netio_recvapacket"
#endif
	gssize		msglen;
	gssize		msglen2;
	guint8*		msgbuf;
	const guint8 v4any[16] = CONST_IPV6_IPV4START;

	// First we peek and see how long the message is...
	*addrlen = sizeof(*srcaddr);
	memset(srcaddr, 0, sizeof(*srcaddr));
	msglen = recvfrom(self->getfd(self), dummy, 1, MSG_DONTWAIT|MSG_PEEK|MSG_TRUNC,
		          (struct sockaddr*)srcaddr, addrlen);
	self->stats.recvcalls ++;
	if (msglen < 0) {
		if (errno != EAGAIN) {
			g_warning("recvfrom(%d, ... MSG_PEEK) failed: %s (in %s:%s:%d)",
				self->getfd(self), g_strerror(errno), __FILE__, __FUNCTION__, __LINE__);
		}
		return NULL;
	}
	if (msglen == 0) {
		g_warning("recvfrom(%d, ... MSG_PEEK) returned zero: %s (in %s:%s:%d)"
		,      self->getfd(self), g_strerror(errno), __FILE__, __FUNCTION__, __LINE__);
		return NULL;
	}

	// Allocate the right amount of memory
	msgbuf = MALLOC(msglen);

	// Receive the message
	*addrlen = sizeof(*srcaddr);
	msglen2 = recvfrom(self->getfd(self), msgbuf, msglen, MSG_DONTWAIT|MSG_TRUNC,
			   (struct sockaddr *)srcaddr, addrlen);
	self->stats.recvcalls ++;

	// Was there an error?
	if (msglen2 < 0) {
		g_warning("recvfrom(%d, ... MSG_DONTWAIT) failed: %s (in %s:%s:%d)"
		,      self->getfd(self), g_strerror(errno), __FILE__, __FUNCTION__, __LINE__);
		FREE(msgbuf); msgbuf = NULL;
		return NULL;
	}
	// Does everything look good?
	if (msglen2 != msglen) {
		g_warning("recvfrom(%d, ... MSG_DONTWAIT) returned %"G_GSSIZE_FORMAT" instead of %"G_GSSIZE_FORMAT" (in %s:%s:%d)"
		,      self->getfd(self), msglen2, msglen, __FILE__, __FUNCTION__ ,	__LINE__);
		FREE(msgbuf); msgbuf = NULL;
		return NULL;
	}

#ifdef WIN32
#define __in6_u    u
#define __u6_addr8 Byte
#endif

	if (memcmp(srcaddr->sin6_addr.__in6_u.__u6_addr8, v4any,  sizeof(v4any)) == 0) {
		//const guint8 localhost[16] = CONST_IPV6_LOOPBACK;
		const guint8 localhost[16] = {CONST_IPV6_IPV4SPACE, 127, 0, 0, 1};
		// Both experience and RFC5735 say that this is basically "localhost"
		memcpy(srcaddr->sin6_addr.__in6_u.__u6_addr8, localhost, sizeof(localhost));
	}

	// Hah! Looks good!
	*pktend = (void*) (msgbuf + msglen);
	DEBUGMSG3("%s.%d: Received %zd byte message", __FUNCTION__, __LINE__, msglen);
	if (self->_shouldlosepkts) {
		if (g_random_double() < self->_rcvloss) {
			g_message("%s: Threw away %"G_GSSIZE_FORMAT" byte input packet"
			,	__FUNCTION__, msglen);
			FREE(msgbuf);
			msgbuf = NULL;
		}
	}
	self->stats.pktsread ++;
	return msgbuf;
}
/// Member function to receive a collection of FrameSets (GSList*) out of our NetIO object
FSTATIC GSList*
_netio_recvframesets(NetIO* self,	///<[in/out] NetIO routine to receive a set of FrameSets
					///< from a single address.
		     NetAddr** src)	///<[out] constructed source address for FrameSets
{
	GSList*			ret = NULL;
	gpointer		pkt;
	gpointer		pktend;
	socklen_t		addrlen;
	struct sockaddr_in6	srcaddr;

	*src = NULL;	// Make python happy in case we fail...
	pkt = _netio_recvapacket(self, &pktend, &srcaddr, &addrlen);

	if (NULL != pkt) {
		ret = self->_decoder->pktdata_to_framesetlist(self->_decoder, pkt, pktend);
		if (NULL != ret) {
			NetAddr*	aliasaddr;
			*src = netaddr_sockaddr_new(&srcaddr, addrlen);
			// Some addresses can confuse our clients -- let's check our alias table...
			if (NULL != (aliasaddr = g_hash_table_lookup(self->aliases, *src))) {
				// This is a good-enough way to make a copy.
				NetAddr* aliascopy = aliasaddr->toIPv6(aliasaddr);
				// Keep the incoming port - since that's always right...
				aliascopy->_addrport = (*src)->_addrport;
				UNREF(*src);
				*src = aliascopy;
			}
			if (DEBUG >= 3) {
				char * srcstr = (*src)->baseclass.toString(&(*src)->baseclass);
				DEBUGMSG("%s.%d: Received %d bytes making %d FrameSets from %s"
				,	__FUNCTION__, __LINE__, (int)((guint8*)pktend-(guint8*)pkt)
				,	g_slist_length(ret), srcstr);
				FREE(srcstr); srcstr = NULL;
			}
		}else{
			g_warning("%s.%d: Received a %lu byte packet from that didn't make any FrameSets"
			,	__FUNCTION__, __LINE__, (unsigned long)((guint8*)pktend-(guint8*)pkt));
			goto badret;
		}
		FREE(pkt);
	}
	if (ret && *src) {
		self->stats.fsreads += g_slist_length(ret);
	}
	return ret;
badret:
	g_slist_free_full(ret, assim_g_notify_unref);
	ret = NULL;
	return ret;
}
/// Set the desired level of packet loss - doesn't take effect from this call alone
FSTATIC void
_netio_setpktloss (NetIO* self, double rcvloss, double xmitloss)
{
	self->_rcvloss = rcvloss;
	self->_xmitloss = xmitloss;
}

/// Enable (or disable) packet loss as requested
FSTATIC void
_netio_enablepktloss (NetIO* self, gboolean enable)
{
	self->_shouldlosepkts = enable;
}



#ifdef IPV6_V6ONLY
#ifndef _MSC_VER
#	include <netdb.h>
#endif

/// Return TRUE if our OS supports dual ipv4/ipv6 sockets.  That is,
/// can a single socket receive and send both ipv4 and ipv6 packets?
/// If so, then return TRUE, otherwise return FALSE.
gboolean
netio_is_dual_ipv4v6_stack(void)
{
	static gboolean	computed_yet = FALSE;
	static gboolean	retval = FALSE;
	gboolean	optval;
	int		sockfd;
	socklen_t	optlen;
	struct protoent*proto;

	if (computed_yet) {
		return retval;
	}
	proto = getprotobyname("ipv6");
#ifdef HAVE_ENDPROTOENT
	endprotoent();
#endif
	g_return_val_if_fail(proto != NULL, FALSE);

	sockfd = socket(AF_INET6, SOCK_DGRAM, IPPROTO_UDP);
	g_return_val_if_fail(sockfd >= 0, FALSE);

	optlen = sizeof(retval);
	optval = TRUE;
	if (getsockopt(sockfd, proto->p_proto, IPV6_V6ONLY, (char *)&optval, &optlen) < 0) {
		g_warning("%s.%d: getsockopt failed:  %s", __FUNCTION__, __LINE__
		,	g_strerror(errno));
		close(sockfd);
		return FALSE;
	}
	if (optlen != sizeof(retval)) {
		// Should never happen...
		g_warning("%s.%d: getsockopt returned incorrect optlen: %d vs %zd"
		,	__FUNCTION__, __LINE__, optlen, sizeof(retval));
		close(sockfd);
		return FALSE;
	}
#ifdef WIN32
	// See http://msdn.microsoft.com/en-us/library/windows/desktop/bb513665%28v=vs.85%29.aspx
	// This might be OK for other OSes too...
	if (optval) {
		optval = FALSE;
		if (setsockopt(sockfd, proto->p_proto, IPV6_V6ONLY, (char *)&optval, optlen) < 0) {
			/// @todo this isn't perfect yet - see Microsoft note for ipv6-only stacks
			///	(presuming someone would disable ipv4 support from their machine)
			optval = TRUE;
		}
	}
#endif
	close(sockfd);
	computed_yet = TRUE;
	retval = !optval;
	return retval;
}
#else /* IPV6_V6ONLY */
gboolean
netio_is_dual_ipv4v6_stack(void)
{
	return FALSE;
}
#endif
FSTATIC gboolean
_netio_sendareliablefs(NetIO*self, NetAddr*dest, guint16 queueid, FrameSet* frameset)
{
	(void)self; (void)dest; (void)queueid; (void)frameset;
	g_warn_if_reached();
	return FALSE;
}
FSTATIC gboolean
_netio_sendreliablefs(NetIO*self, NetAddr* dest, guint16 queueid, GSList* fslist)
{
	(void)self; (void)dest; (void)queueid; (void)fslist;
	g_warn_if_reached();
	return FALSE;
}
FSTATIC gboolean
_netio_ackmessage(NetIO* self, NetAddr* dest, FrameSet* frameset)
{
	(void)self; (void)dest; (void)frameset;
	g_warning("%s.%d: Object does not support ACKing of messages", __FUNCTION__, __LINE__);
	return FALSE;
}
FSTATIC gboolean
_netio_supportsreliable(NetIO* self)
{
	(void)self;
	return FALSE;
}
FSTATIC void
 _netio_closeconn(NetIO* self, guint16 qid, const NetAddr* destaddr)
{
	(void)self; (void)destaddr; (void)qid;
	return;
}
/// g_hash_table destructor for a NetAddr
FSTATIC void
_netio_netaddr_destroy(gpointer addrptr)
{
	NetAddr* self = CASTTOCLASS(NetAddr, addrptr);
	UNREF(self);
}

/// Add an alias to our alias table
FSTATIC void
_netio_addalias(NetIO* self		///< Us
,		     NetAddr * fromaddr		///< Address to map from
,		     NetAddr* toaddr)		///< Address to map the from address to
{
	DUMP3("Aliasing from this address", &fromaddr->baseclass, " to the next address");
	DUMP3("Aliasing to this address", &toaddr->baseclass, " from the previous address");
	REF(fromaddr);
	REF(toaddr);
	g_hash_table_insert(self->aliases, fromaddr, toaddr);
}

///@}
