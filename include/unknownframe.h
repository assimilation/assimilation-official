/**
 * @file
 * @brief Describes interfaces to the Unknown Frame (UnknownFrame) C-Class
 * @details Unknown frame types occur when one side sends a frame and the other side has older
 * software that doesn't know about that Frame type.  Or due to bugs or simlar things :-D
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

WINEXPORT UnknownFrame* unknownframe_new(guint16 frame_type); // Derived classes not possible.
WINEXPORT Frame* unknownframe_tlvconstructor(gpointer tlvstart, gconstpointer pktend, gpointer*,gpointer*);

///@}
#endif /* _UNKNOWNFRAME_H */
