/**
 * @file
 * @brief Implements the @ref CompressFrame class - A Frame for C-style null-terminated strings
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
#include <compressframe.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>

FSTATIC gboolean _compressframe_default_isvalid(const Frame *, gconstpointer, gconstpointer);

///@defgroup CompressFrame CompressFrame class
/// Class for compressing FrameSets   Subclass of @ref Frame.
/// @todo: Not yet implemented
/// @{
/// @ingroup Frame

/// @ref CompressFrame 'isvalid' member function (checks for valid compression method).
/// @todo: Not yet implemented.
FSTATIC gboolean
_compressframe_default_isvalid(const Frame * self,	///<[in] CompressFrame object ('this')
			      gconstpointer tlvptr,	///<[in] Pointer to the TLV for this CompressFrame
			      gconstpointer pktend)	///<[in] Pointer to one byte past the end of the packet
{
	const CompressFrame*	cself = CASTTOCONSTCLASS(CompressFrame, self);

	if (tlvptr == NULL) {
		return cself->compression_method > 0;
	}
	(void)pktend;
	return FALSE;
}


/// Construct a new CompressFrame - derived frame types are not allowed.
/// @todo: Not yet implemented.
CompressFrame*
compressframe_new(guint16 frame_type,	///< TLV type of CompressFrame
	  guint16 compression_method)	///< Compression method.
{
	Frame*	baseframe;
	CompressFrame*	cmpframe;


	baseframe = frame_new(frame_type, sizeof(CompressFrame));
	baseframe->isvalid = _compressframe_default_isvalid;
	proj_class_register_subclassed (baseframe, "CompressFrame");

	cmpframe =  CASTTOCLASS(CompressFrame, baseframe);
	cmpframe->compression_method = compression_method;
	return cmpframe;
}
/// Given marshalled packet data corresponding to an CompressFrame (C-style string),
/// return the corresponding Frame
/// In other words, un-marshall the data...
/// @todo: Not yet implemented.
Frame*
compressframe_tlvconstructor(gconstpointer tlvstart,	///<[in] Start of marshalled CStringFrame data
			    gconstpointer pktend)	///<[in] Pointer to first invalid byte past 'tlvstart'
{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint16		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	//CompressFrame *	ret = compressframe_new(frametype, 0);
	//Frame *		fret = CASTTOCLASS(Frame, ret);
	//g_return_val_if_fail(ret != NULL, NULL);

	//ret->baseclass.length = framelength;
	//ret->baseclass.setvalue(fret, g_memdup(framevalue, framelength), framelength, _frame_default_valuefinalize);
	(void)frametype;
	(void)framelength;
	(void)framevalue;
	return NULL;
}
///@}
