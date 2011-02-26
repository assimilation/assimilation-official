/**
 * @file
 * @brief Implements the IntFrame class - integers in a frame.
 * @details We support 1, 2, 3, 4, and 8 byte integers.
 * @note This class does not use the 'value' field in the
 * base class, and does not implement the setvalue() member function.
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


///@{
/// @ingroup IntFrame

typedef struct _IntFrame IntFrame;
/// This is an @ref IntFrame <b>TLV</b> (type, length, value) frame - representing an integer of some specified length.
/// It is a subclass of the @ref Frame.
/// and is manged by our @ref ProjectClass system.
struct _IntFrame {
	Frame	baseclass;					///< base @ref Frame object
	int	(*intlength)(IntFrame* self);			///< get length of integer this IntFrame supports
	guint64	(*getint)(IntFrame* self);			///< get value of integer in this IntFrame
	void	(*setint)(IntFrame* self, guint64 value);	///< set the integer to the given value
	guint64 _value;						///< network byte order value of this IntFrame
};

IntFrame* intframe_new(guint16 frametype, int intlength);
Frame* intframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend);
///@}

#endif /* _INTFRAME_H */
