/**
 * @file
 * @brief Implements basic Frame class.
 * @details This Frame base class defines semantics for simple binary (blob) frames
 * without any further refined semantics.  It is used as the base class for
 * several derived classes.
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

#ifndef _FRAME_H
#define _FRAME_H
#include <projectcommon.h>
#include <assimobj.h>
#include <generic_tlv_min.h>
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
	guint32		length;				///< Frame <b>L</b>ength
	gpointer	value;				///< Frame <b>V</b>alue (pointer)
	gsize		(*dataspace)(const Frame* self);///< How much space is needed to marshall this Frame?
	void		(*updatedata)(Frame* self, gpointer tlvptr, gconstpointer pktend, FrameSet* fs); ///< Update packet data
	gboolean	(*isvalid)(const Frame* self, gconstpointer tlvptr, gconstpointer pktend); ///< TRUE if TLV data looks valid...
	
	void		(*setvalue)(Frame* self,
				    gpointer value,
				    guint32 length,
				    GDestroyNotify valfinal);		///< member function for setting value
	void		(*dump)(const Frame* self, const char * prefix);///< member function for dumping Frame
	GDestroyNotify	valuefinalize;					///< method for finalizing value
};
#define	FRAME_INITSIZE	GENERICTLV_HDRSZ 
WINEXPORT Frame*	frame_new(guint16 frame_type, gsize framesize);
WINEXPORT Frame*	frame_tlvconstructor(gpointer tlvstart, gconstpointer pktend, gpointer*,gpointer*);
WINEXPORT void frame_default_valuefinalize(gpointer value);
///@}

#endif /* _FRAME_H */
