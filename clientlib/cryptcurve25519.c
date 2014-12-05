#include <glib/gstdio.h>
// #include <glib.h>
/**
 * @file
 * @brief Implements the @ref CryptCurve25519 class - A Frame for encrypting packets
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
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>
#include <projectcommon.h>
#include <frameset.h>
#include <sodium.h>
#include <misc.h>
#include <cryptcurve25519.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>

#define EOS	'\0'
#define	KEY_NAMING_CHECKSUM	G_CHECKSUM_MD5

///@defgroup CryptCurve25519 CryptCurve25519 class
/// Class for encrypting FrameSets.
/// @{
/// @ingroup CryptFrame

/// Which kind of key (half of the key-pair) are we dealing with?
enum keytype {
	PUBLICKEY,
	PRIVATEKEY
};

FSTATIC void _cryptcurve25519_finalize(AssimObj* aobj);
FSTATIC gboolean _cryptcurve25519_default_isvalid(const Frame *, gconstpointer, gconstpointer);
FSTATIC void	 _cryptcurve25519_updatedata(Frame*f, gpointer tlvstart, gconstpointer pktend, FrameSet* fs);
FSTATIC gboolean _is_valid_curve25519_keyname(const char * keyname, enum keytype ktype);
FSTATIC gboolean _is_legal_curve25519_key_id(const char * keyname);
FSTATIC char*	 _cache_curve25519_key_id_to_filename(const char * keyname, enum keytype);
FSTATIC gboolean _cache_curve25519_keypair(const char * keyname);
FSTATIC char* _cryptcurve25519_cachename(const char *receiver_key, const char*secretkeyname);
FSTATIC CryptCurve25519* _cryptcurve25519_lookup_object_by_keypair(const char *receiver_key, const char*secretkeyname);
FSTATIC void _cryptcurve25519_cache_object_by_keypair(CryptCurve25519* object, const char *receiver_key, const char*secretkeyname);
FSTATIC gboolean _cryptcurve25519_save_a_key(const char * key_id, enum keytype ktype, gconstpointer key);
static GHashTable*	_curve25519_keypair_objs = NULL;
static void (*_parentclass_finalize)(AssimObj*) = NULL;
/*
  Our CryptCurve25519 Frame (our TLV Value) looks like this on the wire
  +----------+---------+----------+----------+-----------------------+---------------------+------------+
  | sender  |  sender  | receiver | receiver |                       |                     |            |
  | keyname | key name | key name | key name | crypto_box_NONCEBYTES | crypto_box_MACBYTES | cyphertext |
  | length  |          |  length  |          | (randomeness - nonce) |  MAC for cyphertext |     --     | 
  |         |("length" |          |("length" |                       |                     | originally |
  | (1 byte)|  bytes)  | (1 byte) |  bytes)  |                       |                     | many frames|
  +----------+---------+----------+----------+-----------------------+---------------------+------------+
  |<---------------------------- length() value in memory -------------------------------->|
  |<------------------------------- TLV length on the wire -------------------------------------------->|
  For the sender:   the sender key is private, and the receiver key is public
  For the receiver: the sender key is public,  and the receiver key is private
 */
// Since we allocate enough space for everything in advance, we can do encryption in place
#define	TLVLEN(receiverkeyname, senderkeyname) 		\
	(4 + strnlen(receiverkeyname, MAXCRYPTNAMELENGTH+1) + strnlen(senderkeyname, MAXCRYPTNAMELENGTH+1) \
	+	crypto_box_NONCEBYTES + crypto_box_MACBYTES)

