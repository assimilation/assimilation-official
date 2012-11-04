
/**
 * @file
 * @brief Describes interfaces to Address Frame (AddrFrame) C-Class.
 * AddrFrames are Frames that contain some type of network address.
 * The types of addresses we support are defined by the @ref AddressFamilyNumbers "IETF/IANA Address type assignments".
 * @see AddressFamilyNumbers
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _IPPORTFRAME_H
#define _IPPORTFRAME_H
#include <projectcommon.h>
#include <frame.h>
#include <netaddr.h>
typedef struct _IpPortFrame IpPortFrame;

/// This is our @ref IpPortFrame object - used for holding @ref NetAddr network addresses with
/// <i>non-zero</i> port numbers
/// It has some different member functions implementations than its base @ref Frame -
/// mainly for validating packet contents.
///@{
/// @ingroup AddrFrame
struct _IpPortFrame {
	Frame	baseclass;
	NetAddr*_addr;
	guint16	port;
	void	(*_basefinal)(AssimObj*);	///< Free object (private)
	NetAddr*(*getnetaddr)(IpPortFrame*f);
};

WINEXPORT IpPortFrame* ipportframe_netaddr_new(guint16 frame_type, NetAddr*);
WINEXPORT IpPortFrame* ipportframe_ipv4_new(guint16 frame_type, guint16 port, gconstpointer addrbuf);
WINEXPORT IpPortFrame* ipportframe_ipv6_new(guint16 frame_type, guint16 port, gconstpointer addrbuf);
WINEXPORT Frame* ipportframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend);

///@}
#endif /* _IPPORTFRAME_H */
