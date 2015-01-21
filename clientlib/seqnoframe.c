/**
 * @file
 * @brief Implements Seqno @ref Frame type.
 * This @ref Frame subclass implements packet sequence numbering for reliable packet delivery.
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
#include <string.h>
#include <projectcommon.h>
#include <frameset.h>
#include <seqnoframe.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>

FSTATIC void _seqnoframe_setreqid(SeqnoFrame * self, guint64 value);
FSTATIC guint64 _seqnoframe_getreqid(SeqnoFrame * self);
FSTATIC void _seqnoframe_setqid(SeqnoFrame * self, guint16 value);
FSTATIC guint16 _seqnoframe_getqid(SeqnoFrame * self);
FSTATIC void _seqnoframe_updatedata(Frame*, gpointer, gconstpointer, FrameSet*);
FSTATIC gboolean _seqnoframe_isvalid(const Frame*, gconstpointer, gconstpointer);
FSTATIC gboolean _seqnoframe_equal(SeqnoFrame * self, SeqnoFrame* rhs);
FSTATIC int _seqnoframe_compare(SeqnoFrame * self, SeqnoFrame* rhs);
FSTATIC guint32 _seqnoframe_getsessionid(SeqnoFrame * self);
FSTATIC void _seqnoframe_initsessionid(void);
FSTATIC char * _seqnoframe_toString(gconstpointer vself);

static guint32 _sessionId = 0;

/**
 * @defgroup SeqnoFrameFormats C-class SeqNoFrame wire format
 * @{
 * @ingroup FrameFormats
 * Here is the wire format we use for sequence numbers.
<PRE>
+-----------+---------------+------------+------------+-----------+
| frametype | f_length = 14 | session id | request id | queue id  |
| (16 bits) |   (16-bits)   |  (4 bytes) | (8 bytes)  | (2 bytes) |
+-----------+---------------+------------+------------+-----------+
</PRE>
The session ID is a 32-bit integer in network byte order.
The request ID is a 64-bit integer in network byte order.
The queue ID is a 16-bit integer in network byte order.
 * @}
 */

///@defgroup SeqnoFrame SeqnoFrame class
/// Class representing packet "sequence numbers" - subclass of @ref Frame.
///@{
///@ingroup Frame


/// Initialize our session ID to something monotonically increasing.
/// There are a couple of ways of achieving this...
/// - One method is to store a sequence number in a file - but this has problems
///		when you restore machines or if you can't create persistent files
/// - Another method is to use the time of day - but if the clock gets set back
///		to a time before the previous session id, then this doesn't work.
/// - The best idea seems to be to use the time of day, but also store that
///		value in a file.  If the time gets set back before the previous session id,
///		then use the previous session id + 1.
///
/// Of course, this won't really work without taking into account
/// the fact that we increment the session id by one each time we reset a connection.
/// So, if you decide to do that, please look at _fsprotocol_fspe_reinit()
/// and for good measure, look at _fsqueue_enq() too...
///
FSTATIC void
_seqnoframe_initsessionid(void)
{
#	define		FIVESECONDS	5000000
	guint64	now	= g_get_real_time();
	now /= FIVESECONDS;
	/// @todo: cache this on disk and so on as described above...
	_sessionId = (guint32)now;
}

/// Set the request id value associated with a SeqnoFrame
FSTATIC void
_seqnoframe_setreqid(SeqnoFrame * self, guint64 value)
{
	self->_reqid = value;
}

/// Set the Queue id value associated with a SeqnoFrame
FSTATIC void
_seqnoframe_setqid(SeqnoFrame * self, guint16 value)
{
	self->_qid = value;
}

/// Get the request id associated with a SeqnoFrame
FSTATIC guint64
_seqnoframe_getreqid(SeqnoFrame * self)
{
	return self->_reqid;
}
/// Get the queue id associated with a SeqnoFrame
FSTATIC guint16
_seqnoframe_getqid(SeqnoFrame * self)
{
	return self->_qid;
}
/// Get the session id associated with a SeqnoFrame
FSTATIC guint32
_seqnoframe_getsessionid(SeqnoFrame * self)
{
	return self->_sessionid;
}

