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
FSTATIC void _hblistener_finalize(HbListener * self);
FSTATIC void _hblistener_ref(HbListener * self);
FSTATIC void _hblistener_unref(HbListener * self);
FSTATIC void _hblistener_addlist(HbListener* self);
FSTATIC void _hblistener_dellist(HbListener* self);
FSTATIC void _hblistener_checktimeouts(gboolean urgent);
FSTATIC void _hblistener_hbarrived(FrameSet* fs, NetAddr* srcaddr);
FSTATIC void _hblistener_addlist(HbListener* self);
FSTATIC void _hblistener_dellist(HbListener* self);
FSTATIC void _hblistener_set_deadtime(HbListener* self, guint64 deadtime);
FSTATIC void _hblistener_set_warntime(HbListener* self, guint64 warntime);
FSTATIC guint64 _hblistener_get_deadtime(HbListener* self);
FSTATIC guint64 _hblistener_get_warntime(HbListener* self);
FSTATIC gboolean _hblistener_gsourcefunc(gpointer);

guint64 proj_get_real_time(void); 	///@todo - make this a real global function

///@defgroup HbListener HbListener class.
/// Class for heartbeat Listeners - We listen for heartbeats and time out those which are late.
///@{
///@ingroup C_Classes

static GSList*	_hb_listeners = NULL;
static gint	_hb_listener_count = 0;
static guint64	_hb_listener_lastcheck = 0;
static void	(*_hblistener_deadcallback)(HbListener* who) = NULL;
static void 	(*_hblistener_warncallback)(HbListener* who, guint64 howlate) = NULL;
static void 	(*_hblistener_comealivecallback)(HbListener* who, guint64 howlate) = NULL;
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
	self->ref(self);
}

/// Remove an HbListener from our global list of HBListeners
FSTATIC void
_hblistener_dellist(HbListener* self)	///<[in]The listener to remove from our list
{
	if (g_slist_find(_hb_listeners, self) != NULL) {
		_hb_listeners = g_slist_remove(_hb_listeners, self);
		_hb_listener_count -= 1;
                // We get called by unref - and it expects us to do this...
		self->unref(self);
		return;
	}
	g_warn_if_reached();
}

