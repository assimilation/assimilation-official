/**
 * @file
 * @brief Implements the @ref UnknownFrame class - A frame for C-style null-terminated strings
 * @details UnknownFrames are a frame that we don't recognize.
 * These can be caused by software version mismatches between communicating systems.
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
#include <unknownframe.h>
#include <frameformats.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>

FSTATIC gboolean _unknownframe_default_isvalid(const Frame *, gconstpointer, gconstpointer);

///@defgroup UnknownFrame UnknownFrame class
/// Class representing an unrecogized or unknown type of frame in a packet - subclass of @ref Frame.
/// @{
/// @ingroup Frame

/// @ref UnknownFrame 'isvalid' member function (always returns FALSE)
FSTATIC gboolean
_unknownframe_default_isvalid(const Frame * self,		///<[in] UnknownFrame object ('this')
			      gconstpointer tlvptr,	///<[in] Pointer to the TLV for this UnknownFrame
			      gconstpointer pktend)	///<[in] Pointer to one byte past the end of the packet
{
	(void)self; (void)tlvptr; (void)pktend;
	///@todo think about whether unknown frames are always valid, or always invalid...
	return FALSE;
}


/// Construct a new UnknownFrame - disallowing for "derived" frame types...
/// This can be used only for creating UnknownFrame frames.
UnknownFrame*
unknownframe_new(guint16 frame_type)	///<[in] TLV type associated with this unknown frame
{
	Frame*	baseframe;

	baseframe = frame_new(frame_type, sizeof(UnknownFrame));
	baseframe->isvalid = _unknownframe_default_isvalid;
	proj_class_register_subclassed (baseframe, "UnknownFrame");

	return CASTTOCLASS(UnknownFrame, baseframe);
}


/// Given marshalled data corresponding to an unknown Frame (basic binary frame), return that corresponding Frame
/// In other words, un-marshall the data...
Frame*
unknownframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend)
{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint16		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	UnknownFrame *	ret = unknownframe_new(frametype);
	Frame *		fret = CASTTOCLASS(Frame, ret);
	g_return_val_if_fail(ret != NULL, NULL);

	ret->baseclass.length = framelength;
	fret->setvalue(fret, g_memdup(framevalue, framelength), framelength, _frame_default_valuefinalize);
	return fret;
}
///@}
