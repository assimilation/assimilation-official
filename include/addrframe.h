
/**
 * @file
 * @brief Describes interfaces to Address Frame (AddrFrame) C-Class
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _ADDRFRAME_H
#define _ADDRFRAME_H
#include <frame.h>
typedef struct _AddrFrame AddrFrame;

/// This is our AddrFrame object - used for holding network addresses.
/// It has some different member functions implementations than its base @ref Frame -
/// mainly for validating packet contents.
///@{
/// @ingroup AddrFrame
struct _AddrFrame {
	Frame		baseclass;
	void(*setaddr)	(AddrFrame* f, guint16 addrtype, gpointer addr, gsize addrlen);
};

AddrFrame* addrframe_new(guint16 frame_type, gsize framesize);

///@}
#endif /* _ADDRFRAME_H */