/// Compare two SeqnoFrames for equality including the queue id
FSTATIC gboolean
_seqnoframe_equal(SeqnoFrame * self, SeqnoFrame* rhs)
{
	if (self->_qid != rhs->_qid) {
		return FALSE;
	}
	return self->compare(self, rhs) == 0;
}
/// Compare two SeqnoFrames - ignoring the queue id
FSTATIC int
_seqnoframe_compare(SeqnoFrame * self, SeqnoFrame* rhs)
{
	if (self->getsessionid(self) == self->getsessionid(rhs)) {
		if (self->getreqid(self) < rhs->getreqid(rhs)) {
			return -1;
		}
		if (self->getreqid(self) > rhs->getreqid(rhs)) {
			return 1;
		}
		return 0;
	}
		
	if (self->getsessionid(self) < rhs->getsessionid(rhs)) {
		return -1;
	}
	return 1;
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

	tlv_set_guint32(pktpos,                                self->_sessionid, pktend);
	tlv_set_guint64(pktpos+sizeof(guint32),                self->_reqid, pktend);
	tlv_set_guint16(pktpos+sizeof(guint32)+sizeof(guint64),self->_qid, pktend);
}
/// Construct Frame (SeqnoFrame) object from marshalled packet data
Frame*
seqnoframe_tlvconstructor(gpointer tlvstart,		///<[in] Start of SeqnoFrame TLV area
			  gconstpointer pktend,		///<[in] first byte past end of packet
		          gpointer* ignorednewpkt,	///<[ignored] replacement packet
		          gpointer* ignoredpktend)	///<[ignored] end of replacement packet
{
	SeqnoFrame*	ret;
	guint16		length  = get_generic_tlv_len(tlvstart, pktend);
	guint16		tlvtype = get_generic_tlv_type(tlvstart, pktend);
	const guint8* valpos = get_generic_tlv_value(tlvstart, pktend);

	(void)ignorednewpkt;	(void)ignoredpktend;
	g_return_val_if_fail(length == (sizeof(guint64)+sizeof(guint16)+sizeof(guint32)), NULL);

	ret = seqnoframe_new(tlvtype, 0);
	ret->_sessionid = tlv_get_guint32(valpos, pktend);
	ret->setreqid(ret, tlv_get_guint64(valpos+sizeof(guint32), pktend));
	ret->setqid(ret, tlv_get_guint16(valpos+sizeof(guint32)+sizeof(guint64), pktend));
	return CASTTOCLASS(Frame, ret);
}

/// Return TRUE if this sequence number is valid - if it's the right size
FSTATIC gboolean
_seqnoframe_isvalid(const Frame* self,		///< Frame to validate
		  gconstpointer tlvptr,		///< TLV pointer to our TLV
		  gconstpointer pktend)		///< pointer to one byte past end of packet
{
	(void)tlvptr;
	(void)pktend;
	return self->length == (sizeof(guint32)+sizeof(guint64)+sizeof(guint16));
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
	sframe = NEWSUBCLASS(SeqnoFrame, frame);
	if (_sessionId == 0) {
		_seqnoframe_initsessionid();
	}
	sframe->getreqid = _seqnoframe_getreqid;
	sframe->setreqid = _seqnoframe_setreqid;
	sframe->getqid = _seqnoframe_getqid;
	sframe->setqid = _seqnoframe_setqid;
	sframe->getsessionid = _seqnoframe_getsessionid;
	sframe->equal = _seqnoframe_equal;
	sframe->compare = _seqnoframe_compare;

	// Base class member functions
	sframe->baseclass.baseclass.toString = _seqnoframe_toString;
	sframe->baseclass.updatedata = _seqnoframe_updatedata;
	sframe->baseclass.isvalid = _seqnoframe_isvalid;
	sframe->baseclass.value = NULL;
	sframe->baseclass.setvalue = NULL;
	sframe->baseclass.valuefinalize = NULL;
	sframe->baseclass.length = sizeof(guint32)+sizeof(guint64)+sizeof(guint16);

	// Subclass (i.e., SeqnoFrame) data
	sframe->_sessionid = _sessionId;
	sframe->_reqid = 0;
	sframe->_qid = 0;
	return sframe;
}
/// Construct a fully-initialized SeqnoFrame object
SeqnoFrame*
seqnoframe_new_init(guint16 frametype,	///< Type of frame to create with this value
		    guint64 reqid,	///< Request id
		    guint16 qid)	///< Queue id
{
	SeqnoFrame*	ret = seqnoframe_new(frametype, 0);
	if (ret) {
		ret->setreqid(ret, reqid);
		ret->setqid(ret, qid);
	}
	return ret;
}

FSTATIC char *
_seqnoframe_toString(gconstpointer vself)
{
	const SeqnoFrame*	self = CASTTOCONSTCLASS(SeqnoFrame, vself);
	return g_strdup_printf("SeqnoFrame(type=%d, (%d,%d,"FMT_64BIT"d))", self->baseclass.type, self->_sessionid
	,	self->_qid, self->_reqid);
}
///@}
