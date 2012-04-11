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
void _listener_finalize(AssimObj * self);
FSTATIC gboolean _listener_got_frameset(Listener* self, FrameSet*, NetAddr*);
FSTATIC void _listener_associate(Listener* self, NetGSource* source);
FSTATIC void _listener_dissociate(Listener* self);

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
void
_listener_finalize(AssimObj * self) ///<[in/out] Listener to finalize
{
	Listener* lself = CASTTOCLASS(Listener, self);
	lself->config->baseclass.unref(lself->config);
	lself->dissociate(lself);
	memset(lself, 0x00, sizeof(*lself));
	FREECLASSOBJ(self);
}

/// Associate the given NetGSource with this @ref Listener
FSTATIC void
_listener_associate(Listener* self, NetGSource* source)
{
	// We kinda have to just hope that 'source' lives as long as we do...
	self->transport = source;
}

/// Associate the current NetGSource from this @ref Listener
FSTATIC void
_listener_dissociate(Listener* self)
{
	self->transport = NULL;
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
		newlistener->associate = _listener_associate;
		newlistener->dissociate = _listener_dissociate;
		newlistener->config = config;
		config->baseclass.ref(config);
	}
	return newlistener;
}
///@}
