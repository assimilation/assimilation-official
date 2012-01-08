/**
 * @file
 * @brief Describes interfaces to the Unknown Frame (UnknownFrame) C-Class
 * @details Unknown frame types occur when one side sends a frame and the other side has older
 * software that doesn't know about that Frame type.  Or due to bugs or simlar things :-D
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _UNKNOWNFRAME_H
#define _UNKNOWNFRAME_H
#include <frame.h>
typedef struct _UnknownFrame UnknownFrame;

/// This is our @ref UnknownFrame object - for unrecognized @ref Frame "Frame"s.
/// It is a binary frame of an unrecognized type.
///@{
/// @ingroup UnknownFrame
struct _UnknownFrame {
	Frame		baseclass;
};

#ifdef _MSC_VER
#define EXP_FUNC __declspec( dllexport )
#endif
EXP_FUNC UnknownFrame* unknownframe_new(guint16 frame_type); // Derived classes not possible.
EXP_FUNC Frame* unknownframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend);

///@}
#endif /* _UNKNOWNFRAME_H */
