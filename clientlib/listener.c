/**
 * @file
 * @brief Implements the @ref Listener class - for listening for incoming FrameSets
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
FSTATIC void _listener_finalize(AssimObj * self);
FSTATIC gboolean _listener_got_frameset(Listener* self, FrameSet*, NetAddr*);

///@defgroup Listener Listener class.
/// Base Listener class - Listen for @ref FrameSet "FrameSet"s
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

/// Finalize a Listener
FSTATIC void
_listener_finalize(AssimObj * self) ///<[in/out] Listener to finalize
{
	Listener* lself = CASTTOCLASS(Listener, self);
	lself->config->baseclass.unref(lself->config);
	memset(lself, 0x00, sizeof(*lself));
	FREECLASSOBJ(self);
}


/// Construct a new Listener - setting up GSource and timeout data structures for it.
/// This can be used directly or by derived classes.
Listener*
listener_new(ConfigContext* config,	///<[in/out] configuration context
	     gsize objsize)		///<[in] size of Listener structure (0 for sizeof(Listener))
{
	Listener * newlistener;
	if (objsize < sizeof(Listener)) {
		objsize = sizeof(Listener);
	}
	newlistener = NEWSUBCLASS(Listener, assimobj_new(objsize));
	if (newlistener != NULL) {
		newlistener->baseclass._finalize = _listener_finalize;
		newlistener->got_frameset = _listener_got_frameset;
		newlistener->config = config;
		config->baseclass.ref(config);
	}
	return newlistener;
}
///@}