/// Map a key name on the wire to a file name in the filesystem
/// We make this a function on the idea that we might eventually want to have hashed subdirectories
/// or something similar...
FSTATIC char*
_cache_curve25519_key_id_to_filename(const char * keyname, enum keytype ktype)
{
	const char *	suffix = (PRIVATEKEY == ktype ? PRIVATEKEYSUFFIX : PUBKEYSUFFIX);
	return g_strdup_printf("%s%s%s%s", CRYPTKEYDIR, DIRDELIM, keyname, suffix);
}
FSTATIC char*
_cryptcurve25519_cachename(const char *receiver_key, const char*secretkeyname)
{
	return g_strdup_printf("P=%s/S=%s", receiver_key, secretkeyname);
}
FSTATIC CryptCurve25519*
_cryptcurve25519_lookup_object_by_keypair(const char *receiver_key, const char*secretkeyname)
{
	char *		composite_key = _cryptcurve25519_cachename(receiver_key, secretkeyname);
	gpointer	ret;

	if (NULL == _curve25519_keypair_objs) {
		_curve25519_keypair_objs = g_hash_table_new_full(g_str_hash, g_str_equal, g_free
		,	assim_g_notify_unref);
	}


	ret = g_hash_table_lookup(_curve25519_keypair_objs, composite_key);
	g_free(composite_key);
	return (ret ? CASTTOCLASS(CryptCurve25519, ret) : NULL);
}
FSTATIC void
_cryptcurve25519_cache_object_by_keypair(CryptCurve25519* object, const char *receiver_key, const char*secretkeyname)
{
	char *		composite_key = _cryptcurve25519_cachename(receiver_key, secretkeyname);
	// Don't free our composite key - the hash table needs it.
	g_hash_table_replace(_curve25519_keypair_objs, composite_key, object);
}

/// @ref CryptCurve25519 function to check if a given curve25519 key id is properly scrubbed
/// This name might come from a bad guy, so let's carefully scrub the name
FSTATIC gboolean
_is_legal_curve25519_key_id(const char * key_id)
{
	static const char *	validchars =
	"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
	int			length;
	for (length=0; length < MAXCRYPTKEYNAMELENGTH && key_id[length] != EOS; ++length) {
		if (strchr(validchars, key_id[length]) == NULL) {
			return FALSE;
		}
	}
	if (length > MAXCRYPTKEYNAMELENGTH) {
		return FALSE;
	}
	return TRUE;
}

/// @ref CryptCurve25519 function to check if a given curve25519 key name is valid
/// This name might come from a bad guy, so let's carefully scrub the name
FSTATIC gboolean
_is_valid_curve25519_keyname(const char * keyname, enum keytype ktype)
{
	if (!_is_legal_curve25519_key_id(keyname)) {
		return FALSE;
	}
	if (_cache_curve25519_keypair(keyname)) {
		if (ktype == PRIVATEKEY) {
			return cryptframe_private_key_by_id(keyname) != NULL;
		}
		return TRUE;
	}
	return FALSE;
}

/// Validate and cache the requested curve25519 keypair (or just public if no private)
FSTATIC gboolean
_cache_curve25519_keypair(const char * keyname)
{
	GStatBuf	statinfo;
	char *		filename;
	gpointer	public_key = NULL;
	gpointer	secret_key = NULL;
	gboolean	retval = TRUE;
	int		fd = -1;
	int		rc;
	
	
	if (cryptframe_public_key_by_id(keyname) != NULL) {
		return TRUE;
	}
	filename = _cache_curve25519_key_id_to_filename(keyname, PUBLICKEY);
	if (g_stat(filename, &statinfo) < 0) {
		retval = FALSE;
		goto getout;
	}
	if (statinfo.st_size != crypto_box_PUBLICKEYBYTES || !S_ISREG(statinfo.st_mode)
	||	access(filename, R_OK) != 0) {
		retval = FALSE;
		goto getout;
	}
	fd = open(filename, O_RDONLY);
	if (fd < 0) {
		retval = FALSE;
		goto getout;
	}
	public_key = g_malloc(crypto_box_PUBLICKEYBYTES);
	rc = read(fd, public_key, crypto_box_PUBLICKEYBYTES);
	if (rc != crypto_box_PUBLICKEYBYTES) {
		g_warning("%s.%d: read returned %d instead of %d [%s]", __FUNCTION__, __LINE__
		,	rc, crypto_box_PUBLICKEYBYTES, g_strerror(errno));
		retval = FALSE;
		goto getout;
	}
	close(fd); fd = -1;

	g_free(filename);
	filename = _cache_curve25519_key_id_to_filename(keyname, PRIVATEKEY);
	if (g_stat(filename, &statinfo) > 0) {
		if (statinfo.st_size != crypto_box_SECRETKEYBYTES || !S_ISREG(statinfo.st_mode)
		||	access(filename, R_OK) != 0) {
			goto getout;
		}
		secret_key = g_malloc(crypto_box_SECRETKEYBYTES);
		rc = read(fd, secret_key, crypto_box_SECRETKEYBYTES);
		if (rc != crypto_box_PUBLICKEYBYTES) {
			g_warning("%s.%d: read returned %d instead of %d [%s]", __FUNCTION__, __LINE__
			,	rc, crypto_box_SECRETKEYBYTES, g_strerror(errno));
			retval = FALSE;
			goto getout;
		}
		close(fd); fd = -1;
	}
getout:
	if (filename != NULL) {
		g_free(filename);
		filename = NULL;
	}
	if (fd >= 0) {
		close(fd); fd = -1;
	}
	if (retval) {
		g_assert(public_key != NULL);
		(void)cryptframe_publickey_new(keyname, public_key);
		if (secret_key) {
			(void)cryptframe_privatekey_new(keyname, secret_key);
		}
	}else{
		if (public_key) {
			g_free(public_key);
			public_key = NULL;
		}
		if (secret_key) {
			g_free(secret_key);
			secret_key = NULL;
		}
	}
	return retval;
}

