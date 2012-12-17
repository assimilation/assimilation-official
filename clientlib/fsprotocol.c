/**
 * @file
 * @brief FrameSet queueing class
 * @details This includes code to implement FrameSet queueing for reliable communication
 *
 * This file is part of the Assimilation Project.
 *
 * @author Copyright &copy; 2012 - Alan Robertson <alanr@unix.sh>
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
 *
 */
#include <string.h>
#include <projectcommon.h>
#include <fsprotocol.h>
#include <frametypes.h>
#include <stdio.h>

FSTATIC guint		_fsprotocol_protoelem_hash(gconstpointer fsprotoelemthing);
FSTATIC void		_fsprotocol_protoelem_destroy(gpointer fsprotoelemthing);
FSTATIC gboolean	_fsprotocol_protoelem_equal(gconstpointer lhs, gconstpointer rhs);
FSTATIC gboolean	_fsprotocol_timeoutfun(gpointer userdata);

FSTATIC void		_fsprotocol_finalize(AssimObj* aself);
FSTATIC FsProtoElem*	_fsprotocol_addconn(FsProtocol*self, guint16 qid, NetAddr* destaddr);
FSTATIC FsProtoElem*	_fsprotocol_find(FsProtocol* self, guint16 qid, const NetAddr* destaddr);
FSTATIC FsProtoElem*	_fsprotocol_findbypkt(FsProtocol* self, NetAddr*, FrameSet*);
FSTATIC void		_fsprotocol_updateack(FsProtoElem* fspe, FrameSet* seq);
FSTATIC gboolean	_fsprotocol_iready(FsProtocol*);
FSTATIC FrameSet*	_fsprotocol_read(FsProtocol*, NetAddr**);
FSTATIC void		_fsprotocol_receive(FsProtocol*, NetAddr*, FrameSet*);
FSTATIC gboolean	_fsprotocol_send1(FsProtocol*, FrameSet*, guint16 qid, NetAddr*);
FSTATIC gboolean	_fsprotocol_send(FsProtocol*, GSList*, guint16 qid, NetAddr*);
FSTATIC void		_fsprotocol_xmitifwecan(FsProtoElem*);
FSTATIC void		_fsprotocol_flushall(FsProtocol* self, const NetAddr* addr, enum ioflush op);
FSTATIC void		_fsprotocol_flush1(FsProtocol* self, const NetAddr* addr, enum ioflush op);

DEBUGDECLARATIONS
/// @defgroup FsProtocol FsProtocol class
///@{
/// @ingroup C_Classes

#define		TRYXMIT(fspe)	{_fsprotocol_xmitifwecan(fspe);}

/// Locate the FsProtoElem structure that corresponds to this (destaddr, qid) pair
FSTATIC FsProtoElem*
_fsprotocol_find(FsProtocol*self		///< typical FsProtocol 'self' object
,		 guint16 qid			///< Queue id of far endpoint
,		 const NetAddr* destaddr)	///< destination address
{
	FsProtoElemSearchKey	elem;
	elem.endpoint	= destaddr;
	elem._qid	= qid;
	return (FsProtoElem*)g_hash_table_lookup(self->endpoints, &elem);
}

/// Find the FsProtoElem that corresponds to the given @ref FrameSet.
/// The FrameSet can have a sequence number - or not.
FSTATIC FsProtoElem*
_fsprotocol_findbypkt(FsProtocol* self		///< The FsProtocol object we're operating on
,		      NetAddr* addr		///< The Network address we're looking for
,		      FrameSet* fs)		///< The FrameSet whose queue id we'll use in looking for it
{
	SeqnoFrame*	seq = fs->getseqno(fs);
	return self->addconn(self, (seq == NULL ? DEFAULT_FSP_QID : seq->getqid(seq)), addr);
}

