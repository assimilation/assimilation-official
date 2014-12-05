
/**
 * @file
 * @brief Describes interfaces to Address Frame (IpPortFrame) C-Class.
 * AddrFrames are Frames that contain some type of network address.
 * The types of addresses we support are defined by the @ref AddressFamilyNumbers "IETF/IANA Address type assignments".
 * @see AddressFamilyNumbers
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

#ifndef _IPPORTFRAME_H
#define _IPPORTFRAME_H
#include <projectcommon.h>
#include <frame.h>
#include <netaddr.h>

/// This is our @ref IpPortFrame object - used for holding @ref NetAddr network addresses with
/// <i>non-zero</i> port numbers
/// It has some different member functions implementations than its base @ref Frame -
/// mainly for validating packet contents.
///@{
/// @ingroup IpPortFrame
typedef struct _IpPortFrame IpPortFrame;
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
WINEXPORT Frame* ipportframe_tlvconstructor(gpointer tlvstart, gconstpointer pktend, gpointer*,gpointer*);

///@}
#endif /* _IPPORTFRAME_H */
