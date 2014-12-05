/**
 * @file
 * @brief Implements the @ref Frame class - binary blobs on the wire
 * @details  implementing the base class for marshalling and demarshalling objects on the wire
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
#include <frame.h>
#include <generic_tlv_min.h>
#include <memory.h>

FSTATIC void _frame_default_finalize(AssimObj * self);
FSTATIC gsize _frame_dataspace(const Frame* f);
FSTATIC gboolean _frame_default_isvalid(const Frame *, gconstpointer,	gconstpointer);
FSTATIC void _frame_setvalue(Frame *, gpointer, guint32, GDestroyNotify valnotify);
FSTATIC void _frame_updatedata(Frame *, gpointer, gconstpointer, FrameSet*);
FSTATIC void _frame_dump(const Frame *, const char * prefix);
FSTATIC gchar* _frame_toString(gconstpointer aself);

DEBUGDECLARATIONS

///@defgroup Frame Frame class
/// Class for holding/storing binary blobs -  Base class for all the other Frame types.
///@{
///@ingroup C_Classes

/// Finalize a Frame
FSTATIC void
_frame_default_finalize(AssimObj * obj) ///< Frame to finalize
{
	Frame*	self = CASTTOCLASS(Frame, obj);
	DEBUGMSG5("%s: Finalizing Frame at 0x%p", __FUNCTION__, self);
	if (self->value && self->valuefinalize) {
		self->valuefinalize(self->value);
	}
	memset(self, 0x00, sizeof(Frame));
	_assimobj_finalize(obj);
}
/// Finalize a Frame
FSTATIC void
frame_default_valuefinalize(gpointer value) ///< Value to finalize
{
	if (value) {
		DEBUGMSG4("%s: freeing Frame value at 0x%p", __FUNCTION__, value);
		FREE(value);
	}
}

/// Return total space required to put this frame in a packet (marshalled size)
FSTATIC gsize
_frame_dataspace(const Frame* f)	///< Frame to return the marshalled size of
{
	g_return_val_if_fail(f != NULL, 0);
	return (gsize)(FRAME_INITSIZE + f->length);
}

/// Default @ref Frame 'isvalid' member function (always returns TRUE)
FSTATIC gboolean
_frame_default_isvalid(const Frame * self,		///< Frame object ('this')
		       gconstpointer tlvptr,	///< Pointer to the TLV for this Frame
		       gconstpointer pktend)	///< Pointer to one byte past the end of the packet
{
	(void)self;
	(void)tlvptr;
	(void)pktend;
	return TRUE;
}

/// @ref Frame 'toString' operation - convert a basic Frame into a string
FSTATIC gchar*
_frame_toString(gconstpointer	aself)
{
	const Frame*	self = CASTTOCONSTCLASS(Frame, aself);
	return g_strdup_printf("Frame(frametype=%d, length=%d, address=%p)"
	,	self->type, self->length, self);
}


/// 'setvalue' @ref Frame member function.
FSTATIC void
_frame_setvalue(Frame * self,			///< Frame object ('this')
		gpointer value,			///< Value to save away
		guint32	length,			///< Length of value
		GDestroyNotify valnotify)	///< Value destructor.
{
	if (self->value && self->valuefinalize) {
		self->valuefinalize(self);
	}
	self->value = value;
	self->length = length;
	self->valuefinalize = valnotify;
}

/// Update packet data ('updatedata') @ref Frame member function
FSTATIC void
_frame_updatedata(Frame * self,			///< Frame object ('this')
		  gpointer tlvptr,		///< Where the Frame TLV is
		  gconstpointer pktend,		///< End of packet
		  FrameSet* fs)			///< FrameSet to update (or not)
{
	(void)fs;
	// set_generic_tlv_value does pretty exhaustive error checking.
	set_generic_tlv_value(tlvptr, self->value, self->length, pktend);
}

/// Construct a new frame - allowing for "derived" frame types...
/// This can be used directly for creating basic binary frames, or by derived classes.
Frame*
frame_new(guint16 frame_type,	///< TLV type of Frame
	  gsize framesize)	///< size of frame structure (or zero for sizeof(Frame))
{
	AssimObj * newobj;
	Frame * newframe = NULL;

	BINDDEBUG(Frame);
	if (framesize < sizeof(Frame)) {
		framesize = sizeof(Frame);
	}
	newobj   = assimobj_new(framesize);
	if (framesize == sizeof(Frame)) {
		DEBUGMSG5("%s: Constructing New Frame at 0x%p", __FUNCTION__, newobj);
	}
	if (newobj != NULL) {
		newframe = NEWSUBCLASS(Frame, newobj);
		newobj->_finalize	= _frame_default_finalize;
		newobj->toString	= _frame_toString;
		newframe->type		= frame_type;
		newframe->length	= 0;
		newframe->value		= NULL;
		newframe->dataspace	= _frame_dataspace;
		newframe->isvalid	= _frame_default_isvalid;
		newframe->setvalue	= _frame_setvalue;
		newframe->updatedata	= _frame_updatedata;
		newframe->dump		= _frame_dump;
		newframe->valuefinalize	= NULL;
	}
	return newframe;
}
/// Given marshalled data corresponding to a Frame (basic binary frame), return that corresponding Frame
/// In other words, un-marshall the data...
Frame*
frame_tlvconstructor(gpointer tlvstart,		///<[in] start of TLV for this Frame
		     gconstpointer pktend,	///<[in] first invalid byte past 'tlvstart'
		     gpointer* ignorednewpkt,	///<[ignored] replacement packet
		     gpointer* ignoredpktend)	///<[ignored] end of replacement packet
{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint32		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	Frame *		ret = frame_new(frametype, 0);
	(void)ignorednewpkt; (void)ignoredpktend;
	g_return_val_if_fail(ret != NULL, NULL);

	ret->length = framelength;
	if (framelength > 0) {
		ret->setvalue(ret, g_memdup(framevalue, framelength), framelength
		,	frame_default_valuefinalize);
	}else{
		ret->value = 0;
	}
	return ret;
}
/// Basic "dump a frame" member function - we use g_debug() for output.
/// It would be nice for derived classes to override this as appropriate.
void
_frame_dump(const Frame * f,			///<[in] Frame being dumped
	    const char * prefix)		///<[in] Prefix to put out before each line when dumping it
{
	g_debug("%s%s: type = %d, length = %d dataspace=%zd", 
		prefix,
	        proj_class_classname(f),
		f->type,
		f->length,
		f->dataspace(f));
}
///@}
