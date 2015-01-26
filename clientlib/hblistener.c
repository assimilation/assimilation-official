/**
 * @file
 * @brief Implements the @ref HbListener class - for listening to heartbeats.
 * @details We are told what addresses to listen for, what ones to stop listening for at run time
 * and time out both warning times, and fatal (dead) times.
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
#define IS_LISTENER_SUBCLASS	1
#include <memory.h>
#include <glib.h>
#include <frame.h>
#include <frameset.h>
#include <hblistener.h>
#include <stdlib.h>
/**
 */
FSTATIC void _hblistener_notify_function(gpointer ignoreddata);
FSTATIC void _hblistener_finalize(AssimObj * self);
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

DEBUGDECLARATIONS;

///@defgroup HbListener HbListener class.
/// Class for heartbeat Listeners - We listen for heartbeats and time out those which are late.
///@{
///@ingroup Listener

static GSList*	_hb_listeners = NULL;
static gint	_hb_listener_count = 0;
static guint64	_hb_listener_lastcheck = 0;
static void	(*_hblistener_martiancallback)(NetAddr* who) = NULL;
static gint	hb_timeout_id = -1;

#define	ONESEC	1000000

/// Add an HbListener to our global list of HBListeners,
/// and unref (and neuter) any old HbListeners listening to this same address
FSTATIC void
_hblistener_addlist(HbListener* self)	///<[in]The listener to add
{
	HbListener*	old;
	if (_hb_listeners == NULL) {
		hb_timeout_id = g_timeout_add_seconds_full(G_PRIORITY_LOW, 1
		,	_hblistener_gsourcefunc , NULL, _hblistener_notify_function);
		///@todo start listening for packets...
	}else if ((old=hblistener_find_by_address(self->listenaddr)) != NULL) {
		_hblistener_dellist(old);
	}
	_hb_listeners = g_slist_prepend(_hb_listeners, self);
	_hb_listener_count += 1;
	REF2(self);
}

/// Remove an HbListener from our global list of HBListeners
FSTATIC void
_hblistener_dellist(HbListener* self)	///<[in]The listener to remove from our list
{
	if (g_slist_find(_hb_listeners, self) != NULL) {
		_hb_listeners = g_slist_remove(_hb_listeners, self);
		_hb_listener_count -= 1;
		UNREF2(self);
		return;
	}
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
	guint64		now = g_get_real_time();
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
				char *	addrstr
				= listener->listenaddr->baseclass.toString
				(	&listener->listenaddr->baseclass);
				g_warning("%s.%d: Unhandled deadtime for %s."
				,	__FUNCTION__, __LINE__, addrstr);
				FREE(addrstr);
			}
			listener->status = HbPacketsTimedOut;
		}
	}
}

/// A GSourceFunc to be used with g_timeout_add_seconds()
FSTATIC gboolean
_hblistener_gsourcefunc(gpointer ignored) ///<[ignored] Ignored
{
	gboolean	ret;
	(void)ignored;
	_hblistener_checktimeouts(TRUE);
	ret = (_hb_listeners != NULL);
	if (!ret) {
		hb_timeout_id = -1;
	}
	return ret;
}

/// Function called when a heartbeat @ref FrameSet (fs) arrived from the given @ref NetAddr (srcaddr)
FSTATIC gboolean
_hblistener_got_frameset(Listener* self, FrameSet* fs, NetAddr* srcaddr)
{
	guint64		now = g_get_real_time();
	HbListener*	addmatch;

	(void)self;  // Odd, but true - because we're a proxy for all hblisteners...

	addmatch = hblistener_find_by_address(srcaddr);

	if (DEBUG >= 4) {
		char *	addrstr = srcaddr->baseclass.toString(&srcaddr->baseclass);
		g_debug("%s.%d: Received heartbeat from %s (%sfound)."
		,	__FUNCTION__, __LINE__, addrstr, (addmatch ? "" : "not "));
		FREE(addrstr);
	}
	if (addmatch != NULL) {
		if (addmatch->status == HbPacketsTimedOut) {
			guint64 howlate = now - addmatch->nexttime;
			addmatch->status = HbPacketsBeingReceived;
			howlate /= 1000;
			if (addmatch->_comealive_callback) {
				addmatch->_comealive_callback(addmatch, howlate);
			}else{
				g_message("A node is now back alive! late by "FMT_64BIT "d ms", howlate);
			}
		} else if (now > addmatch->warntime) {
			guint64 howlate = now - addmatch->warntime;
			howlate /= 1000;
			if (addmatch->_warntime_callback) {
				addmatch->_warntime_callback(addmatch, howlate);
			}else{
				g_warning("A node was " FMT_64BIT "u ms late in sending heartbeat..."
				,	howlate);
			}
		}
		if (addmatch->_heartbeat_callback) {
			addmatch->_heartbeat_callback(addmatch);
		}
		addmatch->nexttime = now + addmatch->_expected_interval;
		addmatch->warntime = now + addmatch->_warn_interval;
		UNREF(fs);
		return TRUE;
	}
	// The 'martian' callback is necessarily global to all heartbeat listeners
	if (_hblistener_martiancallback) {
		_hblistener_martiancallback(srcaddr);
	}else{ 
		gchar *	saddr = srcaddr->baseclass.toString(srcaddr);
		g_warning("%s.%d: Received unhandled 'martian' packet from address [%s]"
		,	__FUNCTION__, __LINE__, saddr);
		g_free(saddr); saddr = NULL;
	}
	UNREF(fs);
	return TRUE;
}

/// We get called when our gSource gets removed.  This function is probably unnecessary...
FSTATIC void
_hblistener_notify_function(gpointer ignored)	///<[unused] Unused
{
	(void)ignored;
	hblistener_shutdown();
}

