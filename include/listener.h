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
typedef struct _Listener Listener;

///@{
/// @ingroup Listener

/// This is the @ref Listener object - which generically listens for packets
struct _Listener {
	AssimObj	baseclass;
	gboolean	(*got_frameset)(Listener*, FrameSet*, NetAddr*);
							//< Called when a FrameSet arrives
};

WINEXPORT Listener* listener_new(gsize listen_objsize);

///@}

#endif /* _LISTENER_H */
