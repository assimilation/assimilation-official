/**
 * @file
 * @brief Describes interfaces to C-String Frame (Compressframe) C-Class 
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

#ifndef _COMPRESSFRAME_H
#define _COMPRESSFRAME_H
#include <projectcommon.h>
#include <frame.h>

///@{
/// @ingroup CompressFrame
typedef struct _CompressFrame CompressFrame;

#define	MAXUDPSIZE			65507		///< Maximum UDP packet size	
#define DEFAULT_COMPRESSION_THRESHOLD	(MAXUDPSIZE/3)	///< Default value of when to start compressing

/// Compression methods
#define	COMPRESS_NONE	0	///< No compression
#define	COMPRESS_ZLIB	1	///< Compression using 'zlib'

/// This is our @ref CompressFrame object - used for representing a compression method.
struct _CompressFrame {
	Frame		baseclass;
	guint32		compression_threshold;
	guint32		decompressed_size;
	guint8		compression_method;
	guint8		compression_index;
};


WINEXPORT CompressFrame* compressframe_new(guint16 frame_type, guint16 compression_method);
WINEXPORT CompressFrame* compressframe_new_string(guint16 frame_type, const char* compression_name);
WINEXPORT Frame* compressframe_tlvconstructor(gpointer, gconstpointer, gpointer*,gpointer*);

///@}

#endif /* _COMPRESSFRAME_H */
