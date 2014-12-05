/**
 * @file
 * @brief Implements the @ref SignFrame class - A frame implementing basic Glib digital signatures.
 * @details SignFrames are
 * We validate the signature method, the size of the digital signature, and that the data in
 * following the signature block has the signature that's found in the signature block.
 * This class implements simple checksum digital signatures.
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
#include <signframe.h>
#include <frametypes.h>
#include <generic_tlv_min.h>
#include <tlvhelper.h>
#undef HAVE_SODIUM_H
#ifdef HAVE_SODIUM_H
#	include <sodium.h>
#endif

/**
 * @defgroup SignFrameFormats C-class SignFrame wire format
 * @{
 * @ingroup FrameFormats
 * Here is the wire format we use for digital signatures
<PRE>
+---------------+-----------+-----------------+--------------------+
| frametype = 1 | f_length  | signature-type  | digital signature  |
|   (16 bits)   | (16-bits) |   (16 bits)     | (f_length-2 bytes) |
+---------------+-----------+-----------------+--------------------+
</PRE>
@note
Because of their special nature, all digital signature frames <b>must</b> have frametype <b>1</b>
and be the first frame in the frameset.
 * @}
 */

///@defgroup SignFrame SignFrame class
/// Class representing digital signatures - subclass of @ref Frame.
/// @{
/// @ingroup Frame

FSTATIC gboolean _signframe_isvalid(const Frame *, gconstpointer, gconstpointer);
FSTATIC void _signframe_updatedata(Frame* self, gpointer tlvptr, gconstpointer pktend, FrameSet* fs);
FSTATIC gpointer _signframe_compute_cksum(GChecksumType, gconstpointer tlvptr, gconstpointer pktend);
FSTATIC gpointer _signframe_compute_cksum_glib(GChecksumType, gconstpointer tlvptr, gconstpointer pktend);
FSTATIC gboolean _signframe_isvalid_glib(const Frame * self, gconstpointer tlvptr, gconstpointer pktend);
FSTATIC guint16	_signframe_cksum_size(guint8 majortype, guint8 minortype);
#ifdef SODIUM_H
FSTATIC SignFrame* signframe_sodium_new(guint8 minortype, char * cksumname, gsize framesize);
FSTATIC gpointer _signframe_compute_cksum_sodium(GChecksumType, gconstpointer tlvptr, gconstpointer pktend);
FSTATIC Frame* _signframe_sodium_tlvconstructor(gpointer tlvstart, gconstpointer pktend, gpointer* ignorednewpkt, gpointer* ignoredpktend);
#endif

static	guint8	default_checksum_major_type = 0;
static	guint8	default_checksum_minor_type = 0;
static char*	default_checksum_keyname = NULL;
static guint8*	default_checksum_signkey = NULL;
static guint8	default_checksum_keylen = 0;

///< Return the checksum size for this type of checksum...
FSTATIC guint16
_signframe_cksum_size(guint8 majortype, guint8 minortype)
{
	switch(majortype) {
		case SIGNTYPE_GLIB:
			return g_checksum_type_get_length(minortype);
#ifdef HAVE_SODIUM_H
		case SIGNTYPE_SODIUM: {
			switch(minortype) {
				case SIGNTYPE_SODIUM_SHA512256:
				return crypto_auth_KEYBYTES;
				
				case SIGNTYPE_SODIUM_ED25519:
				return crypto_sign_BYTES;
			}
			break;
		}
#endif
	}
	g_return_val_if_reached(0);
}


///< Set default outbound signing key
gboolean
signframe_setdefault(guint8 majortype		///< Major signature class
		,    guint8 minortype		///< Minor signature type
		,    const char * keyname	///< Name of key used by verifier
		,    const guint8* signkey	///< Pointer to key
		,    gsize keylen)		///< Key length
{
	if (majortype == SIGNTYPE_GLIB) {
		g_return_val_if_fail(keyname == NULL, FALSE);
		g_return_val_if_fail(signkey == NULL, FALSE);
		g_return_val_if_fail(keylen == 0, FALSE);
		g_return_val_if_fail(g_checksum_type_get_length(minortype) > 0, FALSE);
#ifdef HAVE_SODIUM_H
	}else if (majortype == SIGNTYPE_SODIUM) {
		g_return_val_if_fail(keyname != NULL, FALSE);
		g_return_val_if_fail(signkey != NULL, FALSE);
		if (minortype == SIGNTYPE_SODIUM_SHA512256) {
			g_return_val_if_fail(keylen == crypto_auth_KEYBYTES, FALSE);
		}else if (minortype == SIGNTYPE_SODIUM_ED25519) {
			g_return_val_if_fail(keylen == crypto_sign_PUBLICKEYBYTES, FALSE);
		}else{
			g_return_val_if_reached(FALSE);
		}
#endif
	}
	default_checksum_major_type = majortype;
	default_checksum_minor_type = minortype;
	default_checksum_keylen = keylen;
	if (keylen > 0) {
		default_checksum_signkey = g_malloc(keylen);
		memcpy(default_checksum_signkey, signkey, keylen);
	}
	if (keyname != NULL) {
		default_checksum_keyname = g_strdup(keyname);
	}
	return TRUE;
}
FSTATIC gpointer
_signframe_compute_cksum(GChecksumType cksumtype,	///<[in] checksum type
			 gconstpointer tlvptr,		///<[in] pointer to TLV for checksum
			 gconstpointer pktend)		///<[in] one byte past end of packet
{
	return _signframe_compute_cksum_glib(cksumtype, tlvptr, pktend);
}

