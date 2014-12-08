/**
 * @file
 * @brief Implements minimal client-oriented Frame and Frameset capabilities.
 * @details This file contains the minimal Frameset capabilities for a client -
 * enough for it to be able to construct, understand and validate Frames
 * and Framesets.
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
#ifndef _FRAMESET_H
#define _FRAMESET_H
#include <projectcommon.h>
#include <glib.h>
#include <assimobj.h>
#include <frame.h>
#include <signframe.h>
#include <cryptframe.h>
#include <framesettypes.h>
#include <generic_tlv_min.h>
#include <seqnoframe.h>
#include <compressframe.h>

/// @ref FrameSet - used for collecting @ref Frame "Frame"s when not on the wire,
/// and for marshalling/demarshalling them for/from the wire.
/// There are a few "special" frames that have to appear first, and in a certain order.
/// These frames have their values computed based on the values of the frames which follow them
/// in the <i>framelist</i>.  Some of them (notably encryption) can restructure and modify the
/// packet contents which follow them.
/// This is managed by our @ref ProjectClass system.
struct _FrameSet {
	AssimObj	baseclass;
	GSList*		framelist;	///< List of frames in this FrameSet.
					/// @todo figure out if GSlist or GQueue is better...
	gpointer	packet;		///< Pointer to packet (when constructed)
	gpointer	pktend;		///< Last byte past the end of the packet.
	guint16		fstype;		///< Type of frameset.
	guint16		fsflags;	///< Flags for frameset.
	SeqnoFrame*	_seqframe;	///< sequence number for this frameset
	SeqnoFrame*	(*getseqno)(FrameSet*);	///< Return the sequence number for this frameset (if any)
};
#define	FRAMESET_INITSIZE	(GENERICTLV_HDRSZ+sizeof(guint16))

WINEXPORT FrameSet*	frameset_new(guint16 frameset_type);
WINEXPORT void		frameset_prepend_frame(FrameSet* fs, Frame* f);
WINEXPORT void		frameset_append_frame(FrameSet* fs, Frame* f);
WINEXPORT void		frameset_construct_packet(FrameSet* fs, SignFrame* sign, CryptFrame* crypt, CompressFrame* compress);
WINEXPORT Frame*	frame_new(guint16 frame_type, gsize framesize);
WINEXPORT guint16	frameset_get_flags(FrameSet* fs);
WINEXPORT guint16	frameset_set_flags(FrameSet* f, guint16 flagbits);
WINEXPORT guint16	frameset_clear_flags(FrameSet* f, guint16 flagbits);
WINEXPORT gpointer	frame_append_to_frameset_packet(FrameSet*, Frame*, gpointer curpos);
WINEXPORT void		frameset_dump(const FrameSet*);

#endif /* _FRAMESET_H */
