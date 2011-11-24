/**
 * @file
 * @brief Implements Seqno @ref Frame type.
 * This @ref Frame subclass implements packet sequence numbering for reliable packet delivery.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <string.h>
#include <projectcommon.h>
#include <frameset.h>
#include <seqnoframe.h>
#include <frameformats.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>

FSTATIC void _seqnoframe_setreqid(SeqnoFrame * self, guint64 value);
FSTATIC guint64 _seqnoframe_getreqid(SeqnoFrame * self);
FSTATIC void _seqnoframe_setqid(SeqnoFrame * self, guint16 value);
FSTATIC guint16 _seqnoframe_getqid(SeqnoFrame * self);
FSTATIC void _seqnoframe_updatedata(Frame*, gpointer, gconstpointer, FrameSet*);
FSTATIC gboolean _seqnoframe_isvalid(const Frame*, gconstpointer, gconstpointer);
/**
 * @defgroup SeqnoFrameFormats C-class SeqNoFrame wire format
 * @{
 * @ingroup FrameFormats
 * Here is the wire format we use for sequence numbers.
<PRE>
+-----------+---------------+------------+-----------+
| frametype | f_length = 8  | request id | queue id  |
| (16 bits) |   (16-bits)   |  (8 bytes) | (2 bytes) |
+-----------+---------------+------------+-----------+
</PRE>
The request ID is a 64-bit integer in network byte order.
 * @}
 */

///@defgroup SeqnoFrame SeqnoFrame class
/// Class representing packet "sequence numbers" - subclass of @ref Frame.
///@{
///@ingroup Frame


/// Set the request id value associated with an SeqnoFrame
FSTATIC void
_seqnoframe_setreqid(SeqnoFrame * self, guint64 value)
{
	self->_reqid = value;
}

/// Set the Queue id value associated with an SeqnoFrame
FSTATIC void
_seqnoframe_setqid(SeqnoFrame * self, guint16 value)
{
	self->_qid = value;
}

/// Get the request id associated with an SeqnoFrame
FSTATIC guint64
_seqnoframe_getreqid(SeqnoFrame * self)
{
	return self->_reqid;
}
/// Get the queue id associated with an SeqnoFrame
FSTATIC guint16
_seqnoframe_getqid(SeqnoFrame * self)
{
	return self->_qid;
}

/// Update packet data from the frame
FSTATIC void
_seqnoframe_updatedata(Frame* fself,		///< object whose data will be put into FrameSet packet
		     gpointer tlvptr,		///< pointer to our current TLV entry
		     gconstpointer pktend,	///< end of packet
		     FrameSet* fs)		///< FrameSet that we're doing this for
{
	SeqnoFrame* self = CASTTOCLASS(SeqnoFrame, fself);
	// NOTE - this gets rid of the "const" coming out of get_generic_tlv_value...
	///@todo add a new get_generic_nonconst_tlv_value() function.
	guint8* pktpos = get_generic_tlv_nonconst_value(tlvptr, pktend);
	(void)fs;
	g_return_if_fail(NULL != pktpos);

	tlv_set_guint64(pktpos, self->_reqid, pktend);
	tlv_set_guint16(pktpos+sizeof(guint64), self->_qid, pktend);
}

/// Return TRUE if this sequence number is valid - if it's the right size
FSTATIC gboolean
_seqnoframe_isvalid(const Frame* self,		///< Frame to validate
		  gconstpointer tlvptr,		///< TLV pointer to our TLV
		  gconstpointer pktend)		///< pointer to one byte past end of packet
{
	(void)tlvptr;
	(void)pktend;
	return self->length == (sizeof(guint64)+sizeof(guint16));
}

/// Construct new SeqnoFrame object
SeqnoFrame*
seqnoframe_new(guint16 frametype,	///< Type of frame to create with this value
	     int objsize)		///< Size of the object type - 0 means sizeof(SeqnoFrame)
{
	Frame*	frame;
	SeqnoFrame*	sframe;

	if (objsize < ((gssize)sizeof(SeqnoFrame))) {
		objsize = sizeof(SeqnoFrame);
	}

	frame = frame_new(frametype, objsize);
	proj_class_register_subclassed(frame, "SeqnoFrame");
	sframe = CASTTOCLASS(SeqnoFrame, frame);
	sframe->setreqid = _seqnoframe_setreqid;
	sframe->setqid = _seqnoframe_setqid;
	sframe->getreqid = _seqnoframe_getreqid;
	sframe->getqid = _seqnoframe_getqid;
	sframe->baseclass.updatedata = _seqnoframe_updatedata;
	sframe->baseclass.isvalid = _seqnoframe_isvalid;
	sframe->baseclass.value = NULL;
	sframe->baseclass.setvalue = NULL;
	sframe->baseclass.valuefinalize = NULL;
	sframe->baseclass.length = sizeof(guint64)+sizeof(guint16);
	return sframe;
}
/// Construct Frame (SeqnoFrame) object from marshalled packet data
Frame*
seqnoframe_tlvconstructor(gconstpointer tlvstart,	///<[in] Start of SeqnoFrame TLV area
			  gconstpointer pktend)		///<[in] first byte past end of packet
{
	SeqnoFrame*	ret;
	guint16		length  = get_generic_tlv_len(tlvstart, pktend);
	guint16		tlvtype = get_generic_tlv_type(tlvstart, pktend);
	const guint8* valpos = get_generic_tlv_value(tlvstart, pktend);

	g_return_val_if_fail(length < (sizeof(guint64)+sizeof(guint16)), NULL);

	ret = seqnoframe_new(tlvtype, 0);
	ret->setreqid(ret, tlv_get_guint64(valpos, pktend));
	ret->setqid(ret, tlv_get_guint16(valpos+sizeof(guint64), pktend));
	return CASTTOCLASS(Frame, ret);
}
///@}
