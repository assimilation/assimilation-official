
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

#ifndef _CSTRINGFRAME_H
#define _CSTRINGFRAME_H

///@{
/// @ingroup CstringFrame
typedef struct _CstringFrame CstringFrame;

/// This is our @ref CstringFrame object - used for holding C-style NULL terminated strings.
/// It has some different member functions implementations than its base @ref Frame -
/// but mainly for validating packet contents to ensure they're well-formed C strings.
struct _CstringFrame {
	Frame		baseclass;
};

WINEXPORT CstringFrame* cstringframe_new(guint16 frame_type, gsize framesize);
WINEXPORT Frame* cstringframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend);

///@}

#endif /* _CSTRINGFRAME_H */
