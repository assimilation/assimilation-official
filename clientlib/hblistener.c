/**
 * @file
 * @brief Implements the @ref HbListener class - for listening to heartbeats.
 * @details We are told what addresses to listen for, what ones to stop listening for at run time
 * and time out both warning times, and fatal (dead) times.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <memory.h>
#include <glib.h>
#include <frame.h>
#include <frameset.h>
#include <hblistener.h>
/**
 */
FSTATIC void _hblistener_finalize(AssimObj * self);
FSTATIC void _hblistener_unref(gpointer self);
FSTATIC void _hblistener_addlist(HbListener* self);
FSTATIC void _hblistener_dellist(HbListener* self);
FSTATIC void _hblistener_checktimeouts(gboolean urgent);
FSTATIC gboolean _hblistener_got_frameset(Listener*, FrameSet*, NetAddr*);
FSTATIC void _hblistener_set_deadtime(HbListener* self, guint64 deadtime);
FSTATIC void _hblistener_set_warntime(HbListener* self, guint64 warntime);
FSTATIC guint64 _hblistener_get_deadtime(HbListener* self);
FSTATIC guint64 _hblistener_get_warntime(HbListener* self);
FSTATIC gboolean _hblistener_gsourcefunc(gpointer);
FSTATIC void _hblistener_set_deadtime_callback(HbListener*, void (*callback)(HbListener* who));
FSTATIC void _hblistener_set_heartbeat_callback(HbListener*, void (*callback)(HbListener* who));
FSTATIC void _hblistener_set_warntime_callback(HbListener*, void (*callback)(HbListener* who, guint64 howlate));
FSTATIC void _hblistener_set_comealive_callback(HbListener*, void (*callback)(HbListener* who, guint64 howlate));

guint64 proj_get_real_time(void); 	///@todo - make this a real global function

///@defgroup HbListener HbListener class.
/// Class for heartbeat Listeners - We listen for heartbeats and time out those which are late.
///@{
///@ingroup Listener

static GSList*	_hb_listeners = NULL;
static gint	_hb_listener_count = 0;
static guint64	_hb_listener_lastcheck = 0;
static void	(*_hblistener_martiancallback)(const NetAddr* who) = NULL;

#define	ONESEC	1000000

/// Add an HbListener to our global list of HBListeners.
/// @todo make sure we don't duplicate listen addresses...
FSTATIC void
_hblistener_addlist(HbListener* self)	///<[in]The listener to add
{
	if (_hb_listeners == NULL) {
		g_timeout_add_seconds(1, _hblistener_gsourcefunc, NULL);
		///@todo start listening for packets...
	}
	_hb_listeners = g_slist_prepend(_hb_listeners, self);
	_hb_listener_count += 1;
	self->baseclass.baseclass.ref(self);
}

/// Remove an HbListener from our global list of HBListeners
FSTATIC void
_hblistener_dellist(HbListener* self)	///<[in]The listener to remove from our list
{
	if (g_slist_find(_hb_listeners, self) != NULL) {
		_hb_listeners = g_slist_remove(_hb_listeners, self);
		_hb_listener_count -= 1;
                // We get called by unref - and it expects us to do this...
		self->baseclass.baseclass.unref(CASTTOCLASS(Listener, self));
		return;
	}
	g_warn_if_reached();
}

/// Find the listener that's listening to a particular address
HbListener*
hblistener_find_by_address(const NetAddr* which)
{
	GSList*		obj;
	for (obj = _hb_listeners; obj != NULL; obj=g_slist_next(obj)) {
		HbListener* listener = CASTTOCLASS(HbListener, obj->data);
		if (which->equal(which, listener->listenaddr)) {
			return listener;
		}
	}
	return NULL;
}


