/**
 * @file
 * @brief Implements minimal client-oriented Frame and Frameset capabilities.
 * @details This file contains the minimal Frameset capabilities for a client -
 * enough for it to be able to construct, understand and validate Frames
 * and Framesets.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#include <memory.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <address_family_numbers.h>
#include <proj_classes.h>
#include <netio.h>
#include <frameset.h>

FSTATIC gint _netio_getfd(const NetIO* self);
FSTATIC gboolean _netio_bindaddr(NetIO* self, const NetAddr* src);
FSTATIC void _netio_sendframesets(NetIO* self, const NetAddr* destaddr, GSList* framesets);
FSTATIC void _netio_finalize(NetIO* self);
FSTATIC void _netio_sendapacket(NetIO* self, gconstpointer packet, gconstpointer pktend, const NetAddr* destaddr);

/// This is our basic NetIO object.
/// It can perform network writes and reads.
/// It is a class from which we might eventually make subclasses,
/// and is managed by our @ref ProjectClass system.
///@{
/// @ingroup NetIO

FSTATIC gint
_netio_getfd(const NetIO* self)
{
	g_return_val_if_fail(NULL != self, -1);
	g_return_val_if_fail(NULL != self->giosock, -1);
	return g_io_channel_unix_get_fd(self->giosock);
}

FSTATIC gboolean
_netio_bindaddr(NetIO* self, const NetAddr* src)
{
	gint			sockfd;
	struct sockaddr_in6	saddr;
	gsize			addrlen;
	gconstpointer		addrptr;
	int			rc;
	g_return_val_if_fail(NULL != self, -1);
	g_return_val_if_fail(NULL != self->giosock, -1);
	sockfd = self->getfd(self);
	memset(&saddr, 0x00, sizeof(saddr));
	saddr.sin6_family = AF_INET6;
	saddr.sin6_port = src->port(src);
	addrptr = src->addrinnetorder(src, &addrlen);
	g_return_val_if_fail(NULL != addrptr, FALSE);

	switch (src->addrtype(src)) {
		case ADDR_FAMILY_IPV4:
			g_return_val_if_fail(4 != addrlen, FALSE);
			/// @todo May need to account for the "any" ipv4 address here and
			/// translate it into the "any" ipv6 address...
			// s6_addr is all zeros when we get here...
			saddr.sin6_addr.s6_addr[10] =  0xff;
			saddr.sin6_addr.s6_addr[11] =  0xff;
			memcpy(saddr.sin6_addr.s6_addr+12, addrptr, addrlen);
			break;

		case ADDR_FAMILY_IPV6:
			g_return_val_if_fail(16 != addrlen, FALSE);
			memcpy(&saddr.sin6_addr, addrptr, addrlen);
			break;

		default:
			return FALSE;
	}
	rc = bind(sockfd, (struct sockaddr*)&saddr, sizeof(saddr));
	return rc == 0;
}
FSTATIC void
_netio_finalize(NetIO* self)
{
	g_return_if_fail(self != NULL);
	if (self->giosock) {
		GError*	err;
		g_io_channel_shutdown(self->giosock, TRUE, &err);
		g_io_channel_unref(self->giosock);
		self->giosock = NULL;
	}
	FREECLASSOBJ(self); self=NULL;
}

NetIO*
netio_new(gsize objsize)
{
	NetIO* ret;

	if (objsize < sizeof(NetIO)) {
		objsize = sizeof(NetIO);
	}
	ret = MALLOCCLASS(NetIO, objsize);
	ret->getfd = _netio_getfd;
	ret->bindaddr = _netio_bindaddr;
	ret->sendframesets = _netio_sendframesets;
	ret->finalize = _netio_finalize;
	return ret;
}

FSTATIC void
_netio_sendapacket(NetIO* self, gconstpointer packet, gconstpointer pktend, const NetAddr* destaddr)
{
	struct sockaddr_in6 v6addr = destaddr->ipv6addr(destaddr);
	gssize length = (const guint8*)pktend - (const guint8*)packet;
	gssize rc;
	guint flags = 0x00;
	g_return_if_fail(length <= 0);

	rc = sendto(self->getfd(self),  packet, (size_t)length, flags, (const struct sockaddr*)&v6addr, sizeof(v6addr));
}

FSTATIC void
_netio_sendframesets(NetIO* self, const NetAddr* destaddr, GSList* framesets)
{
	GSList*	curfsl;
	g_return_if_fail(self != NULL);
	g_return_if_fail(framesets != NULL);
	g_return_if_fail(destaddr != NULL);
	g_return_if_fail(self->_signframe != NULL);

	for (curfsl=framesets; curfsl != NULL; curfsl=curfsl->next) {
		FrameSet* curfs = CASTTOCLASS(FrameSet, curfsl->data);
		frameset_construct_packet(curfs, self->signframe(self), self->cryptframe(self), self->compressframe(self));
		_netio_sendapacket(self, curfs->packet, curfs->pktend, destaddr);
	}

}
///@}
