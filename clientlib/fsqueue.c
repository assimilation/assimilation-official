/**
 * @file
 * @brief FrameSet queueing class
 * @details This includes code to implement FrameSet queueing for reliable communication
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
 *
 */
#include <projectcommon.h>
#include <fsqueue.h>
#include <frameset.h>
#include <frametypes.h>



DEBUGDECLARATIONS

FSTATIC void		_fsqueue_finalize(AssimObj* aself);
FSTATIC gboolean	_fsqueue_enq(FsQueue* self, FrameSet* fs);
FSTATIC gboolean	_fsqueue_inqsorted(FsQueue* self, FrameSet* fs);
FSTATIC FrameSet*	_fsqueue_qhead(FsQueue* self);
FSTATIC FrameSet*	_fsqueue_deq(FsQueue* self);
FSTATIC guint		_fsqueue_ackthrough(FsQueue* self, SeqnoFrame*);
FSTATIC void		_fsqueue_flush(FsQueue* self);
FSTATIC void		_fsqueue_flush1(FsQueue* self);
FSTATIC guint		_fsqueue_qlen(FsQueue* self);
FSTATIC void		_fsqueue_setmaxqlen(FsQueue* self, guint max);
FSTATIC guint		_fsqueue_getmaxqlen(FsQueue* self);
FSTATIC gboolean	_fsqueue_hasqspace1(FsQueue* self);
FSTATIC gboolean	_fsqueue_hasqspace(FsQueue* self, guint);
FSTATIC char*		_fsqueue_toString(gconstpointer);

/// @defgroup FsQueue FsQueue class
///@{
/// @ingroup C_Classes

/// Enqueue a @ref FrameSet onto an @ref FsQueue - exclusively for output queues - adds sequence number
FSTATIC gboolean
_fsqueue_enq(FsQueue* self	///< us - the FsQueue we're operating on
,	     FrameSet* fs)	///< The @ref FrameSet to enqueue into our queue - must NOT have sequence#
{
	SeqnoFrame*	seqno;
	// This FrameSet shouldn't have a sequence number frame yet...
	g_return_val_if_fail(fs->_seqframe == NULL, FALSE);
	g_return_val_if_fail(self->_maxqlen == 0 || self->_curqlen < self->_maxqlen, FALSE);
	seqno = seqnoframe_new_init(FRAMETYPE_REQID, self->_nextseqno, self->_qid);
	g_return_val_if_fail(seqno != NULL, FALSE);
	++self->_nextseqno;
	DEBUGMSG2("%s: next sequence number for %p is "FMT_64BIT"d", __FUNCTION__, self, self->_nextseqno);

	// Of course, the session id on outbound packets should _never_ change
	// But an uninitialized FsQueue session id is zero
	// So, this test could be more strict
	if (seqno->_sessionid < self->_sessionid) {
		seqno->baseclass.baseclass.unref(&seqno->baseclass.baseclass); seqno = NULL;
		g_return_val_if_reached(FALSE);
	}
	self->_sessionid = seqno->_sessionid;

	// Put the frame at the beginning of the frameset
	frameset_prepend_frame(fs, &seqno->baseclass);
	// And put this FrameSet at the end of the queue
	g_queue_push_tail(self->_q, fs);
	++self->_curqlen;

	// Now do all the paperwork :-D
	// We need for the FrameSet to be kept around for potentially a long time...
	fs->baseclass.ref(&fs->baseclass);
	// But we're done with the seqno frame (prepending it to the frameset bumped the ref count)
	seqno->baseclass.baseclass.unref(&seqno->baseclass.baseclass);
	DUMP2(__FUNCTION__, &self->baseclass, "");
	return TRUE;
}

/// Return the @ref FrameSet from the head of the @ref FsQueue
FSTATIC FrameSet*
_fsqueue_qhead(FsQueue* self)		///< The @ref FsQueue object we're operating on
{
	gpointer	ret = g_queue_peek_head(self->_q);
	return ret ? CASTTOCLASS(FrameSet, ret) : NULL;
}

/// Return the @ref FrameSet from the head of the queue - and remove it from the queue
FSTATIC FrameSet*
_fsqueue_deq(FsQueue* self)		///< The @ref FsQueue object we're operating on
{
	gpointer	ret = g_queue_pop_head(self->_q);
	--self->_curqlen;
	return ret ? CASTTOCLASS(FrameSet, ret) : NULL;
}

