/**
 * @file
 * @brief Implements the ReliableUDP class - providing reliable transmission for UDP
 * @details It adds reliable packet transmission to the @ref NetIOudp class
 * through use of the @ref FsProtocol class.
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
#include <memory.h>
#include <proj_classes.h>
#include <reliableudp.h>
#include <frameset.h>
#include <framesettypes.h>
#include <frametypes.h>


DEBUGDECLARATIONS
/// @defgroup ReliableUDP ReliableUDP class
///@{
///@ingroup NetIOudp
/// A ReliableUDP object implements a protocol to make UDP reliable.
/// It is a class from which we might eventually make subclasses and is managed
/// by our @ref ProjectClass system.
/// It takes great advantage of all the @ref FsProtocol class - which does much of the work.

// Saved base class functions - so we call them w/o storing a copy in every object
static void (*_baseclass_finalize)(AssimObj*);
static GSList* (*_baseclass_rcvmany)(NetIO*, NetAddr**);
// These two could probably be eliminated...
static void (*_baseclass_sendone)(NetIO*, const NetAddr*, FrameSet*);
static void (*_baseclass_sendmany)(NetIO*, const NetAddr*, GSList*);

FSTATIC gboolean _reliableudp_sendreliable(ReliableUDP*self, NetAddr*, guint16, FrameSet*);
FSTATIC gboolean _reliableudp_sendreliableM(ReliableUDP*self, NetAddr*, guint16, GSList*);
FSTATIC gboolean _reliableudp_ackmessage (ReliableUDP* self, NetAddr* dest, FrameSet* frameset);
FSTATIC gboolean _reliableudp_nackmessage (ReliableUDP* self, NetAddr* dest, FrameSet* frameset);
FSTATIC void	 _reliableudp_flushall(ReliableUDP*self, const NetAddr* dest, enum ioflush);

// Our functions that override base class functions...
FSTATIC void _reliableudp_finalize(AssimObj*);
FSTATIC gboolean _reliableudp_input_queued(const NetIO*);
FSTATIC void _reliableudp_sendaframeset(NetIO*, const NetAddr*, FrameSet*);
FSTATIC void _reliableudp_sendframesets(NetIO*, const NetAddr*, GSList*);
FSTATIC GSList* _reliableudp_recvframesets(NetIO*, NetAddr**);


/// Construct new UDP NetIO object (and its socket, etc)
ReliableUDP*
reliableudp_new(gsize objsize		///<[in] Size of NetIOudp object, or zero.
	,	ConfigContext* config	///<[in/out] config info
	,	PacketDecoder* decoder	///<[in/out] packet decoder
	,	guint rexmit_timer_uS)	///<[in] How often to check for retransmission?
{
	NetIOudp*	uret;
	ReliableUDP*	self = NULL;

	BINDDEBUG(ReliableUDP);
	if (objsize < sizeof(ReliableUDP)) {
		objsize = sizeof(ReliableUDP);
	}
	uret = netioudp_new(objsize, config, decoder);
	if (uret) {
		if (!_baseclass_finalize) {
			_baseclass_finalize = uret->baseclass.baseclass._finalize;
			_baseclass_sendone = uret->baseclass.sendaframeset;
			_baseclass_sendmany = uret->baseclass.sendframesets;
			_baseclass_rcvmany = uret->baseclass.recvframesets;
		}
		self = NEWSUBCLASS(ReliableUDP, uret);
		self->sendreliable = _reliableudp_sendreliable;
		self->sendreliableM = _reliableudp_sendreliableM;
		self->ackmessage = _reliableudp_ackmessage;
		self->flushall = _reliableudp_flushall;
		// Now for the base class functions which we override
		self->baseclass.baseclass.baseclass._finalize = _reliableudp_finalize;
		self->baseclass.baseclass.recvframesets = _reliableudp_recvframesets;
		self->baseclass.baseclass.input_queued = _reliableudp_input_queued;
		// These next two don't really do anything different - and could be eliminated
		// as of now.
		self->baseclass.baseclass.sendframesets = _reliableudp_sendframesets;
		self->baseclass.baseclass.sendaframeset = _reliableudp_sendaframeset;

		self->_protocol = fsprotocol_new(0, &uret->baseclass, rexmit_timer_uS);
	}
	return self;
}

/// Finalize (free up) our @ref ReliableUDP object
FSTATIC void
_reliableudp_finalize(AssimObj* obj)
{
	ReliableUDP*	self = CASTTOCLASS(ReliableUDP, obj);
	if (self) {
		if (self->_protocol) {
			// Un-ref that puppy!
			self->_protocol->baseclass.unref(&self->_protocol->baseclass);
			self->_protocol = NULL;
		}
	}
	_baseclass_finalize(&self->baseclass.baseclass.baseclass);
}

FSTATIC gboolean
_reliableudp_input_queued(const NetIO* nself)
{
	const ReliableUDP*	self = CASTTOCONSTCLASS(ReliableUDP, nself);
	gboolean		retval;
	g_return_val_if_fail(nself != NULL, FALSE);
	retval = self->_protocol->iready(self->_protocol);
	DEBUGMSG2("%s: Checking input ready: returning %s", __FUNCTION__, (retval?"True":"False"));
	return retval;
}

/// Reliable UDP verison of 'sendaframeset' from base class.
/// Currently a pretty useless piece of code...
FSTATIC void
_reliableudp_sendaframeset(NetIO* nself, const NetAddr* dest, FrameSet* fs)
{
	_baseclass_sendone(nself, dest, fs);
}

/// Reliable UDP verison of 'sendframesets' from base class
/// Currently a pretty useless piece of code...
FSTATIC void
_reliableudp_sendframesets(NetIO* nself, const NetAddr* dest, GSList* fslist)
{
	_baseclass_sendmany(nself, dest, fslist);
}

/// Reliable UDP verison of 'recvframesets' from base class
/// We get called when the user thinks he might have some packets to receive.
/// We intervene here, and queue them up, making sure they arrive in order and so on.
/// ACKing the packets remains the responsibility of our client code.
FSTATIC GSList*
_reliableudp_recvframesets(NetIO* nself, NetAddr** srcaddr)
{
	NetAddr*	oursrcaddr;
	ReliableUDP*	self;
	GSList*		fsread;
	GSList*		lelem;
	FsProtocol*	proto;
	GSList*		retval = NULL;

	g_return_val_if_fail(nself != NULL, NULL);
	fsread = _baseclass_rcvmany(nself, &oursrcaddr);
	self = CASTTOCLASS(ReliableUDP, nself);
	g_return_val_if_fail(self != NULL, NULL);
	proto = self->_protocol;

	// Loop over all the packets we read in, and put them in our protocol queues
	for (lelem=fsread; lelem; lelem=lelem->next) {
		FrameSet*	fs = CASTTOCLASS(FrameSet, lelem->data);
		// Put that puppy in the queue...
		proto->receive(proto, oursrcaddr, fs);
	}
	// Do we have any packets ready to read out of the reliable protocol?
	if (proto->iready(proto)) {
		FrameSet*	fs = proto->read(proto, srcaddr);

		// In theory, we might have several from the same endpoint...
		// The problem is, they might be from different endpoints too...
		// So, let's just deliver them to our clients one at a time for now...
		if (fs) {
			retval = g_slist_prepend(NULL, fs);
		}
	}
	return retval;
}

/// Send a single packet reliably
FSTATIC gboolean
_reliableudp_sendreliable(ReliableUDP*self, NetAddr* dest, guint16 qid, FrameSet* fs)
{
	// Send it out!
	DUMP2("Sending packet with _protocol->send1", &fs->baseclass, NULL);
	return self->_protocol->send1(self->_protocol, fs, qid, dest);
}

/// Send several packets reliably
FSTATIC gboolean
_reliableudp_sendreliableM(ReliableUDP*self, NetAddr* dest, guint16 qid, GSList* fslist)
{
	DEBUGMSG2("Sending packet with _protocol->send(%d)", g_slist_length(fslist));
	// See if we've been requested to drop a packet for testing
	return self->_protocol->send(self->_protocol, fslist, qid, dest);
}

/// Send an ACK (as requested) for for the packet we've been handed
FSTATIC gboolean
_reliableudp_ackmessage (ReliableUDP* self, NetAddr* dest, FrameSet* frameset)
{
	self->_protocol->ackmessage(self->_protocol, dest, frameset);
	return TRUE;
}

/// Flush all packets to/and/or/from the given destination
FSTATIC void
_reliableudp_flushall(ReliableUDP*self, const NetAddr* dest, enum ioflush flushtype)
{
	self->_protocol->flushall(self->_protocol, dest,  flushtype);
}

///@}
