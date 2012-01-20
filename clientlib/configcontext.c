/**
 * @file
 * @brief Implements the @ref Frame class - the lowest level of data organization for our packets.
 * @details This file contains the minimal Frame capabilities for a client -
 * enough for it to be able to construct, understand and validate Frames.
 * Note that the decoding of packets into Frames is an interesting process, not yet defined...
 * @see FrameSet, GenericTLV
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <string.h>
#include <projectcommon.h>
#include <frameset.h>
#include <frame.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>
/**
 * @defgroup WireDataFormats Data Formats on the Wire (sent and/or received)
 * @{
 * On the wire we send datagrams.
 * Each datagram is a set of one or more @ref FrameSet "FrameSet"s.
 * Each @ref FrameSet "FrameSet" contains a set of one or more @ref Frame "Frame"s.
 * Reliable delivery is handled at the @ref FrameSet "FrameSet" level.
 * @}
 *
 * @defgroup FrameFormats 'Frame' data format on the wire
 * @{
 * @ingroup WireDataFormats
 * Below is the general format for a Frame - which holds general binary data.
 * <PRE>
 * +--------------+-----------+------------------+
 * |   frametype  | f_length  |  frame-value(s)  |
 * |   (16 bits)  | (16-bits) | "f_length" bytes |
 * +--------------+-----------+------------------+
 * </PRE>
 * For any given "frametype", there is a fixed expectation of what 
 * its "frameval" ought to look like - that is, what the data type 
 * and structure of "frameval" is.
 * The formats of individual frame types are documented above the #defines for each frame type in the
 * group @ref IndividualFrameFormats.
 * The generic (base class) Frame is a simple binary object (blob) type Frame.
 * @}
 */
FSTATIC void _frame_default_finalize(Frame * self);
FSTATIC gsize _frame_total_size(Frame* f);
FSTATIC gboolean _frame_default_isvalid(const Frame *, gconstpointer,	gconstpointer);
FSTATIC void _frame_setvalue(Frame *, gpointer, guint16, GDestroyNotify valnotify);
FSTATIC void _frame_updatedata(Frame *, gpointer, gconstpointer, FrameSet*);
FSTATIC void _frame_dump(const Frame *, const char * prefix);
FSTATIC void _frame_ref(Frame *);
FSTATIC void _frame_unref(Frame *);

///@defgroup Frame Frame class
/// Class for holding/storing binary blobs -  Base class for all the other Frame types.
///@{
///@ingroup C_Classes

/// Finalize a Frame
FSTATIC void
_frame_default_finalize(Frame * self) ///< Frame to finalize
{
	if (self->value && self->valuefinalize) {
		self->valuefinalize(self->value);
	}
	memset(self, 0x00, sizeof(Frame));
	FREECLASSOBJ(self);
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
FSTATIC void
_frame_ref(Frame * self)
{
	self->refcount += 1;
}
FSTATIC void
_frame_unref(Frame * self)
{
	g_return_if_fail(self->refcount >= 1);
	self->refcount -= 1;
	if (self->refcount == 0) {
		self->_finalize(self);
	}
}

/// Construct a new frame - allowing for "derived" frame types...
/// This can be used directly for creating basic binary frames, or by derived classes.
Frame*
frame_new(guint16 frame_type,	///< TLV type of Frame
	  gsize framesize)	///< size of frame structure (or zero for sizeof(Frame))
{
	Frame * newframe;
	if (framesize < sizeof(Frame)) {
		framesize = sizeof(Frame);
	}
	newframe = MALLOCCLASS(Frame, framesize);
	if (newframe != NULL) {
		newframe->type = frame_type;
		newframe->length = 0;
		newframe->value = NULL;
		newframe->dataspace	= _frame_total_size;
		newframe->_finalize	= _frame_default_finalize;
		newframe->isvalid	= _frame_default_isvalid;
		newframe->setvalue	= _frame_setvalue;
		newframe->updatedata	= _frame_updatedata;
		newframe->dump		= _frame_dump;
		newframe->valuefinalize	= NULL;
		newframe->refcount	= 1;
		newframe->ref		= _frame_ref;
		newframe->unref		= _frame_unref;
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