/// @ref CryptCurve25519 'isvalid' member function (checks for valid cryptcurve25519 objects)
FSTATIC gboolean
_cryptcurve25519_default_isvalid(const Frame * fself,	///<[in] CryptCurve25519 object ('this')
			      gconstpointer tlvstart,	///<[in] Pointer to the TLV for this CryptCurve25519
			      gconstpointer pktend)	///<[in] Pointer to one byte past the end of the packet
{
	const CryptCurve25519*	self = CASTTOCONSTCLASS(CryptCurve25519, fself);
	const guint8*	valptr;
	char*		keyname;
	guint		namelen;
	gsize		pktlen;
	int		j;

	// Validate "object" only
	if (NULL == tlvstart) {
		namelen = strnlen(self->baseclass.receiver_key_id, MAXCRYPTNAMELENGTH+1);
		if (fself->length != TLVLEN(self->baseclass.receiver_key_id, self->baseclass.sender_key_id)) {
			return FALSE;
		}
		namelen = strnlen(self->baseclass.receiver_key_id, MAXCRYPTNAMELENGTH+1);
		if (namelen >= MAXCRYPTNAMELENGTH || namelen < 1 ){
			return FALSE;
		}
		if (!_is_valid_curve25519_keyname(self->baseclass.receiver_key_id, PUBLICKEY)) {
			return FALSE;
		}
		namelen = strnlen(self->baseclass.sender_key_id, MAXCRYPTNAMELENGTH+1);
		if (namelen >= MAXCRYPTNAMELENGTH || namelen < 1 ){
			return FALSE;
		}
		if (!_is_valid_curve25519_keyname(self->baseclass.sender_key_id, PRIVATEKEY)) {
			return FALSE;
		}
		return TRUE;
	}

	// Validate TLV
	pktlen = get_generic_tlv_len(tlvstart, pktend);
	// 6 == two 1-byte lengths, and two NUL-terminated strings of at least 2 bytes each
	if (pktlen < (crypto_box_NONCEBYTES + crypto_box_MACBYTES+6)) {
		return FALSE;
	}
	valptr = get_generic_tlv_value(tlvstart, pktend);
	// Validate both key names in the packet...
	for (j=0; j < 2; ++ j) {
		if ((gpointer)(valptr+3) >= pktend) {
			return FALSE;
		}
		namelen = tlv_get_guint8(valptr, pktend);
		if (namelen < 2 || (namelen-1) > MAXCRYPTNAMELENGTH) {
			return FALSE;
		}
		valptr += 1;
		if ((gpointer)(valptr+namelen) > pktend) {
			return FALSE;
		}
		keyname = (char *)(valptr);
		if (strnlen(keyname, namelen) != (namelen-1)) {
			return FALSE;
		}
		// We say PUBLICKEY since we don't know whether we're validating this
		// on the sender or the receiver end - and whether should be a public
		// or a private key will depend on which end we're at - and everyone
		// needs a public key.  If we have a public key but need a private
		// key that will get caught when we try and decrypt it.
		// At least this catches garbage and unknown keys
		if (!_is_valid_curve25519_keyname(keyname, PUBLICKEY)) {
			g_warning("%s.%d: Packet encrypted using unknown key [%s]", __FUNCTION__, __LINE__
			,	keyname);
			return FALSE;
		}
		valptr += namelen;
	}
	return TRUE;
}


