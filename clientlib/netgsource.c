/**
 * @file
 * @brief Implements NetIO GSource (NetGSource) object 
 * @details This file contains source code implementing NetGSource objects.
 * NetGSource objects construct GSource objects from NetIO objects, so that
 * input from NetIO objects can be incorporated into the Glib g_main_loop event-driven
 * programming paradigm as a GSource derived class. As a result, functions can
 * be dispatched when NetIO packets arrive.
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

#include <projectcommon.h>
#include <memory.h>
#include <glib.h>
#include <frameset.h>
#include <netgsource.h>

DEBUGDECLARATIONS

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
FSTATIC void	_netgsource_addListener(NetGSource*, guint16, Listener*);
FSTATIC void	_netgsource_del_listener(gpointer);
FSTATIC void	_netgsource_sendaframeset(NetGSource*,const NetAddr*, FrameSet*);
FSTATIC void	_netgsource_sendframesets(NetGSource*,const NetAddr*, GSList*);

static GSourceFuncs _netgsource_gsourcefuncs = {
	_netgsource_prepare,
	_netgsource_check,
	_netgsource_dispatch,
	_netgsource_finalize,
	NULL,
	NULL
};
FSTATIC void
_netgsource_del_listener(gpointer lptr)
{
	Listener*	lobj;
	if (lptr) {
		lobj = CASTTOCLASS(Listener, lptr);
		UNREF(lobj);
	}
}

/// Create a new (abstract) NetGSource object
NetGSource*
netgsource_new(NetIO* iosrc,			///<[in/out] Network I/O object
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

	BINDDEBUG(NetGSource);
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
	ret->_userdata = userdata;
	ret->_netio = iosrc;
	iosrc->setblockio(iosrc, FALSE);
	ret->_socket = iosrc->getfd(iosrc);
	ret->_finalize = notify;
	ret->_gfd.fd = ret->_socket;
	ret->_gfd.events = G_IO_IN|G_IO_ERR|G_IO_HUP;
	ret->_gfd.revents = 0;
	ret->addListener = _netgsource_addListener;
	ret->sendframesets = _netgsource_sendframesets;
	ret->sendaframeset = _netgsource_sendaframeset;

	g_source_add_poll(gsret, &ret->_gfd);
	g_source_set_priority(gsret, priority);
	g_source_set_can_recurse(gsret, can_recurse);

	ret->_gsourceid = g_source_attach(gsret, context);

	if (ret->_gsourceid == 0) {
		FREECLASSOBJ(gsf);
		g_source_remove_poll(gsret, &ret->_gfd);
		memset(ret, 0, sizeof(*ret));
		g_source_unref(gsret);
		gsret = NULL;
		ret = NULL;
		g_return_val_if_reached(NULL);
	}
	// REF(ret->_netio);
	ret->_dispatchers = g_hash_table_new_full(NULL, NULL, NULL, _netgsource_del_listener);
	return ret;
}

/// GSource prepare routine for NetGSource - always returns TRUE
/// Called before going into the select/poll call - to get things ready for the poll call.
FSTATIC gboolean
_netgsource_prepare(GSource* source,	///<[unused] - GSource object
		    gint* timeout)	///<[unused] - timeout
{
	(void)source; (void)timeout;
	return _netgsource_check(source);
}

/// GSource check routine for NetGSource.
/// Called after the select/poll call completes.
/// @return TRUE if if a packet is present, FALSE otherwise
FSTATIC gboolean
_netgsource_check(GSource* gself)	///<[in] NetGSource object being 'check'ed.
{
	NetGSource*	self = CASTTOCLASS(NetGSource, gself);
	// revents: received events...
	// @todo: probably should check for errors in revents
	return ((0 != self->_gfd.revents) || self->_netio->input_queued(self->_netio));
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
	(void)ignore_callback; (void)ignore_userdata;
	if ((self->_gfd.revents & (G_IO_IN|G_IO_ERR|G_IO_HUP|G_IO_NVAL|G_IO_PRI)) == 0) {
		DEBUGMSG("%s.%d: Dispatched due to UNKNOWN REASON: 0x%04x"
		,	__FUNCTION__, __LINE__, self->_gfd.revents);
	}
	while(NULL != (gsl = self->_netio->recvframesets(self->_netio, &srcaddr))) {
		GSList*		thisgsl;
		for (thisgsl=gsl; NULL != thisgsl; thisgsl = gsl->next) {
			Listener*	disp = NULL;
			FrameSet*	fs = CASTTOCLASS(FrameSet, thisgsl->data);
			disp = g_hash_table_lookup(self->_dispatchers, GUINT_TO_POINTER((size_t)fs->fstype));
			if (NULL == disp) {
				disp = CASTTOCLASS(Listener, g_hash_table_lookup(self->_dispatchers, NULL));
			}
			if (NULL != disp) {
				disp->got_frameset(disp, fs, srcaddr);
			}else{ 
				g_warning("No dispatcher for FrameSet type %d", fs->fstype);
			}
		}
		UNREF(srcaddr);
		g_slist_free(gsl); gsl = NULL;
	}
	return TRUE;
}

/// Finalize (free) the NetGSource object
FSTATIC void
_netgsource_finalize(GSource* gself)	///<[in/out] object being finalized
{
#ifndef __FUNCTION__
#	define __FUNCTION__ "_netgsource_finalize"
#endif
	NetGSource*	self = CASTTOCLASS(NetGSource, gself);
	DEBUGMSG("%s(%p) FINALIZING!", __FUNCTION__, self);
	if (self->_finalize) {
		DEBUGMSG("%s: finalizing object at %p with %p", __FUNCTION__, self->_userdata
		,	self->_finalize);
		self->_finalize(self->_userdata);
	}else{
		if (self->_userdata) {
			/// If this next call crashes, you should have supplied your own
			/// finalize routine (and maybe you should anyway)
			FREECLASSOBJ(self->_userdata);
			self->_userdata = NULL;
			DEBUGMSG("%s: FREECLASSOBJ(%p)", __FUNCTION__, self->_userdata);
		}
	}
	if (self->_gsfuncs) {
		FREECLASSOBJ(self->_gsfuncs);
		self->_gsfuncs = NULL;
	}
	// UNREF(self->_netio);
	g_hash_table_unref(self->_dispatchers);
	proj_class_dissociate(gself);// Avoid dangling reference in class system
}
/// Send a single frameset to the given address
FSTATIC void
_netgsource_sendaframeset(NetGSource*		self,	///< @ref NetGSource Object to send via
			  const NetAddr*	addr,	///< @ref NetAddr address to send to
			  FrameSet*		fs)	///< @ref FrameSet to send
{
	NetIO* nio = self->_netio;
	nio->sendaframeset(nio, addr, fs);
}
/// Send a (GSList) list of @ref FrameSet "FrameSet"s to the given address
FSTATIC void
_netgsource_sendframesets(NetGSource*		self,	///< @ref NetGSource object to send via
			  const NetAddr*	addr,	///< @ref NetAddr address to send to
			  GSList*		fslist)	///< GSList of @ref FrameSet objects to send
{
	NetIO* nio = self->_netio;
	nio->sendframesets(nio, addr, fslist);
}
FSTATIC void
_netgsource_addListener(NetGSource* self,	///<[in/out] Object being modified
			guint16 fstype,		///<[in] FrameSet fstype
			Listener* disp)		///<[in] dispatch function
{
	if (disp) {
		REF(disp);
	}
	g_hash_table_replace(self->_dispatchers, GUINT_TO_POINTER((size_t)fstype), disp);
}
///@}