/// Function called when it's time to see if anyone timed out...
FSTATIC void
_hblistener_checktimeouts(gboolean urgent)	///<[in]True if you want it checked now anyway...
{
	guint64		now = proj_get_real_time();
	GSList*		obj;
	if (!urgent && (now - _hb_listener_lastcheck) < ONESEC) {
		return;
	}
	_hb_listener_lastcheck = now;

	for (obj = _hb_listeners; obj != NULL; obj=g_slist_next(obj)) {
		HbListener* listener = CASTTOCLASS(HbListener, obj->data);
		if (now > listener->nexttime && listener->status == HbPacketsBeingReceived) {
			if (listener->_deadtime_callback) {
				listener->_deadtime_callback(listener);
			}else{
				g_warning("our node looks dead from here...");
			}
			listener->status = HbPacketsTimedOut;
		}
	}
}

/// A GSourceFunc to be used with g_timeout_add_seconds()
FSTATIC gboolean
_hblistener_gsourcefunc(gpointer ignored) ///<[ignored] Ignored
{
	(void)ignored;
	_hblistener_checktimeouts(TRUE);
	return _hb_listeners != NULL;
}

/// Function called when a heartbeat @ref FrameSet arrived from the given @ref NetAddr
FSTATIC gboolean
_hblistener_got_frameset(Listener* basethis, FrameSet* fs, NetAddr* srcaddr)
{
	guint64		now = proj_get_real_time();
	HbListener* listener = CASTTOCLASS(HbListener, basethis);
	if (srcaddr->equal(srcaddr, listener->listenaddr)) {
		if (listener->status == HbPacketsTimedOut) {
			guint64 howlate = now - listener->nexttime;
			listener->status = HbPacketsBeingReceived;
			if (listener->_comealive_callback) {
				listener->_comealive_callback(listener, howlate);
			}else{
				g_message("A node is now back alive!");
			}
		} else if (now > listener->warntime) {
			guint64 howlate = now - listener->warntime;
			howlate /= 1000;
			if (listener->_warntime_callback) {
				listener->_warntime_callback(listener, howlate);
			}else{
				g_warning("A node was " FMT_64BIT "u ms late in sending heartbeat..."
				,	howlate);
			}
		}
		if (listener->_heartbeat_callback) {
			listener->_heartbeat_callback(listener);
		}
		listener->nexttime = now + listener->_expected_interval;
		listener->warntime = now + listener->_warn_interval;
		fs->unref(fs);
		return TRUE;
	}
	if (_hblistener_martiancallback) {
		_hblistener_martiancallback(srcaddr);
	}else{ 
		gchar *	saddr = srcaddr->baseclass.toString(srcaddr);
		g_warning("Received 'martian' packet from address %s", saddr);
		g_free(saddr); saddr = NULL;
	}
	fs->unref(fs);
	return TRUE;
}
FSTATIC void
_hblistener_unref(gpointer obj)	///<[in/out] Object to decrement reference count for
{
	HbListener* self = CASTTOCLASS(HbListener, obj);
	g_return_if_fail(self->baseclass.baseclass._refcount > 0);
	self->baseclass.baseclass._refcount -= 1;
	if (self->baseclass.baseclass._refcount == 1) {
		// Our listener list should hold an extra reference count...
		_hblistener_dellist(CASTTOCLASS(HbListener, self));
		// hblistener_dellist will normally decrement reference count by 1
		// We will have gotten called recursively and finished the 'unref' work there...
		self = NULL;
	}else if (self->baseclass.baseclass._refcount == 0) {
		self->baseclass.baseclass._finalize((AssimObj*)self);
		self = NULL;
	}
}

/// Finalize an HbListener
FSTATIC void
_hblistener_finalize(AssimObj * self) ///<[in/out] Listener to finalize
{
	HbListener *hbself = CASTTOCLASS(HbListener, self);
	hbself->listenaddr->baseclass.unref(hbself->listenaddr);
	hbself->listenaddr = NULL;
	hbself->baseclass.config->baseclass.unref(hbself->baseclass.config);
	memset(hbself, 0x00, sizeof(*hbself));
	FREECLASSOBJ(hbself);
	self = NULL; hbself = NULL;
}