/// Enqueue a @ref FrameSet onto an @ref FsQueue - sorted by sequence number - NO dups allowed
/// This method is used ONLY for received packets or it could be used for <i>unsequenced</i> output packets.
FSTATIC gboolean
_fsqueue_inqsorted(FsQueue* self		///< The @ref FsQueue object we're operating on
,		   FrameSet* fs)		///< The @ref FrameSet object to enqueue
{
	GQueue*		Q = self->_q;
	GList*		this;
	SeqnoFrame*	seqno;

	seqno = fs->_seqframe ? fs->_seqframe : fs->getseqno(fs);

	if (seqno && seqno->_sessionid < self->_sessionid) {
		// Replay attack?
		g_warning("Possible replay attack? Current session id: %d, incoming session id: %d"
		,	self->_sessionid, seqno->_sessionid);
		return FALSE;
	}
	if (seqno && seqno->_reqid < self->_nextseqno) {
		// We've already delivered this packet to our customers...
		// We need to see if we've already sent the ACK for this packet.
		// If so, we need to ACK it again...
		DUMP2(__FUNCTION__, &fs->baseclass, " Previously delivered to client");
		DEBUGMSG2("%s: reason: sequence number is "FMT_64BIT"d but next is "FMT_64BIT"d"
		,	__FUNCTION__, seqno->_reqid, self->_nextseqno);
		return FALSE;
	}

	// Probably this shouldn't really log an error - but I'd like to see it happen
	// if it does -- unless of course, it turns out to happen a lot (unlikely...)
	g_return_val_if_fail(self->_maxqlen == 0 || self->_curqlen < self->_maxqlen, FALSE);

	// Frames without sequence numbers go to the head of the queue
	if (seqno == NULL) {
		g_queue_push_head(Q, fs);
		fs->baseclass.ref(&fs->baseclass);
		return TRUE;
	}

	for (this = Q->head; this; this=this->next)  {
		FrameSet*	tfs = CASTTOCLASS(FrameSet, this->data);
		SeqnoFrame*	thisseq = tfs->getseqno(tfs);
		int		diff = seqno->compare(seqno, thisseq);
		if (diff < 0) {
			g_queue_insert_before(Q, this, fs);
			fs->baseclass.ref(&fs->baseclass);
			return TRUE;
		}else if (diff == 0) {
			// Dup - don't keep it...
			return TRUE;
		}
	}
	// Either the list is empty, or this belongs after the last list element
	// Regardless of which is true, we can call g_queue_push_tail...
	fs->baseclass.ref(&fs->baseclass);
	g_queue_push_tail(Q, fs);
	DUMP2(__FUNCTION__, &self->baseclass, "");
	return TRUE;
}

/// Acknowledge and flush all framesets up through and including the given sequence number
/// This is used exclusively for output queues - and is the result of the application on
/// the other end sending us an ACK packet.
/// @return number of packets ACKed by this incoming ACK packet.
FSTATIC guint
_fsqueue_ackthrough(FsQueue* self		///< The output @ref FsQueue object we're operating on
,		    SeqnoFrame*seq)		///< The sequence number to ACK through
{
	FrameSet*	fs;
	guint64		reqid;
	guint		count = 0;

	g_return_val_if_fail(seq != NULL, 0);
	DEBUGMSG1("%s: ACKing through (%d:%d:"FMT_64BIT"d)", __FUNCTION__
	,	seq->getsessionid(seq), seq->getqid(seq), seq->getreqid(seq));
	if (seq->getsessionid(seq) != self->_sessionid) {
		g_warning("%s: Incoming ACK packet has invalid session id [%d instead of %d]"
		" (ACK ignored)."
		,	__FUNCTION__, seq->getsessionid(seq), self->_sessionid);
		return 0;
	}
		
	if (seq->getreqid(seq) >= self->_nextseqno) {
		g_warning("%s: Incoming ACK packet sequence number "FMT_64BIT"d is >= "
		FMT_64BIT"d (ACK Ignored)."
		,	__FUNCTION__, seq->getreqid(seq), self->_nextseqno);
		return 0;
	}
	reqid = seq->getreqid(seq);
	
	// The packets are in the queue in order of ascending sequence number
	while((fs = self->qhead(self)) != NULL) {
		SeqnoFrame*	fseq = fs->getseqno(fs);
		if (fseq != NULL && fseq->getreqid(fseq) > reqid) {
			break;
		}
		self->flush1(self);
		count += 1;
	}
	DEBUGMSG1("%s: returning %d - remaining (output) queue length is %d"
	,	__FUNCTION__, count,	g_queue_get_length(self->_q));
	return count;
}

/// Flush <b>all</b> framesets from the queue (if any).
/// @todo: This is basically a protocol reset - what effect should this have upon
/// sequence numbers and generation numbers (if any)?
/// Normally this is used if we think the machine has died...
FSTATIC void
_fsqueue_flush(FsQueue* self)		///< The @ref FsQueue object we're operating on
{
	gpointer	qelem;
	while (NULL != (qelem = g_queue_pop_head(self->_q))) {
		FrameSet *	fs = CASTTOCLASS(FrameSet, qelem);
		fs->baseclass.unref(&fs->baseclass);
		fs = NULL;
	}
	self->_curqlen = 0;
}

/// Flush only the first frameset from the queue (if any).
/// Could be used on either input or output queues.
FSTATIC void
_fsqueue_flush1(FsQueue* self)		///< The @ref FsQueue object we're operating on
{
	gpointer	qelem = g_queue_pop_head(self->_q);
	if (qelem) {
		FrameSet *	fs = CASTTOCLASS(FrameSet, qelem);
		fs->baseclass.unref(&fs->baseclass);
		fs = NULL;
		--self->_curqlen;
	}
}

