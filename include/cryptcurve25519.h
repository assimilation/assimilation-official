/**
 * @file
 * @brief Describes interfaces to CryptFrame (encryption) C-Class 
 * It represents a FrameSet using libsodium (curve25519) for public key encryption.
 * In particular, we use the libsodium simple_box*() interfaces which use the following algorithms:
 *	Key exchange: Curve25519
 *	Encryption: XSalsa20 stream cipher
 *	Authentication: Poly1305 MAC
 *
 * Note that these interfaces integrate message validation with encryption/decryption
 * so we don't need a separate cryptographic validation of the sender.
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

#ifndef _CRYPTCURVE25519_H
#define _CRYPTCURVE25519_H
#include <cryptframe.h>

///@{
/// @ingroup CryptCurve25519
/// Which kind of key (half of the key-pair) are we dealing with?
enum keytype {
	NOTAKEY,
	PUBLICKEY,
	PRIVATEKEY
};
typedef struct _CryptCurve25519 CryptCurve25519;

/// This is our @ref CryptCurve25519 object - representing a Curve25519 encryption @ref Frame
struct _CryptCurve25519 {
	CryptFrame		baseclass;
	CryptFramePublicKey*	public_key;	///< Pointer to associated public key
	CryptFramePrivateKey*	private_key;	///< Pointer to private key
	gboolean		forsending;	///< TRUE if this is for sending, FALSE for receiving
};

#define	MAXCRYPTNAMELENGTH	64

WINEXPORT CryptCurve25519* cryptcurve25519_new(guint16 frame_type, const char * pubkeyname, const char *privkeyname, gboolean forsending, gsize objsize);
WINEXPORT Frame* cryptcurve25519_tlvconstructor(gpointer tlvstart, gconstpointer pktend, gpointer*,gpointer*);
WINEXPORT void cryptcurve25519_gen_temp_keypair(const char* keyname);
WINEXPORT char* cryptcurve25519_gen_persistent_keypair(const char * keyname);
WINEXPORT gboolean cryptcurve25519_save_public_key(const char * key_id, gpointer public_key, int keysize);
WINEXPORT CryptFrame* cryptcurve25519_new_generic(const char* sender_key_id,
						  const char* receiver_key_id, gboolean forsending);
WINEXPORT void cryptcurve25519_cache_all_keypairs(void);
WINEXPORT gboolean cryptcurve25519_purge_keypair(const char * key_id);
WINEXPORT void cryptcurve25519_set_encryption_method(void);///< Just for python simplicity...
WINEXPORT char*	 curve25519_key_id_to_filename(const char * key_id, enum keytype);
///@}

#endif /* _CRYPTCURVE25519_H */
