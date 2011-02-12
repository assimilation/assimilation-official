/**
 * @file
 * @brief Implements minimal client-oriented Frame and Frameset capabilities.
 * @details This file contains the minimal Frameset capabilities for a client -
 * enough for it to be able to construct, understand and validate Frames
 * and Framesets.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _FRAME_H
#define _FRAME_H
#include <glib.h>
typedef struct _FrameSet FrameSet;
typedef struct _Frame Frame;

/// This is our basic Frame <b>TLV</b> (type, length, value) format.
/// It is an in-memory representation of Frames which might come from or go to the wire.
/// It is basically a class from which we make many subclasses,
/// and is managed by our @ref ProjectClass system.
///@{
/// @ingroup Frame
struct _Frame {
	guint16		type;				///< Frame <b>T</b>ype (see @ref IndividualFrameFormats - frameformats.h )
	guint16		length;				///< Frame <b>L</b>ength
	gpointer	value;				///< Frame <b>V</b>alue (pointer)
	gsize		(*dataspace)(Frame* self);	///< How much space is needed to marshall this Frame?
	void		(*updatedata)(Frame* self, gpointer tlvptr, gconstpointer pktend, FrameSet* fs); ///< Update packet data
	gboolean	(*isvalid)(Frame* self, gconstpointer tlvptr, gconstpointer pktend); ///< TRUE if TLV data looks valid...
	
	void		(*setvalue)(Frame* self,
				    gpointer value,
				    guint16 length,
				    GDestroyNotify valfinal);
	GDestroyNotify	valuefinalize;			///< optional method for finalizing value
	void		(*finalize)(Frame*);		///< Frame Destructor
};
#define	FRAME_INITSIZE	4	///< (sizeof(Frame.type) + sizeof(Frame.length)) - each 2 bytes
Frame* frame_new(guint16 frame_type, gsize framesize);
Frame* frame_tlvconstructor(gpointer tlvstart, gpointer pktend);
void _frame_default_valuefinalize(gpointer value);
///@}

#endif /* _FRAME_H */