/// Return the current length of this queue
FSTATIC guint
_fsqueue_qlen(FsQueue* self)		///< The @ref FsQueue object we're operating on
{
	return self->_curqlen;
}

/// Set the maximum number of queue elements
FSTATIC void
_fsqueue_setmaxqlen(FsQueue* self		///< The @ref FsQueue object we're operating on
,		    guint max)			///< The new maximum queue length
{
	self->_maxqlen = max;
}

/// Return the maximum number of queue elements
FSTATIC guint
_fsqueue_getmaxqlen(FsQueue* self)		///< The @ref FsQueue object we're operating on
{
	return self->_maxqlen;
}

/// Does this queue have room for one more element?
FSTATIC gboolean
_fsqueue_hasqspace1(FsQueue* self)		///< The @ref FsQueue object we're operating on
{
	return self->_maxqlen > g_queue_get_length(self->_q);
}

/// Does this queue have room for 'desired' more elements?
FSTATIC gboolean
_fsqueue_hasqspace(FsQueue* self		///< The @ref FsQueue object we're operating on
,		   guint desired)		///< The number of queue elements we're hoping for
{
	return (self->_maxqlen + desired) >= g_queue_get_length(self->_q);

}

/// Construct an FsQueue object - from a (far endpoint address, Queue Id) pair
WINEXPORT FsQueue*
fsqueue_new(guint objsize		///< Size of the FsQueue object we should create
,	    NetAddr* dest		///< Destination address for this FsQueue
,	    guint16 qid)		///< Associated queue ID for this FsQueue
{
	FsQueue*	self;
	BINDDEBUG(FsQueue);
	if (objsize < sizeof(FsQueue)) {
		objsize = sizeof(FsQueue);
	}
	self = NEWSUBCLASS(FsQueue, assimobj_new(objsize));
	if (!self) {
		return NULL;
	}
	// Initialize member functions
	self->baseclass._finalize=_fsqueue_finalize;
	self->baseclass.toString=_fsqueue_toString;
	self->enq =		_fsqueue_enq;
	self->inqsorted =	_fsqueue_inqsorted;
	self->qhead =		_fsqueue_qhead;
	self->deq =		_fsqueue_deq;
	self->ackthrough =	_fsqueue_ackthrough;
	self->flush =		_fsqueue_flush;
	self->flush1 =		_fsqueue_flush1;
	self->qlen =		_fsqueue_qlen;
	self->setmaxqlen =	_fsqueue_setmaxqlen;
	self->getmaxqlen =	_fsqueue_getmaxqlen;
	self->hasqspace1 =	_fsqueue_hasqspace1;
	self->hasqspace =	_fsqueue_hasqspace;

	// Initialize data members
	self->_q =		g_queue_new();
	self->_qid =		qid;
	self->_maxqlen =	DEFAULT_FSQMAX;
	self->_curqlen =	0;
	self->_nextseqno =	1;
	self->_sessionid =	0;
	self->_destaddr =	dest;	dest->baseclass.ref(&dest->baseclass);
	return self;
}
/// Finalize routine for our @ref FsQueue objects
FSTATIC void
_fsqueue_finalize(AssimObj* aself)		///< The @ref FsQueue object we're operating on
{
	FsQueue*	self = CASTTOCLASS(FsQueue, aself);

	// Let our 'destaddr' object go...
	self->_destaddr->baseclass.unref(&self->_destaddr->baseclass); self->_destaddr = NULL;

	// Now flush (free up) any framesets that are still hanging around...
	self->flush(self);

	// And free up the queue itself
	g_queue_free(self->_q);		self->_q = NULL;
	// And finally, free up our direct storage
	FREECLASSOBJ(self);
}

FSTATIC char*
_fsqueue_toString(gconstpointer vself)
{
	GString*	fsqret = NULL;
	char*		ret = NULL;
	char*		tmp = NULL;
	const FsQueue*	self = CASTTOCONSTCLASS(FsQueue, vself);
	GList*		curfs;
	const char *	comma = "";

	g_return_val_if_fail(self != NULL, NULL);
	fsqret = g_string_new("");
	
	tmp = self->_destaddr->baseclass.toString(&self->_destaddr->baseclass);
	g_string_append_printf(fsqret, "FsQueue(dest=%s//q=%d, [", tmp, self->_qid);
	g_free(tmp); tmp=NULL;

	for (curfs=self->_q->head; curfs != NULL; curfs = g_list_next(curfs)) {
		FrameSet*	fs = CASTTOCLASS(FrameSet, curfs->data);
		
		tmp = fs->baseclass.toString(&fs->baseclass);
		g_string_append_printf(fsqret, "%s%s", comma, tmp);
		g_free(tmp); tmp = NULL;
		comma=", ";
	}
	g_string_append_printf(fsqret, "])");
	ret = fsqret->str;
	g_string_free(fsqret, FALSE);
	return ret;
	
	
}
///@}
