/**
 * @file
 * @brief Implements the @ref AuthListener class - for listening to heartbeats.
 * @details We obey incoming packets from the Collective Authority.
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
 *  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/.
 */
#include <projectcommon.h>
#include <memory.h>
#include <glib.h>
#include <frame.h>
#include <frameset.h>
#define	IS_LISTENER_SUBCLASS
#include <authlistener.h>
#include <nanoprobe.h>
/**
 */
FSTATIC void _authlistener_finalize(AssimObj * self);
FSTATIC gboolean _authlistener_got_frameset(Listener* self, FrameSet*, NetAddr*);
FSTATIC void _authlistener_associate(Listener* self, NetGSource* transport);
FSTATIC void _authlistener_dissociate(Listener* self);

DEBUGDECLARATIONS

///@defgroup AuthListener AuthListener class.
/// Class for listening, authenticating, and obeying packets from the Collective Authority
///@{
///@ingroup Listener
#define	ONESEC	1000000

/// Function called when a @ref FrameSet arrived from the given @ref NetAddr
FSTATIC gboolean
_authlistener_got_frameset(Listener* self, FrameSet* fs, NetAddr* addr)
{
	AuthListener*		aself = CASTTOCLASS(AuthListener, self);
	AuthListenerAction	action;

	if (!nanoprobe_is_cma_frameset(fs)) {
		char *	addr_s = addr->baseclass.toString(&addr->baseclass);
		g_warning("%s.%d: Received unauthorized CMA command [%d] from address %s"
		,	__FUNCTION__, __LINE__, fs->fstype, addr_s);
		FREE(addr_s); addr_s=NULL;
	}

	action = g_hash_table_lookup(aself->actionmap, GINT_TO_POINTER((int)fs->fstype));

	if (NULL == action) {
		g_warning("%s received FrameSet of unrecognized type %u", __FUNCTION__, fs->fstype);
		goto returnout;
	}
	/// @todo need to authorize the sender of this @ref FrameSet before acting on it...
	action(aself, fs, addr);
	


returnout:
	if (aself->autoack) {
		DUMP3("_authlistener_got_frameset: AutoACKing FrameSet", &fs->baseclass, NULL);
		self->transport->_netio->ackmessage(self->transport->_netio, addr, fs);
	}
	UNREF(fs);
	return TRUE;
}
FSTATIC void
_authlistener_associate(Listener* lself, NetGSource* transport)
{
	AuthListener*	self = CASTTOCLASS(AuthListener, lself);
	GHashTableIter	iter;
	gpointer	key;
	gpointer	value;
	if (lself->transport) {
		lself->dissociate(lself);
	}
	g_hash_table_iter_init(&iter, self->actionmap);
	while (g_hash_table_iter_next(&iter, &key, &value)) {
		guint16	fstype = GPOINTER_TO_INT(key);
		transport->addListener(transport, fstype, lself);
	}
	lself->transport = transport;
}
FSTATIC void
_authlistener_dissociate(Listener* lself)
{
	AuthListener*	self = CASTTOCLASS(AuthListener, lself);
	GHashTableIter	iter;
	gpointer	key;
	gpointer	value;
	if (!lself->transport) {
		return;
	}
	g_hash_table_iter_init(&iter, self->actionmap);
	while (g_hash_table_iter_next(&iter, &key, &value)) {
		guint16	fstype = GPOINTER_TO_INT(key);
		lself->transport->addListener(lself->transport, fstype, NULL);
	}
	lself->transport = NULL;
}

/// Finalize a Listener
FSTATIC void
_authlistener_finalize(AssimObj * aself) ///<[in/out] Listener to finalize
{
	AuthListener*		self = CASTTOCLASS(AuthListener, aself);
	self->baseclass.dissociate(&self->baseclass);
	if (self->actionmap) {
		g_hash_table_destroy(self->actionmap);
		self->actionmap = NULL;
	}
	_listener_finalize(aself);
}


/// Construct a new Listener - setting up GSource and timeout data structures for it.
/// This can be used directly or by derived classes.
AuthListener*
authlistener_new(gsize objsize,		 ///<[in] size of Listener structure (0 for sizeof(Listener))
		 ObeyFrameSetTypeMap*map,///<[in] NULL-terminated map of FrameSet types to action functions -
		 ConfigContext* config,	 ///<[in/out] configuration context
		 gboolean autoack)	 ///<[in] TRUE if the authlistener should do the ACKing for us
{
	AuthListener * newlistener;
	BINDDEBUG(AuthListener);
	if (objsize < sizeof(AuthListener)) {
		objsize = sizeof(AuthListener);
	}
	newlistener = NEWSUBCLASS(AuthListener, listener_new(config, objsize));
	if (newlistener != NULL) {
		GHashTable* hash;
		newlistener->baseclass.baseclass._finalize = _authlistener_finalize;
		newlistener->baseclass.got_frameset = _authlistener_got_frameset;
		newlistener->baseclass.associate = _authlistener_associate;
		newlistener->baseclass.dissociate = _authlistener_dissociate;
		hash = g_hash_table_new(NULL, NULL);
		for (; map->action; ++map) {
			g_hash_table_insert(hash, GINT_TO_POINTER(map->framesettype), map->action);
		}
		newlistener->actionmap = hash;
		newlistener->autoack = autoack;
		
		
	}
	return newlistener;
}
///@}