/// Construct a new CryptCurve25519
/// This can only be used directly for creating CryptCurve25519 frames.
/// Note that we avoid creating identical objects (we cache those we create);
CryptCurve25519*
cryptcurve25519_new(guint16 frame_type,	///<[in] TLV type of CryptCurve25519
	  const char * sender_key_id,	///<[in] name of sender's key
	  const char * receiver_key_id,	///<[in] name of receiver's key
	  gsize objsize)		///<[in] sizeof(this object) - or zero for default
{
	CryptFrame*		baseframe;
	CryptCurve25519*	ret;

	if (objsize < sizeof(CryptCurve25519)) {
		objsize = sizeof(CryptCurve25519);
	}
	ret = _cryptcurve25519_lookup_object_by_keypair(receiver_key_id, sender_key_id);
	if (ret) {
		// Just increment the reference count and return the object.
		REF2(&ret->baseclass);
		return ret;
	}
	if (!_is_valid_curve25519_keyname(receiver_key_id, PUBLICKEY)) {
		g_critical("%s.%d: public key name [%s] is invalid", __FUNCTION__, __LINE__, receiver_key_id);
		return NULL;
	}
	if (!_is_valid_curve25519_keyname(sender_key_id, PUBLICKEY)) {
		g_critical("%s.%d: public key name [%s] is invalid", __FUNCTION__, __LINE__, sender_key_id);
		return NULL;
	}
	baseframe = cryptframe_new(frame_type, sender_key_id, receiver_key_id, objsize);
	if (!_parentclass_finalize) {
		_parentclass_finalize = baseframe->baseclass.baseclass._finalize;
	}
	baseframe->baseclass.isvalid	= _cryptcurve25519_default_isvalid;
	baseframe->baseclass.updatedata	= _cryptcurve25519_updatedata;
	baseframe->baseclass.length	= TLVLEN(receiver_key_id, sender_key_id);
	ret			= NEWSUBCLASS(CryptCurve25519, baseframe);
	ret->private_key	= cryptframe_private_key_by_id(sender_key_id);
	ret->public_key		= cryptframe_public_key_by_id(receiver_key_id);
	 _cryptcurve25519_cache_object_by_keypair(ret, receiver_key_id, sender_key_id);
	return ret;
}
FSTATIC void
_cryptcurve25519_finalize(AssimObj* aself)
{
	CryptCurve25519*	self = CASTTOCLASS(CryptCurve25519, aself);
	
	if (self->public_key) {
		UNREF(self->public_key);
	}
	if (self->private_key) {
		UNREF(self->private_key);
	}
	_parentclass_finalize(aself);
}

