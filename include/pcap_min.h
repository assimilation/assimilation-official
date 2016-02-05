#ifndef _PCAP_MIN_H
#define _PCAP_MIN_H
/**
 * @file
 * @brief Simple libpcap interface definitions
 * @details Creates a libpcap <b>pcap_t</b> listener for the given set of protocols.
 * This is a <i>much</i> higher level, but much less flexible approach than the native libpcap interface.
 *
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
///	Enable ARP protocol
#	define	ENABLE_ARP	0x4 
/// @}
struct pcap_capture_iter {
	pcap_t*	pcfd;
};

WINEXPORT pcap_t* create_pcap_listener(const char * dev, gboolean blocking, unsigned listenmask, struct bpf_program*);
WINEXPORT void	 	close_pcap_listener(pcap_t*, const char* dev, unsigned listenmask);
WINEXPORT struct 	pcap_capture_iter* pcap_capture_iter_new(const char* capture_filename);
WINEXPORT void	 	pcap_capture_iter_del(struct pcap_capture_iter* iter);
WINEXPORT const guint8*	pcap_capture_iter_next(struct pcap_capture_iter* iter, const guint8** pktend, guint* pktlen);
#endif
