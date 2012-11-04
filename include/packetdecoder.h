/**
 * @file
 * @brief  This file defines a few functions and interfaces for unmarshalling packet data into FrameSets.
 *
 * @author &copy; 2011-2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _PACKETDECODER_H
#define _PACKETDECODER_H
#include <projectcommon.h>
#include <assimobj.h>
#include <frame.h>

///@{
/// @ingroup PacketDecoder

typedef struct _FrameTypeToFrame FrameTypeToFrame;

typedef Frame*            (*FramePktConstructor)       (gconstpointer tlvstart, gconstpointer pktend);
/// Data structure defining the mapping between frametype integers and corresponding demarshalling
/// modules.
struct _FrameTypeToFrame {
	int			frametype; ///< One of the @ref IndividualFrameFormats
					   ///< "Defined Frame Formats" from frameformats.h
	FramePktConstructor	constructor;
};

typedef struct _PacketDecoder	PacketDecoder;
struct _PacketDecoder {
	AssimObj		baseclass;
	void			(*_pfinalize)(AssimObj*);
	int			_framemaplen;
	const FrameTypeToFrame*	_framemap;
	int			_maxframetype;
	FramePktConstructor*	_frametypemap;
	GSList*			(*pktdata_to_framesetlist)(PacketDecoder*, gconstpointer pktstart, gconstpointer pktend);
};

WINEXPORT PacketDecoder*	packetdecoder_new(guint objsize, const FrameTypeToFrame* framemap, gint mapsize);

///@}
#endif /* PACKETDECODER_H */