/// Shuts down all our hblisteners...
FSTATIC void
hblistener_shutdown(void)
{
	GSList* this;
	GSList* next = NULL;
	static gboolean shuttingdown = FALSE;

	if (shuttingdown) {
		return;
	}
	shuttingdown = TRUE;
	// Unref all our listener objects...
	for (this = _hb_listeners; this; this=next) {
		HbListener* listener = CASTTOCLASS(HbListener, this->data);
		next = this->next;
		UNREF2(listener);
	}
	if (_hb_listeners) {
		g_slist_free(_hb_listeners);
		_hb_listeners = NULL;
	}
	if (hb_timeout_id > 0) {
		g_source_remove(hb_timeout_id);
	}
	shuttingdown = FALSE;
}


/// Finalize an HbListener
FSTATIC void
_hblistener_finalize(AssimObj * self) ///<[in/out] Listener to finalize
{
	HbListener *hbself = CASTTOCLASS(HbListener, self);
	DEBUGMSG3("%s.%d - finalizing.", __FUNCTION__, __LINE__);
	UNREF(hbself->listenaddr);
	_listener_finalize(self);
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
	BINDDEBUG(HbListener);
	if (objsize < sizeof(HbListener)) {
		objsize = sizeof(HbListener);
	}
	base = listener_new(cfg, objsize);
	proj_class_register_subclassed(base, "HbListener");
	newlistener = CASTTOCLASS(HbListener, base);
	if (NULL == newlistener) {
		return NULL;
	}
	base->baseclass._finalize = _hblistener_finalize;
	base->got_frameset = _hblistener_got_frameset;
	newlistener->listenaddr = listenaddr;
	REF(listenaddr);
	newlistener->get_deadtime = _hblistener_get_deadtime;
	newlistener->set_deadtime = _hblistener_set_deadtime;
	newlistener->get_warntime = _hblistener_get_warntime;
	newlistener->set_warntime = _hblistener_set_warntime;
	newlistener->set_deadtime_callback = _hblistener_set_deadtime_callback;
	newlistener->set_warntime_callback = _hblistener_set_warntime_callback;
	newlistener->set_comealive_callback = _hblistener_set_comealive_callback;
	newlistener->set_heartbeat_callback = _hblistener_set_heartbeat_callback;

	if (cfg->getint(cfg, CONFIGNAME_TIMEOUT) > 0) {
		newlistener->set_deadtime(newlistener, cfg->getint(cfg, CONFIGNAME_TIMEOUT));
	}else{
		newlistener->set_deadtime(newlistener, DEFAULT_DEADTIME);
	}
	if (cfg->getint(cfg, CONFIGNAME_WARNTIME) > 0) {
		newlistener->set_warntime(newlistener, cfg->getint(cfg, CONFIGNAME_WARNTIME));
	}else{
		newlistener->set_warntime(newlistener, (DEFAULT_DEADTIME*2)/3);
	}
	newlistener->status = HbPacketsBeingReceived;
	_hblistener_addlist(newlistener);
	if (DEBUG) {
		char *	addrstr = listenaddr->baseclass.toString(&listenaddr->baseclass);
		g_debug("%s.%d: Start expecting heartbeats from %s. Interval: "FMT_64BIT"d"
		" Warntime: "FMT_64BIT"d"
		,	__FUNCTION__, __LINE__, addrstr
		,	newlistener->_expected_interval/1000000
		,	newlistener->_warn_interval/1000000);
		FREE(addrstr);
	}
        return newlistener;
}

/// Set deadtime
FSTATIC void
_hblistener_set_deadtime(HbListener* self,	///<[in/out] Object to set deadtime for
			guint64 deadtime)	///<[in] deadtime to set in seconds
{
	guint64		now = g_get_real_time();
	self->_expected_interval = deadtime*1000000L;
	self->nexttime = now + self->_expected_interval;
	//g_debug("Setting HbListener deadtime to " FMT_64BIT "d secs", deadtime);
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
			guint64 warntime)	///<[in] warntime to set in seconds
{
	guint64		now = g_get_real_time();
	self->_warn_interval = warntime*1000000;
	self->warntime = now + self->_warn_interval;
}
/// Return warntime
FSTATIC guint64
_hblistener_get_warntime(HbListener* self)
{
	return self->_warn_interval;
}


/// Stop expecting (listening for) heartbeats from a particular address
/// @todo - this can cause a bug if the NetGSource object still has a reference to us
/// and we delete ourselves - then it will have a bad reference to us.
/// So, we ought to check for this case and replace ourselves with any other listener
/// in the list -- if any, and do something more drastic if we're the last listener in the list.
FSTATIC void
hblistener_unlisten(NetAddr* unlistenaddr)///<[in/out] Listener to remove from list
{
	HbListener* listener = hblistener_find_by_address(unlistenaddr);
	if (DEBUG) {
		char *	addrstr = unlistenaddr->baseclass.toString(&unlistenaddr->baseclass);
		g_debug("%s.%d: Stop expecting heartbeats from %s (%sfound)."
		,	__FUNCTION__, __LINE__, addrstr, (listener ? "" : "not "));
		FREE(addrstr);
	}
	if (listener != NULL) {
		_hblistener_dellist(listener);
		return;
	}
	// This is probably triggered by a "slow to update" problem...
	if (DEBUG >= 3) {
		char *	addrstr = unlistenaddr->baseclass.toString(&unlistenaddr->baseclass);
		g_debug("%s.%d: Attempt to unlisten an unregistered address: %s"
		,	__FUNCTION__, __LINE__, addrstr);
		FREE(addrstr);
	}
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
hblistener_set_martian_callback(void (*callback)(NetAddr* who))
{
	_hblistener_martiancallback = callback;
}
///@}
