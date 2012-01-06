
/**
 * @file
 * @brief Describes interfaces to C-String Frame (Compressframe) C-Class 
 * It holds conventional zero-terminated byte strings.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _COMPRESSFRAME_H
#define _COMPRESSFRAME_H

///@{
/// @ingroup CompressFrame
typedef struct _CompressFrame CompressFrame;

/// This is our @ref CompressFrame object - used for representing a compression method.
struct _CompressFrame {
	Frame		baseclass;
	guint16		compression_method;
};

CompressFrame* compressframe_new(guint16 frame_type, guint16 compression_method, gsize framesize);
Frame* compressframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend);

///@}

#endif /* _COMPRESSFRAME_H */
