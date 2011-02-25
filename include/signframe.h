
/**
 * @file
 * @brief Describes interfaces to Signature Frame (Signframe) C-Class - providing digital signatures
 * @details Base class for digital signatures.  They can be simple (like the current implementation)
 * and provide data integrity, but not data security, or eventually full-fledged digital signatures.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _SIGNFRAME_H
#define _SIGNFRAME_H
#include <glib.h>
typedef struct _SignFrame SignFrame;

/// This is our SignFrame object - implementing digital signatures for FrameSets.
/// This is a fairly special type of @ref Frame - it has no data of its own, and it
/// constructs data based on the portion of the packet that comes after it in the
/// FrameList-constructed packet.
/// Not too surprising for a digital signature Frame.
///@{
/// @ingroup SignFrame
struct _SignFrame {
	Frame		baseclass;	// Base Frame class object.
	GChecksumType	signaturetype;	// Type of signature...
};

SignFrame* signframe_new(GChecksumType sigtype, gsize framesize);
Frame* signframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend);

///@}

#endif /* _SIGNFRAME_H */
