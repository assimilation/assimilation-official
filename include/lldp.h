/**
 * @file
 * @brief Provides basic Link Layer Discovery Protocol (LLDP) definitions and accessor functions for LLPD packets.
 * @details Most of these definitions are encodings of the IEEE Standard 802.1AB
 * "Station and Media Access Control Connectivity Discovery" (6 May 2005)
 * @see http://standards.ieee.org/getieee802/download/802.1AB-2009.pdf
 * @see http://en.wikipedia.org/wiki/Link_Layer_Discovery_Protocol
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#ifndef _LLDP_H
#define _LLDP_H
#	include <projectcommon.h>
#	include <sys/types.h>
#	include <glib.h>
/*
 *	LLDP TLV types
 */

#define	LLDP_INVAL		65535

/** @defgroup lldp_type_fields LLDP: Known values for TLV types.
 *  @see get_lldptlv_type
 *  @{ 
 *  @ingroup lldp_format
 */
#define	LLDP_TLV_END		0	///< end of TLV - Length must be zero
#define	LLDP_TLV_CHID		1	///< Chassis ID 
#define	LLDP_TLV_PID		2	///< Port ID
#define	LLDP_TLV_TTL		3	///< Time to Live (seconds)
#define	LLDP_TLV_PORT_DESCR	4	///< Port description
#define	LLDP_TLV_SYS_NAME	5	///< System name
#define	LLDP_TLV_SYS_DESCR	6	///< System description
#define	LLDP_TLV_SYS_CAPS	7	///< System capabilities
#define	LLDP_TLV_MGMT_ADDR	8	///< System capabilities
#define	LLDP_TLV_ORG_SPECIFIC	127	///< So-called organizationally specific TLVs
/// @} 

/** @defgroup lldp_chassis_id_types LLDP: Methods of encoding Chassis ID.
 *  @see type LLDP_TLV_CHID
 *  @{ 
 *  @ingroup lldp_format
 */
#define LLDP_CHIDTYPE_COMPONENT	1	///< entPhysicalAlias when entPhysicalClass
					///< is chassis(3) - RFC 2737
#define LLDP_CHIDTYPE_ALIAS	2	///< ifAlias -  RFC 2863
#define LLDP_CHIDTYPE_PORT	3	///< entPhysicalAlias when entPhysical
					///< Class is port(10) or backplane(4)
#define LLDP_CHIDTYPE_MACADDR	4	///< IEEE Std 802-2001
#define LLDP_CHIDTYPE_NETADDR	5	///< Network address w/family number
#define LLDP_CHIDTYPE_IFNAME	6	///< RFC 2863
#define LLDP_CHIDTYPE_LOCAL	7	///< "local" alphanumeric string
/// @} 

/** @defgroup lldp_port_id_types LLDP: Methods of encoding Port ID.
 *  @see LLDP_TLV_PID
 *  @{ 
 *  @ingroup lldp_format
 */
#define LLDP_PIDTYPE_ALIAS	1	///< ifAlias RFC 2863
#define LLDP_PIDTYPE_COMPONENT	2	///< entPhysicalAlias when entPhysicalClass
					///< is port(10) or backplane(4) - RFC 2737
#define LLDP_PIDTYPE_MACADDR	3	///< IEEE Std 802-2001
#define LLDP_PIDTYPE_NETADDR	4	///< Network address w/family number
#define LLDP_PIDTYPE_IFNAME	5	///< RFC 2863
#define LLDP_PIDTYPE_CIRCUITID	6	///< agent circuit ID RFC 3046
#define LLDP_PIDTYPE_LOCAL	7	///< "local" alphanumeric string
/// @} 

/// @defgroup lldp_sys_caps LLDP: bit mask of switch capabilities.
/// @see LLDP_TLV_SYS_CAPS data
/// @{ 
/// @ingroup lldp_format
#define LLDP_CAPMASK_REPEATER	0x02	///< RFC 2108
#define LLDP_CAPMASK_BRIDGE	0x04	///< RFC 2674
#define LLDP_CAPMASK_WLAN_AP	0x08	///< 802.11 MIB (Access Point)
#define LLDP_CAPMASK_ROUTER	0x10	///< RFC 1812
#define LLDP_CAPMASK_PHONE	0x20	///< RFC 2011
#define LLDP_CAPMASK_DOCSIS	0x40	///< RFC 2669 + 2670
#define LLDP_CAPMASK_STATION	0x80	///< RFC 2011
/// @} 

/// @defgroup lldp_oui_802_1 LLDP: IEEE 802.1 Organizationally specific TLV subtypes.
/// 802.1 Organizationally Specific TLVs -- OUI == 00-80-C2
/// @see LLDP_TLV_ORG_SPECIFIC
/// @{ 
/// @ingroup lldp_format
#define LLDP_ORG802_1_VLAN_PVID		1	///< Section F.2 - Port VLAN ID
#define LLDP_ORG802_1_VLAN_PORTPROTO	2	///< Section F.3 - Port and Protocol VLAN ID
#define LLDP_ORG802_1_VLAN_NAME		3	///< Section F.4 - VLAN Name
#define LLDP_ORG802_1_VLAN_PROTOID	4	///< Section F.5 - Protocol Identity TLV
/// @} 

/// @defgroup lldp_oui_802_3 LLDP: IEEE 802.3 Organizationally specific TLV subtypes.
/// 802.3 Organizationally Specific TLVs -- OUI == 00-12-0F
/// @see LLDP_TLV_ORG_SPECIFIC
/// @{ 
/// @ingroup lldp_format
#define LLDP_ORG802_3_PHY_CONFIG	1	///< Section G.2 - Physical setup
#define LLDP_ORG802_3_POWERVIAMDI	2	///< Section G.3 - PoE status
#define LLDP_ORG802_3_LINKAGG		3	///< Section G.4 - Link Aggregation
#define LLDP_ORG802_3_MTU		4	///< Section G.5 - MTU
/// @} 


WINEXPORT unsigned	get_lldp_chassis_id_type(gconstpointer tlv_vp, gconstpointer tlv_vpend);
WINEXPORT gconstpointer	get_lldp_chassis_id(gconstpointer tlv_vp, gssize* idlength, gconstpointer tlv_vpend);
gconstpointer	get_lldp_port_id(gconstpointer tlv_vp, gssize* idlength, gconstpointer tlv_vpend);
WINEXPORT unsigned	get_lldp_port_id_type(gconstpointer tlv_vp, gconstpointer tlv_vpend);

WINEXPORT guint8		get_lldptlv_type(gconstpointer tlvp_vp, gconstpointer pktend);
WINEXPORT gsize		get_lldptlv_len(gconstpointer tlvp_vp, gconstpointer pktend);
WINEXPORT gconstpointer	get_lldptlv_first(gconstpointer tlv_vp, gconstpointer pktend);
WINEXPORT gconstpointer	get_lldptlv_next(gconstpointer tlv_vp, gconstpointer pktend);
WINEXPORT gconstpointer	get_lldptlv_body(gconstpointer tlv_vp, gconstpointer pktend);
WINEXPORT gconstpointer	find_next_lldptlv_type(gconstpointer tlv_vp, unsigned tlvtype, gconstpointer tlv_vpend);
WINEXPORT gboolean	is_valid_lldp_packet(gconstpointer tlv_vp, gconstpointer tlv_vpend);
WINEXPORT gboolean	enable_lldp_packets(gboolean enableme);
#endif /* _LLDP_H */
