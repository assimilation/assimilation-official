
/**
 * @file
 * @brief Describes interfaces to Signature Frame (Signframe) C-Class - providing digital signatures
 * @details Base class for digital signatures.  They can be simple (like the current implementation)
 * and provide data integrity, but not data security, or eventually full-fledged digital signatures.
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

#ifndef _SIGNFRAME_H
#define _SIGNFRAME_H
#include <glib.h>
#include <frame.h>
///@{
/// @ingroup SignFrame

#define SIGNTYPE_GLIB	1	//< Glib GCheckSum objects
#ifdef HAVE_SODIUM_H
#	define SIGNTYPE_SODIUM	2		///< Sodium checksum objects
#	define SIGNTYPE_SODIUM_SHA512256 1	///< Secret key signature
#	define SIGNTYPE_SODIUM_ED25519	2	///< Public key signature
#endif

typedef struct _SignFrame SignFrame;

/// The @ref SignFrame object - implements digital signatures for @ref FrameSet "FrameSet"s.
/// This is a fairly special type of @ref Frame - it has no data of its own, and it
/// constructs data based on the portion of the packet that comes after it in the
/// @ref FrameSet "FrameSet"-constructed packet.
/// Not too surprising for a digital signature Frame.
struct _SignFrame {
	Frame		baseclass;			///< Base @ref Frame object.
	guint8		majortype;			///< Which signature module
	guint8		minortype;			///< signature subtype
};

WINEXPORT SignFrame* signframe_glib_new(GChecksumType sigtype, gsize framesize);
#ifdef HAVE_SODIUM_H
WINEXPORT SignFrame* signframe_sodium_new(guint8 sodiumtype, const guint8* key, gsize keylen, gsize framesize);
#endif
WINEXPORT SignFrame* signframe_new_default(gsize framesize);
WINEXPORT gboolean signframe_setdefault(guint8 majortype, guint8 minortype, const char* keyname, const guint8* signkey, gsize keylen);
WINEXPORT Frame* signframe_tlvconstructor(gpointer tlvstart, gconstpointer pktend, gpointer*,gpointer*);

///@}

#endif /* _SIGNFRAME_H */
