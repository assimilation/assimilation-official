/**
 * @file
 * @brief Simple libpcap interface definitions
 * @details Creates a libpcap <b>pcap_t</b> listener for the given set of protocols.
 * This is a <i>much</i> higher level, but much less flexible approach than the native libpcap interface.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 *
 */

#include <pcap.h>


/** @defgroup pcap_protocols Protocols known to (supported by) create_pcap_listener().
 *  These protocols can be ored together to create the complete set of interesting protocols to be
 *  passed as the 'listenmask' argument.
 *  Since they are used to create a bit mask, each "enum" value must be a power of two.
 *  @see create_pcap_listener
 *  @{ 
 *  @ingroup DefineEnums
 */
///	Enable LLDP protocol
#	define	ENABLE_LLDP	0x1
///	Enable CDP protocol
#	define	ENABLE_CDP	0x2 
/// @}

pcap_t* create_pcap_listener(const char * dev, gboolean blocking, unsigned listenmask);
