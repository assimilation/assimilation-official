/**
 * @file
 * @brief Implements the FsProtocol object
 * @details @ref FsProtocol objects implement a protocol that provides reliable @ref FrameSet transmission.
 * This sits in the middle of packet transmission and reception.
 *
 * I think I want one of these objects to manage all the various destinations we have - so that there is one
 * for each @ref NetIO object, not <i>many</i> per NetIO object (i.e., not one per destination).
 *
 * Incoming packets get filtered here to make sure we send ACKs, and receive them in sequence number order.
 *
 * Outgoing packets go out through the FsQueue object, and we schedule retransmissions when ACKs are not forthcoming.
 *
 * This class is related to @ref FsQueue and @ref FrameSet objects.
 *
 *
 * @author Copyright &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 *  This file is part of the Assimilation Project.
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

#ifndef _FSPROTOCOL_H
#define _FSPROTOCOL_H
#include <assimobj.h>
#include <frameset.h>
#include <netaddr.h>
#include <fsqueue.h>
#include <netio.h>

///@{
/// @ingroup FsProtocol

typedef struct _FsProtocol FsProtocol;
typedef struct _FsProtoElem FsProtoElem;

/// Not a full-blown class - just a utility structure.  Endpoint+qid constitute a key for it.
struct _FsProtoElem {
	NetAddr*	endpoint;	///< Who is our partner in this?
	guint16		_qid;		///< Queue id of far endpoint
	FsQueue*	outq;		///< Queue of outbound messages
	FsQueue*	inq;		///< Queue of incoming messages - perhaps missing packets...
	FsProtocol*	parent;		///< Our parent FsProtocol object
};

/// This is an @ref FsProtocol object - designed for managing our reliable user-level @ref FrameSet delivery system
/// It is a subclass of the @ref AssimObj and is managed by our @ref ProjectClass system.
struct _FsProtocol {
	AssimObj	baseclass;					///< base @ref AssimObj object
	NetIO*		io;						///< Our parent NetIO object
	GHashTable*	endpoints;					///< All our FsProtoElem endpoints
	GList*		unacked;					///< List of FsProtoElems awaiting ACKs
	GList*		ipend;						///< List of FsProtoElems ready to be read
	FsProtoElem*	(*find)(FsProtocol*,guint16, NetAddr*);		///< Find a connection to the given endpoint
	FsProtoElem*	(*findbypkt)(FsProtocol*, NetAddr*, FrameSet*);	///< Find a connection to the given endpoint
	FsProtoElem*	(*addconn)(FsProtocol*, guint16, NetAddr*);	///< Add a connection to the given endpoint
	gboolean	(*iready)(FsProtocol*);				///< TRUE if input is ready to be read
	FrameSet*	(*read)(FsProtocol*, NetAddr**);		///< Read the next packet
	void		(*receive)(FsProtocol*, NetAddr*, FrameSet*);	///< Enqueue a received input packet
	gboolean	(*send1)(FsProtocol*, FrameSet*, guint16, NetAddr*);///< Send one packet
	gboolean	(*send)(FsProtocol*, GSList*, guint16, NetAddr*);///< Send a list of packets
};
WINEXPORT FsProtocol* fsprotocol_new(guint objsize, NetIO* ioobj);
#define	DEFAULT_FSP_QID	0 ///< What is the Queue ID of a packet w/o a sequence number?

///@}

#endif /* _FSPROTOCOL_H */
