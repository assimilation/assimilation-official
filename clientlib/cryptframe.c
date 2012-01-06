/**
 * @file
 * @brief Implements the @ref CryptFrame class - A Frame for encrypting packets
 * @details This frame cannot be usefully subclassed because of restrictions in FrameSets.
 * There are currently <b>no</b> implementations of encryption as of now.
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

	/// @TODO: Not yet implemented
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
Frame*
cryptframe_tlvconstructor(gconstpointer tlvstart,	///<[in] Start of marshalled CStringFrame data
			    gconstpointer pktend)	///<[in] Pointer to first invalid byte past 'tlvstart'
{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint16		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	/// @TODO: Not yet implemented
	CryptFrame *	cret = cryptframe_new(frametype, 0, NULL);
	Frame *		ret = CASTTOCLASS(Frame, cret);
	g_return_val_if_fail(cret != NULL, NULL);

	cret->baseclass.length = framelength;
	(void)frametype;
	(void)framelength;
	(void)framevalue;
	(void)ret;
	/// @TODO: Not yet implemented
	return NULL;
}
///@}