/// (possibly) Update the last-ACK-sent sequence number in our FsProtoElem
FSTATIC void
_fsprotocol_updateack(FsProtoElem* fspe, FrameSet* fs)
{
	SeqnoFrame*	seq = fs->getseqno(fs);
	if (seq
	&&	(fspe->lastacksent == NULL || fspe->lastacksent->compare(fspe->lastacksent, seq) < 0)) {
		if (fspe->lastacksent) {
			fspe->lastacksent->baseclass.baseclass.unref(&fspe->lastacksent->baseclass.baseclass);
		}
		fspe->lastacksent = seq;
		seq->baseclass.baseclass.ref(&seq->baseclass.baseclass);
	}
}

/// Add and return a FsProtoElem connection to our collection of connections...
/// Note that if it's already there, the exiting connection will be returned.
FSTATIC FsProtoElem*
_fsprotocol_addconn(FsProtocol*self		///< typical FsProtocol 'self' object
,		    guint16 qid			///< Queue id for the connection
,		    NetAddr* destaddr)	///< destination address
{
	FsProtoElem*	ret;

	if ((ret = self->find(self, qid, destaddr))) {
		return ret;
	}
	ret = MALLOCTYPE(FsProtoElem);
	if (ret) {
		///@todo: Need to make a way to delete FsProtoElem connections...
		ret->endpoint = destaddr;
		destaddr->baseclass.ref(&destaddr->baseclass);
		ret->_qid = qid;
		ret->outq = fsqueue_new(0, destaddr, qid);
		ret->inq  = fsqueue_new(0, destaddr, qid);
		ret->lastacksent  = NULL;
		ret->lastseqsent  = NULL;
		ret->outstanding_acks  = 0;
		ret->nextrexmit  = 0;
		ret->parent = self;
		g_hash_table_insert(self->endpoints, ret, ret);
	}
	return ret;
}

/// Construct an FsQueue object
WINEXPORT FsProtocol*
fsprotocol_new(guint objsize		///< Size of object to be constructed
,	      NetIO* io			///< Pointer to NetIO for us to reference
,	      guint rexmit_timer_uS)	///< Retransmit timer in microseconds
{
	FsProtocol*		self;
	BINDDEBUG(FsProtocol);
	if (objsize < sizeof(FsProtocol)) {
		objsize = sizeof(FsProtocol);
	}
	self = NEWSUBCLASS(FsProtocol, assimobj_new(objsize));
	if (!self) {
		return NULL;
	}
	// Initialize our (virtual) member functions
	self->baseclass._finalize = _fsprotocol_finalize;
	self->find =		_fsprotocol_find;
	self->findbypkt =	_fsprotocol_findbypkt;
	self->addconn =		_fsprotocol_addconn;
	self->iready =		_fsprotocol_iready;
	self->read =		_fsprotocol_read;
	self->receive =		_fsprotocol_receive;
	self->send1 =		_fsprotocol_send1;
	self->send =		_fsprotocol_send;
	self->flushall =	_fsprotocol_flushall;

	// Initialize our data members
	self->io =		io; io->baseclass.ref(&io->baseclass);
	/// The key and the data are in fact the same object
	/// Don't want to free the object twice ;-) - hence the final NULL argument
	self->endpoints = g_hash_table_new_full(_fsprotocol_protoelem_hash,_fsprotocol_protoelem_equal
        ,		_fsprotocol_protoelem_destroy, NULL);
	self->unacked = NULL;
	self->ipend = NULL;
	self->window_size = FSPROTO_WINDOWSIZE;
	self->rexmit_interval = FSPROTO_REXMITINTERVAL;

	if (rexmit_timer_uS == 0) {
		rexmit_timer_uS = self->rexmit_interval/2;
	}


	if ((rexmit_timer_uS % 1000000) == 0) {
		self->_timersrc = g_timeout_add_seconds(rexmit_timer_uS/1000000, _fsprotocol_timeoutfun, self);
	}else{
		self->_timersrc = g_timeout_add(rexmit_timer_uS/1000, _fsprotocol_timeoutfun, self);
	}
	return self;
}

