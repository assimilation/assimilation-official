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

FSTATIC gboolean _cryptcurve25519_default_isvalid(const Frame *, gconstpointer, gconstpointer);
FSTATIC void	 _cryptcurve25519_updatedata(Frame*f, gpointer tlvstart, gconstpointer pktend, FrameSet* fs);
FSTATIC gboolean _is_valid_curve25519_keyname(const char * keyname, enum keytype ktype);
FSTATIC gboolean _cache_curve25519_keys(const char * keyname);
FSTATIC char*	 _cache_curve25519_keyname_to_filename(const char * keyname, enum keytype);
static GHashTable*	_curve25519_pubkeys = NULL;
static GHashTable*	_curve25519_seckeys = NULL;
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
#define	TLVLEN(pubkeyname, privkeyname) 		\
	(4 + strnlen(pubkeyname, MAXCRYPTNAMELENGTH+1) + strnlen(privkeyname, MAXCRYPTNAMELENGTH+1) \
	+	crypto_box_NONCEBYTES + crypto_box_MACBYTES)

/// Map a key name on the wire to a file name in the filesystem
/// We make this a function on the idea that we might eventually want to have hashed subdirectories
/// or something similar...
FSTATIC char*
_cache_curve25519_keyname_to_filename(const char * keyname, enum keytype ktype)
{
	const char *	suffix = (PRIVATEKEY == ktype ? PRIVATEKEYSUFFIX : PUBKEYSUFFIX);
	return g_strdup_printf("%s%s%s%s", CRYPTKEYDIR, DIRDELIM, keyname, suffix);
}


/// @ref CryptCurve25519 function to check if a given curve25519 key name is valid
/// This name might come from a bad guy, so let's scrub the name
FSTATIC gboolean
_is_valid_curve25519_keyname(const char * keyname, enum keytype ktype)
{
	static const char *	validchars =
	"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
	int			length;
	for (length=0; length < MAXCRYPTKEYNAMELENGTH && keyname[length] != EOS; ++length) {
		if (strchr(validchars, keyname[length]) == NULL) {
			return FALSE;
		}
	}
	if (length > MAXCRYPTKEYNAMELENGTH) {
		return FALSE;
	}
	if (_cache_curve25519_keys(keyname)) {
		if (ktype == PRIVATEKEY) {
			return g_hash_table_lookup(_curve25519_seckeys, keyname) != NULL;
		}
		return TRUE;
	}
	return FALSE;
}

