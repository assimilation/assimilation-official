/**
 * @file
 * @brief Implements the @ref ConfigContext class - providing configuration values for nanoprobe runtime
 * @details Allows for the holding of configuration values of various kinds.
 *
 * @author &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <frame.h>
#include <generic_tlv_min.h>
#include <memory.h>
/**
 *
 */
FSTATIC void _frame_default_finalize(AssimObj * self);
FSTATIC gsize _frame_total_size(Frame* f);
FSTATIC gboolean _frame_default_isvalid(const Frame *, gconstpointer,	gconstpointer);
FSTATIC void _frame_setvalue(Frame *, gpointer, guint16, GDestroyNotify valnotify);
FSTATIC void _frame_updatedata(Frame *, gpointer, gconstpointer, FrameSet*);
FSTATIC void _frame_dump(const Frame *, const char * prefix);
FSTATIC void _frame_default_valuefinalize(gpointer value);

///@defgroup Frame Frame class
/// Class for holding/storing binary blobs -  Base class for all the other Frame types.
///@{
///@ingroup C_Classes

/// Finalize a Frame
FSTATIC void
_frame_default_finalize(AssimObj * obj) ///< Frame to finalize
{
	Frame*	self = CASTTOCLASS(Frame, obj);
	if (self->value && self->valuefinalize) {
		self->valuefinalize(self->value);
	}
	memset(self, 0x00, sizeof(Frame));
	_assimobj_finalize(obj);
}
/// Finalize a Frame
FSTATIC void
_frame_default_valuefinalize(gpointer value) ///< Value to finalize
{
	if (value) {
		FREE(value);
	}
}

/// Return total space required to put this frame in a packet (marshalled size)
FSTATIC gsize
_frame_total_size(Frame* f)	///< Frame to return the marshalled size of
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

/// 'setvalue' @ref Frame member function.
FSTATIC void
_frame_setvalue(Frame * self,			///< Frame object ('this')
		gpointer value,			///< Value to save away
		guint16	length,			///< Length of value
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
		  FrameSet* fs)			///< Frameset to update (or not)
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
	if (framesize < sizeof(Frame)) {
		framesize = sizeof(Frame);
	}
	newobj   = assimobj_new(framesize);
	if (newobj != NULL) {
		proj_class_register_subclassed(newobj, "Frame");
		newframe = CASTTOCLASS(Frame, newobj);
		newobj->_finalize	= _frame_default_finalize;
		newframe->type		= frame_type;
		newframe->length	= 0;
		newframe->value		= NULL;
		newframe->dataspace	= _frame_total_size;
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
frame_tlvconstructor(gconstpointer tlvstart,	///<[in] start of TLV for this Frame
		     gconstpointer pktend)	///<[in] first invalid byte past 'tlvstart'
{
	guint16		frametype = get_generic_tlv_type(tlvstart, pktend);
	guint16		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	Frame *		ret = frame_new(frametype, 0);
	g_return_val_if_fail(ret != NULL, NULL);

	ret->length = framelength;
	ret->setvalue(ret, g_memdup(framevalue, framelength), framelength, _frame_default_valuefinalize);
	return ret;
}
/// Basic "dump a frame" member function - we use g_debug() for output.
/// It would be nice for derived classes to override this as appropriate.
void
_frame_dump(const Frame * f,			///<[in] Frame being dumped
	    const char * prefix)		///<[in] Prefix to put out before each line when dumping it
{
	g_debug("%s%s: type = %d, length = %d", 
		prefix,
	        proj_class_classname(f),
		f->type,
		f->length);
}
///@}
