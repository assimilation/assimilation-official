/**
 * @file
 * @brief Implements the FsProtocol object
 * @details @ref FsProtocol objects implement a protocol that provides reliable @ref FrameSet transmission.
 * This sits in the middle of packet transmission and reception.
 *
 * Incoming packets come into FsQueues, and we make sure we process ACKs, and give them to our
 * clients in sequence number order.
 *
 * Outgoing packets go out through the FsQueue object, and we schedule retransmissions when ACKs
 * are not forthcoming.
 *
 * In addition, we manage the initiation and termination of communication to endpoints.
 *
 * This class is related to @ref FsQueue and @ref FrameSet objects.
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

typedef struct	_FsProtocol FsProtocol;
typedef struct	_FsProtoElem FsProtoElem;
typedef struct	_FsProtoElemSearchKey FsProtoElemSearchKey;
typedef enum	_FsProtoState FsProtoState;

/**
 * Part of what's implied here is that we need to invent some protocol-level packets for starting up
 * and shutting down the connections. Note that a startup packet always has packet sequence number 1.
 * Eventually we need to figure out what we need to do about CMA failover - where the clients might
 * be in the middle of a connection, and still need to send the packets they have on hand.
 * This is not likely to be an issue for the nanoprobes - since they are ephemeral by design.
 *
 * We also need a CONN_NAK packet where we assert that there is no connection currently active - indicating
 * that the two sides are likely out of sync - and need to get in sync before proceeding.
 * If this happens and we still want to talk to the other side, we need to resequence our packets, or invent
 * some new kind of "resume connection" packet.  The CMA isn't likely to want to do this, but we will need
 * to do something like this for the nanoprobes to be able to tolerate CMA failover without losing things
 * they want to tell the CMA.
 *
 * Now all I have to do is figure out the inputs and state machine for these states...
 */
enum _FsProtoState {
	FSPR_NONE	= 0,	///< No connection in progress
	FSPR_INIT	= 1,	///< Connection initiated, awaiting first ACK packet
				///< from far side.  Unsure if this means we need to send
				///< a packet and get an ACK before we come out of this
				///< state if the other side initiated the connection.
				///< My inclination is to say "not".
	FSPR_UP		= 2,	///< Connection fully established - received at least one ACK
	FSPR_SHUT1	= 3,	///< Waiting on CONNSHUT and ACK
	FSPR_SHUT2	= 4,	///< Received a CONNSHUT packet, waiting for output to drain
	FSPR_SHUT3	= 5,	///< Output drained, Waiting for CONNSHUT
	FSPR_INVALID,		///< End marker - Invalid state
};

#define	 FSPR_ISSHUTDOWN(state)	(state >= FSPR_SHUT1)


/// Not a full-blown class - just a utility structure.  Endpoint+qid constitute a key for it.
/// Note that the @ref FsProtocol class is a glorified hash table of these FsProtoElem structures
struct _FsProtoElem {
	NetAddr*	endpoint;	///< Who is our partner in this?
	guint16		_qid;		///< Queue id of far endpoint
	FsQueue*	outq;		///< Queue of outbound messages
	FsQueue*	inq;		///< Queue of incoming messages - perhaps missing packets...
	SeqnoFrame*	lastacksent;	///< The highest sequence number we've sent an ACK for.
	SeqnoFrame*	lastseqsent;	///< Last sequence number which has been sent at least once
	FsProtocol*	parent;		///< Our parent FsProtocol object
	gint64		nextrexmit;	///< When to retransmit next...
	gint64		acktimeout;	///< When to timeout waiting for an ACK
	FsProtoState	state;		///< State of this connection
};

struct _FsProtoElemSearchKey {
	const NetAddr*	endpoint;	///< Who is our partner in this?
	guint16		_qid;		///< Queue id of far endpoint
};
	

/// This is an @ref FsProtocol object - implementing a reliable user-level @ref FrameSet delivery system
/// It is a subclass of the @ref AssimObj and is managed by our @ref ProjectClass system.
struct _FsProtocol {
	AssimObj	baseclass;					///< base @ref AssimObj object
	NetIO*		io;						///< Our parent NetIO object
	GHashTable*	endpoints;					///< All our FsProtoElem endpoints
	GList*		unacked;					///< List of FsProtoElems awaiting ACKs
	GList*		ipend;						///< List of FsProtoElems ready to be read
	guint		window_size;					///< Window size of our connections
	gint64		rexmit_interval;				///< How often to retransmit - in uS
	guint		_timersrc;					///< gmainloop timer source id
	FsProtoElem*	(*find)(FsProtocol*,guint16,const NetAddr*);	///< Find connection to given endpoint
	FsProtoElem*	(*findbypkt)(FsProtocol*, NetAddr*, FrameSet*);	///< Find connection to given originator
	FsProtoElem*	(*addconn)(FsProtocol*, guint16, NetAddr*);	///< Add a connection to the given endpoint
	void		(*closeconn)(FsProtocol*, guint16, const NetAddr*);///< Close this connection (reset it)
	gboolean	(*iready)(FsProtocol*);				///< TRUE if input is ready to be read
	gboolean	(*outputpending)(FsProtocol*);			///< Return TRUE if output is pending
	FrameSet*	(*read)(FsProtocol*, NetAddr**);		///< Read the next @ref FrameSet
	void		(*receive)(FsProtocol*, NetAddr*, FrameSet*);	///< Enqueue a received input @ref FrameSet
	gboolean	(*send1)(FsProtocol*, FrameSet*, guint16, NetAddr*);///< Send one @ref FrameSet
	gboolean	(*send)(FsProtocol*, GSList*, guint16, NetAddr*);///< Send a list of FrameSets
	void		(*ackmessage)(FsProtocol*, NetAddr*, FrameSet*);///< ACK the given @ref FrameSet
};
WINEXPORT FsProtocol* fsprotocol_new(guint objsize, NetIO* ioobj, guint rexmit_timer_uS);
#define	DEFAULT_FSP_QID		0		///< Queue ID of a packet w/o a sequence number?
#define FSPROTO_WINDOWSIZE	7		///< FsProtocol window size
#define FSPROTO_REXMITINTERVAL	(2000000)	///< FsProtocol retransmit interval in microseconds

///@}

#endif /* _FSPROTOCOL_H */
