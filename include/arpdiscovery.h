/**
 * @file
 * @brief Class for discovering address resolution (IP to MAC address information) using the ARP protocol.
 * @details
 *
 * This file is part of the Assimilation Project.
 *
 * @author Carrie Oswald (carrie_oswald@yahoo.com) - Copyright &copy; 2014 - Assimilation Systems Limited
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

#ifndef _ARPDISCOVERY_H
#define _ARPDISCOVERY_H
#include <projectcommon.h>
#include <discovery.h>
#include <pcap_GSource.h>
#include <glib.h>
#include <configcontext.h>
///@{
/// @ingroup ArpDiscovery

typedef struct _ArpDiscovery ArpDiscovery;
/// @ref ArpDiscovery C-class - for discovering IP/MAC address resolution via the ARP protocol captured using <i>libpcap</i>.
struct _ArpDiscovery {
	Discovery	baseclass;			/// Base class object
	GSource*	source;				/// GSource for the pcap data
	void		(*finalize)(AssimObj* self);	/// Saved parent class destructor
	ConfigContext*	ArpMap;				/// Arp IP/MAC addresses hash table
	ConfigContext*	ArpMapData;			/// The actual address portion
        guint           timeout_source;                 ///< timeout source id

};

#define DEFAULT_ARP_SENDINTERVAL 120	// 2 minutes

WINEXPORT ArpDiscovery* arpdiscovery_new(ConfigContext*, gint, GMainContext*,
					       NetGSource*, ConfigContext*, gsize);


///@}

#endif /* _ARPDISCOVERY_H */
