/**
 * @file
 * @brief Implements the SeqnoFrame class
 * @details @ref SeqnoFrame "SeqnoFrame"s are used to provide sequence numbers for
 * reliable @ref FrameSet transmission.
 * Each @ref SeqnoFrame consists of four components:
 *  - A Session ID (32 bits)
 *  - A Queue ID (16 bits)
 *  - A FrameSet request ID (48 bits)
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

#ifndef _SEQNOFRAME_H
#define _SEQNOFRAME_H
#include <frame.h>

///@{
/// @ingroup SeqnoFrame
typedef struct _SeqnoFrame SeqnoFrame;

/// This is an @ref SeqnoFrame <b>TLV</b> (type, length, value) frame.
/// It is a subclass of the @ref Frame.
/// and is managed by our @ref ProjectClass system.
/// Every transmitted @ref SeqnoFrame uses the current session id.
/// @note This class does not use the 'value' field in the
/// base class, and does not implement the setvalue() member function.
struct _SeqnoFrame {
	Frame	baseclass;					///< base @ref Frame object
	guint64	(*getreqid)(SeqnoFrame* self);			///< get value of request id 
	void	(*setreqid)(SeqnoFrame* self, guint64 value);	///< set the request id
	guint16	(*getqid)(SeqnoFrame* self);			///< get value of queue id 
	void	(*setqid)(SeqnoFrame* self, guint16 value);	///< set the queue id
	guint32	(*getsessionid)(SeqnoFrame* self);		///< get value of session id
	int	(*equal)(SeqnoFrame* self, SeqnoFrame*rhs);	///< Equal compare two SeqnoFrames including qid
	int	(*compare)(SeqnoFrame* self, SeqnoFrame*rhs);	///< Compare two SeqnoFrames: -1, 0, +1
	guint64 _reqid;						///< value of this request id
	guint32 _sessionid;					///< value of this session id
	guint16 _qid;						///< value of this queue id
};
WINEXPORT SeqnoFrame* seqnoframe_new(guint16 frametype, int objsize);
WINEXPORT SeqnoFrame* seqnoframe_new_init(guint16 frametype, guint64 requestid, guint16 qid);
WINEXPORT Frame* seqnoframe_tlvconstructor(gpointer tlvstart, gconstpointer pktend, gpointer*,gpointer*);

///@}

#endif /* _SEQNOFRAME_H */
