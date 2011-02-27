/**
 * @file
 * @brief Implements IntFrame @ref Frame type.
 * This @ref Frame subclass implements 2, 3, 4, and 8 byte integers.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <string.h>
#include <projectcommon.h>
#include <frameset.h>
#include <intframe.h>
#include <frameformats.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>
/**
 * @defgroup IntFrameFormats C-Class IntFrame wire format
 * @{
 * @ingroup FrameFormats
 * Here are the various frame formats that we use for packaging single integers
 * as whole frames.
 *
 * Below is the wire format for an 8-bit integer IntFrame.
 * <PRE>
 * +--------------+-----------+------------------+
 * |   frametype  | f_length  |  frame-value(s)  |
 * |   (16 bits)  |    1      |     1 byte       |
 * +--------------+-----------+------------------+
 * </PRE>
 * Below is the wire format for a 16-bit integer.
 * <PRE>
 * +--------------+-----------+------------------+
 * |   frametype  | f_length  |  2 byte integer  |
 * |   (16 bits)  |    2      |  net byte order  |
 * +--------------+-----------+------------------+
 * </PRE>
 * Below is the wire format for a 24-bit integer IntFrame.
 * <PRE>
 * +--------------+-----------+-------------.----------------+
 * |   frametype  | f_length  |  high-order . 2 byte integer |
 * |   (16 bits)  |    3      |     byte    . net byte order |
 * +--------------+-----------+-------------.----------------+
 * </PRE>
 * Below is the wire format for a 32-bit integer IntFrame.
 * <PRE>
 * +--------------+-----------+------------------+
 * |   frametype  | f_length  |  4 byte integer  |
 * |   (16 bits)  |    4      |  net byte order  |
 * +--------------+-----------+------------------+
 * </PRE>
 * Below is the wire format for a 64-bit integer IntFrame.
 * <PRE>
 * +--------------+-----------+------------------+
 * |   frametype  | f_length  |  8 byte integer  |
 * |   (16 bits)  |    8      |  net byte order  |
 * +--------------+-----------+------------------+
 * </PRE>
 * @}
 */

FSTATIC int _intframe_intlength(IntFrame *);
FSTATIC void _intframe_setint(IntFrame * self, guint64 value);
FSTATIC guint64 _intframe_getint(IntFrame * self);
FSTATIC void _intframe_updatedata(Frame*, gpointer, gconstpointer, FrameSet*);
FSTATIC gboolean _intframe_isvalid(const Frame*, gconstpointer, gconstpointer);

///@defgroup IntFrame IntFrame class
/// Class representing various length of integers - subclass of @ref Frame.
///@{
///@ingroup Frame

/// Return number of bytes in this integer
FSTATIC int
_intframe_intlength(IntFrame * self)
{
	return self->baseclass.length;
}

/// Set the integer value associated with an IntFrame
FSTATIC void
_intframe_setint(IntFrame * self, guint64 value)
{
	guint64	limit = 0;
	switch (self->baseclass.length) {
		case 1:	limit = G_MAXUINT8;
			break;
		case 2:	limit = G_MAXUINT16;
			break;
		case 3:	limit = ((2ULL<<24)-1);
			break;
		case 4:	limit = G_MAXUINT32;
			break;
		case 8:	limit = G_MAXUINT64;
			break;
	}
	g_return_if_fail(value <= limit);
	self->_value = value;
}

/// Get the integer value associated with an IntFrame
FSTATIC guint64
_intframe_getint(IntFrame * self)
{
	return self->_value;
}

FSTATIC void
_intframe_updatedata(Frame* fself,		///< object whose data will be put into FrameSet packet
		     gpointer tlvptr,		///< pointer to our current TLV entry
		     gconstpointer pktend,	///< end of packet
		     FrameSet* fs)		///< FrameSet that we're doing this for
{
	IntFrame* self = CASTTOCLASS(IntFrame, fself);
	// NOTE - this gets rid of the "const" coming out of get_generic_tlv_value...
	///@todo add a new get_generic_nonconst_tlv_value() function.
	void * pktpos = GINT_TO_POINTER(GPOINTER_TO_INT(get_generic_tlv_value(tlvptr, pktend)));
	g_return_if_fail(NULL != pktpos);

	switch (self->baseclass.length) {
		case 1:	tlv_set_guint8(pktpos, (guint8)self->_value, pktend);
			break;
		case 2:	tlv_set_guint16(pktpos, (guint16)self->_value, pktend);
			break;
		case 3:	tlv_set_guint24(pktpos, (guint32)self->_value, pktend);
			break;
		case 4:	tlv_set_guint32(pktpos, (guint32)self->_value, pktend);
			break;
		case 8:	tlv_set_guint64(pktpos, (guint64)self->_value, pktend);
			break;
		default:g_return_if_reached();
			break;
	}
}

/// Return TRUE if this integer is valid - basically is it of one of our supported lengths...
FSTATIC gboolean
_intframe_isvalid(const Frame* self,			///< Frame to validate
		  gconstpointer tlvptr,		///< TLV pointer to our TLV
		  gconstpointer pktend)		///< pointer to one byte past end of packet
{
	if (self->length != get_generic_tlv_len(tlvptr, pktend)) {
		return FALSE;
	}
	switch (self->length) {
		case 1: case 2: case 3: case 4: case 8:
		return TRUE;
	}
	return FALSE;
}

/// Construct new IntFrame object
IntFrame*
intframe_new(guint16 frametype,	///< Type of frame to create with this value
	     int intbytes)	///< number of bytes for the integer - should be one of 1,2,3,4,8
{
	Frame*	frame;
	IntFrame*	iframe;
	g_return_val_if_fail(intbytes == 1 || intbytes == 2 || intbytes == 3 || intbytes == 4 || intbytes == 8, NULL);
	frame = frame_new(frametype, sizeof(IntFrame));
	proj_class_register_subclassed(frame, "IntFrame");
	iframe = CASTTOCLASS(IntFrame, frame);
	iframe->baseclass.length = intbytes;
	iframe->intlength = _intframe_intlength;
	iframe->setint = _intframe_setint;
	iframe->getint = _intframe_getint;
	iframe->baseclass.updatedata = _intframe_updatedata;
	iframe->baseclass.isvalid = _intframe_isvalid;
	iframe->baseclass.value = NULL;
	iframe->baseclass.setvalue = NULL;
	iframe->baseclass.valuefinalize = NULL;
	iframe->baseclass.length = intbytes;
	return iframe;
}
/// Given marshalled data corresponding to an IntFrame (integer frame), return that corresponding Frame
/// In other words, un-marshall the data...
Frame*
intframe_tlvconstructor(gconstpointer tlvstart,	///<[in] First byte of the IntFrame TLV
			gconstpointer pktend)	///<[in] First invalid byte past pktend
{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint16		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	IntFrame *	ret = intframe_new(frametype, framelength);
	guint64		intvalue = 0xffffffffffffffffULL;
	g_return_val_if_fail(ret != NULL, NULL);

	ret->baseclass.length = framelength;
	switch (ret->baseclass.length) {
		case 1:
			intvalue = tlv_get_guint8(framevalue, pktend);
			break;
		case 2:
			intvalue = tlv_get_guint16(framevalue, pktend);
			break;
		case 3:
			intvalue = tlv_get_guint24(framevalue, pktend);
			break;
		case 4:
			intvalue = tlv_get_guint32(framevalue, pktend);
			break;
		case 8:
			intvalue = tlv_get_guint64(framevalue, pktend);
			break;
	}
	ret->setint(ret, intvalue);
	return CASTTOCLASS(Frame, ret);
}


///@}
///@}
