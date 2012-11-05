/**
 * @file
 * @brief Defines Heartbeat Sender interfaces
 * @details This file defines interfaces for the Heartbeat Sender class.  It sends heartbeats
 * to designated listeners - allowing them to be added and dropped at run time.
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

#ifndef _HBSENDER_H
#define _HBSENDER_H
#include <projectcommon.h>
#include <netaddr.h>
#include <netio.h>
#include <netgsource.h>
typedef struct _HbSender HbSender;

///@{
/// @ingroup HbSender

/// This is the base @ref HbSender object - which sends heartbeats to particular listeners.
/// @todo Need to make this a subclass of AssimObj
struct _HbSender {
	void		(*ref)(HbSender*);		///< Increment reference count
	void		(*unref)(HbSender*);		///< Decrement reference count
	void		(*_finalize)(HbSender*);	///< HbSender destructor
	guint64		_expected_interval;		///< How often to expect heartbeats
	NetGSource*	_outmethod;			///< How to send out heartbeats
	NetAddr*	_sendaddr;			///< What address are we sending to?
	int		_refcount;			///< Current reference count
	guint		timeout_source;			///< timeout source id
};
#define	DEFAULT_DEADTIME	60 // seconds

WINEXPORT HbSender* hbsender_new(NetAddr*, NetGSource*, guint interval, gsize hblisten_objsize);
WINEXPORT void hbsender_stopsend(NetAddr* unlistenaddr);
WINEXPORT void hbsender_stopallsenders(void);

///@}

#endif /* _HBSENDER */
