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
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <glib.h>
#include <frame.h>
#include <signframe.h>

#ifndef _FRAMESET_H
#define _FRAMESET_H
/// This is our basic FrameSet collection data structure - used for collecting @ref Frame "Frame"s
/// when not on the wire, and for marshalling/demarshalling them for the wire.
/// There are a few "special" frames that have to appear first, and in a certain order.
/// These frames have their values computed based on the values of the frames which follow them
/// in the <i>framelist</i>.  Some of them (notably encryption) can restructure and modify the
/// packet contents which follow them.
/// This is managed by our @ref ProjectClass system.
struct _FrameSet {
	GSList*		framelist;	///< List of frames in this FrameSet.
					/// @todo figure out if GSlist or GQueue is better...
	gpointer	packet;		///< Pointer to packet (when constructed)
	gpointer	pktend;		///< Last byte past the end of the packet.
	guint16		fstype;		///< Type of frameset.
	guint16		fsflags;	///< Flags for frameset.
	void		(*finalize)(FrameSet*); ///< FrameSet Destructor
};
#define	FRAMESET_INITSIZE	6	///< type+length+flags - each 2 bytes


FrameSet*	frameset_new(guint16 frameset_type);
void		frameset_prepend_frame(FrameSet* fs, Frame* f);
void		frameset_append_frame(FrameSet* fs, Frame* f);
void		frameset_construct_packet(FrameSet* fs, SignFrame* sign, Frame* crypt, Frame* compress);
Frame*		frame_new(guint16 frame_type, gsize framesize);
guint16		frameset_get_flags(FrameSet* fs);
guint16		frameset_set_flags(FrameSet* f, guint16 flagbits);
guint16		frameset_clear_flags(FrameSet* f, guint16 flagbits);
gpointer	frame_append_to_frameset_packet(FrameSet*, Frame*, gpointer curpos);
void		frameset_dump(const FrameSet*);

#define		FRAMESETTYPE_HEARTBEAT		1	///< A heartbeat packet
#define		FRAMESETTYPE_NAK		2	///< We don't like the frameset mentioned
#define		FRAMESETTYPE_PING		3	///< Are you alive?
#define		FRAMESETTYPE_PONG		4	///< yes, I'm alive

#define		FRAMESETTYPE_HBDEAD		16	///< System named in packet appears to be dead.
#define		FRAMESETTYPE_CLIENTCONFIG	17	///< Packet contains client configuration directives
#define		FRAMESETTYPE_SWDISCOVER		18	///< Packet encapsulates switch discovery packet
#define		FRAMESETTYPE_LOCALNETDISCOVER	19	///< Packet contains local network config data
#define		FRAMESETTYPE_ARPDISCOVER	20	///< Packet contains ARP table data

#endif /* _FRAMESET_H */
