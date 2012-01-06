
/**
 * @file
 * @brief Describes interfaces to name/value pair Frame (NVpairFrame) C-Class 
 * It holds conventional zero-terminated byte strings.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _NVPAIRFRAME_H
#define _NVPAIRFRAME_H

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
Frame* nvpairframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend);

///@}

#endif /* _NVPAIRFRAME_H */
