/**
 * @file
 * @brief Defines Listener interfaces for packets coming from the Collective Authority
 * @details Each of the packets thus received are acted on appropriately.
 * @todo It should authorize the sender of the FrameSet.
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
 *
 */

#ifndef _AUTHLISTENER_H
#define _AUTHLISTENER_H
#include <projectcommon.h>
#include <netaddr.h>
#include <listener.h>
typedef struct _AuthListener AuthListener;
#include <netgsource.h>

///@{
/// @ingroup AuthListener
typedef struct _ObeyFrameSetTypeMap ObeyFrameSetTypeMap;


/// This is the @ref AuthListener object - which (authorizes and) obeys packets from the Authority
//
struct _AuthListener {
	Listener	baseclass;
	GHashTable*	actionmap;
	gboolean	autoack;
	gboolean	(*authenticator)(const FrameSet*fs);
};


typedef void    (*AuthListenerAction)(AuthListener*, FrameSet*, NetAddr*);
///	Structure associating @ref FrameSet types with actions to perform when they're received
struct _ObeyFrameSetTypeMap {
	int	framesettype;		///< @ref FrameSet type
	AuthListenerAction action;	///< What to do when we get it
};


/// Create an AuthListener
WINEXPORT AuthListener* authlistener_new(gsize listen_objsize, ObeyFrameSetTypeMap* map
,					 ConfigContext* config, gboolean autoack
,	gboolean(*authenticator)(const FrameSet*fs));
///@}
#endif /* _AUTHLISTENER_H */
