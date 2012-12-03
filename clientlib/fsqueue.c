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

/// @defgroup FsQueue FsQueue class
///@{
/// @ingroup C_Classes

/// Enqueue a @ref FrameSet onto an @ref FsQueue
FSTATIC gboolean
_fsqueue_enq(FsQueue* self, FrameSet* fs)
{
	SeqnoFrame*	seqno;
	g_return_val_if_fail(fs->_seqframe == NULL, FALSE);
	g_return_val_if_fail(self->_curqlen == 0 || self->_curqlen < self->_maxqlen, FALSE);
	seqno = seqnoframe_new_init(FRAMETYPE_REQID, self->_nextseqno, self->_qid);

	frameset_prepend_frame(fs, &seqno->baseclass);
	g_queue_push_tail(self->_q, fs);

	// Now do all the paperwork :-D
	++self->_nextseqno;
	++self->_curqlen;
	fs->baseclass.ref(&fs->baseclass);
	seqno->baseclass.baseclass.unref(&seqno->baseclass.baseclass);
	return TRUE;
}

/// Return the @ref FrameSet from the head of the @ref FsQueue
FSTATIC FrameSet*
_fsqueue_qhead(FsQueue* self)
{
	gpointer	ret = g_queue_peek_head(self->_q);
	return ret ? CASTTOCLASS(FrameSet, ret) : NULL;
}

/// Return the @ref FrameSet from the head of the queue - and remove it from the queue
FSTATIC FrameSet*
_fsqueue_deq(FsQueue* self)
{
	gpointer	ret = g_queue_pop_head(self->_q);
	--self->_curqlen;
	return ret ? CASTTOCLASS(FrameSet, ret) : NULL;
}

/// Enqueue a @ref FrameSet onto an @ref FsQueue - sorted by sequence number - NO dups allowed
/// This method is used for queues used for received packets.
FSTATIC gboolean
_fsqueue_inqsorted(FsQueue* self, FrameSet* fs)
{
	GQueue*		Q = self->_q;
	GList*		this = Q->head;
	SeqnoFrame*	seqno;

	seqno = fs->_seqframe ? fs->_seqframe : fs->getseqno(fs);

	// Frames without sequence number go to the head of the queue
	if (seqno == NULL) {
		g_queue_push_head(Q, fs);
		return TRUE;
	}

	g_return_val_if_fail(self->_curqlen == 0 || self->_curqlen < self->_maxqlen, FALSE);

	for (this = Q->head; this; this=this->next)  {
		FrameSet*	tfs = CASTTOCLASS(FrameSet, this->data);
		SeqnoFrame*	thisseq = tfs->getseqno(tfs);
		int		diff = seqno->compare(seqno, thisseq);
		if (diff < 0) {
			g_queue_insert_before(Q, this, fs);
			return TRUE;
		}else if (diff == 0) {
			// Dup - throw it away...
			fs->baseclass.unref(&fs->baseclass); fs = NULL;
			return TRUE;
		}
	}
	// Either the list is empty, or this belongs after the last list element
	// Regardless of which is true, we can call g_queue_push_tail...
	g_queue_push_tail(Q, fs);
	return TRUE;
}

/// Acknowledge and flush all framesets up through and including the given sequence number
FSTATIC guint
_fsqueue_ackthrough(FsQueue* self, SeqnoFrame*seq)
{
	FrameSet*	fs;
	guint64		reqid = seq->getreqid(seq);
	guint		count = 0;
	
	
	while((fs = self->qhead(self)) != NULL) {
		SeqnoFrame*	fseq = fs->getseqno(fs);
		if (fseq != NULL && fseq->getreqid(fseq) > reqid) {
			break;
		}
		self->flush1(self);
		count += 1;
	}
	return count;
}

/// Flush <b>all</b> framesets from the queue (if any).
FSTATIC void
_fsqueue_flush(FsQueue* self)
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
FSTATIC void
_fsqueue_flush1(FsQueue* self)
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
_fsqueue_qlen(FsQueue* self)
{
	return self->_curqlen;
}

/// Set the maximum number of queue elements
FSTATIC void
_fsqueue_setmaxqlen(FsQueue* self, guint max)
{
	self->_maxqlen = max;
}

/// Return the maximum number of queue elements
FSTATIC guint
_fsqueue_getmaxqlen(FsQueue* self)
{
	return self->_maxqlen;
}

/// Does this queue have room for one more element?
FSTATIC gboolean
_fsqueue_hasqspace1(FsQueue* self)
{
	return self->_maxqlen > g_queue_get_length(self->_q);
}

/// Does this queue have room for 'desired' more elements?
FSTATIC gboolean
_fsqueue_hasqspace(FsQueue* self, guint desired)
{
	return self->_maxqlen + desired >= g_queue_get_length(self->_q);

}

/// Construct an FsQueue object
WINEXPORT FsQueue*
fsqueue_new(guint objsize, NetAddr* dest, guint16 qid)
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
	self->enq =		_fsqueue_enq;
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
	self->_q =		g_queue_new();
	self->_qid =		qid;
	self->_maxqlen =	DEFAULT_FSQMAX;
	self->_curqlen =	0;
	self->_destaddr =	dest;
	self->_nextseqno =	1;
	dest->baseclass.ref(&dest->baseclass);
	return self;
}
///@}
