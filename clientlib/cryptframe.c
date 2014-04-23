/**
 * @file
 * @brief Implements the @ref CryptFrame class - A Frame for encrypting packets
 * @details This frame cannot be usefully subclassed because of restrictions in FrameSets.
 * There are currently <b>no</b> implementations of encryption as of now.
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
#include <cryptframe.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>

FSTATIC gboolean _cryptframe_default_isvalid(const Frame *, gconstpointer, gconstpointer);

///@defgroup CryptFrame CryptFrame class
/// Class for encrypting FrameSets.
/// @{
/// @ingroup Frame

/// @ref CryptFrame 'isvalid' member function (checks for valid cryptframe objects)
FSTATIC gboolean
_cryptframe_default_isvalid(const Frame * self,	///<[in] CryptFrame object ('this')
			      gconstpointer tlvptr,	///<[in] Pointer to the TLV for this CryptFrame
			      gconstpointer pktend)	///<[in] Pointer to one byte past the end of the packet
{
	gsize		length;
	const CryptFrame*	cself = CASTTOCONSTCLASS(CryptFrame, self);

	if (tlvptr == NULL) {
		if (cself->encryption_method <= 0 ) {
			return FALSE;
		}
		length = self->length;
	}else{
		length = get_generic_tlv_len(tlvptr, pktend);
	}
	(void)length;

	/// @todo: Not yet implemented
	return FALSE;
}


/// Construct a new CryptFrame
/// This can only be used directly for creating CryptFrame frames.
CryptFrame*
cryptframe_new(guint16 frame_type,	///<[in] TLV type of CryptFrame
	  guint16 encryption_method,	///<[in] Encryption method
	  void * keyinfo)		///<[in] size of frame structure (or zero for sizeof(CryptFrame))
{
	Frame*		baseframe;
	CryptFrame*	ret;

	baseframe = frame_new(frame_type, sizeof(CryptFrame));
	baseframe->isvalid = _cryptframe_default_isvalid;
	proj_class_register_subclassed (baseframe, "CryptFrame");
	

	ret = CASTTOCLASS(CryptFrame, baseframe);
	ret->encryption_method = encryption_method;
	ret->encryption_key_info = keyinfo;
	return ret;
}
/// Given marshalled packet data corresponding to an CryptFrame (C-style string),
/// return the corresponding Frame
/// In other words, un-marshall the data...
WINEXPORT Frame*
cryptframe_tlvconstructor(gconstpointer tlvstart,	///<[in] Start of marshalled CStringFrame data
			  gconstpointer pktend,		///<[in] Pointer to first invalid byte past 'tlvstart'
		          gpointer* ignorednewpkt,	///<[ignored] replacement packet
		          gpointer* ignoredpktend)	///<[ignored] end of replacement packet
{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint16		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	/// @todo: Not yet implemented
	CryptFrame *	cret = cryptframe_new(frametype, 0, NULL);
	Frame *		ret = CASTTOCLASS(Frame, cret);

	(void)ignorednewpkt;
	(void)ignoredpktend;
	g_return_val_if_fail(cret != NULL, NULL);

	cret->baseclass.length = framelength;
	(void)frametype;
	(void)framelength;
	(void)framevalue;
	(void)ret;
	/// @todo: Not yet implemented
	return NULL;
}
///@}
