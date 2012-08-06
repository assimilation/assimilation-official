/**
 * @file
 * @brief Implements the inbound frame decoding function: Packet-chunk->FrameSet-list
 * @details 
 * This code walks through an packet and creates a collection of @ref FrameSet "FramSet"s that correspond to
 * the @ref FrameSet "FrameSet"s that the originator created.
 * In a lot of ways, this is all auxilliary functions for the @ref FrameSet objects.
 *
 * @author &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <memory.h>
#include <projectcommon.h>
#include <assimobj.h>
#include <generic_tlv_min.h>
#include <frameset.h>
#include <frametypes.h>
#include <signframe.h>
#include <cryptframe.h>
#include <compressframe.h>
#include <tlvhelper.h>
#include <packetdecoder.h>
#include <intframe.h>
#include <addrframe.h>
#include <ipportframe.h>
#include <signframe.h>
#include <cstringframe.h>
#include <seqnoframe.h>
#include <nvpairframe.h>
#include <unknownframe.h>
#include <frametypes.h>
/// @defgroup PacketDecoder PacketDecoder class
/// A base class for transforming an incoming packet into a GSList of @ref FrameSet objects.
/// Each @ref FrameSet is composed of a series of @ref Frame "Frames".
///@{
///@ingroup C_Classes

#define	FRAMESET_HDR_SIZE	(3*sizeof(guint16))


FSTATIC Frame*	_framedata_to_frameobject(PacketDecoder*, gconstpointer, gconstpointer gconstpointer);
FSTATIC FrameSet* _decode_packet_get_frameset_data(gconstpointer, gconstpointer, void const **);
FSTATIC Frame* _decode_packet_framedata_to_frameobject(PacketDecoder*, gconstpointer, gconstpointer, void const **);
FSTATIC GSList* _pktdata_to_framesetlist(PacketDecoder*, gconstpointer, gconstpointer);

FSTATIC void _packetdecoder_finalize(AssimObj*);

/// Function for finalizing
FSTATIC void
_packetdecoder_finalize(AssimObj* selfobj)
{
	PacketDecoder* self = CASTTOCLASS(PacketDecoder, selfobj);

	FREE(self->_frametypemap);	self->_frametypemap = NULL;
	self->_pfinalize(selfobj);
}

static FrameTypeToFrame _defaultmap[] = FRAMETYPEMAP;

/// Initialize our frame type map.
/// Post-condition:  Every element of 'frametypemap' is initialized with a valid function pointer.
PacketDecoder*
packetdecoder_new(guint objsize, const FrameTypeToFrame* framemap, gint mapsize)
{
	gint		j;
	AssimObj*	baseobj;
	PacketDecoder*	self;
	
	if (objsize < sizeof(PacketDecoder)) {
		objsize = sizeof(PacketDecoder);
	}
	if (NULL == framemap) {
		framemap = _defaultmap;
		mapsize = DIMOF(_defaultmap);
	}

	baseobj = assimobj_new(objsize);
	proj_class_register_subclassed(baseobj, "PacketDecoder");
	self = CASTTOCLASS(PacketDecoder, baseobj);
	

	self->_pfinalize = baseobj->_finalize;
	baseobj->_finalize = _packetdecoder_finalize;
	self->pktdata_to_framesetlist = _pktdata_to_framesetlist;
	self->_maxframetype = 0;
	self->_framemap = framemap;
	self->_framemaplen = mapsize;

	for (j=0; j < self->_framemaplen; ++j) {
		if (self->_framemap[j].frametype > self->_maxframetype) {
			self->_maxframetype = self->_framemap[j].frametype;
		}
	}
	self->_frametypemap = MALLOC0((self->_maxframetype+1)*sizeof(gpointer));
	for (j=0; j <= self->_maxframetype; ++j) {
		self->_frametypemap[j] = unknownframe_tlvconstructor;
	}
	for (j=0; j < self->_framemaplen; ++j) {
		self->_frametypemap[self->_framemap[j].frametype] = self->_framemap[j].constructor;
	}
	return self;
}

/// Given a pointer to a TLV entry for the data corresponding to a Frame, construct a corresponding Frame
/// @return a decoded frame <i>plus</i> pointer to the first byte past this Frame (in 'nextframe')
FSTATIC Frame*
_decode_packet_framedata_to_frameobject(PacketDecoder*self,	///<[in/out] PacketDecoder object
					gconstpointer pktstart,	///<[in] Pointer to marshalled Frame data
					gconstpointer pktend,	///<[in] Pointer to first byte past end of pkt
					void const ** nextframe)///<[out] Start of next frame (if any)
{
	guint16		frametype = get_generic_tlv_type(pktstart, pktend);
	Frame*	ret;

	if (frametype <= self->_maxframetype) {
		ret = self->_frametypemap[frametype](pktstart, pktend);
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
				 gconstpointer vpktend,		///<[in] First byte past end of packet
				 const void ** fsnext)		///<[out] Pointer to first byte after this FrameSet
								///<(that is, the first byte of contained frames)
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
_pktdata_to_framesetlist(PacketDecoder*self,		///<[in] PacketDecoder object
			 gconstpointer pktstart,	///<[in] start of packet
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
			newframe = _decode_packet_framedata_to_frameobject(self, curframe, nextframeset, &nextframe);
			if (nextframe > nextframeset) {
				newframe->baseclass.unref(newframe); newframe=NULL;
				fs->unref(fs);
				return ret;
			}
			frameset_append_frame(fs, newframe);
                        newframe->baseclass.unref(newframe); newframe = NULL;
			curframe = nextframe;
		}
		ret = g_slist_append(ret, fs); fs = NULL;
		curframeset = nextframeset;
	}
	return ret;
}
///@}