/// Finalize function for our @ref FsProtocol objects
FSTATIC void
_fsprotocol_finalize(AssimObj* aself)	///< FsProtocol object to finalize
{
	FsProtocol*	self = CASTTOCLASS(FsProtocol, aself);

	self->io->baseclass.unref(&self->io->baseclass); self->io = NULL;

	// Free up the unacked list
	g_list_free(self->unacked);		// No additional 'ref's were taken for this list
	self->unacked = NULL;

	// Free up the input pending list
	g_list_free(self->ipend);		// No additional 'ref's were taken for this list either
	self->ipend = NULL;

	// Free up our hash table of endpoints
	g_hash_table_destroy(self->endpoints);	// It will free the FsProtoElems contained therein
	self->endpoints = NULL;

	// Lastly free our base storage
	FREECLASSOBJ(self);
}

/// Finalize function suitable for GHashTables holding FsProtoElems as keys (and values)
FSTATIC void
_fsprotocol_protoelem_destroy(gpointer fsprotoelemthing)	///< FsProtoElem to destroy
{
	FsProtoElem *	self = (FsProtoElem*)fsprotoelemthing;
	self->endpoint->baseclass.unref(&self->endpoint->baseclass); self->endpoint = NULL;
	self->inq->baseclass.unref(&self->inq->baseclass); self->inq = NULL;
	memset(self, 0, sizeof(*self));
}

/// Equal-compare function for FsProtoElem structures suitable for GHashTables
FSTATIC gboolean
_fsprotocol_protoelem_equal(gconstpointer lhs	///< FsProtoElem left hand side to compare
,			    gconstpointer rhs)	///< FsProtoElem right hand side to compare
{
	const FsProtoElem *	lhselem = (const FsProtoElem*)lhs;
	const FsProtoElem *	rhselem = (const FsProtoElem*)rhs;

	return lhselem->endpoint->equal(lhselem->endpoint, rhselem->endpoint);


}

/// Hash function over FsProtoElem structures suitable for GHashTables
FSTATIC guint
_fsprotocol_protoelem_hash(gconstpointer fsprotoelemthing)	///< FsProtoElem to hash
{
	const FsProtoElem *	key = (const FsProtoElem*)fsprotoelemthing;
	// One could imagine doing a random circular rotate on the Queue Id before xoring it...
	// But this is probably good enough...
	return (key->endpoint->hash(key->endpoint) ^ key->_qid);
}

/// Return TRUE if there are any packets available to read
FSTATIC gboolean	
_fsprotocol_iready(FsProtocol* self)	///< Our object
{
	return NULL != self->ipend;
}

/// Read the next available packet from any of our sources
FSTATIC FrameSet*
_fsprotocol_read(FsProtocol* self	///< Our object - our very self!
,		 NetAddr** fromaddr)	///< Where return result is coming from
{
	GList*	list;	// List of all our FsQueues which have input

	// Loop over all the FSqueues which we think are ready to read...
	for (list=self->ipend; list != NULL; list=list->next) {
		FrameSet*	fs;
		SeqnoFrame*	seq;
		FsProtoElem*	fspe = (FsProtoElem*)list->data;
		FsQueue*	iq;
		if (NULL == fspe || (NULL == (iq = fspe->inq)) || (NULL == (fs = iq->qhead(iq)))) {
			g_warn_if_reached();
			continue;
		}
		if (!fspe->inq->isready) {
			g_warn_if_reached();
			// But trudge on anyway...
		}
		seq = fs->getseqno(fs);
		// Look to see if there is something ready to be read on this queue
		// There should be something ready to be read!
		if (seq == NULL || seq->_reqid == iq->_nextseqno) {
			FrameSet*	ret;
			gboolean	del_link = FALSE;
			if (seq != NULL) {
				iq->_nextseqno += 1;
			}
			iq->_destaddr->baseclass.ref(&iq->_destaddr->baseclass);
			*fromaddr = iq->_destaddr;
			ret = iq->deq(iq);
			// Now look and see if there will _still_ be something
			// ready to be read on this input queue.  If not, then
			// we should remove this FsProtoElem from the 'ipend' queue
			fs = iq->qhead(iq);
			if (fs == NULL) {
				// Our FsQueue is empty. Remove our FsProtoElem from the ipend queue
				del_link = TRUE;
			}else{
				// We can read the next packet IF:
				// it doesn't have a sequence number, OR it is the seqno we expect
				seq = fs->getseqno(fs);
				if (seq != NULL && seq->_reqid != iq->_nextseqno) {
					del_link = TRUE;
				}
			}
			if (del_link) {
				self->ipend = g_list_delete_link(self->ipend, list);
				fspe->inq->isready = FALSE;
			}
			TRYXMIT(fspe);
			return ret;
		}
		g_warn_if_reached();
		TRYXMIT(fspe);
	}
	return NULL;
}

