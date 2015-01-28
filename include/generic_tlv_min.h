/**
 * @file
 * @brief Provides definitions for using our generic TLV capabilities.
 * @details We structure our packet bodies using this TLV (Type, Length, Value) approach
 * so all the Frame-derived classes make good use of these generic TLV functions.
 * @see Frame
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
#include <projectcommon.h>

/// Size of Generic TLV header -  ((type + length) == 5)
#define	GENERICTLV_HDRSZ	(sizeof(guint16)+/*sizeof(guint24)*/3)

WINEXPORT guint16 get_generic_tlv_type(gconstpointer tlv_vp, gconstpointer pktend);
/// get_generic_tlv_len returns a "tainted" result which should be validated against other criteria.
WINEXPORT guint32 get_generic_tlv_len(gconstpointer tlv_vp, gconstpointer pktend);
WINEXPORT gconstpointer get_generic_tlv_value(gconstpointer tlv_vp, gconstpointer pktend);
WINEXPORT gpointer get_generic_tlv_nonconst_value(gpointer tlv_vp, gconstpointer pktend);
/// get_generic_tlv_totalsize returns a "tainted" result which should be validated against other criteria.
WINEXPORT guint32 get_generic_tlv_totalsize(gsize datasize);
WINEXPORT gboolean is_valid_generic_tlv_packet(gconstpointer tlv_vp, gconstpointer pktend);
WINEXPORT gconstpointer get_generic_tlv_first(gconstpointer packet, gconstpointer pktend);
WINEXPORT gconstpointer get_generic_tlv_next(gconstpointer tlv_vp, gconstpointer pktend);
WINEXPORT gconstpointer find_next_generic_tlv_type(gconstpointer tlv_vp, guint16 tlvtype, gconstpointer pktend);
WINEXPORT void set_generic_tlv_type(gpointer tlv_vp, guint16 newtype, gconstpointer pktend);
WINEXPORT void set_generic_tlv_len(gpointer tlv_vp, guint32 newsize, gconstpointer pktend);
WINEXPORT void set_generic_tlv_value(gpointer tlv_vp, void* srcdata, guint32 srcsize, gconstpointer pktend);
