/**
 * @file
 * @brief Describes interfaces to the Unknown Frame (UnknownFrame) C-Class
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

/// This is our UnknownFrame object.
/// It is a binary frame of an unrecognized type.
///@{
/// @ingroup UnknownFrame
struct _UnknownFrame {
	Frame		baseclass;
};

UnknownFrame* unknownframe_new(guint16 frame_type); // Derived classes not possible.
Frame* unknownframe_tlvconstructor(gpointer tlvstart, gpointer pktend);

///@}
#endif /* _UNKNOWNFRAME_H */
