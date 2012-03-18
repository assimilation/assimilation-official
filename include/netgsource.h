/**
 * @file
 * @brief Implements NetIO GSource object
 * @details This file contains the header definitions for NetIOGSource objects
 * NetIOGsource objects are derived from the Glib GSource object type.
 * We treat these as Classes in our C-Class implementation.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _NETGSOURCE_H
#define _NETGSOURCE_H
#include <projectcommon.h>
#include <glib.h>
#include <netgsource.h>
#include <netaddr.h>
#include <netio.h>
#include <listener.h>
///@{
/// @ingroup NetGSource

typedef struct _NetGSource NetGSource;

/// The @ref NetGSource objects integrate @ref NetIO objects into the g_main_loop paradigm.
/// It is a class from which we might eventually make subclasses,
/// and is managed by our @ref ProjectClass system.
struct _NetGSource {
	GSource			baseclass;	///< Parent GSource Object pointer
	GPollFD			_gfd;		///< Poll/select object for gmainloop
	int			_socket;	///< Underlying socket descriptor
	gint			_gsourceid;	///< Source ID from g_source_attach()
	gpointer		_userdata;	///< Saved user data	
	GSourceFuncs*		_gsfuncs;	///< pointers to GSource functions
	NetIO*			_netio;		///< netio this object is based on
	GHashTable*		_dispatchers;	///< Table of dispatch functions.
	GDestroyNotify 		_finalize;	///< Function to call when we're destroyed
	void			(*sendaframeset)(NetGSource*,const NetAddr*, FrameSet*);///< Send a single frameset
	void			(*sendframesets)(NetGSource*,const NetAddr*, GSList*);  ///< Send a frameset list
	void(*addListener)(NetGSource*,guint16, Listener*);///< Register a new listener
};
WINEXPORT NetGSource* netgsource_new(NetIO* iosrc, GDestroyNotify notify,
	       		   gint priority, gboolean can_recurse, GMainContext* context,
	       		   gsize objsize, gpointer userdata);
#endif /* _NETGSOURCE_H */
