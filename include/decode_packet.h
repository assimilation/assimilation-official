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
	int			frametype; ///< One of the @ref IndividualFrameFormats
					   ///< "Defined Frame Formats" from frameformats.h
	FramePktConstructor	constructor;
};

///@{
/// @ingroup AssimObj
typedef struct _AssimObj	AssimObj;

struct _AssimObj {
	int		_refcount;			///< Reference count (private)
	void		(*_finalize)(AssimObj*);	///< Free object (private)
	void		(*ref)(gpointer);		///< Increment reference count
	void		(*unref)(gpointer);		///< Decrement reference count
	char*		(*toString)(gpointer);		///< Produce malloc-ed string representation
};
WINEXPORT AssimObj*		assimobject_new(guint objsize);
///@}


///@{
/// @ingroup PacketDecoder
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
#endif /* DECODE_PACKET_H */
