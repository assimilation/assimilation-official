/**
 * @file
 * @brief Implements the FsQueue object
 * @details @ref FsQueue objects provide queueing of @ref FrameSet objects for performing
 * reliable @ref FrameSet transmission.
 * An @ref FsQueue object queues up @ref FrameSet objects to a single destination.
 * From our perspective, a destination is an IP address plus a Queue ID.
 * This class is related to @ref FrameSet objects (obviously) and also to @ref SeqnoFrame objects as well.
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
 */

#ifndef _FSQUEUE_H
#define _FSQUEUE_H
#include <assimobj.h>
#include <frameset.h>
#include <seqnoframe.h>
#include <netaddr.h>

///@{
/// @ingroup FsQueue
typedef struct _FsQueue FsQueue;

/// This is an @ref FsQueue object - designed for queueuing up @ref FrameSet objects for transmission.
/// It is a subclass of the @ref AssimObj.
/// and is managed by our @ref ProjectClass system.
struct _FsQueue {
	AssimObj	baseclass;				///< base @ref AssimObj object
	guint64		_nextseqno;				///< Next sequence number
	guint		_maxqlen;				///< Maximum queue length
	guint		_curqlen;				///< Current queue length
	GQueue*		_q;					///< @ref FrameSet queue
	NetAddr*	_destaddr;				///< Far endpoint address
	guint16		_qid;					///< Far endpoint queue id
	gboolean	isready;				///< TRUE when ready for I or O (depending)
	gboolean	(*enq)(FsQueue* self, FrameSet* fs);	///< Enqueue an outgoing FrameSet - adding seqno
	gboolean	(*inqsorted)(FsQueue*, FrameSet* fs);	///< Enqueue an incoming FrameSet - sorted by
								///< by sequence # - no dups allowed
	FrameSet*	(*qhead)(FsQueue* self);		///< return packet at head of queue
	FrameSet*	(*deq)(FsQueue* self);			///< return and remove head packet
	guint		(*ackthrough)(FsQueue* self, SeqnoFrame*);///< ACK packets through given seqno
	void		(*flush)(FsQueue* self);		///< flush all FrameSet in the queue
	void		(*flush1)(FsQueue* self);		///< flush head FrameSet in the queue
	guint		(*qlen)(FsQueue* self);			///< return current queue length
	void		(*setmaxqlen)(FsQueue* self, guint max);///< set maximum queue length
	guint		(*getmaxqlen)(FsQueue* self);		///< return max q length
	gboolean	(*hasqspace1)(FsQueue* self);		///< TRUE if space for one more FrameSet
	gboolean	(*hasqspace)(FsQueue* self, guint);	///< TRUE if space for desired packets available
};
WINEXPORT FsQueue* fsqueue_new(guint objsize, NetAddr* dest, guint16 qid);
#define	DEFAULT_FSQMAX	0	///< Default to unlimited queue length

///@}

#endif /* _FSQUEUE_H */
