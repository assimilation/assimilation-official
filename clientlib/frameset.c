/**
 * @file
 * @brief Implements minimal client-oriented FrameSet capabilities.
 * @details This file contains the minimal FrameSet capabilities for a client -
 * enough for it to be able to manage a FrameSet (ordered collection of Frames).
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

/**
 * @defgroup FrameSetFormats 'FrameSet' data format on the wire
 * @{
 * @ingroup WireDataFormats
 * As noted earlier, FrameSets are logical packets.
 * Here is my current thinking about the layout of frameset data - which is a variant
 * of Type, Length, Value (TLV) entries like those used by LLDP and CDP.
 * Below you will see a number of 2-byte integers, which are all in network-byte order.
 * <PRE>
 * +--------------+
 * | framesettype | 16 bits
 * +--------------+
 * |  fs_length   | 16 bits
 * +--------------+
 * |   fsflags    | 16 bits
 * +--------------+
 * |  frames...   | "fs_length" bytes
 * +--------------+
 * </PRE>
 * All framesets look like this - but the content of the fs_length
 * bytes worth of frames at the end change.
 * Any given framesettype has a set of expected frames
 * that might be included - some mandatory, some optional.
 * All others would be considered unexpected - and will be ignored.
 * @}
 */
#include <string.h>
#include <projectcommon.h>
#include <frameset.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>
FSTATIC void _frameset_indir_finalize(void* f);
FSTATIC void _frameset_finalize(AssimObj* self);

///@defgroup FrameSet FrameSet class
/// Class representing a collection of @ref Frame "Frame"s to be sent in a single datagram.
/// Note that more than one FrameSet can be sent in a datagram, but a FrameSet may not
/// be split across datagrams.
///@{
///@ingroup C_Classes


/// static: finalize (free) frame
FSTATIC void
_frameset_indir_finalize(void* f)	///< Frame to finalize
{
	Frame*	frame = CASTTOCLASS(Frame, f);
	frame->baseclass.unref(f);
}

/// static: finalize (free) frameset and all its constituent frames...
FSTATIC void
_frameset_finalize(AssimObj* obj)	///< frameset to finalize
{
	FrameSet* fs = CASTTOCLASS(FrameSet, obj);
	g_return_if_fail(NULL != fs);
	/// @todo should only do this if the frameset won't need retransmitting -
	/// - of course that should be handled by reference counts - not by special code here...
	if (fs->framelist) {
		// Would rather use g_slist_free_full() - but it's too new to be widely deployed...
		while (NULL != fs->framelist) {
			_frameset_indir_finalize(fs->framelist->data);
			fs->framelist->data = NULL;
			fs->framelist = g_slist_delete_link(fs->framelist, fs->framelist);
		}
	}
	if (fs->packet) {
		FREE(fs->packet);
		fs->packet = NULL;
		fs->pktend = NULL;
	}
	memset(fs, 0x0, sizeof(*fs));
	FREECLASSOBJ(fs);
}



/// Construct a new frameset of the given type
FrameSet*
frameset_new(guint16 frameset_type) ///< Type of frameset to create
{
	AssimObj*	obj = assimobj_new(sizeof(FrameSet));
	FrameSet*	s = NEWSUBCLASS(FrameSet, obj);
	g_return_val_if_fail(s != NULL, NULL);
	s->fstype = frameset_type;
	s->framelist = NULL;
	s->packet = NULL;
	s->pktend = NULL;
	s->fsflags = 0;
	s->baseclass._finalize = _frameset_finalize;
	return s;
}

/// Prepend frame to the front of the frame list
void
frameset_prepend_frame(FrameSet* fs,	///< FrameSet to fetch flags for
		       Frame* f)	///< Frame to put at the front of the frame list
{
	g_return_if_fail(NULL != fs && NULL != f);
	f->baseclass.ref(f);
	fs->framelist = g_slist_prepend(fs->framelist, f);
}

/// Append frame to the front of the end of the frame list
void
frameset_append_frame(FrameSet* fs,	///< FrameSet to fetch flags for
		      Frame* f)		///< Frame to put at the back of the frame list
{
	g_return_if_fail(NULL != fs && NULL != f);
	f->baseclass.ref(f);
	fs->framelist = g_slist_append(fs->framelist, f);
}

