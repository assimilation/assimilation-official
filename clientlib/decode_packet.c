/**
 * @file
 * @brief Implements the inbound frame decoding function: Packet-chunk->Frameset-list
 * @details 
 * This code walks through an packet and creates a collection of @ref FrameSet "FramSet"s that correspond to
 * the @ref FrameSet "FrameSet"s that the originator created.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <projectcommon.h>
#include <frameset.h>
#include <signframe.h>
#include <frameformats.h>
#include <generic_tlv_min.h>
#include <decode_packet.h>
#include <intframe.h>
#include <addrframe.h>
#include <signframe.h>
#include <cstringframe.h>
#include <seqnoframe.h>
#include <unknownframe.h>

/// @{

static const FrameTypeToFrame	framemap[] =
{
	{FRAMETYPE_END,		frame_tlvconstructor},
	{FRAMETYPE_SIG,		signframe_tlvconstructor},
	{FRAMETYPE_REQID,	seqnoframe_tlvconstructor},
	{FRAMETYPE_REPLYID,	seqnoframe_tlvconstructor},
	{FRAMETYPE_PKTDATA,	frame_tlvconstructor},
	{FRAMETYPE_WALLCLOCK,	intframe_tlvconstructor},
	{FRAMETYPE_INTERFACE,	cstringframe_tlvconstructor},
};
static FramePktConstructor*	frametypemap;
static int			maxframetype;
static gboolean		_decode_packet_inityet = FALSE;
FSTATIC void		_init_decode_packet(void);
#define			INITDECODE	{if (!_decode_packet_inityet) {		\
						_decode_packet_inityet = TRUE;	\
						_init_decode_packet();		\
					}}
FSTATIC Frame*		_framedata_to_frameobject(gpointer tlvstart, gpointer pktend);

/// Initialize our frame type map.
/// Should only be called by the INITDECODE macro.
/// Post-condition:  Every element of 'frametypemap' is initialized with a valid function pointer.
void
_init_decode_packet(void)
{
	int	j;
	int	maxframetype = 0;

	for (j=0; j < DIMOF(framemap); ++j) {
		if (framemap[j].frametype > maxframetype) {
			maxframetype = framemap[j].frametype;
		}
	}
	frametypemap = MALLOC0((maxframetype+1)*sizeof(gpointer));
	for (j=0; j <= maxframetype; ++j) {
		frametypemap[j] = unknownframe_tlvconstructor;
	}
	for (j=0; j < DIMOF(framemap); ++j) {
		frametypemap[framemap[j].frametype] = framemap[j].constructor;
	}
}
/// Given a pointer to a TLV entry for the data corresponding to a Frame, construct a corresponding Frame
FSTATIC Frame*
_framedata_to_frameobject(gpointer pktstart, gpointer pktend)
{
	guint16		frametype = get_generic_tlv_type(pktstart, pktend);
	//guint16		framelen = get_generic_tlv_len(pktstart, pktend);

	INITDECODE;
	if (frametype <= maxframetype) {
		return frametypemap[frametype](pktstart, pktend);
	}
	return unknownframe_tlvconstructor(pktstart, pktend);
}

/// Constructs a GSList list of @ref FrameSet objects from a datagram/packet.
/// That is, it decodes the datagram/packet.
/// @ret GSList of @ref FrameSet object pointers.
GSList*
pktdata_to_frameset_list(gpointer pktstart, gpointer pktend)
{
	INITDECODE;
	return NULL;
}


///@}
