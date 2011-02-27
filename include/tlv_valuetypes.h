/**
 * @file
 * @brief Defines a set of value types - used for semi-intelligent dumping of TLV data.
 * @details It defines a set of <i>data</i> types. Each <i>TLV</i> type is an object of a certain data type.
 * We define those common sets of data types here.
 * BUT THIS HEADER DOESN'T SEEM TO BE USED! - and I think the concept has changed since I wrote it. (?)
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
/**
 * @defgroup TLV_common_data_types Data Types corresponding our various TLV types
 * Each of the types below has a method associated with it which knows how to convert it to a string.
 * I think this header isn't used for anything.  IGNOREME?
 *  @{ 
 *  @ingroup DefineEnums
 */
#define	TLV_DTYPE_BINARY		1	///< Just raw binary - no special meaning
#define	TLV_DTYPE_UINT8			2	///< 8-bit unsigned integer
#define	TLV_DTYPE_UINT16		3	///< 16-bit unsigned integer - network byte order
#define	TLV_DTYPE_UINT32		4	///< 32-bit unsigned integer - network byte order
#define	TLV_DTYPE_UINT32		5	///< 64-bit unsigned integer - network byte order
#define	TLV_DTYPE_OUI			6	///< IEEE 3-byte Organizationally Unique Identifier
#define	TLV_DTYPE_MACADDR		7	///< Variable-length MAC address
#define	TLV_DTYPE_IPV4ADDR		8	///< IPV4 address
#define	TLV_DTYPE_IPV6ADDR		9	///< IPV6 address
#define	TLV_DTYPE_GENADDR		10	///< Network address prefixed with address type
#define	TLV_DTYPE_LLCHASSIS		11	///< LLDP Chassis ID
#define	TLV_DTYPE_LLPORTID		12	///< LLDP Port ID
#define	TLV_DTYPE_LLCAPS		13	///< LLDP Capabilities
#define	TLV_DTYPE_LLMGMTADDR		14	///< LLDP Management address
#define	TLV_DTYPE_LL8021_VLANID		15	///< LLDP 802.1 Port VLAN ID
#define	TLV_DTYPE_LL8021_PPVLANID	16	///< LLDP 802.1 Port and Protocol VLAN ID
#define	TLV_DTYPE_LL8021_VLANNAME	17	///< LLDP 802.1 VLAN Name
#define	TLV_DTYPE_LL8021_PROTOID	18	///< LLDP 802.1 Protocol Identity
#define	TLV_DTYPE_LL8023_MACPHY		19	///< LLDP 802.3 MAC/PHY Config/Status
#define	TLV_DTYPE_LL8023_POWER		20	///< LLDP 802.3 MAC/PHY Config/Status
#define	TLV_DTYPE_LL8023_LINKAGGR	21	///< LLDP 802.3 Link Aggregation
#define	TLV_DTYPE_LL8023_MTU		22	///< LLDP 802.3 Maximum Frame Size
#define	TLV_DTYPE_FSTYPE		23	///< Our Frameset types
#define	TLV_DTYPE_FSFLAGS		24	///< Our Frameset flags
#define	TLV_DTYPE_FRAMETYPE		25	///< Our Frame types
#define	TLV_DTYPE_FR_REQTYPE		26	///< Our Frame request type
/// @}
