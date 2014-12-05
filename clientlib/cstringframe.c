/**
 * @file
 * @brief Implements the @ref CstringFrame class - A Frame for C-style null-terminated strings
 * @details All we really add above basic Frame objects
 * is validation that they have exactly one zero, and that one at the end - normal 'C' string
 * semantics.
 *
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
#include <cstringframe.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>

DEBUGDECLARATIONS;

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
		if (NULL == self->value) {
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

	BINDDEBUG(CstringFrame);
	if (framesize < sizeof(CstringFrame)){
		framesize = sizeof(CstringFrame);
	}

	baseframe = frame_new(frame_type, framesize);
	if (framesize == sizeof(CstringFrame)) {
		DEBUGMSG5("%s: Constructing New CstringFrame at 0x%p", __FUNCTION__, baseframe);
	}
	baseframe->isvalid = _cstringframe_default_isvalid;
	baseframe->baseclass.toString = _cstringframe_toString;
	return NEWSUBCLASS(CstringFrame, baseframe);

}
/// Given marshalled packet data corresponding to an CstringFrame (C-style string),
/// return the corresponding Frame
/// In other words, un-marshall the data...
WINEXPORT Frame*
cstringframe_tlvconstructor(gpointer tlvstart,		///<[in] Start of marshalled CStringFrame data
			    gconstpointer pktend,	///<[in] Pointer to first invalid byte past 'tlvstart'
		            gpointer* ignorednewpkt,	///<[ignored] replacement packet
		            gpointer* ignoredpktend)	///<[ignored] end of replacement packet
{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint32		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	CstringFrame *	ret = cstringframe_new(frametype, 0);
	Frame *		fret = CASTTOCLASS(Frame, ret);

	(void)ignorednewpkt;	(void)ignoredpktend;
	g_return_val_if_fail(ret != NULL, NULL);

	ret->baseclass.length = framelength;
	ret->baseclass.setvalue(fret, g_memdup(framevalue, framelength), framelength, frame_default_valuefinalize);
	return fret;
}
///@}
