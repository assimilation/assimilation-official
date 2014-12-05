/**
 * @file
 * @brief Implements the IntFrame class - integers in a frame.
 * @details We support 1, 2, 3, 4, and 8 byte integers.
 * @note This class does not use the 'value' field in the
 * base class, and does not implement the setvalue() member function.
 *
 *
 * This file is part of the Assimilation Project.
 *
 * @author Copyright &copy; 2011, 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 *  The Assimilation software is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  The Assimilation software is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
 */

#ifndef _INTFRAME_H
#define _INTFRAME_H
#include <projectcommon.h>
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

WINEXPORT IntFrame* intframe_new(guint16 frametype, int intlength);
WINEXPORT Frame* intframe_tlvconstructor(gpointer tlvstart, gconstpointer pktend, gpointer*,gpointer*);
///@}

#endif /* _INTFRAME_H */
