/**
 * @file
 * @brief Implements NetIO GSource object
 * @details This file contains the header definitions for NetIOGSource objects
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _NETGSOURCE_H
#define _NETGSOURCE_H
#include <glib.h>
#include <netgsource.h>
#include <netaddr.h>
#include <netio.h>
typedef struct _NetGSource NetGSource;

/// Dispatch function for NetGSource objects - called when new data has arrived
typedef gboolean (*NetGSourceDispatch)
		   (NetGSource* gs,	///<[in/out] 'this' object causing the dispatch
		    GSList* gsl,	///<[in/out] GSList of FrameSets in this datagram.
		    NetAddr*srcaddr,	///<[in] Source address for this datagram
		    gpointer userdata);	///<[in/out] User data passed in during _new function.

/// This is our basic NetGSource object.
/// It is used for reading from network sockets, and managing flow control to them.
/// It is a class from which we might eventually make subclasses,
/// and is managed by our @ref ProjectClass system.
///@{
/// @ingroup NetGSource
struct _NetGSource {
	GSource*		baseclass;	///< Parent GSource Object pointer
	GPollFD			_gfd;		///< Poll/select object for gmainloop
	int			_socket;	///< Underlying socket descriptor
	gint			_gsourceid;	///< Source ID from g_source_attach()
	gpointer		_userdata;	///< Saved user data	
	GSourceFuncs*		_gsfuncs;	///< pointers to GSource functions
	NetIO*			_netio;		///< netio this object is based on
	NetGSourceDispatch	_dispatch;	///< Called when new data has arrived
	GDestroyNotify 		finalize;	///< Function to call when we're destroyed
};
NetGSource*	netgsource_new(NetIO* source, NetGSourceDispatch, gpointer userdata, gsize objsize);
///@}

#endif /* _NETGSOURCE_H */
