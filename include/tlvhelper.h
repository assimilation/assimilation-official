/**
 * @file
 * @brief TLV helper interfaces definitions.
 * @details Provides a bunch of generic getters and putters for TLV-style integer information.
 * Used by all our TLV implementations (3 of them at this writing)
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 *
 */
#include <glib.h>
#ifdef _MSC_VER
#define EXP_FUNC __declspec( dllexport )
#else
#define EXP_FUNC
#endif
EXP_FUNC guint8 tlv_get_guint8 (const void* vitem,  const void* bufend);
EXP_FUNC guint16 tlv_get_guint16(const void* vitem, const void* bufend);
EXP_FUNC guint32 tlv_get_guint24(const void* vitem, const void* bufend);
EXP_FUNC guint32 tlv_get_guint32(const void* vitem, const void* bufend);
EXP_FUNC guint64 tlv_get_guint64(const void* vitem, const void* bufend);
EXP_FUNC void tlv_set_guint8 (void* vitem, guint8  item, const void* bufend);
EXP_FUNC void tlv_set_guint16(void* vitem, guint16 item, const void* bufend);
EXP_FUNC void tlv_set_guint24(void* vitem, guint32 item, const void* bufend);
EXP_FUNC void tlv_set_guint32(void* vitem, guint32 item, const void* bufend);
EXP_FUNC void tlv_set_guint64(void* vitem, guint64 item, const void* bufend);
