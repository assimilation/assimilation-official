
/**
 * @file
 * @brief Describes interfaces to C-String Frame (Cstringframe) C-Class 
 * It holds conventional zero-terminated byte strings.
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

#ifndef _CSTRINGFRAME_H
#define _CSTRINGFRAME_H
#include <frame.h>

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
WINEXPORT Frame* cstringframe_tlvconstructor(gpointer tlvstart, gconstpointer pktend, gpointer*,gpointer*);

///@}

#endif /* _CSTRINGFRAME_H */