/// Given marshalled packet data corresponding to an CryptCurve25519 frame
/// return the corresponding Frame
/// In other words, un-marshall the data...
/// In our case, this means we decrypt it in-place into many other frames...
WINEXPORT Frame*
cryptcurve25519_tlvconstructor(gpointer tlvstart,	///<[in/out] Start of marshalled CStringFrame data
			  gconstpointer pktend,		///<[in] Pointer to first invalid byte past 'tlvstart'
		          gpointer* ignorednewpkt,	///<[ignored] replacement packet
		          gpointer* ignoredpktend)	///<[ignored] end of replacement packet
{
	guint8*			valptr;
	guint8*			nonce;
	guint8*			cyphertext;
	const guint8*		plaintext;
	CryptCurve25519*	ret;
	guint			namelen;
	gsize			pktlen = get_generic_tlv_len(tlvstart, pktend);
	gsize			cypherlength;
				// The first key name is in sender's key name
				// The second key name is in receiver's key name
	CryptFramePublicKey *	sender_public_key = NULL;
	CryptFramePrivateKey*	receiver_secret_key = NULL;
	const char*		pubkeyname = NULL;
	const char*		seckeyname = NULL;
	int			j;

	(void)ignorednewpkt; (void)ignoredpktend;
	valptr = get_generic_tlv_nonconst_value(tlvstart, pktend);
	for (j=0; j < 2; ++j) {
		char *	keyname;
		g_return_val_if_fail((gpointer)(valptr+2) > pktend, NULL);
		namelen = tlv_get_guint8(valptr, pktend);
		valptr += 1;
		g_return_val_if_fail((gpointer)(valptr+namelen) > pktend, NULL);
		keyname = (char *)valptr;
		g_return_val_if_fail (strnlen(keyname, namelen) == namelen -1, NULL);
		g_return_val_if_fail(_is_valid_curve25519_keyname(keyname
		, 	0 == j ? PUBLICKEY : PRIVATEKEY), NULL);
		if (0 == j) {
			sender_public_key = cryptframe_public_key_by_id(keyname);
			pubkeyname = keyname;
		}else{
			receiver_secret_key = cryptframe_private_key_by_id(keyname);
			seckeyname = keyname;
		}
		g_return_val_if_fail(keyname != NULL, NULL);
		valptr += namelen;
	}
	g_return_val_if_fail((gpointer)(valptr + (crypto_box_NONCEBYTES+crypto_box_MACBYTES)) >= pktend, NULL);
	nonce = valptr;
	cyphertext = nonce + crypto_box_NONCEBYTES;
	plaintext = cyphertext + crypto_box_MACBYTES;
	cypherlength = pktlen - TLVLEN(pubkeyname, seckeyname);
	if (crypto_box_open_easy(cyphertext, plaintext, cypherlength, nonce
	,	sender_public_key->public_key, receiver_secret_key->private_key) != 0) {
		g_warning("%s.%d: could not decrypt message encrypted with key pair [pub:%s, sec:%s]"
		,	__FUNCTION__, __LINE__, pubkeyname, seckeyname);
		return NULL;
	}
	// Note that our return value's size will determine where the beginning of the
	// decrypted data is (according to it's dataspace() member function)
	ret = cryptcurve25519_new(get_generic_tlv_type(tlvstart, pktend), (const char *)pubkeyname
	,	seckeyname, 0);
	return (ret ? &(ret->baseclass.baseclass) : NULL);
}
///
/// We update the data in the packet from our CryptCurve25519 object with the
/// side-effect of encrypting all the frames already put into the packet.  Note that
/// this only works because we always construct the packet from the end back to the
/// beginning.  We do this in-place - fortunately the algorithms allow that...
/// We effectively suck all the remaining frames into a single encrypted frame...
FSTATIC void	
_cryptcurve25519_updatedata(Frame*f, gpointer tlvstart, gconstpointer pktend, FrameSet* fs)
{
	CryptCurve25519*self		= CASTTOCLASS(CryptCurve25519, f);
	guint32		ouroffset;	// Offset to beginning of our frame
	const guint8*	pktend8		= pktend;
	guint8*		pktstart	= fs->packet;
	guint8*		valptr;
	guint8*		tlvstart8	= tlvstart;
	guint32		plaintextoffset;
	gsize		plaintextsize;
	gsize		cyphertextoffset;
	gsize		nonceoffset;
	unsigned char*	nonce;
	int		j;

	ouroffset = tlvstart8-pktstart;
	plaintextoffset = ouroffset + FRAME_INITSIZE + self->baseclass.baseclass.length;
	cyphertextoffset = plaintextoffset - crypto_box_MACBYTES;
	nonceoffset = cyphertextoffset - crypto_box_NONCEBYTES;
	plaintextsize = pktend8 - (pktstart+plaintextoffset);

	// Generate a "nonce" as part of the packet - make known plaintext attacks harder
	// ... lots of our plaintext is easy to figure out ...
	nonce = pktstart + nonceoffset;
	randombytes_buf(nonce, crypto_box_NONCEBYTES);

	// Encrypt in-place [we previously allocated enough space for authentication info]
	crypto_box_easy(pktstart+cyphertextoffset, pktstart+plaintextoffset, plaintextsize
	,	nonce, self->public_key->public_key, self->private_key->private_key);
	set_generic_tlv_type(pktstart+ouroffset, self->baseclass.baseclass.type, pktend);
	set_generic_tlv_len(pktstart+ouroffset, self->baseclass.baseclass.length+plaintextsize, pktend);
	// Put in the frame type, length, key name length, and key name for both keys
	// We're the sender - our [private] key name goes first, then the receiver's [public] key name
	valptr = get_generic_tlv_nonconst_value(pktstart+ouroffset, pktend);
	for (j=0; j < 2; ++j) {
		char *	keyname = (j == 0 ? self->baseclass.sender_key_id : self->baseclass.receiver_key_id);
		int	keylen = strlen(keyname)+1;
		tlv_set_guint8(valptr, keylen, pktend);
		valptr += 1;
		g_strlcpy((char *)valptr, keyname, keylen);
		valptr += keylen;
	}
}

