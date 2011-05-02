/**
 * @file
 * @brief Implements Heartbeat Listener class
 * @details This class implements the Heartbeat Listener class.  It listens for
 * heartbeats from a particular sender.
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
typedef struct _HbListener HbListener;

///@{
/// @ingroup HbListener

/// This is the base @ref HbListener object - which listens for heartbeats from a
/// particular sender.
struct _HbListener {
	void		(*ref)(HbListener*);		///< Increment reference count
	void		(*unref)(HbListener*);		///< Decrement reference count
	void		(*_finalize)(HbListener*);	///< Frame Destructor
	guint64		_expected_interval;		///< How often to expect heartbeats
	guint64		_warn_interval;			///< When to warn about late heartbeats
	guint64		_nexttime;			///< When next heartbeat is due
	guint64		_warntime;			///< Warn heartbeat time
	int		_refcount;
	NetAddr*	_listenaddr;
};
#define	DEFAULT_DEADTIME	60
HbListener* hblistener_new(NetAddr*, gsize);
///@}

#endif /* _FRAME_H */