/// Function called when it's time to see if anyone timed out...
FSTATIC void
_hblistener_checktimeouts(gboolean urgent)///<[in]True if you want it checked now anyway...
{
	guint64		now = proj_get_real_time();
	GSList*		obj;
	if (!urgent && (now - _hb_listener_lastcheck) < ONESEC) {
		return;
	}
	_hb_listener_lastcheck = now;

	for (obj = _hb_listeners; obj != NULL; obj=obj->next) {
		HbListener* listener = CASTTOCLASS(HbListener, obj->data);
		if (now > listener->nexttime && listener->status == HbPacketsBeingReceived) {
			if (_hblistener_deadcallback) {
				_hblistener_deadcallback(listener);
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

/// Function called when a heartbeat @ref Frame arrived from the given @ref NetAddr
FSTATIC void
_hblistener_hbarrived(FrameSet* fs, NetAddr* srcaddr)
{
	GSList*		obj;
	guint64		now = proj_get_real_time();
	for (obj = _hb_listeners; obj != NULL; obj=obj->next) {
		HbListener* listener = CASTTOCLASS(HbListener, obj->data);
		if (srcaddr->equal(srcaddr, listener->listenaddr)) {
			g_message("Received heartbeat...");
			///@todo ADD CODE TO PROCESS PACKET, not just observe that it arrived??
			/// - probably add yet another callback?
			if (listener->status == HbPacketsTimedOut) {
				guint64 howlate = now - listener->nexttime;
				listener->status = HbPacketsBeingReceived;
				if (_hblistener_comealivecallback) {
					_hblistener_comealivecallback(listener, howlate);
				}else{
					g_message("A node is now back alive!");
				}
			} else if (now > listener->warntime) {
				guint64 howlate = now - listener->warntime;
				howlate /= 1000;
				if (_hblistener_warncallback) {
					_hblistener_warncallback(listener, howlate);
				}else{
					g_warning("A node was " FMT_64BIT "u ms late in sending heartbeat..."
					,	howlate);
				}
			}
			listener->nexttime = now + listener->_expected_interval;
			listener->warntime = now + listener->_warn_interval;
			fs->unref(fs);
			return;
		}
	}
	if (_hblistener_martiancallback) {
		_hblistener_martiancallback(srcaddr);
	}else{ 
		gchar *	saddr = srcaddr->toString(srcaddr);
		g_warning("Received 'martian' packet from address %s", saddr);
		g_free(saddr); saddr = NULL;
	}
	fs->unref(fs);
}

/// Increment the reference count by one.
FSTATIC void
_hblistener_ref(HbListener* self)	///<[in/out] Object to increment reference count for
{
	self->_refcount += 1;
}

/// Decrement the reference count by one - possibly freeing up the object.
FSTATIC void
_hblistener_unref(HbListener* self)	///<[in/out] Object to decrement reference count for
{
	g_return_if_fail(self->_refcount > 0);
	self->_refcount -= 1;
	if (self->_refcount == 1) {
		// Our listener list should hold an extra reference count...
		_hblistener_dellist(self);
		// hblistener_dellist will normally decrement reference count by 1
		// We will have gotten called recursively and finished the 'unref' work there...
		self = NULL;
	}else if (self->_refcount == 0) {
		self->_finalize(self);
		self = NULL;
	}
}

/// Finalize an HbListener
FSTATIC void
_hblistener_finalize(HbListener * self) ///<[in/out] Listener to finalize
{
	self->listenaddr->unref(self->listenaddr);
	// self->listenaddr = NULL;
	memset(self, 0x00, sizeof(*self));
	FREECLASSOBJ(self);
}


/// Construct a new HbListener - setting up GSource and timeout data structures for it.
/// This can be used directly or by derived classes.
///@todo Create Gsource for packet reception, attach to context, write dispatch code,
/// to call _hblistener_hbarrived()
HbListener*
hblistener_new(NetAddr*	listenaddr,	///<[in] Address to listen to
	       gsize objsize)		///<[in] size of HbListener structure (0 for sizeof(HbListener))
{
	HbListener * newlistener;
	if (objsize < sizeof(HbListener)) {
		objsize = sizeof(HbListener);
	}
	newlistener = MALLOCCLASS(HbListener, objsize);
	if (newlistener != NULL) {
		newlistener->listenaddr = listenaddr;
		listenaddr->ref(listenaddr);
		newlistener->_refcount = 1;
		newlistener->ref = _hblistener_ref;
		newlistener->unref = _hblistener_unref;
		newlistener->_finalize = _hblistener_finalize;
		newlistener->set_deadtime = _hblistener_set_deadtime;
		newlistener->get_deadtime = _hblistener_get_deadtime;
		newlistener->set_warntime = _hblistener_set_warntime;
		newlistener->get_warntime = _hblistener_get_warntime;
		newlistener->set_deadtime(newlistener, DEFAULT_DEADTIME*1000000);
		newlistener->set_warntime(newlistener, DEFAULT_DEADTIME*1000000/4);
		newlistener->status = HbPacketsBeingReceived;
		_hblistener_addlist(newlistener);
	}
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
void
hblistener_unlisten(NetAddr* unlistenaddr)///<[in/out] Listener to remove from list
{
	GSList*		obj;
	for (obj = _hb_listeners; obj != NULL; obj=obj->next) {
		HbListener* listener = CASTTOCLASS(HbListener, obj->data);
		if (unlistenaddr->equal(unlistenaddr, listener->listenaddr)) {
			_hblistener_dellist(listener);
			return;
		}
	}
	g_warning("Attempt to unlisten an unregistered address");
}

/// Call to set a callback to be called when a node apparently dies
void
hblistener_set_deadtime_callback(void (*callback)(HbListener* who))
{
	_hblistener_deadcallback = callback;
}

/// Call to set a callback to be called when a node passes warntime before heartbeating again
void
hblistener_set_warntime_callback(void (*callback)(HbListener* who, guint64 howlate))
{
	_hblistener_warncallback = callback;
}

/// Call to set a callback to be called when a node passes deadtime but heartbeats again
void
hblistener_set_comealive_callback(void (*callback)(HbListener* who, guint64 howlate))
{
	_hblistener_comealivecallback = callback;
}

/// Call to set a callback to be called when an unrecognized node sends us a heartbeat
void
hblistener_set_martian_callback(void (*callback)(const NetAddr* who))
{
	_hblistener_martiancallback = callback;
}

gboolean
hblistener_netgsource_dispatch(NetGSource* gs,		///<[in] NetGSource input source
			       FrameSet* fs,		///<[in] FrameSet
			       NetAddr* srcaddr, 	///<[in] source address
			       gpointer ignoreme)	///<[ignore] ignore me
{
	(void)gs; (void)ignoreme;
	_hblistener_hbarrived(fs, srcaddr);
	return TRUE;
}
///@}
