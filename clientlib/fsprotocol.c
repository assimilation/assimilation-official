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

FSTATIC guint		_fsprotocol_protoelem_hash(gconstpointer fsprotoelemthing);
FSTATIC void		_fsprotocol_protoelem_destroy(gpointer fsprotoelemthing);
FSTATIC gboolean	_fsprotocol_protoelem_equal(gconstpointer lhs, gconstpointer rhs);

FSTATIC void		_fsprotocol_finalize(AssimObj* aself);
FSTATIC FsProtoElem*	_fsprotocol_addconn(FsProtocol*self, guint16 qid, NetAddr* destaddr);
FSTATIC FsProtoElem*	_fsprotocol_find(FsProtocol* self, guint16 qid, NetAddr* destaddr);
FSTATIC FsProtoElem*	_fsprotocol_findbypkt(FsProtocol* self, NetAddr*, FrameSet*);
FSTATIC gboolean	_fsprotocol_iready(FsProtocol*);
FSTATIC FrameSet*	_fsprotocol_read(FsProtocol*, NetAddr**);
FSTATIC void		_fsprotocol_receive(FsProtocol*, NetAddr*, FrameSet*);
FSTATIC gboolean	_fsprotocol_send1(FsProtocol*, FrameSet*, guint16 qid, NetAddr*);
FSTATIC gboolean	_fsprotocol_send(FsProtocol*, GSList*, guint16 qid, NetAddr*);
FSTATIC void		_fsprotocol_xmitifwecan(FsProtoElem*);
FSTATIC void		_fsprotocol_flushall(FsProtocol* self, NetAddr* addr, enum ioflush op);
FSTATIC void		_fsprotocol_flush1(FsProtocol* self, NetAddr* addr, enum ioflush op);

DEBUGDECLARATIONS
/// @defgroup FsProtocol FsProtocol class
///@{
/// @ingroup C_Classes

#define		TRYXMIT(fspe)	{_fsprotocol_xmitifwecan(fspe);}

/// Locate the FsProtoElem structure that corresponds to this (qid, destaddr) pair
FSTATIC FsProtoElem*
_fsprotocol_find(FsProtocol*self	///< typical FsProtocol 'self' object
,		 guint16 qid		///< Queue id of far endpoint
,		 NetAddr* destaddr)	///< destination address
{
	FsProtoElem	elem;
	elem.endpoint	= destaddr;
	elem._qid	= qid;
	return (FsProtoElem*)g_hash_table_lookup(self->endpoints, &elem);
}

/// Find the FsProtoElem that goes with the given packet.  It can have a sequence number - or not.
FSTATIC FsProtoElem*
_fsprotocol_findbypkt(FsProtocol* self	///< The FsProtocol object we're operating on
,		      NetAddr* addr	///< The Network address we're looking for
,		      FrameSet* fs)	///< The FrameSet whose queue id we'll use in looking for it
{
	SeqnoFrame*	seq = fs->getseqno(fs);
	return self->find(self, (seq == NULL ? DEFAULT_FSP_QID : seq->getqid(seq)), addr);
}

/// Add and return a FsProtoElem connection to our collection of connections...
FSTATIC FsProtoElem*
_fsprotocol_addconn(FsProtocol*self	///< typical FsProtocol 'self' object
,		    guint16 qid		///< Queue id for the connection
,		    NetAddr* destaddr)	///< destination address
{
	FsProtoElem*	ret;
	if ((ret = self->find(self, qid, destaddr))) {
		return ret;
	}
	ret = MALLOCTYPE(FsProtoElem);
	if (ret) {
		destaddr->baseclass.ref(&destaddr->baseclass);
		ret->endpoint = destaddr;
		ret->outq = fsqueue_new(0, destaddr, qid);
		ret->parent = self;
		ret->_qid = qid;
		g_hash_table_insert(self->endpoints, ret, ret);
	}
	return ret;
}

/// Construct an FsQueue object
WINEXPORT FsProtocol*
fsprotocol_new(guint objsize	///< Size of object to be constructed
	,      NetIO* io)	///< Pointer to NetIO for us to reference
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
	self->io =		io;
	io->baseclass.ref(&io->baseclass);
	/// The key and the data are in fact the same object
	/// Don't want to free the object twice ;-) - hence the final NULL argument
	self->endpoints = g_hash_table_new_full(_fsprotocol_protoelem_hash,_fsprotocol_protoelem_equal
        ,		_fsprotocol_protoelem_destroy, NULL);
	self->unacked = NULL;
	self->ipend = NULL;
	return self;
}
/// Finalize function for our @ref FsProtocol objects
FSTATIC void
_fsprotocol_finalize(AssimObj* aself)	///< FsProtocol object to finalize
{
	FsProtocol*	self = CASTTOCLASS(FsProtocol, aself);
	self->io->baseclass.ref(&self->io->baseclass); self->io = NULL;
	g_list_free(self->unacked);		// No additional 'ref's were taken for this list
	self->unacked = NULL;
	g_list_free(self->ipend);		// No additional 'ref's were taken for this list either
	self->ipend = NULL;
	g_hash_table_destroy(self->endpoints);	// It will free the FsProtoElems contained therein
	self->endpoints = NULL;
	FREECLASSOBJ(self);
}
/// Finalize function suitable for GHashTables holding FsProtoElems
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
	/// FIXME - need to take the queue id into account
	return key->endpoint->hash(key->endpoint);
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
	GList*	list;
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
			// We should remove this FsProtoElem from the 'ipend' queue
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



