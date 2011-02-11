/**
 * @file
 * @brief Provides definitions for using minimal client-oriented Generic TLV capabilities.
 * @see Frame
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <projectcommon.h>

guint16 get_generic_tlv_type(gconstpointer tlv_vp, gconstpointer pktend);
guint16 get_generic_tlv_len(gconstpointer tlv_vp, gconstpointer pktend);
gconstpointer get_generic_tlv_value(gconstpointer tlv_vp, gconstpointer pktend);
gpointer get_generic_tlv_nonconst_value(gpointer tlv_vp, gconstpointer pktend);
guint16 get_generic_tlv_totalsize(gsize datasize);
gboolean is_valid_generic_tlv_packet(gconstpointer tlv_vp, gconstpointer pktend);
gconstpointer get_generic_tlv_first(gconstpointer packet, gconstpointer pktend);
gconstpointer get_generic_tlv_next(gconstpointer tlv_vp, gconstpointer pktend);
gconstpointer find_next_generic_tlv_type(gconstpointer tlv_vp, guint16 tlvtype, gconstpointer pktend);
void set_generic_tlv_type(gpointer tlv_vp, guint16 newtype, gconstpointer pktend);
void set_generic_tlv_len(gpointer tlv_vp, guint16 newsize, gconstpointer pktend);
void set_generic_tlv_value(gpointer tlv_vp, void* srcdata, guint16 srcsize, gconstpointer pktend);
