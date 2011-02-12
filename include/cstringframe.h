
/**
 * @file
 * @brief Describes interfaces to C-String Frame (Cstringframe) C-Class 
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _CSTRINGFRAME_H
#define _CSTRINGFRAME_H
typedef struct _CstringFrame CstringFrame;

/// This is our CstringFrame object - used for holding C-style NULL terminated strings
/// It has some different member functions implementations than its base @ref Frame -
/// but mainly for validating packet contents.
///@{
/// @ingroup CstringFrame
struct _CstringFrame {
	Frame		baseclass;
};

CstringFrame* cstringframe_new(guint16 frame_type, gsize framesize);
Frame* cstringframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend);

///@}

#endif /* _CSTRINGFRAME_H */
