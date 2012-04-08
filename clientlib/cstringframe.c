/**
 * @file
 * @brief Implements the @ref CstringFrame class - A Frame for C-style null-terminated strings
 * @details All we really add above basic Frame objects
 * is validation that they have exactly one zero, and that one at the end - normal 'C' string
 * semantics.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <string.h>
#include <projectcommon.h>
#include <frameset.h>
#include <cstringframe.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>
/**
 * @defgroup CstringFrameFormats C-Class C-string wire format
 * @{
 * @ingroup FrameFormats
 * Here is the format we use for packaging a NUL-terminated C-style string (@ref CstringFrame) for the wire.
<PRE>
+-------------+----------------+------------------+------------+
| frametype   |    f_length    |    String Data   |  NUL char  |
|  16 bits)   |    (16-bits)   | f_length-1 bytes |  (1 byte)  |
+-------------+----------------+------------------+------------+
</PRE>
*@}
*/

FSTATIC gboolean _cstringframe_default_isvalid(const Frame *, gconstpointer, gconstpointer);
FSTATIC gchar* _cstringframe_toString(gconstpointer);

///@defgroup CstringFrame CstringFrame class
/// Class for holding/storing C-style null-terminated strings -  Subclass of @ref Frame.
/// @{
/// @ingroup Frame

/// @ref CstringFrame 'isvalid' member function (checks for valid C-style string)
FSTATIC gboolean
_cstringframe_default_isvalid(const Frame * self,	///<[in] CstringFrame object ('this')
			      gconstpointer tlvptr,	///<[in] Pointer to the TLV for this CstringFrame
			      gconstpointer pktend)	///<[in] Pointer to one byte past the end of the packet
{
	gsize		length;
	const guint8*	stringstart;
	const guint8*	endplace;
	const guint8*	expectedplace;

	(void)self;
	if (tlvptr == NULL) {
		if (self->value == NULL) {
			return FALSE;
		}
		length = self->length;
		stringstart = self->value;
	}else{
		length = get_generic_tlv_len(tlvptr, pktend);
		stringstart = get_generic_tlv_value(tlvptr, pktend);
		g_return_val_if_fail(NULL != tlvptr, FALSE);
		g_return_val_if_fail(NULL != pktend, FALSE);
		g_return_val_if_fail(length > 0,  FALSE);
	}

	endplace = stringstart + length;
	expectedplace = endplace-1;
	return expectedplace == memchr(stringstart, 0x00, length);
}

FSTATIC
gchar*
_cstringframe_toString(gconstpointer obj)
{
	const CstringFrame* self = CASTTOCONSTCLASS(CstringFrame, obj);
	return g_strdup_printf("CstringFrame(%d, \"%s\")"
	,	self->baseclass.type, (gchar*)self->baseclass.value);
}


/// Construct a new CstringFrame - allowing for "derived" frame types...
/// This can be used directly for creating CstringFrame frames, or by derived classes.
WINEXPORT CstringFrame*
cstringframe_new(guint16 frame_type,	///< TLV type of CstringFrame
	  gsize framesize)	///< size of frame structure (or zero for sizeof(CstringFrame))
{
	Frame*	baseframe;

	if (framesize < sizeof(CstringFrame)){
		framesize = sizeof(CstringFrame);
	}

	baseframe = frame_new(frame_type, framesize);
	baseframe->isvalid = _cstringframe_default_isvalid;
	baseframe->baseclass.toString = _cstringframe_toString;
	return NEWSUBCLASS(CstringFrame, baseframe);

}
/// Given marshalled packet data corresponding to an CstringFrame (C-style string),
/// return the corresponding Frame
/// In other words, un-marshall the data...
WINEXPORT Frame*
cstringframe_tlvconstructor(gconstpointer tlvstart,	///<[in] Start of marshalled CStringFrame data
			    gconstpointer pktend)	///<[in] Pointer to first invalid byte past 'tlvstart'
{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint16		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	CstringFrame *	ret = cstringframe_new(frametype, 0);
	Frame *		fret = CASTTOCLASS(Frame, ret);
	g_return_val_if_fail(ret != NULL, NULL);

	ret->baseclass.length = framelength;
	ret->baseclass.setvalue(fret, g_memdup(framevalue, framelength), framelength, frame_default_valuefinalize);
	return fret;
}
///@}
