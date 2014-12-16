/**
 * @file
 * @brief Implements the @ref CryptFrame class - A Frame for encrypting packets
 * @details This frame cannot be usefully subclassed because of restrictions in FrameSets.
 * There are currently <b>no</b> implementations of encryption as of now.
 *
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
#include <string.h>
#include <projectcommon.h>
#include <frameset.h>
#include <cryptframe.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>
#include <misc.h>
#include <sodium.h>

FSTATIC gboolean _cryptframe_default_isvalid(const Frame *, gconstpointer, gconstpointer);
FSTATIC void _cryptframe_finalize(AssimObj* aself);
FSTATIC CryptFramePublicKey*  cryptframe_public_key_by_id(const char* key_id);
FSTATIC CryptFramePrivateKey*  cryptframe_private_key_by_id(const char* key_id);
static void (*_parentclass_finalize)(AssimObj*) = NULL;

///@defgroup CryptFrame CryptFrame class
/// Class for encrypting FrameSets.
/// @{
/// @ingroup Frame

/// @ref CryptFrame 'isvalid' member function (checks for valid cryptframe objects)
FSTATIC gboolean
_cryptframe_default_isvalid(const Frame * self,	///<[in] CryptFrame object ('this')
			      gconstpointer tlvptr,	///<[in] Pointer to the TLV for this CryptFrame
			      gconstpointer pktend)	///<[in] Pointer to one byte past the end of the packet
{
	(void)self;
	(void)tlvptr;
	(void)pktend;

	/// Abstract base class - always FALSE
	g_return_val_if_reached(FALSE);
}

/// Finalize (destructor) function for our CryptFramePublicKey objects
FSTATIC void
_cryptframe_finalize(AssimObj* aself) ///< object to finalize/destroy
{
	CryptFrame*	self = CASTTOCLASS(CryptFrame, aself);
	if (self->sender_key_id) {
		g_free(self->sender_key_id);
		self->sender_key_id = NULL;
	}
	if (self->receiver_key_id) {
		g_free(self->receiver_key_id);
		self->receiver_key_id = NULL;
	}
	_parentclass_finalize(aself);
}

/// Construct a new CryptFrame
/// This can only be used directly for creating subclassed CryptFrame frames because
/// CryptFrame is an abstract class...
CryptFrame*
cryptframe_new( guint16 frame_type,		///<[in] TLV type of CryptFrame
		const char * sender_key_id,	///<[in] Sender key id
		const char * receiver_key_id,	///<[in] Receiver key id
		gsize objsize)			///<[in] size of object
{
	Frame*		baseframe;
	CryptFrame*	self;

	if (objsize < sizeof(CryptFrame)) {
		objsize = sizeof(CryptFrame);
	}
	baseframe = frame_new(frame_type, objsize);
	if (!_parentclass_finalize) {
		_parentclass_finalize = baseframe->baseclass._finalize;
	}
	baseframe->isvalid = _cryptframe_default_isvalid;
	self = NEWSUBCLASS(CryptFrame, baseframe);
	self->sender_key_id = g_strdup(sender_key_id);
	self->receiver_key_id = g_strdup(receiver_key_id);
	return self;
}
/// Given marshalled packet data corresponding to an CryptFrame - which we can't do
/// because we're an abstract class...
WINEXPORT Frame*
cryptframe_tlvconstructor(gpointer tlvstart,		///<[in] Start of marshalled CStringFrame data
			  gconstpointer pktend,		///<[in] Pointer to first invalid byte past 'tlvstart'
		          gpointer* ignorednewpkt,	///<[ignored] replacement packet
		          gpointer* ignoredpktend)	///<[ignored] end of replacement packet
{
	(void)tlvstart;
	(void)pktend;
	(void)ignorednewpkt;
	(void)ignoredpktend;
	// Abstract base class - can't do this...
	g_return_val_if_reached(NULL);
}
FSTATIC void _cryptframe_publickey_finalize(AssimObj* key);
FSTATIC void _cryptframe_privatekey_finalize(AssimObj* key);
FSTATIC void _cryptframe_initialize_maps(void);
// All our hash tables have strings for keys
static GHashTable*	public_key_map = NULL;		///< map of all public keys by key id
static GHashTable*	private_key_map = NULL;		///< map of all private keys by key id
static GHashTable*	identity_map_by_key_id = NULL;	///< map of identies by key id
static GHashTable*	key_id_map_by_identity = NULL;	///< A hash table of hash tables
							///< keyed by identity
							///< with strings for keys and values
							///< It tells you all the key ids
							///< associated with a given identity
GHashTable*	addr_to_public_key_map = NULL;		///< Maps @ref NetAddr to public key
static CryptFramePrivateKey*	default_signing_key = NULL;
#define	INITMAPS	{if (!maps_inityet) {_cryptframe_initialize_maps();}}
static gboolean		maps_inityet = FALSE;

/// Initialize all our maps
FSTATIC void
_cryptframe_initialize_maps(void)
{
	if (maps_inityet) {
		return;
	}
	key_id_map_by_identity = g_hash_table_new_full(g_str_hash, g_str_equal
	,	NULL, (GDestroyNotify)g_hash_table_destroy);
	identity_map_by_key_id = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, g_free);
	public_key_map = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, assim_g_notify_unref);
	private_key_map = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, assim_g_notify_unref);
	addr_to_public_key_map = g_hash_table_new_full(netaddr_g_hash_hash
	,	netaddr_g_hash_equal, assim_g_notify_unref, assim_g_notify_unref);
	maps_inityet = TRUE;
}

/// Shut down our key caches and so on... (destroy our maps)
WINEXPORT void
cryptframe_shutdown(void)
{
	g_hash_table_destroy(key_id_map_by_identity);	key_id_map_by_identity=NULL;
	g_hash_table_destroy(identity_map_by_key_id);	identity_map_by_key_id=NULL;
	g_hash_table_destroy(public_key_map);		public_key_map=NULL;
	g_hash_table_destroy(private_key_map);		private_key_map=NULL;
	g_hash_table_destroy(addr_to_public_key_map);	addr_to_public_key_map=NULL;
	if (default_signing_key) {
		UNREF(default_signing_key);
	}
	maps_inityet = FALSE;
}

/// Finalize (destructor) function for our CryptFramePublicKey objects
FSTATIC void
_cryptframe_publickey_finalize(AssimObj* pubkey) ///< object to finalize/destroy
{
	CryptFramePublicKey*	self = CASTTOCLASS(CryptFramePublicKey, pubkey);
	if (self->key_id) {
		g_free(self->key_id);
		self->key_id = NULL;
	}
	if (self->public_key) {
		g_free(self->public_key);
		self->public_key = NULL;
	}
	_assimobj_finalize(pubkey);
}

/// Finalize (destructor) function for our CryptFramePrivateKey objects
FSTATIC void
_cryptframe_privatekey_finalize(AssimObj* privkey) ///< object to finalize/destroy
{
	CryptFramePrivateKey*	self = CASTTOCLASS(CryptFramePrivateKey, privkey);
	if (self->key_id) {
		g_free(self->key_id);
		self->key_id = NULL;
	}
	if (self->private_key) {
		g_free(self->private_key);
		self->private_key = NULL;
	}
	_assimobj_finalize(privkey);
}


/// Create a new public key - or return the existing public key with this id
WINEXPORT CryptFramePublicKey*
cryptframe_publickey_new (const char *key_id,	///< Key id of the given public key
			  gpointer public_key)	///< MALLOCed public key
{
	AssimObj*		aself;
	CryptFramePublicKey*	self;
	INITMAPS;
	self = cryptframe_public_key_by_id(key_id);
	if (self) {
		return self;
	}
	aself = assimobj_new(sizeof(CryptFramePublicKey));
	aself->_finalize = _cryptframe_publickey_finalize;
	self = NEWSUBCLASS(CryptFramePublicKey, aself);
	self->key_id = g_strdup(key_id);
	self->key_size = crypto_box_PUBLICKEYBYTES;
	self->frame_type = FRAMETYPE_PUBKEYCURVE25519;
	self->public_key = public_key;
	g_hash_table_insert(public_key_map, self->key_id, self);
	return self;
}

/// Create a new private key - or return the existing private key with this id
WINEXPORT CryptFramePrivateKey*
cryptframe_privatekey_new(const char *key_id,	///<[in] Key id of given private key
			  gpointer private_key)	///<[in] MALLOCed private key
{
	AssimObj*		aself;
	CryptFramePrivateKey*	self;
	INITMAPS;
	self = cryptframe_private_key_by_id(key_id);
	if (self) {
		return self;
	}
	aself = assimobj_new(sizeof(CryptFramePrivateKey));
	aself->_finalize = _cryptframe_privatekey_finalize;
	self = NEWSUBCLASS(CryptFramePrivateKey, aself);
	self->key_id = g_strdup(key_id);
	self->key_size = crypto_box_SECRETKEYBYTES;
	self->private_key = private_key;
	g_hash_table_insert(private_key_map, self->key_id, self);
	return self;
}

/// Return the non-const public key with the given id
WINEXPORT CryptFramePublicKey*
cryptframe_public_key_by_id(const char* key_id)	///[in] Key id of public key being sought
{
	gpointer	ret;
	INITMAPS;
	ret = g_hash_table_lookup(public_key_map, key_id);
	return (ret ? CASTTOCLASS(CryptFramePublicKey, ret): NULL);
}
/// Return the non-const private key with the given id
WINEXPORT CryptFramePrivateKey*
cryptframe_private_key_by_id(const char* key_id) ///<[in] Key id of the given private key being sought
{
	gpointer	ret;
	INITMAPS;
	ret = g_hash_table_lookup(private_key_map, key_id);
	return (ret ? CASTTOCLASS(CryptFramePrivateKey, ret): NULL);
}

/// Associate the given key id with the given identity
/// Note that it is OK to associate multiple key ids with a given identity
/// but it is NOT OK to associate multiple identities with a given key id
/// Return TRUE if we could make the association (it's OK to make
/// the same valid association multiple times)
WINEXPORT gboolean
cryptframe_associate_identity(const char * identity,	///<[in] identity to associate key with
			      const char * key_id)	///<[in] key to associate with identity
{
	GHashTable*	key_id_map;
	const char*	found_identity;
	char*		key_id_duplicate;
	char*		identity_duplicate;
	INITMAPS;
	g_return_val_if_fail(cryptframe_public_key_by_id(key_id)!= NULL, FALSE);
	found_identity = cryptframe_whois_key_id(key_id);
	if (found_identity) {
		if (strcmp(found_identity, key_id) != 0) {
			g_critical("%s.%d: Key id %s cannot be associated with identity %s."
			" Already associated with identity %s", __FUNCTION__, __LINE__
			,	key_id, identity, found_identity);
			return FALSE;
		}
		return TRUE;
	}
	key_id_duplicate = g_strdup(key_id);
	identity_duplicate = g_strdup(identity);
	g_hash_table_insert(identity_map_by_key_id, key_id_duplicate, identity_duplicate);

	key_id_map = cryptframe_key_ids_for(identity);
	if (NULL == key_id_map) {
		key_id_map = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
		g_hash_table_insert(key_id_map_by_identity, identity_duplicate, key_id_map);
	}
	if (!g_hash_table_lookup((GHashTable*)key_id_map, key_id)) {
		g_hash_table_insert(key_id_map, key_id_duplicate, key_id_duplicate);
	}
	return TRUE;
}

/// Dissociate the given key from the given identity (analogous to revoking the key)
WINEXPORT gboolean
cryptframe_dissociate_identity(const char * identity,	///<[in] identity to dissociate key from
			       const char * key_id)	///<[in] key id to "revoke"
{
	char*		found_identity;
	GHashTable*	key_id_map;
	INITMAPS;

	found_identity = g_hash_table_lookup(identity_map_by_key_id, key_id);
	if (NULL == found_identity) {
		return FALSE;
	}
	// The order of these deletions matters - because of shared data between tables.
	key_id_map = cryptframe_key_ids_for(identity);
	if (key_id_map) {
		g_hash_table_remove(key_id_map, key_id);
		if (g_hash_table_size(key_id_map) == 0) {
			// This identity doesn't meaningfully exist any more...
			g_hash_table_remove(key_id_map_by_identity, identity);
		}
	}
	g_hash_table_remove(identity_map_by_key_id, key_id);
	return TRUE;
}

/// Return the identity associated with the given public key object
WINEXPORT const char*
cryptframe_whois_public_key(const CryptFramePublicKey* public_key) ///<[in] public key whose identity
								   ///< is sought
{
	INITMAPS;
	return cryptframe_whois_key_id(public_key->key_id);
}

/// Return the identity associated with the given key id
WINEXPORT const char*
cryptframe_whois_key_id(const char * key_id)	///<[in] key id whose identity is sought
{
	INITMAPS;
	return (const char *)g_hash_table_lookup(identity_map_by_key_id, key_id);
}

/// Return a GHashTable of strings of all the key ids associated with the given identity
WINEXPORT GHashTable*
cryptframe_key_ids_for(const char* identity) 
{
	INITMAPS;
	return (GHashTable *)g_hash_table_lookup(key_id_map_by_identity, identity);
}

/// Return a GList of strings of all known identities
WINEXPORT GList*
cryptframe_get_identities(void)
{
	INITMAPS;
	return g_hash_table_get_keys(key_id_map_by_identity);
}

/// Return a GList of strings of all known key ids
WINEXPORT GList*
cryptframe_get_key_ids(void)
{
	INITMAPS;
	return g_hash_table_get_keys(identity_map_by_key_id);
}

WINEXPORT void
cryptframe_purge_key_id(const char * key_id)
{
	const char* whoarewe = cryptframe_whois_key_id(key_id);
	if (NULL != whoarewe) {
		cryptframe_dissociate_identity(whoarewe, key_id);
	}
	g_hash_table_remove(public_key_map, key_id);
	g_hash_table_remove(private_key_map, key_id);
}

/// Set the default signing key
WINEXPORT void
cryptframe_set_signing_key_id(const char * key_id)
{
	CryptFramePrivateKey*	secret_key = cryptframe_private_key_by_id(key_id);
	if (secret_key) {
		if (default_signing_key) {
			UNREF(default_signing_key);
			default_signing_key = NULL;
		}
		REF(secret_key);
		default_signing_key = secret_key;
	}else{
		g_warning("%s.%d: Cannot set signing key to [%s] - no such private key"
		,	__FUNCTION__, __LINE__, key_id);
	}
}

/// Return the key_id of the default signing key
WINEXPORT const char *
cryptframe_get_signing_key_id(void)
{
	return (default_signing_key ? default_signing_key->key_id : NULL);
}

/// Return the default signing key
WINEXPORT CryptFramePrivateKey*
cryptframe_get_signing_key(void)
{
	return default_signing_key;
}

static CryptFrame*	(*current_encryption_method) (const char* sender_key_id,
						      const char * receiver_key_id);
///
///	Set the encryption key to use when sending to destaddr
///	Set destkey to NULL to stop encrypting to that destination
WINEXPORT void
cryptframe_set_dest_public_key(NetAddr*destaddr,	///< Destination addr,port
			     CryptFramePublicKey*destkey)///< Public key to use when encrypting
{
	INITMAPS;
	g_return_if_fail(NULL != destaddr);
	if (NULL == destkey) {
		g_hash_table_remove(addr_to_public_key_map, destaddr);
	}else{
		REF(destaddr);
		REF(destkey);
		g_hash_table_insert(addr_to_public_key_map, destaddr, destkey);
	}
}
///
///	Set the encryption key to use when sending to destaddr
///	Set destkey to NULL to stop encrypting to that destination
WINEXPORT void
cryptframe_set_dest_public_key_id(NetAddr*destaddr,	///< Destination addr,port
			     const char * key_id)	///< Public key id to use when encrypting
{
	CryptFramePublicKey*	destkey;
	INITMAPS;
	g_return_if_fail(NULL != destaddr && NULL != key_id);
	destkey = g_hash_table_lookup(public_key_map, key_id);
	g_return_if_fail(NULL != destkey);
	cryptframe_set_dest_public_key(destaddr, destkey);
}

/// Construct a @ref CryptFrame appropriate for encrypting messages to <i>destaddr</i>
WINEXPORT CryptFrame*
cryptframe_new_by_destaddr(const NetAddr* destaddr)
{
	CryptFramePublicKey* receiver_key;
	if (NULL == current_encryption_method || NULL == default_signing_key) {
		return NULL;
	}
	receiver_key = g_hash_table_lookup(addr_to_public_key_map, destaddr);
	if (NULL == receiver_key) {
		return NULL;
	}
	return current_encryption_method(default_signing_key->key_id, receiver_key->key_id);
}
// Set the current encryption method
WINEXPORT void
cryptframe_set_encryption_method(CryptFrame*	(*method)	///< method/constructor for encryption
							(const char* sender_key_id,
							 const char * receiver_key_id))
{
	current_encryption_method = method;
}


///@}