/// Enqueue a received packet - handling ACKs (and NAKs) when they show up
FSTATIC void
_fsprotocol_receive(FsProtocol* self			///< Self pointer
,				NetAddr* fromaddr	///< Address that this FrameSet comes from
,				FrameSet* fs)		///< Frameset that was received
{
	FsProtoElem*	fspe = self->findbypkt(self, fromaddr, fs);
	SeqnoFrame*	seq = fs->getseqno(fs);
	gboolean is_acknack = (fs->fstype == FRAMESETTYPE_ACK || fs->fstype == FRAMESETTYPE_NACK);

	g_return_if_fail(fspe != NULL);
	
	if (is_acknack) {
		int ackcount;
		// Find the packet being ACKed, remove it from the output queue, and send
		// out the  next packet in that output queue...
		char *	fsout = fs->baseclass.toString(&fs->baseclass);
		DEBUGMSG1("%s: Received this FrameSet: [%s]", __FUNCTION__, fsout);
		g_free(fsout); fsout = NULL;
		g_return_if_fail(seq != NULL);
		ackcount = fspe->outq->ackthrough(fspe->outq, seq);
		// Update outstanding ack count by the number of packets ACKed
		fspe->outstanding_acks -= ackcount;
		if (fs->fstype == FRAMESETTYPE_ACK) {
			TRYXMIT(fspe);
			return;
		}
		// NACKs get treated like ACKs, except they're also
		// passed along to the application like a regular FrameSet
		/// @todo: NAKs ARE EVIL AND NEED TO BE REMOVED
	}
	// Queue up the received frameset
	DUMP2(__FUNCTION__, &fs->baseclass, "given to inq->inqsorted");
	if (!fspe->inq->inqsorted(fspe->inq, fs)) {
		DUMP2(__FUNCTION__, &fs->baseclass, "Failed to go into queue");
		// One reason for not queueing it is that we've already sent it
		// to our client If they have already ACKed it, then we will ACK
		// it again automatically - because our application won't be shown
		// this packet again - so they can't ACK it and our ACK might have
		// gotten lost, so we need to send it again...
		// 
		if (seq && fspe->lastacksent && seq->_sessionid == fspe->lastacksent->_sessionid
		&&	seq->compare(seq, fspe->lastacksent) < 0) {
			// We've already sent an ACK for this packet, send it again...
			FrameSet*	fs;
			SeqnoFrame*	ackseq;

			fs = frameset_new(FRAMESETTYPE_ACK);
			ackseq = seqnoframe_new_init(FRAMETYPE_REPLYID, seq->getreqid(seq), seq->getqid(seq));
			frameset_append_frame(fs, &ackseq->baseclass);
			ackseq->baseclass.baseclass.unref(&ackseq->baseclass.baseclass); ackseq = NULL;

			self->io->sendaframeset(self->io, fspe->endpoint, fs);
			fs->baseclass.unref(&fs->baseclass); ackseq = NULL;
		}
	}

	DEBUGMSG2("%s: isready: %d seq->_reqid:%d , fspe->inq->_nextseqno: "FMT_64BIT"d"
	,	__FUNCTION__, fspe->inq->isready, (seq ? (gint)seq->_reqid : -1), fspe->inq->_nextseqno);
	// If this queue wasn't shown as ready before - see if it is ready for reading now...
	if (!fspe->inq->isready) {
		if (seq == NULL || seq->_reqid == fspe->inq->_nextseqno) {
			// Now ready to read - put our fspe on the list of fspes with input pending
			self->ipend = g_list_prepend(self->ipend, fspe);
			fspe->inq->isready = TRUE;
		}
	}
	TRYXMIT(fspe);
}