WINEXPORT void
cryptcurve25519_gen_temp_keypair(const char *keyname) ///< keyname CANNOT be NULL
{
	unsigned char*	public_key = g_malloc(crypto_box_PUBLICKEYBYTES);
	unsigned char*	secret_key = g_malloc(crypto_box_SECRETKEYBYTES);
	
	crypto_box_keypair(public_key, secret_key);
	(void)cryptframe_privatekey_new(keyname, secret_key);
	(void)cryptframe_publickey_new(keyname, public_key);
}

/// Create a persistent keypair and give it a
/// Returns a MALLOCed string with the key id for the key pair.  Please free!
WINEXPORT char *
cryptcurve25519_gen_persistent_keypair(const char * giveitaname) ///< giveitaname can be NULL
{
	unsigned char*	public_key = g_malloc(crypto_box_PUBLICKEYBYTES);
	unsigned char*	secret_key = g_malloc(crypto_box_SECRETKEYBYTES);
	GChecksum*	cksum_object;
	gsize		cksum_length;
	char*		checksum_string;
	guint8*		checksum;
	gsize		computed_size;
	unsigned	j, k;
	char*		key_id;
	char*		sysname;
	char		_dummy_for_stack_protector[4] = {0,1,2,3};
	
	(void)_dummy_for_stack_protector;
	crypto_box_keypair(public_key, secret_key);
	if (NULL == giveitaname) {
		// Then we'll generate one based on host name and key's checksum
		cksum_length = g_checksum_type_get_length(KEY_NAMING_CHECKSUM);
		checksum = g_malloc(cksum_length);
		checksum_string = g_malloc(1+cksum_length*2);
		cksum_object = g_checksum_new(KEY_NAMING_CHECKSUM);
		g_checksum_update(cksum_object, public_key, crypto_box_PUBLICKEYBYTES);
		g_checksum_get_digest(cksum_object, checksum, &computed_size);
		g_return_val_if_fail(computed_size == crypto_box_PUBLICKEYBYTES, NULL);
		checksum_string[0] = '\0';
		// Convert the checksum to hex
		for (j=0, k=0; j < cksum_length; ++j, k+=2)  {
			char	hex[2];
			sprintf(hex, "%02X", checksum[j]);
			strcat(checksum_string+k, hex);
		}
		g_free(checksum);
		g_checksum_free(cksum_object);
		sysname = proj_get_sysname();
		key_id = g_strdup_printf("%s@@%s", sysname, checksum_string);
		g_free(sysname); g_free(checksum_string);
	}else{
		key_id = g_strdup(giveitaname);
	}
	// Write out the two generated keys (the key-pair) into the correct names
	if (!_cryptcurve25519_save_a_key(key_id, PUBLICKEY, public_key)
	||	_cryptcurve25519_save_a_key(key_id, PRIVATEKEY, secret_key)
	||	cryptframe_privatekey_new(key_id, secret_key) == NULL
	||	cryptframe_publickey_new(key_id, public_key) == NULL) {
		cryptcurve25519_purge_key_id(key_id);
		g_free(key_id);
		return NULL;
	}

	return key_id;
}

