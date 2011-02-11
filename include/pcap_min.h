/**
 * @file
 * @brief Simple pcap interface code header file
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
 *  Since they are used to create a bit mask, each #define must be a power of two.
 *  @see create_pcap_listener
 *  @{ 
 */
///	Enable LLDP protocol
#	define	ENABLE_LLDP	0x1
///	Enable CDP protocol
#	define	ENABLE_CDP	0x2 
/// @}

pcap_t* create_pcap_listener(const char * dev, unsigned listenmask);
