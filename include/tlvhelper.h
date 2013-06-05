/**
 * @file
 * @brief TLV helper interfaces definitions.
 * @details Provides a bunch of generic getters and putters for TLV-style integer information.
 * Used by all our TLV implementations (3 of them at this writing)
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
 *
 */
#include <projectcommon.h>
#include <glib.h>
WINEXPORT guint8 tlv_get_guint8 (const void* vitem,  const void* bufend);
WINEXPORT guint16 tlv_get_guint16(const void* vitem, const void* bufend);
WINEXPORT guint32 tlv_get_guint24(const void* vitem, const void* bufend);
WINEXPORT guint32 tlv_get_guint32(const void* vitem, const void* bufend);
WINEXPORT guint64 tlv_get_guint64(const void* vitem, const void* bufend);
WINEXPORT void tlv_set_guint8 (void* vitem, guint8  item, const void* bufend);
WINEXPORT void tlv_set_guint16(void* vitem, guint16 item, const void* bufend);
WINEXPORT void tlv_set_guint24(void* vitem, guint32 item, const void* bufend);
WINEXPORT void tlv_set_guint32(void* vitem, guint32 item, const void* bufend);
WINEXPORT void tlv_set_guint64(void* vitem, guint64 item, const void* bufend);
