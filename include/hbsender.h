/**
 * @file
 * @brief Defines Heartbeat Sender interfaces
 * @details This file defines interfaces for the Heartbeat Sender class.  It sends heartbeats
 * to designated listeners - allowing them to be added and dropped at run time.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
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
struct _HbSender {
	void		(*ref)(HbSender*);		///< Increment reference count
	void		(*unref)(HbSender*);		///< Decrement reference count
	void		(*_finalize)(HbSender*);	///< HbSender destructor
	guint64		_expected_interval;		///< How often to expect heartbeats
	NetIO*		_outmethod;			///< How to send out heartbeats
	NetAddr*	_sendaddr;			///< What address are we sending to?
	int		_refcount;			///< Current reference count
	guint		timeout_source;			///< timeout source id
};
#define	DEFAULT_DEADTIME	60 // seconds

WINEXPORT HbSender* hbsender_new(NetAddr*, NetIO*, guint interval, gsize hblisten_objsize);
WINEXPORT void hbsender_stopsend(NetAddr* unlistenaddr);

///@}

#endif /* _HBSENDER */
