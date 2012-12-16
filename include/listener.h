/**
 * @file
 * @brief Defines Generic Listener interfaces
 * @details This file defines interfaces for the Base Listener class.  It listens for
 * packets from a variety of sources.
 *
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
	NetGSource*	transport;
	gboolean	(*got_frameset)(Listener* self,		///< Listener 'self' object
					FrameSet* fs,		///< Incoming @ref FrameSet
					NetAddr* na		///< Address 'fs' came from
					);			///< called when a FrameSet arrives
	void		(*associate) (Listener* self,		///< Listener 'self' object
				      NetGSource* source);	///< @ref NetGSource to associate with
	void		(*dissociate) (Listener* self);		///< Dissociate us from our source
};

WINEXPORT Listener* listener_new(ConfigContext* config, gsize listen_objsize);
#ifdef IS_LISTENER_SUBCLASS
WINEXPORT void _listener_finalize(AssimObj* self);
#endif

///@}

#endif /* _LISTENER_H */
