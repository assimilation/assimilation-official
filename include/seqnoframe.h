/**
 * @file
 * @brief Implements the SeqnoFrame class
 * @details @ref SeqnoFrame "SeqNoFrame"s are used to provide sequence numbers for
 * reliable @ref FrameSet transmission.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
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
#ifdef _MSC_VER
#define EXP_FUNC __declspec( dllexport )
#endif
EXP_FUNC SeqnoFrame* seqnoframe_new(guint16 frametype, int objsize);
EXP_FUNC Frame* seqnoframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend);

///@}

#endif /* _SEQNOFRAME_H */
