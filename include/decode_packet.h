/**
 * @file
 * @brief  This file defines a few functions and interfaces for unmarshalling packet data into FrameSets.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _DECODE_PACKET_H
#define _DECODE_PACKET_H
#include <projectcommon.h>
#include <frame.h>

typedef struct _FrameTypeToFrame FrameTypeToFrame;

typedef Frame*            (*FramePktConstructor)       (gconstpointer tlvstart, gconstpointer pktend);
/// Data structure defining the mapping between frametype integers and corresponding demarshalling
/// modules.
struct _FrameTypeToFrame {
	int			frametype; ///< One of the @ref IndividualFrameFormats "Defined Frame Formats" from frameformats.h
	FramePktConstructor	constructor;
};
WINEXPORT GSList*		pktdata_to_frameset_list(gconstpointer pktstart, gconstpointer pktend);
#endif /* DECODE_PACKET_H */
