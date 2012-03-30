/**
 * @file
 * @brief Implements the @ref AuthListener class - for listening to heartbeats.
 * @details We obey incoming packets from the Collective Authority.
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
#define	IS_LISTENER_SUBCLASS
#include <authlistener.h>
/**
 */
FSTATIC void _authlistener_finalize(AssimObj * self);
FSTATIC gboolean _authlistener_got_frameset(Listener* self, FrameSet*, NetAddr*);
FSTATIC void _authlistener_associate(AuthListener* self, NetGSource* transport);
FSTATIC void _authlistener_dissociate(AuthListener* self);

///@defgroup AuthListener Listener class.
/// Class for listening, authenticating, and obeying packets from the Collectiv e Authority
///@{
///@ingroup Listener
#define	ONESEC	1000000

/// Function called when a @ref FrameSet arrived from the given @ref NetAddr
FSTATIC gboolean
_authlistener_got_frameset(Listener* self, FrameSet* fs, NetAddr* addr)
{
	AuthListener*		aself = CASTTOCLASS(AuthListener, self);
	AuthListenerAction	action;

	action = g_hash_table_lookup(aself->actionmap, GINT_TO_POINTER((int)fs->fstype));

	if (NULL == action) {
		g_warning("%s received FrameSet of unrecognized type %u", __FUNCTION__, fs->fstype);
		goto returnout;
	}
	/// @todo need to authorize the sender of this @ref FrameSet before acting on it...
	action(aself, fs, addr);


returnout:
	fs->unref(fs);
	return TRUE;
}
FSTATIC void
_authlistener_associate(AuthListener* self, NetGSource* transport)
{
	GHashTableIter	iter;
	gpointer	key;
	gpointer	value;
	Listener*	lself = CASTTOCLASS(Listener, self);
	if (self->transport) {
		self->dissociate(self);
	}
	g_hash_table_iter_init(&iter, self->actionmap);
	while (g_hash_table_iter_next(&iter, &key, &value)) {
		guint16	fstype = GPOINTER_TO_INT(key);
		transport->addListener(transport, fstype, lself);
	}
	self->transport = transport;
}
FSTATIC void
_authlistener_dissociate(AuthListener* self)
{
	GHashTableIter	iter;
	gpointer	key;
	gpointer	value;
	if (!self->transport) {
		return;
	}
	g_hash_table_iter_init(&iter, self->actionmap);
	while (g_hash_table_iter_next(&iter, &key, &value)) {
		guint16	fstype = GPOINTER_TO_INT(key);
		self->transport->addListener(self->transport, fstype, NULL);
	}
	self->transport = NULL;
}

/// Finalize a Listener
FSTATIC void
_authlistener_finalize(AssimObj * self) ///<[in/out] Listener to finalize
{
	AuthListener*		aself = CASTTOCLASS(AuthListener, self);
	aself->dissociate(aself);
	if (aself->actionmap) {
		g_hash_table_destroy(aself->actionmap);
		aself->actionmap = NULL;
	}
	_listener_finalize(self);
}


/// Construct a new Listener - setting up GSource and timeout data structures for it.
/// This can be used directly or by derived classes.
AuthListener*
authlistener_new(ObeyFrameSetTypeMap*map,///<[in] NULL-terminated map of FrameSet types to action functions -
		 ConfigContext* config,	 ///<[in/out] configuration context
		 gsize objsize)		 ///<[in] size of Listener structure (0 for sizeof(Listener))
{
	AuthListener * newlistener;
	if (objsize < sizeof(AuthListener)) {
		objsize = sizeof(AuthListener);
	}
	newlistener = NEWSUBCLASS(AuthListener, listener_new(config, objsize));
	if (newlistener != NULL) {
		GHashTable* hash;
		newlistener->baseclass.baseclass._finalize = _authlistener_finalize;
		newlistener->baseclass.got_frameset = _authlistener_got_frameset;
		newlistener->associate = _authlistener_associate;
		newlistener->dissociate = _authlistener_dissociate;
		hash = g_hash_table_new(NULL, NULL);
		for (; map->action; ++map) {
			g_hash_table_insert(hash, GINT_TO_POINTER(map->framesettype), map->action);
		}
		newlistener->actionmap = hash;
		
		
	}
	return newlistener;
}
///@}