/// Construct a new HbListener - setting up GSource and timeout data structures for it.
/// This can be used directly or by derived classes.
HbListener*
hblistener_new(NetAddr*	listenaddr,	///<[in] Address to listen to
	       ConfigContext*cfg,	///<[in/out] Configuration context
	       gsize objsize)		///<[in] size of HbListener structure (0 for sizeof(HbListener))
{
	HbListener *	newlistener;
	Listener *	base;
	if (objsize < sizeof(HbListener)) {
		objsize = sizeof(HbListener);
	}
	base = listener_new(cfg, objsize);
	proj_class_register_subclassed(base, "HbListener");
	newlistener = CASTTOCLASS(HbListener, base);
	if (NULL == newlistener) {
		return NULL;
	}
	base->baseclass.unref = _hblistener_unref;
	base->baseclass._finalize = _hblistener_finalize;
	base->got_frameset = _hblistener_got_frameset;
	newlistener->listenaddr = listenaddr;
	listenaddr->baseclass.ref(listenaddr);
	newlistener->get_deadtime = _hblistener_get_deadtime;
	newlistener->set_deadtime = _hblistener_set_deadtime;
	newlistener->get_warntime = _hblistener_get_warntime;
	newlistener->set_warntime = _hblistener_set_warntime;
	newlistener->set_deadtime_callback = _hblistener_set_deadtime_callback;
	newlistener->set_warntime_callback = _hblistener_set_warntime_callback;
	newlistener->set_comealive_callback = _hblistener_set_comealive_callback;
	newlistener->set_heartbeat_callback = _hblistener_set_heartbeat_callback;

	newlistener->set_deadtime(newlistener, DEFAULT_DEADTIME*1000000);
	newlistener->set_warntime(newlistener, DEFAULT_DEADTIME*1000000/4);
	newlistener->status = HbPacketsBeingReceived;
	_hblistener_addlist(newlistener);
        return newlistener;
}

/// Set deadtime
FSTATIC void
_hblistener_set_deadtime(HbListener* self,	///<[in/out] Object to set deadtime for
			guint64 deadtime)	///<[in] deadtime to set in usec
{
	guint64		now = proj_get_real_time();
	self->_expected_interval = deadtime;
	self->nexttime = now + self->_expected_interval;

}

/// Return deadtime
FSTATIC guint64
_hblistener_get_deadtime(HbListener* self)
{
	return self->_expected_interval;
}

/// Set warntime
FSTATIC void
_hblistener_set_warntime(HbListener* self,	///<[in/out] Object to set warntime for
			guint64 warntime)	///<[in] warntime to set in usec
{
	guint64		now = proj_get_real_time();
	self->_warn_interval = warntime;
	self->warntime = now + self->_warn_interval;
}
/// Return warntime
FSTATIC guint64
_hblistener_get_warntime(HbListener* self)
{
	return self->_warn_interval;
}


/// Stop expecting (listening for) heartbeats from a particular address
FSTATIC void
hblistener_unlisten(NetAddr* unlistenaddr)///<[in/out] Listener to remove from list
{
	HbListener* listener = hblistener_find_by_address(unlistenaddr);
	if (listener != NULL) {
		_hblistener_dellist(listener);
		return;
	}
	g_warning("Attempt to unlisten an unregistered address");
}

/// Call to set a callback to be called when a node apparently dies
FSTATIC void
_hblistener_set_deadtime_callback(HbListener* self, void (*callback)(HbListener* who))
{
	self->_deadtime_callback = callback;
}

/// Call to set a callback to be called when a heartbeat is received
FSTATIC void
_hblistener_set_heartbeat_callback(HbListener* self, void (*callback)(HbListener* who))
{
	self->_heartbeat_callback = callback;
}

/// Call to set a callback to be called when a node passes warntime before heartbeating again
FSTATIC void
_hblistener_set_warntime_callback(HbListener* self, void (*callback)(HbListener* who, guint64 howlate))
{
	self->_warntime_callback = callback;
}

/// Call to set a callback to be called when a node passes deadtime but heartbeats again
FSTATIC void
_hblistener_set_comealive_callback(HbListener* self, void (*callback)(HbListener* who, guint64 howlate))
{
	self->_comealive_callback = callback;
}

/// Call to set a callback to be called when an unrecognized node sends us a heartbeat
FSTATIC void
hblistener_set_martian_callback(void (*callback)(const NetAddr* who))
{
	_hblistener_martiancallback = callback;
}
///@}