/// Internal helper routine for computing checksum on data in a frame.
/// It is used both for computing checksums on "new" data and verifying checksums on received packets.
FSTATIC gpointer
_signframe_compute_cksum_glib(GChecksumType cksumtype,	///<[in] checksum type
			 gconstpointer tlvptr,		///<[in] pointer to TLV for checksum
			 gconstpointer pktend)		///<[in] one byte past end of packet
{
	guint32		framelen  = get_generic_tlv_len(tlvptr, pktend);
	const guint8*	nextframe;
	gssize		cksumsize;
	gssize		remainsize;
	gsize		bufsize;
	GChecksum*	cksumobj;
	guint8*		cksumbuf = NULL;

	// Get the size of this type checksum
	cksumsize = g_checksum_type_get_length(cksumtype);
	g_return_val_if_fail(cksumsize > 1, NULL);
	g_return_val_if_fail((gssize)framelen == (cksumsize + 2), NULL);

	// Find out what data is left after our frame - the data we operate on...
	nextframe = get_generic_tlv_next(tlvptr, pktend);
	g_return_val_if_fail(nextframe != NULL, NULL);

	// Compute size of remaining data (data after this frame)
	remainsize = (const guint8*)pktend - nextframe;
	g_return_val_if_fail(remainsize > 0, NULL);

	// Create a new checksum object
	cksumobj = g_checksum_new(cksumtype);
	g_return_val_if_fail(NULL != cksumobj, NULL);

	// Compute the checksum on the remainder of the packet
	g_checksum_update(cksumobj, nextframe, remainsize);

	bufsize = cksumsize;
	cksumbuf = MALLOC0(bufsize);
	if (cksumbuf != NULL) {
		// Accumulate the checksum itself - into binary digest form
		g_checksum_get_digest(cksumobj, cksumbuf, &bufsize);

		if (bufsize != (gsize)cksumsize) {
			FREE(cksumbuf);
			cksumbuf=NULL;
		}
	}
	g_checksum_free(cksumobj);
	return cksumbuf;
}
/// @ref SignFrame 'isvalid' member function - verifies a Glib digital signature
FSTATIC gboolean
_signframe_isvalid(const Frame * self,		///< SignFrame object ('this')
		   gconstpointer tlvptr,	///< Pointer to the TLV for this SignFrame
		   gconstpointer pktend)	///< Pointer to one byte past the end of the packet
{
	const guint8*	framedata;
	guint32		framelen;
	guint8		majortype;
	if (tlvptr == NULL) {
		const SignFrame*	sframe = CASTTOCONSTCLASS(SignFrame, self);
		if (sframe->majortype == SIGNTYPE_GLIB) {
			return _signframe_isvalid_glib(self, tlvptr, pktend);
#ifdef HAVE_SODIUM_H
		}else if (sframe->majortype == SIGNTYPE_SODIUM) {
			return _signframe_isvalid_sodium(self, tlvptr, pktend);
#endif
		}
		return FALSE;
	}
	framedata = get_generic_tlv_value(tlvptr, pktend);
	framelen  = get_generic_tlv_len(tlvptr, pktend);
	g_return_val_if_fail(framedata != NULL, FALSE);
	g_return_val_if_fail(framelen > 2, FALSE);
	
	// Verify that we are majortype 1 (byte 0)
	majortype   = tlv_get_guint8(framedata,   pktend);
	if (majortype == SIGNTYPE_GLIB) {
		return _signframe_isvalid_glib(self, tlvptr, pktend);
#ifdef SODIUM_H
	}else if (majortype == SIGNTYPE_SODIUM) {
		return _signframe_isvalid_sodium(self, tlvptr, pktend);
#endif
	}
	return FALSE;
}

