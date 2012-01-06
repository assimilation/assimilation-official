/**
 * @file
 * @brief Implements the inbound frame decoding function: Packet-chunk->Frameset-list
 * @details 
 * This code walks through an packet and creates a collection of @ref FrameSet "FramSet"s that correspond to
 * the @ref FrameSet "FrameSet"s that the originator created.
 * In a lot of ways, this is all auxilliary functions for the @ref FrameSet objects.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <projectcommon.h>
#include <generic_tlv_min.h>
#include <frameset.h>
#include <frametypes.h>
#include <signframe.h>
#include <cryptframe.h>
#include <compressframe.h>
#include <tlvhelper.h>
#include <decode_packet.h>
#include <intframe.h>
#include <addrframe.h>
#include <signframe.h>
#include <cstringframe.h>
#include <seqnoframe.h>
#include <nvpairframe.h>
#include <unknownframe.h>

/// @{

#define	FRAMESET_HDR_SIZE	(3*sizeof(guint16))

static const FrameTypeToFrame	framemap[] = FRAMETYPEMAP;
static FramePktConstructor*	frametypemap;
static guint16			maxframetype = 0;
static gboolean			_decode_packet_inityet = FALSE;
FSTATIC void			_decode_packet_init(void);
#define			INITDECODE	{if (!_decode_packet_inityet) {		\
						_decode_packet_inityet = TRUE;	\
						_decode_packet_init();		\
					}}
FSTATIC Frame*	_framedata_to_frameobject(gconstpointer tlvstart, gconstpointer gconstpointer);
FSTATIC FrameSet* _decode_packet_get_frameset_data(gconstpointer, gconstpointer, void const **);
FSTATIC Frame* _decode_packet_framedata_to_frameobject(gconstpointer, gconstpointer, void const ** nextframe);

/// Initialize our frame type map.
/// Should only be called by the INITDECODE macro.
/// Post-condition:  Every element of 'frametypemap' is initialized with a valid function pointer.
void
_decode_packet_init(void)
{
	unsigned	j;

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
/// @return a decoded frame <i>plus</i> pointer to the first byte past this Frame (in 'nextframe')
FSTATIC Frame*
_decode_packet_framedata_to_frameobject(gconstpointer pktstart,	///<[in] Pointer to marshalled Frame data
					gconstpointer pktend,	///<[in] Pointer to first invalid byte past 'pktstart'
					void const ** nextframe)///<[out] Start of next frame (if any)
{
	guint16		frametype = get_generic_tlv_type(pktstart, pktend);
	Frame*	ret;

	INITDECODE;
	if (frametype <= maxframetype) {
		ret = frametypemap[frametype](pktstart, pktend);
	}else{ 
		ret =  unknownframe_tlvconstructor(pktstart, pktend);
	}
	g_return_val_if_fail(ret != NULL, NULL);
	*nextframe = (gconstpointer) ((const guint8*)pktstart + ret->dataspace(ret));
	return ret;
}

/// Construct a basic FrameSet object from the initial marshalled FrameSet data in a packet
FSTATIC FrameSet*
_decode_packet_get_frameset_data(gconstpointer vfsstart,	///<[in] Start of this FrameSet
				 gconstpointer vpktend,		///<[in] First invalid byte after 'vfsstart'
				 const void ** fsnext)		///<[out] Pointer to first byte after this FrameSet
{
	const guint8*	fsstart = vfsstart;
	const guint8*	pktend = vpktend;
	gssize		bytesleft = pktend - fsstart;
	guint16		fstype;
	guint16		fslen;
	guint16		fsflags;
	FrameSet*	ret;

	*fsnext = vpktend;
	if  (bytesleft < (gssize)FRAMESET_HDR_SIZE) {
		return NULL;
	}
	fstype = tlv_get_guint16(fsstart, pktend);
	fslen = tlv_get_guint16(fsstart + sizeof(guint16), pktend);
	fsflags = tlv_get_guint16(fsstart + 2*sizeof(guint16), pktend);
	ret = frameset_new(fstype);
	g_return_val_if_fail(ret != NULL, NULL);
	frameset_set_flags(ret, fsflags);
	*fsnext = (gconstpointer) (fsstart + (3*sizeof(guint16)) + fslen);
	return ret;
}


/// Constructs a GSList list of @ref FrameSet objects from a datagram/packet.
/// That is, it decodes the datagram/packet.
/// @return GSList of @ref FrameSet object pointers.
GSList*
pktdata_to_frameset_list(gconstpointer pktstart,	///<[in] start of packet
			 gconstpointer pktend)		///<[in] first byte past end of packet
{
	gconstpointer	curframeset = pktstart;
	GSList*		ret = NULL;

	while (curframeset < pktend) {
		gconstpointer nextframeset = pktend;
		gconstpointer curframe = (gconstpointer)((const guint8*)curframeset + FRAMESET_HDR_SIZE);
		FrameSet* fs = _decode_packet_get_frameset_data(curframeset, pktend, &nextframeset);

		g_return_val_if_fail(fs != NULL && nextframeset <= pktend, ret);

		while (curframe < nextframeset) {
			gconstpointer nextframe = nextframeset;
			Frame* newframe;
			newframe = _decode_packet_framedata_to_frameobject(curframe, nextframeset, &nextframe);
			if (nextframe > nextframeset) {
				newframe->unref(newframe); newframe=NULL;
				///@todo fix this: frameset_finalize(fs) for the error case
				return ret;
			}
			frameset_append_frame(fs, newframe);
                        newframe->unref(newframe); newframe = NULL;
			curframe = nextframe;
		}
		ret = g_slist_append(ret, fs); fs = NULL;
		curframeset = nextframeset;
	}
	return ret;
}
///@}
