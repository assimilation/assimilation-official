/**
 * @file
 * @brief Implements NetIO GSource object
 * @details This file contains the header definitions for NetIOGSource objects
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#include <memory.h>
#include <glib.h>
#include <netgsource.h>

/// @defgroup NetGSource NetGSource class
///@{
/// @ingroup C_Classes
/// This is our basic NetGSource object.
/// It is used for reading from @ref NetIO objects in the context of the g_main_loop GSource paradigm.
/// It is a class from which we might eventually make subclasses,
/// and is managed by our @ref ProjectClass system.

FSTATIC gboolean _netgsource_prepare(GSource* source, gint* timeout);
FSTATIC gboolean _netgsource_check(GSource* source);
FSTATIC gboolean _netgsource_dispatch(GSource* source, GSourceFunc callback, gpointer user_data);
FSTATIC void     _netgsource_finalize(GSource* source);

static GSourceFuncs _netgsource_gsourcefuncs = {
	_netgsource_prepare,
	_netgsource_check,
	_netgsource_dispatch,
	_netgsource_finalize,
	NULL,
	NULL
};
/// Create a new (abstract) NetGSource object
NetGSource*
netgsource_new(NetIO* iosrc,			///<[in/out] Network I/O object
	       NetGSourceDispatch dispatch,	///<[in] Dispatch function to call when a packet arrives
	       GDestroyNotify notify,		///<[in] Called when object destroyed
	       gint priority,			///<[in] g_main_loop
						///< <a href="http://library.gnome.org/devel/glib/unstable/glib-The-Main-Event-Loop.html#G-PRIORITY-HIGH:CAPS">dispatch priority</a>
	       gboolean can_recurse,		///<[in] TRUE if it can recurse
	       GMainContext* context,		///<[in] GMainContext or NULL
	       gsize objsize,			///<[in] number of bytes in NetGSource object - or zero
	       gpointer userdata		///<[in/out] Userdata to pass to dispatch function
	       )
{
	GSource*	gsret;
	NetGSource*	ret;
	GSourceFuncs*	gsf;

	if (objsize < sizeof(NetGSource)) {
		objsize = sizeof(NetGSource);
	}
	gsf  = MALLOCBASECLASS(GSourceFuncs);
	*gsf = _netgsource_gsourcefuncs;
	
	gsret = g_source_new(gsf, objsize);
	if (gsret == NULL) {
		FREECLASSOBJ(gsf);
		g_return_val_if_reached(NULL);
	}
	proj_class_register_object(gsret, "GSource");
	proj_class_register_subclassed(gsret, "NetGSource");
	ret = CASTTOCLASS(NetGSource, gsret);

	ret->_gsfuncs = gsf;
	ret->_dispatch = dispatch;
	ret->_userdata = userdata;
	ret->_netio = iosrc;
	ret->_socket = iosrc->getfd(iosrc);
	ret->_finalize = notify;
	ret->_gfd.fd = ret->_socket;
	ret->_gfd.events = G_IO_IN|G_IO_ERR|G_IO_HUP;
	ret->_gfd.revents = 0;
	g_source_add_poll(gsret, &ret->_gfd);
	g_source_set_priority(gsret, priority);
	g_source_set_can_recurse(gsret, can_recurse);
	ret->_gsourceid = g_source_attach(gsret, context);
	if (ret->_gsourceid == 0) {
		g_source_remove_poll(gsret, &ret->_gfd);
		memset(ret, 0, sizeof(*ret));
		g_source_unref(gsret);
		gsret = NULL;
		ret = NULL;
	}
	return ret;
}

/// GSource prepare routine for NetGSource - always returns TRUE
/// Called before going into the select/poll call - to get things ready for the poll call.
FSTATIC gboolean
_netgsource_prepare(GSource* source,	///<[unused] - GSource object
		    gint* timeout)	///<[unused] - timeout
{
	return FALSE;
}

/// GSource check routine for NetGSource.
/// Called after the select/poll call completes.
/// @return TRUE if if a packet is present, FALSE otherwise
FSTATIC gboolean
_netgsource_check(GSource* gself)	///<[in] NetGSource object being 'check'ed.
{
	NetGSource*	self = CASTTOCLASS(NetGSource, gself);
	// revents: received events...
	// @todo: should check for errors in revents
	if (self->_gfd.revents & G_IO_IN) {
		g_debug("Got input packet");
	}
	if (self->_gfd.revents & G_IO_ERR) {
		g_debug("Got i/o error");
	}
	if (self->_gfd.revents & G_IO_HUP) {
		g_debug("Got HUP");
	}
	if ((self->_gfd.revents & (G_IO_IN|G_IO_ERR|G_IO_HUP)) == 0) {
		g_debug("Got NOTHING: 0x%04x", self->_gfd.revents);
	}
	return 0 != self->_gfd.revents;
}
/// GSource dispatch routine for NetGSource.
/// Called after our check function returns TRUE.
/// If a bunch of events are fired at once, then this call will be dispatched before the next prepare
/// call, but perhaps not quite right away - depending on what other events (with possibly higher
/// priority) get dispatched ahead of us, and how long they take to complete.
FSTATIC gboolean
_netgsource_dispatch(GSource* gself,			///<[in/out] NetGSource object being dispatched
		     GSourceFunc ignore_callback,	///<[ignore] callback not being used
		     gpointer ignore_userdata)		///<[ignore] userdata not being used
{
	NetGSource*	self = CASTTOCLASS(NetGSource, gself);
	GSList*		gsl;
	NetAddr*	srcaddr;
	if (self->_gfd.revents & G_IO_IN) {
		g_debug("Dispatched due to input packet");
	}
	if (self->_gfd.revents & G_IO_OUT) {
		g_debug("Dispatched due to G_IO_OUT ");
	}
	if (self->_gfd.revents & G_IO_PRI) {
		g_debug("Dispatched due to G_IO_PRI");
	}
	if (self->_gfd.revents & G_IO_NVAL) {
		g_debug("Dispatched due to G_IO_NVAL");
	}
	if (self->_gfd.revents & G_IO_ERR) {
		g_debug("Dispatched due to i/o error");
	}
	if (self->_gfd.revents & G_IO_HUP) {
		g_debug("Dispatched due to HUP");
	}
	if ((self->_gfd.revents & (G_IO_IN|G_IO_ERR|G_IO_HUP)) == 0) {
		g_debug("Dispatched due to UNKNOWN REASON: 0x%04x", self->_gfd.revents);
	}
	while(NULL != (gsl = self->_netio->recvframesets(self->_netio, &srcaddr))) {
		self->_dispatch(self, gsl, srcaddr, self->_userdata);
		///< @todo Figure out the lifetime of packets and addresses
		/// probably need to add some reference counters.
	}
	return TRUE;
}

/// Finalize (free) the NetGSource object
FSTATIC void
_netgsource_finalize(GSource* gself)	///<[in/out] object being finalized
{
	NetGSource*	self = CASTTOCLASS(NetGSource, gself);

	if (self->_finalize) {
		self->_finalize(self->_userdata);
	}else{
		if (self->_userdata) {
			/// If this next call crashes, you should have supplied your own
			/// finalize routine (and maybe you should anyway)
			FREECLASSOBJ(self->_userdata);
			self->_userdata = NULL;
		}
	}
	if (self->_gsfuncs) {
		FREECLASSOBJ(self->_gsfuncs);
		self->_gsfuncs = NULL;
	}
}
///@}