/// Construct packet to go correspond to this frameset.
/// Once this is done, then this can be either sent out directly
/// or queued with other framesets to send to the machine in question.
/// If it needs to be retransmitted, that can also happen...
/// If encryption methods have changed in the meantime, if we are asked
/// to reconstruct a packet later.
///
void
frameset_construct_packet(FrameSet* fs,		///< FrameSet for which we're creating a packet
			  SignFrame* sigframe,	///< digital Signature method (cannot be NULL)
			  Frame* cryptframe,	///< Optional Encryption method.
						///< This method might change the packet size.
			  Frame* compressframe)	///< Optional Compression method.
						///< It is expected that this method should modify the packet
						///< "in place", and adjust things accordingly.
{
	GSList*		curframe;		// Current frame as we marshall packet...
	gpointer	curpktpos;		// Current position as we marshall packet...
	gsize		pktsize;
	gsize		fssize = 6;		// "frameset" overhead size
	g_return_if_fail(NULL != fs);
	g_return_if_fail(NULL != sigframe);
	// g_return_if_fail(NULL != fs->framelist); // Is an empty frame list OK?

	/*
	 * The general method we employ here is to:
	 * 1. Free the current packet, if any
	 * 2. Remove current Framelist signature, compression, and encryption frames (if any).
	 * 3. Prepend a compression Frame if compm != NULL
	 * 4. Prepend an encryption Frame if cryptm != NULL
	 * 5. Prepend a signature Frame (sigm may not be NULL).
	 * 6. Figure out how much space we think we need to malloc for the packet using Frames.
	 * 7. Malloc enough space.
	 * 8. Populate all the frames into this new packet in reverse order.
	 */

	// Free current packet, if any...
	if (fs->packet) {
		FREE(fs->packet);
		fs->packet = NULL;
		fs->pktend = NULL;
	}
	// Remove any current signature, compression, or encryption frames...
	// (this method only works if they're first, and all together - but that's OK)
	while (fs->framelist) {
		Frame*	item = CASTTOCLASS(Frame, fs->framelist->data);
		g_return_if_fail(NULL != item);
		switch (item->type) {
			case FRAMETYPE_SIG:
			case FRAMETYPE_CRYPT:
			case FRAMETYPE_COMPRESS:
				item->baseclass.unref(item);
				fs->framelist->data = NULL;
				fs->framelist = g_slist_delete_link(fs->framelist, fs->framelist);
				continue;
		}
		break;
	}
	///@note
	///@{
	/// The order we put these special frames in the frameset is important.
	/// We apply them here from last to first, but on the other end
	/// they have to be applied from first to last.
	/// That means that we do these things in this order:
	///	Compress the frame - all the frame after the @ref FRAMETYPE_COMPRESS TLV
	///	Encrypt the frame - all the frame after the @ref FRAMETYPE_CRYPT TLV
	///	Perform a signature over the whole frame after the @ref FRAMETYPE_SIG TLV
	///
	/// At the other end, this is reversed.
	///	Check the signature according to the initial @ref FRAMETYPE_SIG frame,
	///		discard if incorrect.
	///	Decrypt the frame after the @ref FRAMETYPE_CRYPT TLV
	///	Uncompress the frame after the @ref FRAMETYPE_COMPRESS TLV
	///
	/// Encryption tends to make data hard to compress, so it's better to compress before
	/// encrypting.
	///@}
	/// 
	if (NULL != compressframe) {
		frameset_prepend_frame(fs, compressframe);
	}
	if (NULL != cryptframe) {
		frameset_prepend_frame(fs, cryptframe);
	}
	// "sigframe" cannot be NULL (see check above)
	frameset_prepend_frame(fs, CASTTOCLASS(Frame, sigframe));

	// Reverse list...
	fs->framelist = g_slist_reverse(fs->framelist);

	// Add "end" frame to the "end" - if not already present...
	if (CASTTOCLASS(Frame, fs->framelist->data)->type != FRAMETYPE_END) {
                Frame* endframe = frame_new(FRAMETYPE_END, 0);
		frameset_prepend_frame(fs, endframe);
                endframe->baseclass.unref(endframe);
	}

	pktsize = fssize;
	for (curframe=fs->framelist; curframe != NULL; curframe = g_slist_next(curframe)) {
		Frame* frame = CASTTOCLASS(Frame, curframe->data);
		pktsize += frame->dataspace(frame);
	}
	fs->packet = MALLOC0(pktsize);
	fs->pktend = ((guint8*)fs->packet + pktsize);
	g_return_if_fail(fs->packet != NULL);

	curpktpos = fs->pktend;

	// Marshall out all our data - in reverse order...
	for (curframe=fs->framelist; curframe != NULL; curframe = g_slist_next(curframe)) {
		Frame* frame = CASTTOCLASS(Frame, curframe->data);
	
		curpktpos = ((guint8*)curpktpos) - frame->dataspace(frame);
		g_return_if_fail(curpktpos >= fs->packet);
		set_generic_tlv_type(curpktpos, frame->type, fs->pktend);
		set_generic_tlv_len(curpktpos, frame->length, fs->pktend);
		frame->updatedata(frame, curpktpos, fs->pktend, fs);
		if (!frame->isvalid(frame, curpktpos, fs->pktend)) {
			g_error("Generated %s frame is not valid(!)"
			, proj_class_classname(frame));
		}
	}
	g_return_if_fail(curpktpos == (((guint8*)fs->packet)+fssize));
	// Reverse list - putting it back in the right order
	fs->framelist = g_slist_reverse(fs->framelist);
	// Write out the initial FrameSet header.
	set_generic_tlv_type(fs->packet, fs->fstype, ((guint8*)fs->packet)+fssize);
	set_generic_tlv_len(fs->packet, pktsize-fssize, ((guint8*)fs->packet)+fssize);
	tlv_set_guint16(((guint8*)fs->packet)+4, fs->fsflags, ((guint8*)fs->packet)+fssize);
}

