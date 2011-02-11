/**
 * @file
 * @brief Implements minimal client-oriented Frame and Frameset capabilities.
 * @details This file contains the minimal Frameset capabilities for a client -
 * enough for it to be able to construct, understand and validate Frames
 * and Framesets.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _INTFRAME_H
#define _INTFRAME_H
#include <frame.h>


/// This is an @ref IntFrame <b>TLV</b> (type, length, value) frame.
/// It is a subclass of the @ref Frame.
/// and is manged by our @ref ProjectClass system.
/// @note This class does not use the 'value' field in the
/// base class, and does not implement the setvalue() member function.
///@{
/// @ingroup IntFrame
typedef struct _IntFrame IntFrame;
struct _IntFrame {
	Frame	baseclass;					///< base @ref Frame object
	int	(*intlength)(IntFrame* self);			///< get length of integer this IntFrame supports
	guint64	(*getint)(IntFrame* self);			///< get value of integer in this IntFrame
	void	(*setint)(IntFrame* self, guint64 value);	///< set the integer to the given value
	guint64 _value;						///< network byte order value of this IntFrame
};

IntFrame* intframe_new(guint16 frametype, int intlength);
///@}

#endif /* _INTFRAME_H */
