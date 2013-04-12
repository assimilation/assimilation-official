/**
 * @file
 * @brief Implements the @ref Listener class - for listening for incoming FrameSets
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
	UNREF(fs);
	(void)addr;
	return TRUE;
}

/// Finalize a Listener
void
_listener_finalize(AssimObj * aself) ///<[in/out] Listener to finalize
{
	Listener* self = CASTTOCLASS(Listener, aself);
	UNREF(self->config);
	self->dissociate(self);
	memset(self, 0x00, sizeof(*self));
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
		REF(config);
	}
	return newlistener;
}
///@}
