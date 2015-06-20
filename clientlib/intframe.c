/**
 * @file
 * @brief Implements IntFrame @ref Frame type.
 * This @ref Frame subclass implements 2, 3, 4, and 8 byte integers.
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
#include <intframe.h>
#include <frametypes.h>
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
FSTATIC gchar* _intframe_toString(gconstpointer obj);

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
		case 3:	limit = 0x00ffffffL;
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
	void * pktpos = get_generic_tlv_nonconst_value(tlvptr, pktend);
	(void)fs;
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
	int	length = self->length;
	if (tlvptr != NULL) {
		int	tlvlen = get_generic_tlv_len(tlvptr, pktend);
		if (length != tlvlen) {
			return FALSE;
		}
	}
	switch (self->length) {
		case 1: case 2: case 3: case 4: case 8:
		return TRUE;
	}
	return FALSE;
}

/// Return a printable representation of our IntFrame object
FSTATIC gchar*
_intframe_toString(gconstpointer obj)
{
	const IntFrame* self = CASTTOCONSTCLASS(IntFrame, obj);
	return g_strdup_printf("IntFrame(%d, %d, "FMT_64BIT"d)"
	,	self->baseclass.type, self->baseclass.length, self->_value);
}

/// Construct new IntFrame object
IntFrame*
intframe_new(guint16 frametype,	///< Type of frame to create with this value
	     int intbytes)	///< number of bytes for the integer - should be one of 1,2,3,4,8
{
	Frame*	frame;
	IntFrame*	iframe;
	if (intbytes != 1 && intbytes != 2 && intbytes != 3 && intbytes != 4 && intbytes != 8) {
		return NULL;
	}
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
	iframe->baseclass.baseclass.toString = _intframe_toString;
	return iframe;
}
/// Given marshalled data corresponding to an IntFrame (integer frame), return that corresponding Frame
/// In other words, un-marshall the data...
Frame*
intframe_tlvconstructor(gpointer tlvstart,	///<[in] First byte of the IntFrame TLV
			gconstpointer pktend,	///<[in] First invalid byte past pktend
		        gpointer* ignorednewpkt,///<[ignored] replacement packet
		        gpointer* ignoredpktend)///<[ignored] end of replacement packet
{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint16		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	IntFrame *	ret = intframe_new(frametype, framelength);
	guint64		intvalue = G_MAXUINT64;

	(void)ignorednewpkt;	(void)ignoredpktend;
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
