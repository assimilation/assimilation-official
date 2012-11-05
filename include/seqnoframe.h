/**
 * @file
 * @brief Implements the SeqnoFrame class
 * @details @ref SeqnoFrame "SeqNoFrame"s are used to provide sequence numbers for
 * reliable @ref FrameSet transmission.
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

///@{
/// @ingroup SeqnoFrame
typedef struct _SeqnoFrame SeqnoFrame;

/// This is an @ref SeqnoFrame <b>TLV</b> (type, length, value) frame.
/// It is a subclass of the @ref Frame.
/// and is manged by our @ref ProjectClass system.
/// @note This class does not use the 'value' field in the
/// base class, and does not implement the setvalue() member function.
struct _SeqnoFrame {
	Frame	baseclass;					///< base @ref Frame object
	guint64	(*getreqid)(SeqnoFrame* self);			///< get value of request id in this SeqnoFrame
	guint16	(*getqid)(SeqnoFrame* self);			///< get value of queue id in this SeqnoFrame
	void	(*setreqid)(SeqnoFrame* self, guint64 value);	///< set the request id to the given value
	void	(*setqid)(SeqnoFrame* self, guint16 value);	///< set the queue id to the given value
	gboolean(*equal)(SeqnoFrame* self, SeqnoFrame*rhs);	///< Compare two SeqnoFrames
	guint64 _reqid;						///< value of this SeqnoFrame request id
	guint16 _qid;						///< value of this SeqnoFrame queue id
};
WINEXPORT SeqnoFrame* seqnoframe_new(guint16 frametype, int objsize);
WINEXPORT Frame* seqnoframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend);

///@}

#endif /* _SEQNOFRAME_H */
