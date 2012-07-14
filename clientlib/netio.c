/**
 * @file
 * @brief Implements network I/O class (@ref NetIO)
 * @details This file contains the code to support the @ref NetIO objects for doing network I/O.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#include <projectcommon.h>
#include <errno.h>
#include <memory.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/types.h>
#ifdef _MSC_VER
#	include <winsock2.h>
#	include <ws2tcpip.h>
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

FSTATIC gint _netio_getfd(const NetIO* self);
FSTATIC void _netio_setblockio(const NetIO* self, gboolean blocking);
FSTATIC gboolean _netio_bindaddr(NetIO* self, const NetAddr* src);
FSTATIC void _netio_sendframesets(NetIO* self, const NetAddr* destaddr, GSList* framesets);
FSTATIC void _netio_sendaframeset(NetIO* self, const NetAddr* destaddr, FrameSet* frameset);
FSTATIC void _netio_finalize(AssimObj* self);
FSTATIC void _netio_sendapacket(NetIO* self, gconstpointer packet, gconstpointer pktend, const NetAddr* destaddr);
FSTATIC gpointer _netio_recvapacket(NetIO*, gpointer*, struct sockaddr_in6*, socklen_t*addrlen);
FSTATIC gsize _netio_getmaxpktsize(const NetIO* self);
FSTATIC gsize _netio_setmaxpktsize(NetIO* self, gsize maxpktsize);
FSTATIC GSList* _netio_recvframesets(NetIO*self , NetAddr** src);
FSTATIC SignFrame* _netio_signframe (NetIO *self);
FSTATIC Frame* _netio_cryptframe (NetIO *self);
FSTATIC Frame* _netio_compressframe (NetIO *self);
FSTATIC gboolean _netio_mcastjoin(NetIO* self, const NetAddr* src, const NetAddr*localaddr);

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
	fcntl(self->getfd(self), F_SETFL, fcntlflags);
#endif
	if (blocking) {
		chanflags |= G_IO_FLAG_NONBLOCK;
	}else{
		chanflags &= ~G_IO_FLAG_NONBLOCK;
	}
	g_io_channel_set_flags(self->giosock, chanflags, NULL);
}


/// Set up a NetIO object to listen to (join) a particular multicast group.
///@todo DOES NOT APPEAR TO WORK FOR V4 addresses
FSTATIC gboolean
_netio_mcastjoin(NetIO* self, const NetAddr* src, const NetAddr*localaddr)
{
	int			rc = -1;



	errno = 0;

	if (!src->ismcast(src)) {
		g_warning("%s: Cannot join multicast group with non-multicast address"
		,	__FUNCTION__);
		return FALSE;
	}
	if (localaddr != NULL && src->_addrtype != localaddr->_addrtype) {
		g_warning("%s: Cannot join multicast group with differing address types"
		,	__FUNCTION__);
		return FALSE;
	}

	if (ADDR_FAMILY_IPV6 == src->_addrtype ) {
		struct ipv6_mreq	multicast_request;
		struct sockaddr_in6	saddr;
		saddr = src->ipv6sockaddr(src);
		memset(&multicast_request, 0, sizeof(multicast_request));
		memcpy(&multicast_request.ipv6mr_multiaddr, &saddr
		,	sizeof(multicast_request.ipv6mr_multiaddr));

		if (localaddr != NULL) {
			struct sockaddr_in6	laddr;
			laddr = localaddr->ipv6sockaddr(localaddr);
			memcpy(&multicast_request.ipv6mr_interface, &laddr
			,	sizeof(multicast_request.ipv6mr_interface));
		}
		
		rc = setsockopt(self->getfd(self), IPPROTO_IPV6, IPV6_JOIN_GROUP
		,	(gpointer)&multicast_request, sizeof(multicast_request));
		if (rc != 0) {
			g_warning("%s: Cannot join multicast group [%s (errno:%d)]"
			,	__FUNCTION__, g_strerror(errno), errno);
		}
	}else if (ADDR_FAMILY_IPV4 == src->_addrtype) {
		struct ip_mreq	multicast_request;
		struct sockaddr_in	saddr;
		saddr = src->ipv4sockaddr(src);
		memcpy(&multicast_request.imr_multiaddr, &saddr
		,	sizeof(multicast_request.imr_multiaddr));

		if (localaddr != NULL) {
			struct sockaddr_in	laddr;
			laddr = localaddr->ipv4sockaddr(localaddr);
			memcpy(&multicast_request.imr_interface, &laddr
			,	sizeof(multicast_request.imr_interface));
		}
		
		rc = setsockopt(self->getfd(self), IPPROTO_IP, IP_ADD_MEMBERSHIP
		,	(gpointer)&multicast_request, sizeof(multicast_request));
	}
	if (rc != 0) {
		g_warning("%s: Cannot join multicast group [%s (errno:%d)]"
		,	__FUNCTION__, g_strerror(errno), errno);
	}
	return (rc == 0);
}

/// Member function to bind this NewIO object to a NetAddr address
FSTATIC gboolean
_netio_bindaddr(NetIO* self,		///<[in/out] The object being bound
		const NetAddr* src)	///<[in] The address to bind it to
{
	gint			sockfd;
	struct sockaddr_in6	saddr;
	int			rc;
	g_return_val_if_fail(NULL != self, FALSE);
	g_return_val_if_fail(NULL != self->giosock, FALSE);
	sockfd = self->getfd(self);
	memset(&saddr, 0x00, sizeof(saddr));
	saddr.sin6_family = AF_INET6;
	saddr.sin6_port = src->port(src);
	g_return_val_if_fail(src->addrtype(src) == ADDR_FAMILY_IPV4 || src->addrtype(src) == ADDR_FAMILY_IPV6, FALSE);

	saddr = src->ipv6sockaddr(src);
	rc = bind(sockfd, (struct sockaddr*)&saddr, sizeof(saddr));
	if (rc != 0) {
		g_warning("%s: Cannot bind to address [%s (errno:%d)]"
		,	__FUNCTION__, g_strerror(errno), errno);
	}
	return rc == 0;
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
		self->_signframe->baseclass.baseclass.unref(self->_signframe);
		self->_signframe = NULL;
	}
	if (self->_cryptframe) {
		self->_cryptframe->baseclass.unref(self->_cryptframe);
		self->_cryptframe = NULL;
	}
	if (self->_compressframe) {
		self->_compressframe->baseclass.unref(self->_compressframe);
		self->_compressframe = NULL;
	}
	if (self->_decoder) {
		self->_decoder->baseclass.unref(self->_decoder);
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
FSTATIC Frame*
_netio_compressframe (NetIO *self)
{
	return self->_compressframe;
}
FSTATIC Frame*
_netio_cryptframe(NetIO *self)
{
	return self->_cryptframe;
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
	ret->bindaddr = _netio_bindaddr;
	ret->sendframesets = _netio_sendframesets;
	ret->sendaframeset = _netio_sendaframeset;
	ret->getmaxpktsize = _netio_getmaxpktsize;
	ret->setmaxpktsize = _netio_setmaxpktsize;
	ret->recvframesets = _netio_recvframesets;
	ret->mcastjoin = _netio_mcastjoin;
	ret->signframe = _netio_signframe;
	ret->cryptframe = _netio_cryptframe;
	ret->compressframe = _netio_compressframe;
	ret->_maxpktsize = 65300;
	ret->_configinfo = config;
	ret->_decoder = decoder;
	decoder->baseclass.ref(decoder);
	f =  config->getframe(config, CONFIGNAME_OUTSIG);
	g_return_val_if_fail(f != NULL, NULL);
	f->baseclass.ref(f);
	ret->_signframe = CASTTOCLASS(SignFrame, f);
	ret->_cryptframe = config->getframe(config, CONFIGNAME_CRYPT);
	if (ret->_cryptframe) {
		ret->_cryptframe->baseclass.ref(ret->_cryptframe);
	}
	ret->_compressframe = config->getframe(config, CONFIGNAME_COMPRESS);
	if (ret->_compressframe) {
		ret->_compressframe->baseclass.ref(ret->_compressframe);
	}
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

	rc = sendto(self->getfd(self),  packet, (size_t)length, flags, (const struct sockaddr*)&v6addr, sizeof(v6addr));
        if (rc != length) {
		char *	tostring = destaddr->baseclass.toString(destaddr);
		g_warning(
		"%s: sendto returned %"G_GSSIZE_FORMAT " vs %"G_GSSIZE_FORMAT" with errno %s"
		,	__FUNCTION__, rc, (size_t)length, g_strerror(errno));
		g_warning("%s: destaddr:[%s] ", __FUNCTION__, tostring);
		g_free(tostring); tostring = NULL;
	}
	g_return_if_fail(rc == length);
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
		Frame*	cryptframe	= self->cryptframe(self);
		Frame*	compressframe	= self->compressframe(self);
		if (cryptframe) {
			cryptframe->baseclass.ref(cryptframe);
		}
		if (compressframe) {
			compressframe->baseclass.ref(compressframe);
		}
		frameset_construct_packet(curfs, signframe, cryptframe, compressframe);
		_netio_sendapacket(self, curfs->packet, curfs->pktend, destaddr);
		
	}
}
FSTATIC void
_netio_sendaframeset(NetIO* self,		///< [in/out] The NetIO object doing the sending
		     const NetAddr* destaddr,	///< [in] Where to send the FrameSets
		     FrameSet* frameset)	///< [in] The framesets being sent
{
	SignFrame* signframe	= self->signframe(self);
	Frame*	cryptframe	= self->cryptframe(self);
	Frame*	compressframe	= self->compressframe(self);
	g_return_if_fail(self != NULL);
	g_return_if_fail(self->_signframe != NULL);
	g_return_if_fail(frameset != NULL);
	g_return_if_fail(destaddr != NULL);

	if (cryptframe) {
		cryptframe->baseclass.ref(cryptframe);
	}
	if (compressframe) {
		compressframe->baseclass.ref(compressframe);
	}
	frameset_construct_packet(frameset, signframe, cryptframe, compressframe);
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

	// First we peek and see how long the message is...
	*addrlen = sizeof(*srcaddr);
memset(srcaddr, 0, sizeof(*srcaddr));
	msglen = recvfrom(self->getfd(self), dummy, 1, MSG_DONTWAIT|MSG_PEEK|MSG_TRUNC,
		          (struct sockaddr*)srcaddr, addrlen);
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

	// Was there an error?
	if (msglen2 < 0) {
		g_warning("recvfrom(%d, ... MSG_DONTWAIT) failed: %s (in %s:%s:%d)"
		,      self->getfd(self), g_strerror(errno), __FILE__, __FUNCTION__, __LINE__);
		FREE(msgbuf); msgbuf = NULL;
		return NULL;
	}
	// Does everything look good?
	if (msglen2 != msglen) {
		g_warning("recvfrom(%d, ... MSG_DONTWAIT) returned %zd instead of %zd (in %s:%s:%d)"
		,      self->getfd(self), msglen2, msglen, __FILE__, __FUNCTION__ ,	__LINE__);
		FREE(msgbuf); msgbuf = NULL;
		return NULL;
	}
	// Hah! Looks good!
	*pktend = (void*) (msgbuf + msglen);
	//g_debug("netio: Received %zd byte message", msglen);
	return msgbuf;
}
/// Member function to receive a collection of FrameSets (GSList*) out of our NetIO object
FSTATIC GSList*
_netio_recvframesets(NetIO* self,	///<[in/out] NetIO routine to receive a set of FrameSets
					///< from a single address.
		     NetAddr** src)	///<[out] constructed source address for FrameSets
{
	GSList*		ret = NULL;
	gpointer	pkt;
	gpointer	pktend;
	socklen_t	addrlen;
	struct sockaddr_in6	srcaddr;

	*src = NULL;	// Make python happy in case we fail...
	pkt = _netio_recvapacket(self, &pktend, &srcaddr, &addrlen);

	if (NULL != pkt) {
		ret = self->_decoder->pktdata_to_framesetlist(self->_decoder, pkt, pktend);
		if (NULL != ret) {
			*src = netaddr_sockaddr_new(&srcaddr, addrlen);
		}else{
			FREE(ret); ret = NULL;
		}
		FREE(pkt);
	}
	return ret;
}

#ifdef IPV6_V6ONLY
#	include <netdb.h>
#	include <unistd.h>

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
	endprotoent();
	g_return_val_if_fail(proto != NULL, FALSE);
	
	sockfd = socket(AF_INET6, SOCK_DGRAM, IPPROTO_UDP);
	g_return_val_if_fail(sockfd >= 0, FALSE);
	
	optlen = sizeof(retval);
	optval = TRUE;
	if (getsockopt(sockfd, proto->p_proto, IPV6_V6ONLY, &optval, &optlen) < 0) {
		g_warning("getsockopt failed: errno %d", errno);
		close(sockfd);
		return FALSE;
	}
	// Should never happen...
	g_return_val_if_fail(optlen == sizeof(retval), FALSE);
#ifdef WIN32
	// See http://msdn.microsoft.com/en-us/library/windows/desktop/bb513665%28v=vs.85%29.aspx
	// This might be OK for other OSes too...
	if (optval) {
		optval = FALSE;
		if (setsockopt(sockfd, proto->p_proto, IPV6_V6ONLY, &optval, &optlen) < 0) {
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

///@}
