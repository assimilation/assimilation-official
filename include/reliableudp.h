/**
 * @file
 * @brief Implements the Reliable UDP network I/O transport (ReliableUDP) class.
 * @details It knows how to construct UDP sockets, write to them, bind them, and get packets from them.
 * This is a subclass of the @ref NetIOudp class.
 *
 *
 * This file is part of the Assimilation Project.
 *
 * @author &copy; Copyright 2011, 2012 - Alan Robertson <alanr@unix.sh>
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

#ifndef _RELIABLE_UDP_H
#define _RELIABLE_UDP_H
#include <projectcommon.h>
#include <glib.h>
#include <netioudp.h>
#include <netaddr.h>
#include <frameset.h>
#include <configcontext.h>
#include <packetdecoder.h>
#include <fsprotocol.h>

///@{
/// @ingroup ReliableUDP
typedef struct _ReliableUDP ReliableUDP;
/// NetIOudp  is a @ref NetIOudp subclass specialized to provide reliable UDP connections.
/// It can perform network writes and reads, binds, etc. for UDP sockets
/// It is a class from which one could make subclasses, and is managed by our @ref ProjectClass system.
struct _ReliableUDP {
	NetIOudp	baseclass;	///< Base class (NetIO) object.
	FsProtocol*	_protocol;	///< Queuing, ordering, retransmission and ACKing discipline
};
WINEXPORT ReliableUDP* reliableudp_new(gsize objsize, ConfigContext* config, PacketDecoder* decoder,
	guint rexmit_timer_uS);
///@}

#endif /* _RELIABLE_UDP_H */
