/**
 * @file
 * @brief Defines Heartbeat Listener interfaces
 * @details This file defines interfaces for the Heartbeat Listener class.  It listens for
 * heartbeats from designated senders - allowing them to be added and dropped at run time.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _HBLISTENER_H
#define _HBLISTENER_H
#include <projectcommon.h>
#include <netaddr.h>
#include <netgsource.h>
typedef struct _HbListener HbListener;

typedef enum {
	HbPacketsBeingReceived = 1,
	HbPacketsTimedOut = 2,
}HbNodeStatus;

///@{
/// @ingroup HbListener

/// This is the base @ref HbListener object - which listens for heartbeats from a
/// particular sender.
struct _HbListener {
	void		(*ref)(HbListener*);		///< Increment reference count
	void		(*unref)(HbListener*);		///< Decrement reference count
	void		(*_finalize)(HbListener*);	///< HbListener destructor
	guint64		(*get_deadtime)(HbListener*);	///< Retrieve deadtime
	void		(*set_deadtime)(HbListener*, guint64);	///< Set deadtime
	guint64		(*get_warntime)(HbListener*);	///< Retrieve warntime
	void		(*set_warntime)(HbListener*, guint64);	///< Set warntime
	guint64		_expected_interval;		///< How often to expect heartbeats
	guint64		_warn_interval;			///< When to warn about late heartbeats
	guint64		nexttime;			///< When next heartbeat is due
	guint64		warntime;			///< Warn heartbeat time
	int		_refcount;			///< Current reference count
	NetAddr*	listenaddr;			///< What address are we listening for?
	HbNodeStatus	status;				///< What status is this node in?
};
#define	DEFAULT_DEADTIME	60 // seconds

WINEXPORT HbListener* hblistener_new(NetAddr*, gsize hblisten_objsize);
WINEXPORT void hblistener_unlisten(NetAddr* unlistenaddr);
WINEXPORT void hblistener_set_deadtime_callback(void (*)(HbListener* who));
WINEXPORT void hblistener_set_warntime_callback(void (*)(HbListener* who, guint64 howlate));
WINEXPORT void hblistener_set_comealive_callback(void (*)(HbListener* who, guint64 howlate));
WINEXPORT void hblistener_set_martian_callback(void (*)(const NetAddr* who));
WINEXPORT gboolean hblistener_netgsource_dispatch(NetGSource*, FrameSet*, NetAddr*,gpointer);

///@}

#endif /* _FRAME_H */