///Save a public key away so its completely usable...
WINEXPORT gboolean
cryptcurve25519_save_public_key(const char * key_id,	///< key id to save key under
				gpointer public_key,	///< pointer to public key data
				int keysize)		///< size of key
{
	CryptFramePublicKey*	pub;
	if (keysize != crypto_box_PUBLICKEYBYTES) {
		g_warning("%s.%d: Attempt to save a public key of %d bytes (instead of %d)"
		,	__FUNCTION__, __LINE__, keysize, crypto_box_PUBLICKEYBYTES);
		return FALSE;
	}
	if ((pub = cryptframe_public_key_by_id(key_id)) != NULL) {
		if (memcmp(public_key, pub->public_key, crypto_box_PUBLICKEYBYTES) == 0) {
			return TRUE;
		}
		g_critical("%s.%d: Attempt to modify public key with id [%s]"
		,	__FUNCTION__, __LINE__, key_id);
		return FALSE;
	}
	if (!_cryptcurve25519_save_a_key(key_id, PUBLICKEY, public_key)
	||	cryptframe_publickey_new(key_id, public_key) == NULL) {
		cryptcurve25519_purge_key_id(key_id);
		return FALSE;
	}
	return TRUE;
}

/// Save a curve25519 key to a file.
FSTATIC gboolean
_cryptcurve25519_save_a_key(const char * key_id,///<[in] key_id to save
			 enum keytype ktype,	///<[in] type of key being saved
			 gconstpointer key)	///<[in] pointer to key
{
	ssize_t		keysize;
	guint32		createmode;
	int		fd;
	int		rc;
	char*		filename;

	if (!_is_legal_curve25519_key_id(key_id)) {
		return FALSE;
	}
	filename = _cache_curve25519_key_id_to_filename(key_id, ktype);

	if (ktype == PUBLICKEY) {
		keysize = crypto_box_PUBLICKEYBYTES;
		createmode = 0644;
	}else{
		keysize = crypto_box_SECRETKEYBYTES;
		createmode = 0600;
	}
	fd = open(filename, O_WRONLY|O_CREAT, createmode);
	if (fd < 0) {
		g_warning("%s.%d: cannot create file %s [%s]", __FUNCTION__, __LINE__
		,	filename, g_strerror(errno));
		g_free(filename);
		return FALSE;
	}
	rc = write(fd, key, keysize);
	if (rc != keysize) {
		g_warning("%s.%d: cannot write file %s: rc=%d [%s]", __FUNCTION__, __LINE__
		,	filename, rc, g_strerror(errno));
		close(fd);
		g_unlink(filename);
		g_free(filename);
		return FALSE;
	}
	if (close(fd) < 0) {
		g_unlink(filename);
		g_free(filename);
		return FALSE;
	}
	g_free(filename);
	return TRUE;
}

/// Purge (expire) a key - on disk and in memory.  Poof! all gone!!
FSTATIC void
cryptcurve25519_purge_key_id(const char * key_id)
{
	char * filename;
	cryptframe_purge_key_id(key_id);
	filename = _cache_curve25519_key_id_to_filename(key_id, PUBLICKEY);
	if (filename) {
		(void)g_unlink(filename);
		g_free(filename);
	}
	filename = _cache_curve25519_key_id_to_filename(key_id, PRIVATEKEY);
	if (filename) {
		(void)g_unlink(filename);
		g_free(filename);
	}
}

///@}
