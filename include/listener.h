/**
 * @file
 * @brief Defines Generic Listener interfaces
 * @details This file defines interfaces for the Base Listener class.  It listens for
 * packets from a variety of sources.
 *
 *
 * @author &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _LISTENER_H
#define _LISTENER_H
#include <projectcommon.h>
#include <assimobj.h>
#include <netaddr.h>
#include <frameset.h>
#include <configcontext.h>
typedef struct _Listener Listener;
#include <netgsource.h>

///@{
/// @ingroup Listener
//typedef struct _Listener Listener;

/// This is the @ref Listener object - which generically listens for packets
struct _Listener {
	AssimObj	baseclass;
	ConfigContext*	config;
	gboolean	(*got_frameset)(Listener* self,	///< Listener 'self' object
					FrameSet* fs,	///< Incoming @ref FrameSet
					NetAddr* na	///< Address 'fs' came from
					);		//< got_frameset called when FrameSet arrives
};

WINEXPORT Listener* listener_new(ConfigContext* config, gsize listen_objsize);
#ifdef IS_LISTENER_SUBCLASS
WINEXPORT void _listener_finalize(AssimObj* self);
#endif

///@}

#endif /* _LISTENER_H */
