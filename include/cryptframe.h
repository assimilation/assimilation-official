
/**
 * @file
 * @brief Describes interfaces to CryptFrame (encryption) C-Class 
 * It represents FrameSet encryption
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

#ifndef _CRYPTFRAME_H
#define _CRYPTFRAME_H
#include <frame.h>

///@{
/// @ingroup CryptFrame
typedef struct _CryptFrame CryptFrame;

/// This is our @ref CryptFrame object - representing an encryption method.
struct _CryptFrame {
	Frame		baseclass;
	int		encryption_method;
	void*		encryption_key_info;
};

CryptFrame* cryptframe_new(guint16 frame_type, guint16 encryption_method, void* encryption_info);
WINEXPORT Frame* cryptframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend, gpointer*,gpointer*);

///@}

#endif /* _CRYPTFRAME_H */
