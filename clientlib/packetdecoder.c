/**
 * @file
 * @brief Implements the inbound frame decoding function: Packet-chunk->FrameSet-list
 * @details 
 * This code walks through an packet and creates a collection of @ref FrameSet "FramSet"s that correspond to
 * the @ref FrameSet "FrameSet"s that the originator created.
 * In a lot of ways, this is all auxilliary functions for the @ref FrameSet objects.
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
#include <memory.h>
#include <projectcommon.h>
#include <assimobj.h>
#include <generic_tlv_min.h>
#include <frameset.h>
#include <frametypes.h>
#include <signframe.h>
#include <cryptcurve25519.h>
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



FSTATIC Frame*	_framedata_to_frameobject(PacketDecoder*, gpointer, gconstpointer, gconstpointer);
FSTATIC FrameSet* _decode_packet_get_frameset_data(gpointer, gconstpointer, gpointer *);
FSTATIC Frame* _decode_packet_framedata_to_frameobject(PacketDecoder*, gpointer*, gconstpointer*, gpointer*);
FSTATIC GSList* _pktdata_to_framesetlist(PacketDecoder*, gpointer, gconstpointer);

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
_decode_packet_framedata_to_frameobject(PacketDecoder* self,	///<[in/out] PacketDecoder object
					gpointer* pktstart,///<[in/out] Marshalled Frame data
					gconstpointer* pktend,	///<[in/out] 1st byte past pkt end
					gpointer* newpacket)	///<[out] Replacement packet from
								///<frame decoding (if any)
{
	guint16		frametype = get_generic_tlv_type(*pktstart, *pktend);
	gpointer	newpacketend = NULL;
	Frame*		ret;

	*newpacket = NULL;
	// A note: It's easy to get these gpointer* objects confused.
	// Because they're void**, they can be a bit too flexible ;-)
	if (frametype <= self->_maxframetype) {
		ret = self->_frametypemap[frametype](*pktstart, *pktend, newpacket, &newpacketend);
	}else{ 
		ret =  unknownframe_tlvconstructor(*pktstart, *pktend, newpacket, &newpacketend);
	}
	g_return_val_if_fail(ret != NULL, NULL);
	if (NULL == *newpacket) {
		*pktstart = (gpointer) ((guint8*)*pktstart + ret->dataspace(ret));
	}else{
		*pktstart = *newpacket;
		*pktend = newpacketend;
	}
	return ret;
}

/// Construct a basic FrameSet object from the initial marshalled FrameSet data in a packet
FSTATIC FrameSet*
_decode_packet_get_frameset_data(gpointer vfsstart,		///<[in] Start of this FrameSet
				 gconstpointer vpktend,		///<[in] First byte past end of packet
				 gpointer* fsnext)		///<[out] Pointer to first byte after this FrameSet
								///<(that is, the first byte of contained frames)
{
	guint8*		fsstart = vfsstart;
	const guint8*	pktend = vpktend;
	gssize		bytesleft = pktend - fsstart;
	guint16		fstype;
	guint32		fslen;
	guint16		fsflags;
	FrameSet*	ret;

	*fsnext = NULL;
	if  (bytesleft < (gssize)FRAMESET_INITSIZE) {
		return NULL;
	}
	fstype = get_generic_tlv_type(fsstart, pktend);
	fslen = get_generic_tlv_len(fsstart, pktend);
	fsflags = tlv_get_guint16(fsstart + GENERICTLV_HDRSZ, pktend);
	ret = frameset_new(fstype);
	g_return_val_if_fail(ret != NULL, NULL);
	frameset_set_flags(ret, fsflags);
	*fsnext = (gpointer) (fsstart + FRAMESET_INITSIZE + fslen);
	return ret;
}


/// Constructs a GSList list of @ref FrameSet objects from a datagram/packet.
/// That is, it decodes the datagram/packet.
/// @return GSList of @ref FrameSet object pointers.
GSList*
_pktdata_to_framesetlist(PacketDecoder*self,		///<[in] PacketDecoder object
			 gpointer pktstart,		///<[in] start of packet
			 gconstpointer pktend)		///<[in] first byte past end of packet
{
	gpointer	curframeset = pktstart;
	GSList*		ret = NULL;

	// Loop over all the FrameSets in the packet we were given.
	while (curframeset < pktend) {
		gpointer	nextframeset = NULL;
		gpointer	framestart = ((guint8*)curframeset + FRAMESET_INITSIZE);
		gpointer	curframe;
		FrameSet*	fs = _decode_packet_get_frameset_data(curframeset, pktend, &nextframeset);
		gconstpointer	fsend = pktend;
		gpointer	newframestart = NULL;
		gboolean	firstframe = TRUE;

		g_return_val_if_fail(fs != NULL,  ret);

		if (!is_valid_generic_tlv_packet(framestart, pktend)) {
			g_warning("%s.%d:  Frameset type %d not a valid TLV frameset"
			,	__FUNCTION__, __LINE__, fs->fstype);
			UNREF(fs);
			goto getnextframeset;
		}

		// Construct this FrameSet from the series of frames encoded in the packet.
		// Note that two special kinds of frames can alter the packet we're examining.
		// This is explained in more detail inside the loop.
		curframe = framestart;
		while (curframe != NULL && curframe < fsend) {
			Frame*		newframe;
			gpointer	newpacket = NULL;
			// The first special case frame is the compression frame, in which case the
			// remaining packet is replaced by a new, larger (decompressed) packet.
			//
			// The second type is the encryption packet, in which case the remaining
			// packet is replaced by a new chunk of data which will have different
			// (decrypted) content, and would normally be expected to be the same size
			// as the original.
			//
			// This means that "decode_packet_framedata_to_frameobject" might replace the
			// packet data we've been looking at.
			// (FWIW: It's perfectly OK to have an encryption frame followed by a
			// (embedded) compression frame -- both kinds can occur in the same FrameSet).
			newframe = _decode_packet_framedata_to_frameobject(self, &curframe, &fsend, &newpacket);
			if (newpacket) {
				if (newframestart != NULL) {
					// We did packet replacement more than once...
					g_free(newframestart);
				}
				newframestart = newpacket;
			}
			if (NULL == newframe) {
				UNREF(fs);
				goto getnextframeset;
			}
			if (TRUE == firstframe) {
				if (!OBJ_IS_A(newframe, "SignFrame")) {
					UNREF(newframe);
					UNREF(fs);
					g_warning("%s.%d: First frame NOT a signature frame - [%d] instead"
					,	__FUNCTION__, __LINE__, newframe->type);
					goto getnextframeset;
				}
				firstframe = FALSE;
			}
			frameset_append_frame(fs, newframe);
			UNREF(newframe);
		}
	getnextframeset:
		if (newframestart) {
			g_free(newframestart); newframestart = NULL;
		}
		if (fs) {
			ret = g_slist_append(ret, fs); fs = NULL;
		}
		curframeset = nextframeset;
	}
	return ret;
}
///@}
