/**
 * @file
 * @brief Implements UDP network I/O (NetIOudp) class.
 * @details It knows how to construct UDP sockets, write to them, bind them, and get packets from them.
 * This is a subclass of the @ref NetIO class.
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

#ifndef _NETIOUDP_H
#define _NETIOUDP_H
#include <projectcommon.h>
#include <glib.h>
#include <netio.h>
#include <cryptframe.h>

///@{
/// @ingroup NetIOudp
typedef struct _NetIOudp NetIOudp;
/// NetIOudp  is a @ref NetIO subclass specialized to UDP connections.
/// It can perform network writes and reads, binds, etc. for UDP sockets
/// It is a class from which we make subclasses (like @ref ReliableUDP)
/// and is managed by our @ref ProjectClass system.
struct _NetIOudp {
	NetIO		baseclass;	///< Base class (NetIO) object.
	GDestroyNotify	_finalize;	///< Saved (base class) finalize routine
};
WINEXPORT NetIOudp* netioudp_new(gsize objsize, ConfigContext* config,    PacketDecoder* decoder);
///@}

#endif /* _NETIOUDP_H */
