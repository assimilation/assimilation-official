/**
 * @file
 * @brief Implements NetIO GSource object
 * @details This file contains the header definitions for NetIOGSource objects
 * NetIOGsource objects are derived from the Glib GSource object type.
 * We treat these as Classes in our C-Class implementation.
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

#ifndef _NETGSOURCE_H
#define _NETGSOURCE_H
#include <projectcommon.h>
#include <glib.h>
#include <netgsource.h>
#include <netaddr.h>
#include <netio.h>
typedef struct _NetGSource NetGSource;
#include <listener.h>
///@{
/// @ingroup NetGSource


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
	void(*addListener)(NetGSource*, guint16, Listener*);///< Register a new listener
};
WINEXPORT NetGSource* netgsource_new(NetIO* iosrc, GDestroyNotify notify,
	       		   gint priority, gboolean can_recurse, GMainContext* context,
	       		   gsize objsize, gpointer userdata);
#endif /* _NETGSOURCE_H */