/// Enqueue and send a single reliable frameset
FSTATIC gboolean
_fsprotocol_send1(FsProtocol* self	///< Our object
,		  FrameSet* fs		///< Frameset to send
,		  guint16   qid		///< Far endpoint queue id
,		  NetAddr* toaddr)	///< Where to send it
{
	FsProtoElem*	fspe = self->addconn(self, qid, toaddr);
	gboolean	ret;
	gboolean is_acknack = (fs->fstype == FRAMESETTYPE_ACK || fs->fstype == FRAMESETTYPE_NACK);
	ret =  fspe->outq->enq(fspe->outq, fs);
	if (!g_list_find(fspe->parent->unacked, fspe)) {
		///@todo: This might be slow if we send a lot of packets to an endpoint
		/// before getting a response, but that's not very likely.
		fspe->parent->unacked = g_list_prepend(fspe->parent->unacked, fspe);
	}
	if (is_acknack) {
		_fsprotocol_updateack(fspe, fs);
	}
	TRYXMIT(fspe);
	return ret;
}
/// Enqueue and send a list of reliable FrameSets (send all or none)
FSTATIC gboolean
_fsprotocol_send(FsProtocol* self	///< Our object
,		 GSList* framesets	///< Framesets to be sent
,		 guint16   qid		///< Far endpoint queue id
,		 NetAddr* toaddr)	///< Where to send them
{
	FsProtoElem*	fspe = self->addconn(self, qid, toaddr);
	gboolean	ret = TRUE;
	// Send them all -- or none of them...
	ret =  fspe->outq->hasqspace(fspe->outq, g_slist_length(framesets));
	if (ret) {
		GSList*	this;
		int	count = 0;
		// Loop over our framesets and send them ouit...
		for (this=framesets; this; this=this->next) {
			FrameSet* fs = CASTTOCLASS(FrameSet, this->data);
			gboolean is_acknack;
			g_return_val_if_fail(fs != NULL, FALSE);
			is_acknack = (fs->fstype == FRAMESETTYPE_ACK || fs->fstype == FRAMESETTYPE_NACK);
			DEBUGMSG1("%s: queueing up frameset %d of type %d", __FUNCTION__, count, fs->fstype);
			fspe->outq->enq(fspe->outq, fs);
			if (is_acknack) {
				_fsprotocol_updateack(fspe, fs);
			}
			++count;
		}
		// Add this fspe to the list of fspes with un-ACKed FrameSets - if not already on it
		if (!g_list_find(fspe->parent->unacked, fspe)) {
			fspe->parent->unacked = g_list_prepend(fspe->parent->unacked, fspe);
			// This might eventually need to be improved for efficiency...
		}
	}
	TRYXMIT(fspe);
	return ret;
}