/// @ref SignFrame 'isvalid' member function - verifies a Glib digital signature
FSTATIC gboolean
_signframe_isvalid_glib(const Frame * self,		///< SignFrame object ('this')
		   gconstpointer tlvptr,	///< Pointer to the TLV for this SignFrame
		   gconstpointer pktend)	///< Pointer to one byte past the end of the packet
{
	const guint8*	framedata;
	guint32		framelen;
	guint8		majortype;
	GChecksumType	cksumtype;
	gssize		cksumsize;
	guint8*		cksumbuf;
	gboolean	ret = TRUE;


	if (tlvptr == NULL) {
		const SignFrame*	sframe = CASTTOCONSTCLASS(SignFrame, self);
		g_return_val_if_fail(sframe->majortype == SIGNTYPE_GLIB, FALSE);
		return (g_checksum_type_get_length(sframe->minortype) >= 1);
	}
	framedata = get_generic_tlv_value(tlvptr, pktend);
	framelen  = get_generic_tlv_len(tlvptr, pktend);
	g_return_val_if_fail(framedata != NULL, FALSE);
	g_return_val_if_fail(framelen > 2, FALSE);
	
	// Verify that we are majortype 1 (byte 0)
	majortype   = tlv_get_guint8(framedata,   pktend);
	g_return_val_if_fail(majortype == SIGNTYPE_GLIB, FALSE);

	// Get the type of the checksum (byte 1)
	cksumtype = (GChecksumType)tlv_get_guint8(framedata+1, pktend);

	cksumsize = g_checksum_type_get_length(cksumtype);
	if (cksumsize < 1) {
		ret = FALSE;
	}else{
		cksumbuf = _signframe_compute_cksum_glib(cksumtype, tlvptr, pktend);
		if (cksumbuf == NULL) {
			// Failed to compute checksum...
			ret = FALSE;
		}else{
			if (memcmp(cksumbuf, framedata+2, cksumsize) != 0) {
				// Checksum mismatch
				ret = FALSE;
			}
			FREE(cksumbuf);
			cksumbuf = NULL;
		}
	}
	return ret;
}

/// Write/update digital signature in packet.
/// This is based on all the data that follows this frame in the packet.
/// Since this is always the first frame in the packet, that means all data
/// past this initial digital signature frame - all the packet except for
/// this signature frame.
///@pre a properly constructed @ref SignFrame as the 'fself' object pointer.
FSTATIC void
_signframe_updatedata(Frame* fself,		///<[in] SignFrame signature Frame
		      gpointer tlvptr,		///<[in/out] Pointer to our TLV data in the packet
		      gconstpointer pktend,	///<[in] One byte past end of packet
		      FrameSet* fs)		///<[ignored] FrameSet to update
{
	SignFrame*	self = CASTTOCLASS(SignFrame, fself);
	GChecksumType	cksumtype = self->minortype;
	gssize		cksumsize;
	guint8*		cksumbuf;
	guint8*		framedata = get_generic_tlv_nonconst_value(tlvptr, pktend);

	(void)fs;
	g_return_if_fail(self->majortype == SIGNTYPE_GLIB);
	g_return_if_fail(framedata != NULL);
	
	// Compute the checksum
	cksumbuf = _signframe_compute_cksum(cksumtype, tlvptr, pktend);
	g_return_if_fail(cksumbuf != NULL);

	// Make sure our frame is sized exactly right
	cksumsize = g_checksum_type_get_length(cksumtype);
	g_return_if_fail((gssize)(self->baseclass.length) == (2 + cksumsize));

	// Put in the major checksum type (byte 0)
	tlv_set_guint8(framedata, self->majortype, pktend);

	// Put in the minor checksum type (byte 1)
	tlv_set_guint8(framedata+1, self->minortype, pktend);

	// Copy over the checksum data (bytes 2 through cksumsize+2)
	memcpy(framedata+2, cksumbuf, cksumsize);

	// Free the computed checksum
	FREE(cksumbuf); cksumbuf = NULL;
	// That's it!
}


/// Construct a new SignFrame - allowing for "derived" frame types...
/// This can be used directly for creating SignFrame frames, or by derived classes.
WINEXPORT SignFrame*
signframe_glib_new(GChecksumType sigtype,	///< signature type
	      gsize framesize)		///< size of frame structure (or zero for sizeof(SignFrame))
{
	Frame*		baseframe;
	SignFrame*	ret;
	gssize		cksumsize;
	guint16		frame_type = FRAMETYPE_SIG;

	if (framesize < sizeof(SignFrame)) {
		framesize = sizeof(SignFrame);
	}
	cksumsize = g_checksum_type_get_length(sigtype);
	if (cksumsize <= 1) {
		return NULL;
	}
	baseframe = frame_new(frame_type, framesize);
	baseframe->isvalid = _signframe_isvalid;
	baseframe->updatedata = _signframe_updatedata;
	baseframe->length = cksumsize + 2;
	baseframe->value = NULL;
	proj_class_register_subclassed (baseframe, "SignFrame");

	ret = CASTTOCLASS(SignFrame, baseframe);
	ret->majortype = SIGNTYPE_GLIB;
	ret->minortype = sigtype;
	return ret;
}


