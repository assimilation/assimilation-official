/**
 * @file
 * @brief  This file defines a few functions and interfaces for unmarshalling packet data into FrameSets.
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

#ifndef _PACKETDECODER_H
#define _PACKETDECODER_H
#include <projectcommon.h>
#include <assimobj.h>
#include <frame.h>

///@{
/// @ingroup PacketDecoder

typedef struct _FrameTypeToFrame FrameTypeToFrame;

typedef Frame*            (*FramePktConstructor)       (gpointer tlvstart, gconstpointer pktend, gpointer*, gpointer*);
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
	GSList*			(*pktdata_to_framesetlist)(PacketDecoder*, gpointer pktstart, gconstpointer pktend);
};

WINEXPORT PacketDecoder*	packetdecoder_new(guint objsize, const FrameTypeToFrame* framemap, gint mapsize);

///@}
#endif /* PACKETDECODER_H */