/// Our role in life is to send any packets that need sending.
///
///	Find every packet which is eligible to be sent and send it out
///
///	What makes a packet eligible to be sent?
///
///	It hasn't been sent yet and there are not too many ACKs outstanding on this fspe
///		Too many means: fspe->outstanding_acks >= parent->window_size.
///
///	OR it is time to retransmit.
///
///	When do we perform re-transmission of unACKed packets?
///		When it's been longer than parent->rexmit_period seconds
///			since the last re-transmission of this fspe
///
///	What do we do when it's time to perform a re-transmission?
///		We retransmit only the oldest FrameSet awaiting an ACK.
//
FSTATIC void
_fsprotocol_xmitifwecan(FsProtoElem* fspe)	///< The FrameSet protocol element to operate on
{
	FsQueue*	outq = fspe->outq;
	FsProtocol*	parent = fspe->parent;
	SeqnoFrame*	lastseq = fspe->lastseqsent;
	GList*		qelem;
	NetIO*		io = parent->io;
	guint		orig_outstanding = fspe->outstanding_acks;
	gint64		now;

	// Look for any new packets that might have showed up to send
	// 	Check to see if we've exceeded our window size...
	if (fspe->outstanding_acks < parent->window_size) {
		// Nope.  Look for packets that we haven't yet sent.
		// This code is sub-optimal when congestion occurs and we have a larger
		// window size (i.e. when we have a number of un-ACKed packets)
		for (qelem=outq->_q->head; NULL != qelem; qelem=qelem->next) {
			FrameSet*	fs = CASTTOCLASS(FrameSet, qelem->data);
			SeqnoFrame*	seq = fs->getseqno(fs);
			if (NULL != lastseq && NULL != seq && seq->compare(seq, lastseq) <= 0) {
				// Not a new packet (we've sent it before)
				continue;
			}
			DUMP1(__FUNCTION__, &seq->baseclass.baseclass, " is frame being sent");
			io->sendaframeset(io, fspe->endpoint, fs);
			fspe->lastseqsent = seq;
			// lastseq = seq; -- is not necessary
			// This FrameSet will be removed from the queue when its ACK arrives...
			++fspe->outstanding_acks;
			if (fspe->outstanding_acks >= parent->window_size) {
				break;
			}
		}
	}
	now = g_get_monotonic_time();

	if (fspe->nextrexmit == 0 && fspe->outstanding_acks > 0) {
		// Next retransmission time not yet set...
		fspe->nextrexmit = now + parent->rexmit_interval;
	} else if (fspe->nextrexmit != 0 && now > fspe->nextrexmit) {
		FrameSet*	fs = outq->qhead(outq);
		// It's time to retransmit something.  Hurray!
		/// @todo: SHOULD THIS BE IN ITS OWN FUNCTION?
		if (NULL != fs) {
			// Update next retransmission time...
			fspe->nextrexmit = now + parent->rexmit_interval;
			DUMP1(__FUNCTION__, &fs->baseclass, " is frameset being REsent");
			io->sendaframeset(io, fspe->endpoint, fs);
		}else{
			g_warn_if_reached();
			fspe->nextrexmit = 0;
		}
	}


	// Make sure we remember to check this periodicially for retransmits...
	if (orig_outstanding == 0 && fspe->outstanding_acks > 0) {
		// Put 'fspe' on the list of fspe's with unacked packets
		fspe->parent->unacked = g_list_prepend(fspe->parent->unacked, fspe);
		// See comment in the _send function regarding eventual efficiency concerns
	}
}

///< Flush all queues that connect to the given address - happens when an endpoint dies
FSTATIC void
_fsprotocol_flushall(FsProtocol* self	///< The FsProtocol object we're operating on
,		     const NetAddr* addr///< The address we should flush to/from
,		     enum ioflush op)	///< What kind of flush to perform?
{
	GHashTableIter	iter;
	FsProtoElem*	fspe;
	/// @todo If we actually _have_ a million servers, this will have to be looked at again -
	/// We may eventually need to create a list of queues per server -- or this will be horribly slow

	g_hash_table_iter_init(&iter, self->endpoints);
	while (g_hash_table_iter_next(&iter, (gpointer*)&fspe, NULL)) {
		if (!addr->equal(addr, fspe->endpoint)) {
			continue;
		}
		if (op == FsProtoFLUSHIN || op == FsProtoFLUSHBOTH) {
			fspe->inq->flush(fspe->inq);
		}
		if (op == FsProtoFLUSHOUT || op == FsProtoFLUSHBOTH) {
			fspe->outq->flush(fspe->outq);
		}
	}
}
/// Retransmit timer function...
FSTATIC gboolean
_fsprotocol_timeoutfun(gpointer userdata)
{
	FsProtocol*	self = CASTTOCLASS(FsProtocol, userdata);
	GList*		pending;
	GList*		next;

	g_return_val_if_fail(self != NULL, FALSE);

	DEBUGMSG2("%s: checking for timeouts: unacked = %p", __FUNCTION__, self->unacked);
	for (pending = self->unacked; NULL != pending; pending=next) {
		FsProtoElem*	fspe = (FsProtoElem*)pending->data;
		next = pending->next;
		_fsprotocol_xmitifwecan(fspe);
	}
	return TRUE;
}
///@}
