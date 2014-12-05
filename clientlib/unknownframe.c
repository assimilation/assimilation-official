/**
 * @file
 * @brief Implements the @ref UnknownFrame class - A frame for C-style null-terminated strings
 * @details UnknownFrames are a frame that we don't recognize.
 * These can be caused by software version mismatches between communicating systems.
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
#include <unknownframe.h>
#include <frametypes.h>
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
unknownframe_tlvconstructor(gpointer tlvstart,		///<[in] Start of our Frame in the packet
			    gconstpointer pktend,	///<[in] One byte past end of packet
			    gpointer* ignorednewpkt,	///<[ignored]
			    gpointer* ignorednewpktend)	///<[ignored]
{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint32		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	UnknownFrame *	ret = unknownframe_new(frametype);
	Frame *		fret = CASTTOCLASS(Frame, ret);
	(void)ignorednewpkt;
	(void)ignorednewpktend;
	g_return_val_if_fail(ret != NULL, NULL);

	ret->baseclass.length = framelength;
	fret->setvalue(fret, g_memdup(framevalue, framelength), framelength, frame_default_valuefinalize);
	return fret;
}
///@}
