/**
 * @file
 * @brief Implements the @ref Frame class - the lowest level of data organization for our packets.
 * @details This file contains the minimal Frame capabilities for a client -
 * enough for it to be able to construct, understand and validate Frames.
 * Note that the decoding of packets into Frames is an interesting process, not yet defined...
 * @see FrameSet, GenericTLV
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <memory.h>
#include <glib.h>
#include <frame.h>
#include <hblistener.h>
/**
 */
FSTATIC void _hblistener_finalize(HbListener * self);
FSTATIC void _hblistener_ref(HbListener * self);
FSTATIC void _hblistener_unref(HbListener * self);
FSTATIC void _hblistener_addlist(HbListener* self);
FSTATIC void _hblistener_dellist(HbListener* self);
FSTATIC void _hblistener_checktimeouts(gboolean urgent);
FSTATIC void _hblistener_hbarrived(Frame* hbframe, NetAddr* srcaddr);
guint64 proj_get_real_time(void); 

///@defgroup HbListener HbListener class
/// Class for heartbeat Listeners - I can hear you...
///@{
///@ingroup C_Classes

static GList*	_hb_listeners = NULL;
static gint	_hb_listener_count = 0;
static guint64	_hb_listener_lastcheck = 0;

#define	ONESEC	1000000


FSTATIC void
_hblistener_addlist(HbListener* self)
{
	_hb_listeners = g_list_prepend(_hb_listeners, self);
	_hb_listener_count += 1;
	self->ref(self);
}

FSTATIC void
_hblistener_dellist(HbListener* self)
{
	if (g_list_find(_hb_listeners, self) != NULL) {
		_hb_listeners = g_list_remove(_hb_listeners, self);
		_hb_listener_count -= 1;
		self->unref(self);
		return;
	}
	g_warn_if_reached();
}

FSTATIC void
_hblistener_checktimeouts(gboolean urgent)
{
	guint64		now = proj_get_real_time();
	GList*		obj;
	if (!urgent && (now - _hb_listener_lastcheck) < ONESEC) {
		return;
	}
	_hb_listener_lastcheck = now;

	for (obj = _hb_listeners; obj != NULL; obj=obj->next) {
		HbListener* listener = CASTTOCLASS(HbListener, obj->data);
		if (now > listener->_nexttime) {
			///@todo - really lousy message and action - probably need callback!
			g_warning("our node looks dead from here...");
		}
	}
}
FSTATIC void
_hblistener_hbarrived(Frame* hbframe, NetAddr* srcaddr)
{
	GList*		obj;
	guint64		now = proj_get_real_time();
	for (obj = _hb_listeners; obj != NULL; obj=obj->next) {
		HbListener* listener = CASTTOCLASS(HbListener, obj->data);
		if (srcaddr->equal(srcaddr, listener->_listenaddr)) {
			if (now > listener->_warntime) {
				guint64 howlate = now - listener->_warntime;
				howlate /= 1000;
				///@todo - really lousy message and action - probably need callback!
				g_warning("our node is %lums late in sending heartbeat..."
				,	howlate);
			}
			listener->_nexttime = now + listener->_expected_interval;
			listener->_warntime = now + listener->_warn_interval;
			return;
		}
	}
	g_warn_if_reached();
}

FSTATIC void
_hblistener_ref(HbListener* self)
{
	self->_refcount += 1;
}

FSTATIC void
_hblistener_unref(HbListener* self)
{
	g_return_if_fail(self->_refcount > 0);
	self->_refcount -= 1;
	if (self->_refcount == 0) {
		self->_finalize(self);
		self=NULL;
	}
}

/// Finalize an HbListener
FSTATIC void
_hblistener_finalize(HbListener * self) ///< Listener to finalize
{
	self->_listenaddr->unref(self->_listenaddr);
	// self->_listenaddr = NULL;
	memset(self, 0x00, sizeof(*self));
	FREECLASSOBJ(self);
}


/// Construct a new HbListener - setting up GSource and timeout data structures for it.
/// This can be used directly or by derived classes.
///@todo Create Gsource, attach to context, write dispatch code,
///@todo Add to list/table of listeners
///@todo Create scan process - ensuring we don't do it any more often than once every 900ms or so.
///@todo Add interface and code for registering dead machine callbacks - Lots to do!

HbListener*
hblistener_new(NetAddr*	listenaddr,
	       gsize objsize)	///< size of HbListener structure (or zero for sizeof(HbListener))
{
	HbListener * newlistener;
	if (objsize < sizeof(HbListener)) {
		objsize = sizeof(HbListener);
	}
	newlistener = MALLOCCLASS(HbListener, objsize);
	if (newlistener != NULL) {
		newlistener->_listenaddr = listenaddr;
		listenaddr->ref(listenaddr);
		newlistener->_refcount = 1;
		newlistener->ref = _hblistener_ref;
		newlistener->unref = _hblistener_unref;
		newlistener->_finalize = _hblistener_finalize;
		newlistener->_expected_interval = DEFAULT_DEADTIME * 1000000;
		newlistener->_warn_interval = newlistener->_expected_interval / 4;
		newlistener->_nexttime = proj_get_real_time() + newlistener->_expected_interval;
		newlistener->_warntime = proj_get_real_time() + newlistener->_warn_interval;
	}
	return newlistener;
}
