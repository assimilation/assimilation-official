/**
 * @file
 * @brief Implements the @ref NVpairFrame class - A Frame for two strings defining a name/value pair
 * @details Need to implement this Real Soon Now...
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
#include <nvpairframe.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>


#if defined(_MSC_VER) && _MSC_VER < 1400
// Probably should be defined in some other file - for the case the system doesn't supply it.
gsize
strnlen(char*  str, size_t  maxlen)
{
	char*  p = memchr(str, '\0', maxlen);
 
	if (p == NULL) {
		return maxlen;
	}
	return (p - str);
}
#endif


FSTATIC gboolean _nvpairframe_default_isvalid(const Frame *, gconstpointer, gconstpointer);

///@defgroup NVpairFrame NVpairFrame class
/// Class for holding/storing pairs of strings as name/value pairs  Subclass of @ref Frame.
/// @{
/// @ingroup Frame

/// @ref NVpairFrame 'isvalid' member function (checks for valid name/value pairs)
gboolean
_nvpairframe_default_isvalid(const Frame * self,	///<[in] NVpairFrame object ('this')
			      gconstpointer tlvptr,	///<[in] Pointer to the TLV for this NVpairFrame
			      gconstpointer pktend)	///<[in] Pointer to one byte past the end of the packet
{
	const NVpairFrame*	nvself;
	gsize			length;
	const guint8*		namestart;
	const guint8*		valuestart;
	const guint8*		valueendplace;
	const guint8*		valuexpectedplace;

	nvself = CASTTOCONSTCLASS(NVpairFrame, self);
	if (tlvptr == NULL) {
		if (nvself->value == NULL || nvself->name == NULL) {
			return FALSE;
		}
		return (strnlen(nvself->name, self->length) + strnlen(nvself->value, self->length))
		== (gsize)(self->length-2);
	}
	length = get_generic_tlv_len(tlvptr, pktend);
	namestart = get_generic_tlv_value(tlvptr, pktend);
	valuestart = memchr(namestart, 0x00, length-2);
	if (valuestart == NULL) {
		return FALSE;
	}
	valuestart++;
	g_return_val_if_fail(NULL != tlvptr, FALSE);
	g_return_val_if_fail(NULL != pktend, FALSE);
	g_return_val_if_fail(length > 0,  FALSE);
	g_return_val_if_fail(valuestart < namestart+1, FALSE);

	valueendplace = namestart + length;
	valuexpectedplace = valueendplace-1;
	return valuexpectedplace == memchr(valuestart, 0x00, 1+(valueendplace-valuestart));
}


/// Construct a new NVpairFrame - allowing for "derived" frame types...
/// This can be used directly for creating NVpairFrame frames, or by derived classes.
NVpairFrame*
nvpairframe_new(guint16 frame_type,	///<[in] TLV type of NVpairFrame
		gchar*	name,		///<[in] name to initialize nvpair to
		gchar*	value,		///<[in] value to initialize nvpair to
	  	gsize framesize)	///< size of frame structure (or zero for sizeof(NVpairFrame))
{
	Frame*		baseframe;
	NVpairFrame*	self;

	if (framesize < sizeof(NVpairFrame)){
		framesize = sizeof(NVpairFrame);
	}

	if (name != NULL) {
		g_return_val_if_fail(value != NULL, NULL);
		g_return_val_if_fail(name[0] != '\0', NULL);
	}
	baseframe = frame_new(frame_type, framesize);
	baseframe->isvalid = _nvpairframe_default_isvalid;
	if (name != NULL) {
		name = g_strdup(name);
		value = g_strdup(value);
		baseframe->length = strlen(name) + strlen(value) + 2;
	}
	proj_class_register_subclassed (baseframe, "NVpairFrame");

	self =  CASTTOCLASS(NVpairFrame, baseframe);
	self->name = name;
	self->value = value;
	return self;
}
/// Given marshalled packet data corresponding to an NVpairFrame (name/value pair)
/// return the corresponding Frame
/// In other words, un-marshall the data...
WINEXPORT Frame*
nvpairframe_tlvconstructor(gpointer tlvstart,		///<[in] Start of marshalled CStringFrame data
			   gconstpointer pktend,	///<[in] Pointer to first invalid byte past 'tlvstart'
			   gpointer* ignorednewpkt,	///<[ignored] replacement packet if any
			   gpointer* ignoredpktend)	///<[ignored] end of replaement packet
{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint32		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	NVpairFrame *	ret = nvpairframe_new(frametype, NULL, NULL, 0);
	Frame *		fret = CASTTOCLASS(Frame, ret);

	(void)ignorednewpkt;	(void)ignoredpktend;
	g_return_val_if_fail(ret != NULL, NULL);

	ret->baseclass.length = framelength;
	///@todo FIXMEthis code is probably wrong...
	///@todo FIXME CERTAINLY ARE MEMORY LEAKS HERE!
	ret->baseclass.setvalue(fret, g_memdup(framevalue, framelength), framelength, frame_default_valuefinalize);
	return fret;
}
///@}