/// Return the flags currently set on this FrameSet.
guint16
frameset_get_flags(FrameSet* fs)	///< FrameSet to fetch fsflags for
{
	g_return_val_if_fail(NULL != fs, 0xffff);
	return fs->fsflags;
}

/// Set (OR in) the given set of FrameSet flags.
guint16
frameset_set_flags(FrameSet* fs,	///< FrameSet to fetch flags for
		   guint16 flagbits)	///< Bits to set
{
	g_return_val_if_fail(NULL != fs, 0xffff);
	fs->fsflags |= flagbits;
	return fs->fsflags;
}

/// Clear the given set of FrameSet flags (& ~flagbits)
guint16
frameset_clear_flags(FrameSet* fs,	///< FrameSet to fetch flags for
		     guint16 flagbits)	///< Bits to clear
{
	g_return_val_if_fail(NULL != fs, 0xffff);
	g_return_val_if_fail(flagbits != 0x0000, fs->fsflags);
	fs->fsflags &= ~flagbits;
	return fs->fsflags;
}

/// Append the given Frame to a FrameSet packet.
/// @return updated current position
gpointer
frame_append_to_frameset_packet(FrameSet* fs,		///< FrameSet to append frame to
				Frame* f,		///< Frame to append...
				gpointer curpktpos)	///< Current position in packet (not NULL)
{
	guint8 *	curpos = curpktpos;
	guint8 *	endpos = fs->pktend;

	g_return_val_if_fail(fs != NULL && f != NULL && fs->packet != NULL && curpktpos != NULL, NULL);
	g_return_val_if_fail((curpos + f->dataspace(f)) <= endpos, NULL);

	tlv_set_guint16(curpos, f->type, fs->pktend);
	curpos += 2; // sizeof(guint16)
	tlv_set_guint16(curpos, f->length, fs->pktend);
	curpos += 2; // sizeof(guint16)
	if (f->length > 0) {
		// Zero-length frames are just fine.
		memcpy(curpos, f->value, f->length);
	}
	curpos += f->length;
	return (gpointer)curpos;
}
/// Dump out a FrameSet
void
frameset_dump(const FrameSet* fs)	///< FrameSet to dump
{
	GSList*	curframe;
	g_debug("BEGIN Dumping FrameSet:");
	for (curframe=fs->framelist; curframe != NULL; curframe = g_slist_next(curframe)) {
		Frame* frame = CASTTOCLASS(Frame, curframe->data);
		frame->dump(frame, ".... ");
	}
	g_debug("END FrameSet dump");
}
///@}
