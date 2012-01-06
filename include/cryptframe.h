
/**
 * @file
 * @brief Describes interfaces to C-String Frame (Cstringframe) C-Class 
 * It holds conventional zero-terminated byte strings.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _CRYPTFRAME_H
#define _CRYPTFRAME_H

///@{
/// @ingroup CryptFrame
typedef struct _CryptFrame CryptFrame;

/// This is our @ref CryptFrame object - representing an encryption method.
struct _CryptFrame {
	Frame		baseclass;
	int		encryption_method;
	void*		encryption_key_info;
};

CryptFrame* cryptframe_new(guint16 frame_type, guint16 encryption_method, void* encryption_info);
Frame* cryptframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend);

///@}

#endif /* _CRYPTFRAME_H */