/// Given marshalled data corresponding to a SignFrame (signature frame), return that corresponding Frame
/// In other words, un-marshall the data...
/// @note when we add more subtypes to signatures (which will surely happen), then
/// this code will have to be updated to deal with that...
Frame*
signframe_tlvconstructor(gpointer tlvstart,		///<[in] beginning of the SignFrame in packet
			 gconstpointer pktend,		///<[in] end of packet
		         gpointer* newpkt,		///<[in/out] replacement packet
		         gpointer* newpktend)		///<[in/out] end of replacement packet
{
	guint32		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	guint8		majortype;
	GChecksumType	minortype;

	(void)newpkt; (void)newpktend;
	g_return_val_if_fail(framelength > 2, NULL);
	majortype = tlv_get_guint8(framevalue, pktend);
	minortype = tlv_get_guint8(framevalue+1, pktend);

	/// @note we currently ignore the subtype - since we only support one...
	if (majortype == SIGNTYPE_GLIB) {
		SignFrame *	ret = NULL;
		ret = signframe_glib_new(minortype, 0);
		g_return_val_if_fail(NULL != ret, NULL);
		ret->baseclass.length = framelength;
		//ret->baseclass.value = framevalue; // @TODO Should .value be set???
		return CASTTOCLASS(Frame, ret);
#ifdef HAVE_SODIUM_H
	}else if (majortype == SIGNTYPE_SODIUM) {
		return signframe_sodium_tlvconstructor(tlvstart, pktend, newpkt, newpktend);
#endif
	}else{
		return NULL;
	}
}
#ifdef HAVE_SODIUM_H
static GHashTable*	pki_keys = NULL;
static GHashTable*	sharedkeys = NULL;

FSTATIC SignFrame*
_signframe_sodium_new(guint8 minortype, char * signname, gsize framesize)
{
}
FSTATIC gpointer
_signframe_compute_cksum_sodium(GChecksumType, gconstpointer tlvptr, gconstpointer pktend)
{
}

// Minimum packet: major, minor, checksum, {cksumname}, NULL byte
#define MINSODLEN(cksumsize)	(2+(cksumsize)+1)
FSTATIC Frame*
signframe_sodium_tlvconstructor(gpointer tlvstart,	///<[in] beginning of the SignFrame in packet
			 gconstpointer pktend,		///<[in] end of packet
		         gpointer* ignorednewpkt,	///<[ignored] replacement packet
		         gpointer* ignoredpktend)	///<[ignored] end of replacement packet
{
	guint32		framelength = get_generic_tlv_len(tlvstart, pktend);
	const guint8*	framevalue = get_generic_tlv_value(tlvstart, pktend);
	guint8		majortype = tlv_get_guint8(framevalue, pktend);
	GChecksumType	minortype = tlv_get_guint8(framevalue+1, pktend);
	SignFrame *	ret;
	gint16		cksumlen;
	gint16		namelen;
	guint8*		key;
	char *		cksumname;
	g_return_val_if_fail (majortype == SIGNTYPE_GLIB, NULL);
	cksumlen = _signframe_cksum_size(majortype, minortype);
	g_return_val_if_fail (cksumlen < 1);
	g_return_val_if_fail (framelength < MINSODLEN(cksumlen));
	// Make sure it's NUL-terminated
	g_return_val_if_fail(tlv_get_guint8(framevalue+framelength-1) == 0, NULL);
	namelen = framelength - MINSODLEN(cksumlen);
	g_return_val_if_fail(namelen < 1);
	// Make sure it only exactly *one* NUL byte
	cksumname = (char *) (framevalue+MINSODLEN(cksumlen))
	g_return_val_if_fail(strnlen(cksumname, namelen) == namelen, NULL);
	g_return_val_if_fail(SIGNTYPE_SODIUM_SHA512256 == minortype
	||	SIGNTYPE_SODIUM_ED25519 == minortype);
	ret = _signframe_sodium_new(minortype, cksumname, 0);
	g_return_val_if_fail(NULL != ret, NULL);
	ret->baseclass.length = framelength;
	//ret->baseclass.value = framevalue; // @TODO Should .value be set???
	return CASTTOCLASS(Frame, ret);
}
#endif
///@}
