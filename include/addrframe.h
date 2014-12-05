
/**
 * @file
 * @brief Describes interfaces to Address Frame (AddrFrame) C-Class.
 * AddrFrames are Frames that contain some type of network address.
 * The types of addresses we support are defined by the @ref AddressFamilyNumbers "IETF/IANA Address type assignments".
 * @see AddressFamilyNumbers
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

#ifndef _ADDRFRAME_H
#define _ADDRFRAME_H
#include <projectcommon.h>
#include <frame.h>
#include <netaddr.h>
typedef struct _AddrFrame AddrFrame;

/// This is our @ref AddrFrame object - used for holding @ref NetAddr network addresses.
/// It has some different member functions implementations than its base @ref Frame -
/// mainly for validating packet contents.
///@{
/// @ingroup AddrFrame
struct _AddrFrame {
	Frame	baseclass;
	NetAddr*_addr;
	void	(*_basefinal)(AssimObj*);	///< Free object (private)
	void	(*setaddr)(AddrFrame* f, guint16 addrtype, gconstpointer addr, gsize addrlen);
	void	(*setnetaddr)(AddrFrame* f, NetAddr* addr);
	NetAddr*(*getnetaddr)(AddrFrame*f);
	void	(*setport)(AddrFrame*f, guint16 port);
};

WINEXPORT AddrFrame* addrframe_new(guint16 frame_type, gsize framesize);
WINEXPORT AddrFrame* addrframe_ipv4_new(guint16 frame_type, gconstpointer addr);
WINEXPORT AddrFrame* addrframe_ipv6_new(guint16 frame_type, gconstpointer addr);
WINEXPORT AddrFrame* addrframe_mac48_new(guint16 frame_type, gconstpointer addr);
WINEXPORT AddrFrame* addrframe_mac64_new(guint16 frame_type, gconstpointer addr);
WINEXPORT Frame* addrframe_tlvconstructor(gpointer tlvstart, gconstpointer pktend, gpointer*,gpointer*);

///@}
#endif /* _ADDRFRAME_H */
