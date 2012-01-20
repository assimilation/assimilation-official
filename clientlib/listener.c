/**
 * @file
 * @brief Implements the @ref Listener class - for listening to heartbeats.
 * @details We are told what addresses to listen for, what ones to stop listening for at run time
 * and time out both warning times, and fatal (dead) times.
 *
 * @author &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <projectcommon.h>
#include <memory.h>
#include <glib.h>
#include <frame.h>
#include <frameset.h>
#include <listener.h>
/**
 */
FSTATIC void _listener_finalize(Listener * self);
FSTATIC void _listener_ref(Listener * self);
FSTATIC void _listener_unref(Listener * self);
FSTATIC gboolean _listener_got_frameset(Listener* self, FrameSet*, NetAddr*);

///@defgroup Listener Listener class.
/// Class for heartbeat Listeners - We listen for heartbeats and time out those which are late.
///@{
///@ingroup C_Classes
#define	ONESEC	1000000

/// (not very useful) Function called when a @ref Frame arrived from the given @ref NetAddr
FSTATIC gboolean
_listener_got_frameset(Listener* self, FrameSet* fs, NetAddr* addr)
{
	(void)self;
	fs->unref(fs);
	(void)addr;
	return TRUE;
}

/// Increment the reference count by one.
FSTATIC void
_listener_ref(Listener* self)	///<[in/out] Object to increment reference count for
{
	self->_refcount += 1;
}

/// Decrement the reference count by one - possibly freeing up the object.
FSTATIC void
_listener_unref(Listener* self)	///<[in/out] Object to decrement reference count for
{
	g_return_if_fail(self->_refcount > 0);
	self->_refcount -= 1;
	if (self->_refcount == 0) {
		self->_finalize(self);
		self = NULL;
	}
}

/// Finalize a Listener
FSTATIC void
_listener_finalize(Listener * self) ///<[in/out] Listener to finalize
{
	memset(self, 0x00, sizeof(*self));
	FREECLASSOBJ(self);
}


/// Construct a new Listener - setting up GSource and timeout data structures for it.
/// This can be used directly or by derived classes.
Listener*
listener_new(gsize objsize)		///<[in] size of Listener structure (0 for sizeof(Listener))
{
	Listener * newlistener;
	if (objsize < sizeof(Listener)) {
		objsize = sizeof(Listener);
	}
	newlistener = MALLOCCLASS(Listener, objsize);
	if (newlistener != NULL) {
		newlistener->_refcount = 1;
		newlistener->ref = _listener_ref;
		newlistener->unref = _listener_unref;
		newlistener->_finalize = _listener_finalize;
		newlistener->got_frameset = _listener_got_frameset;
	}
	return newlistener;
}
///@}