/// Enqueue a received packet - handling ACKs when they show up
FSTATIC void
_fsprotocol_receive(FsProtocol* self, NetAddr* fromaddr, FrameSet* fs)
{
	FsProtoElem*	fspe = self->findbypkt(self, fromaddr, fs);
	SeqnoFrame*	seq = fs->getseqno(fs);
	gboolean is_acknack = (fs->fstype == FRAMESETTYPE_ACK || fs->fstype == FRAMESETTYPE_NACK);

	g_return_if_fail(fspe != NULL);
	if (is_acknack) {
		// Find the packet being ACKed, remove it from the output queue, and send
		// out the  next packet in that output queue...
		g_return_if_fail(seq != NULL);
		fspe->outq->ackthrough(fspe->outq, seq);
		if (fs->fstype == FRAMESETTYPE_ACK) {
			TRYXMIT(fspe);
			return;
		}
		// NACKs get treated like ACKs, except they're also passed along to the application
		// like a regular FrameSet
	}
	// Queue up frameset, and possibly add to the list of fspe's with input ready to read
	/// FIXME - need to look at the length of the queue of incoming packets
	fspe->inq->inqsorted(fspe->inq, fs);
	if (!fspe->inq->isready) {
		if (seq == NULL || seq->_reqid == fspe->inq->_nextseqno) {
			fspe->parent->unacked = g_list_prepend(self->ipend, fspe);
			fspe->inq->isready = TRUE;
		}
	}
	TRYXMIT(fspe);
}

/// Enqueue and reliably send a single frameset
FSTATIC gboolean
_fsprotocol_send1(FsProtocol* self	///< Our object
,		  FrameSet* frameset	///< Frameset to send
,		  guint16   qid		///< Far endpoint queue id
,		  NetAddr* toaddr)	///< Where to send it
{
	FsProtoElem*	fspe = self->addconn(self, qid, toaddr);
	gboolean	ret;
	ret =  fspe->outq->enq(fspe->outq, frameset);
	if (!g_list_find(fspe->parent->unacked, fspe)) {
		fspe->parent->unacked = g_list_prepend(fspe->parent->unacked, fspe);
	}
	TRYXMIT(fspe);
	return ret;
}
/// Enqueue and reliably send a list of FrameSets 
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
		for (this=framesets; this; this=this->next) {
			fspe->outq->enq(fspe->outq, CASTTOCLASS(FrameSet, this->data));
		}
		if (!g_list_find(fspe->parent->unacked, fspe)) {
			fspe->parent->unacked = g_list_prepend(fspe->parent->unacked, fspe);
		}
	}
	TRYXMIT(fspe);
	return ret;
}
/// Our role in life is to send any packets that need sending.
FSTATIC void
_fsprotocol_xmitifwecan(FsProtoElem* fspe)	///< The FrameSet protocol element to operate on
{
	FsQueue*	outq = fspe->outq;
	FrameSet*	fs;
	(void)fspe;
	// At this point we _ought_ to have at least one packet to transmit...
	while (NULL != (fs = outq->qhead(outq))) {
		SeqnoFrame*	seq = fs->getseqno(fs);
		if (seq == NULL || seq->_reqid <= outq->_nextseqno) {
			NetIO*	io = fspe->parent->io;
			io->sendaframeset(io, fspe->endpoint, fs);
			outq->flush1(outq);
		}else{
			break;
		}
	}
	if (fs != NULL) {
		// No more packets to send...
		fspe->parent->unacked = g_list_remove(fspe->parent->unacked, fspe);
	}else{
		// Ensure that this 'fspe' is on the list of fspe's with unacked packets
		if (!g_list_find(fspe->parent->unacked, fspe)) {
			fspe->parent->unacked = g_list_prepend(fspe->parent->unacked, fspe);
		}
	}
}
///< Flush all queues that connect to the given address
FSTATIC void
_fsprotocol_flushall(FsProtocol* self	///< The FsProtocol object we're operating on
,		     NetAddr* addr	///< The address we should flush to/from
,		     enum ioflush op)	///< What kind of flush to perform?
{
	GHashTableIter	iter;
	FsProtoElem*	fspe;
	/// @TODO If we actually _have_ a million servers, this will have to be looked at again -
	/// We will have to have a list of queues per server -- or this will be horribly slow

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
///@}
