
/**
 * @file
 * @brief Describes interfaces to name/value pair Frame (NVpairFrame) C-Class 
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

#ifndef _NVPAIRFRAME_H
#define _NVPAIRFRAME_H
#include <frame.h>

///@{
/// @ingroup NVpairFrame
typedef struct _NVpairFrame NVpairFrame;

/// This is our @ref NVpairFrame object - used for holding Name/Value pairs
struct _NVpairFrame {
	Frame		baseclass;
	gchar*		name;
	gchar*		value;
};

NVpairFrame* nvpairframe_new(guint16 frame_type, gchar* name, gchar* value, gsize framesize);
WINEXPORT Frame* nvpairframe_tlvconstructor(gpointer tlvstart, gconstpointer pktend, gpointer*,gpointer*);

///@}

#endif /* _NVPAIRFRAME_H */
