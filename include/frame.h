/**
 * @file
 * @brief Implements basic Frame class.
 * @details This Frame base class defines semantics for simple binary (blob) frames
 * without any further refined semantics.  It is used as the base class for
 * several derived classes.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _FRAME_H
#define _FRAME_H
#include <projectcommon.h>
#include <assimobj.h>
typedef struct _FrameSet FrameSet;
typedef struct _Frame Frame;

///@{
/// @ingroup Frame

/// This is the base @ref Frame object (in-memory <b>TLV</b> (type, length, value))
/// for every general component of a packet.
/// It is an in-memory representation of Frames which might come from or go to the wire.
/// It is the base class for all @ref Frame objects,
/// and is managed by our @ref ProjectClass system.
struct _Frame {
	AssimObj	baseclass;			///< Base object class for our Class system
	guint16		type;				///< Frame <b>T</b>ype (see @ref IndividualFrameFormats - frameformats.h )
	guint16		length;				///< Frame <b>L</b>ength
	gpointer	value;				///< Frame <b>V</b>alue (pointer)
	gsize		(*dataspace)(Frame* self);	///< How much space is needed to marshall this Frame?
	void		(*updatedata)(Frame* self, gpointer tlvptr, gconstpointer pktend, FrameSet* fs); ///< Update packet data
	gboolean	(*isvalid)(const Frame* self, gconstpointer tlvptr, gconstpointer pktend); ///< TRUE if TLV data looks valid...
	
	void		(*setvalue)(Frame* self,
				    gpointer value,
				    guint16 length,
				    GDestroyNotify valfinal);		///< member function for setting value
	void		(*dump)(const Frame* self, const char * prefix);///< member function for dumping Frame
	GDestroyNotify	valuefinalize;					///< method for finalizing value
};
#define	FRAME_INITSIZE	4	///< (sizeof(Frame.type) + sizeof(Frame.length)) - each 2 bytes
WINEXPORT Frame*	frame_new(guint16 frame_type, gsize framesize);
WINEXPORT Frame*	frame_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend);
WINEXPORT void _frame_default_valuefinalize(gpointer value);
///@}

#endif /* _FRAME_H */
