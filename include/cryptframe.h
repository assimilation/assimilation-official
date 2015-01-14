/**
 * @file
 * @brief Describes interfaces to CryptFrame (encryption) C-Class 
 * It represents the abstract base class for FrameSet encryption
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

#ifndef _CRYPTFRAME_H
#define _CRYPTFRAME_H
#include <frame.h>
#include <netaddr.h>

///@{
/// @ingroup CryptFrame
#define MAXCRYPTKEYNAMELENGTH	64	///< Maximum length of a crypt key name
typedef struct _CryptFrame CryptFrame;

typedef struct {
	AssimObj	baseclass;
	char*		key_id;		///< unique name for this key
	int		key_size;	///< sizeof(public_key)
	int		frame_type;	///< FrameType of this type of public key
					///< (we never send private keys - no symmetry here)
	gpointer	public_key;	///< Pointer to the (malloced) public key;
}CryptFramePublicKey;

typedef struct {
	AssimObj	baseclass;
	char*		key_id;		///< unique name for this key
	int		key_size;	///< sizeof(private_key)
	gpointer	private_key;	///< Pointer to the (malloced) private key
}CryptFramePrivateKey;



/// This is our @ref CryptFrame object - representing an encryption method.
struct _CryptFrame {
	Frame		baseclass;
	char *		sender_key_id;
	char *		receiver_key_id;
};

CryptFrame* cryptframe_new(guint16 frame_type, const char *sender_key_id, const char * receiver_key_id
,	gsize framesize);
WINEXPORT Frame* cryptframe_tlvconstructor(gpointer tlvstart, gconstpointer pktend, gpointer*,gpointer*);

WINEXPORT CryptFramePublicKey*  cryptframe_public_key_by_id(const char* key_id);
WINEXPORT CryptFramePrivateKey* cryptframe_private_key_by_id(const char* key_id);
WINEXPORT CryptFramePublicKey*  cryptframe_publickey_new (const char *key_id, gpointer public_key);
WINEXPORT CryptFramePrivateKey*	cryptframe_privatekey_new(const char *key_id, gpointer private_key);
WINEXPORT gboolean		cryptframe_associate_identity(const char * identity, const char * key_id);
WINEXPORT gboolean		cryptframe_dissociate_identity(const char * identity, const char * key_id);
WINEXPORT void			cryptframe_purge_key_id(const char * key_id);
WINEXPORT const char*		cryptframe_whois_public_key(const CryptFramePublicKey* public_key);
WINEXPORT const char*		cryptframe_whois_key_id(const char * key_id);
WINEXPORT GHashTable*		cryptframe_key_ids_for(const char* identity);
WINEXPORT GList*		cryptframe_get_identities(void);	// List of String values
WINEXPORT GList*		cryptframe_get_key_ids(void);		// List of String values
WINEXPORT void			cryptframe_shutdown(void);
WINEXPORT void			cryptframe_set_signing_key_id(const char * key_id);
WINEXPORT const char *		cryptframe_get_signing_key_id(void);
WINEXPORT CryptFramePrivateKey*	cryptframe_get_signing_key(void);
WINEXPORT void cryptframe_set_dest_public_key(NetAddr*, CryptFramePublicKey*);
WINEXPORT void cryptframe_set_dest_key_id(NetAddr*, const char * key_id);
WINEXPORT const char * cryptframe_get_dest_key_id(const NetAddr*);
WINEXPORT CryptFrame*		cryptframe_new_by_destaddr(const NetAddr* destination_address);
WINEXPORT void			cryptframe_set_encryption_method(CryptFrame*(*)
					(const char* sender_key_id, const char * receiver_key_id));
///@}
#endif /* _CRYPTFRAME_H */