/// Validate and cache the requested curve25519 keypair (or just public if no private)
FSTATIC gboolean
_cache_curve25519_keys(const char * keyname)
{
	GStatBuf	statinfo;
	char *		filename;
	gpointer	public_key = NULL;
	gpointer	secret_key = NULL;
	gboolean	retval = TRUE;
	int		fd = -1;
	int		rc;
	
	
	if (NULL == _curve25519_pubkeys) {
		_curve25519_pubkeys = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, g_free);
	}
	if (NULL == _curve25519_seckeys) {
		_curve25519_seckeys = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, g_free);
	}
	if (g_hash_table_lookup(_curve25519_pubkeys, keyname) != NULL) {
		return TRUE;
	}
	filename = _cache_curve25519_keyname_to_filename(keyname, PUBLICKEY);
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
	filename = _cache_curve25519_keyname_to_filename(keyname, PRIVATEKEY);
	if (g_stat(filename, &statinfo) > 0) {
		if (statinfo.st_size != crypto_box_SECRETKEYBYTES || !S_ISREG(statinfo.st_mode)
		||	access(filename, R_OK) != 0) {
			retval = FALSE;
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
		g_hash_table_insert(_curve25519_pubkeys, g_strdup(keyname), public_key);
		if (secret_key) {
			g_hash_table_insert(_curve25519_seckeys, g_strdup(keyname), secret_key);
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
		if (!self->publickey || !self->privatekey) {
			return FALSE;
		}
		namelen = strnlen(self->pubkeyname, MAXCRYPTNAMELENGTH+1);
		if (fself->length != TLVLEN(self->pubkeyname, self->privkeyname)) {
			return FALSE;
		}
		namelen = strnlen(self->pubkeyname, MAXCRYPTNAMELENGTH+1);
		if (namelen >= MAXCRYPTNAMELENGTH || namelen < 1 ){
			return FALSE;
		}
		if (!_is_valid_curve25519_keyname(self->pubkeyname, PUBLICKEY)) {
			return FALSE;
		}
		namelen = strnlen(self->privkeyname, MAXCRYPTNAMELENGTH+1);
		if (namelen >= MAXCRYPTNAMELENGTH || namelen < 1 ){
			return FALSE;
		}
		if (!_is_valid_curve25519_keyname(self->privkeyname, PRIVATEKEY)) {
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
CryptCurve25519*
cryptcurve25519_new(guint16 frame_type,	///<[in] TLV type of CryptCurve25519
	  const char * pubkeyname,	///<[in] name of public key
	  const char * privkeyname,	///<[in] name of secret/private key
	  gsize objsize)		///<[in] sizeof(this object) - or zero for default
{
	CryptFrame*		baseframe;
	CryptCurve25519*	ret;

	if (objsize < sizeof(CryptCurve25519)) {
		objsize = sizeof(CryptCurve25519);
	}
	if (!_is_valid_curve25519_keyname(pubkeyname, PUBLICKEY)) {
		g_critical("%s.%d: public key name [%s] is invalid", __FUNCTION__, __LINE__, pubkeyname);
		return NULL;
	}
	if (!_is_valid_curve25519_keyname(privkeyname, PRIVATEKEY)) {
		g_critical("%s.%d: public key name [%s] is invalid", __FUNCTION__, __LINE__, privkeyname);
		return NULL;
	}
	baseframe = cryptframe_new(frame_type, objsize);
	baseframe->baseclass.isvalid =		_cryptcurve25519_default_isvalid;
	baseframe->baseclass.updatedata =	_cryptcurve25519_updatedata;
	baseframe->baseclass.length = TLVLEN(pubkeyname, privkeyname);
	ret = NEWSUBCLASS(CryptCurve25519, baseframe);
	ret->pubkeyname	= g_strdup(pubkeyname);
	ret->pubkeyname	= g_strdup(privkeyname);
	ret->publickey	= g_hash_table_lookup(_curve25519_pubkeys, pubkeyname);
	ret->privatekey	= g_hash_table_lookup(_curve25519_seckeys, privkeyname);
	return ret;
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
	const unsigned char *	sender_public_key;
	const unsigned char *	receiver_secret_key;
	const char*		pubkeyname;
	const char*		seckeyname;
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
			sender_public_key = g_hash_table_lookup(_curve25519_pubkeys, keyname);
			pubkeyname = keyname;
		}else{
			receiver_secret_key = g_hash_table_lookup(_curve25519_seckeys, keyname);
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
	,	sender_public_key, receiver_secret_key) != 0) {
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
	// ... lots of our plaintext is well-known ...
	nonce = pktstart + nonceoffset;
	randombytes_buf(nonce, crypto_box_NONCEBYTES);

	// Encrypt in-place [we previously allocated enough space for authentication info]
	crypto_box_easy(pktstart+cyphertextoffset, pktstart+plaintextoffset, plaintextsize
	,	nonce, self->publickey, self->privatekey);
	set_generic_tlv_type(pktstart+ouroffset, self->baseclass.baseclass.type, pktend);
	set_generic_tlv_len(pktstart+ouroffset, self->baseclass.baseclass.length+plaintextsize, pktend);
	// Put in the frame type, length, key name length, and key name for both keys
	// We're the sender - our private key name goes first, then the receiver's public key name
	valptr = get_generic_tlv_nonconst_value(pktstart+ouroffset, pktend);
	for (j=0; j < 2; ++j) {
		char *	keyname = (j == 0 ? self->privkeyname : self->pubkeyname);
		int	keylen = strlen(keyname)+1;
		tlv_set_guint8(valptr, keylen, pktend);
		valptr += 1;
		g_strlcpy((char *)valptr, keyname, keylen);
		valptr += keylen;
	}
}

WINEXPORT void
cryptcurve25519_gen_temp_keypair(const char *keyname) //< keyname CANNOT be NULL
{
	unsigned char*	public_key = g_malloc(crypto_box_PUBLICKEYBYTES);
	unsigned char*	secret_key = g_malloc(crypto_box_SECRETKEYBYTES);
	
	crypto_box_keypair(public_key, secret_key);
	g_hash_table_insert(_curve25519_pubkeys, g_strdup(keyname), public_key);
	g_hash_table_insert(_curve25519_seckeys, g_strdup(keyname), secret_key);
}

// Create a persistent keypair and give it a
// Returns a MALLOCed string.  Please free!
WINEXPORT char *
cryptcurve25519_gen_persistent_keypair(const char * giveitaname) //< giveitaname can be NULL
{
	unsigned char*	public_key = g_malloc(crypto_box_PUBLICKEYBYTES);
	unsigned char*	secret_key = g_malloc(crypto_box_SECRETKEYBYTES);
	GChecksum*	cksum_object;
	gsize		cksum_length;
	char*		checksum_string;
	guint8*		checksum;
	gsize		computed_size;
	unsigned	j, k;
	char*		keyname;
	char*		sysname;
	int		fd;
	char*		filename;
	
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
		keyname = g_strdup_printf("%s@@%s", sysname, checksum_string);
		g_free(sysname); g_free(checksum_string);
	}else{
		keyname = g_strdup(giveitaname);
	}
	// Write out the two generated keys (the key-pair) into the correct names
	for (j=0; j < 2; ++j) {
		int	rc;
		void*	whichkey;
		ssize_t	keysize;
		guint32	createmode;
		filename = _cache_curve25519_keyname_to_filename(keyname, 0==j?PUBLICKEY:PRIVATEKEY);
		if (j == 0) {
			keysize = crypto_box_PUBLICKEYBYTES;
			whichkey = public_key;
			createmode = 0644;
			g_hash_table_insert(_curve25519_pubkeys, g_strdup(keyname), public_key);
		}else{
			keysize = crypto_box_SECRETKEYBYTES;
			whichkey = secret_key;
			createmode = 0600;
			g_hash_table_insert(_curve25519_seckeys, g_strdup(keyname), secret_key);
		}
		fd = open(filename, O_WRONLY|O_CREAT, createmode);
		if (fd < 0) {
			g_warning("%s.%d: cannot create file %s [%s]", __FUNCTION__, __LINE__
			,	filename, g_strerror(errno));
			g_free(filename);
			return NULL;
		}
		rc = write(fd, whichkey, keysize);
		if (rc != keysize) {
			g_warning("%s.%d: cannot write file %s: rc=%d [%s]", __FUNCTION__, __LINE__
			,	filename, rc, g_strerror(errno));
			close(fd);
			g_free(filename);
			return NULL;
		}
		close(fd);
	}
	return keyname;
}


///@}
