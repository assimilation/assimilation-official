/**
 * @file
 * @brief Class for discovering Link-Level (switch) information (using CDP or LLDP or some future analogous protocol).
 * @details
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

#ifndef _SWITCHDISCOVERY_H
#define _SWITCHDISCOVERY_H
#include <projectcommon.h>
#include <discovery.h>
#include <pcap_GSource.h>
///@{
/// @ingroup SwitchDiscovery

typedef struct _SwitchDiscovery SwitchDiscovery;
/// @ref SwitchDiscovery C-class - for discovering switch and port configuration via LLDP, CDP and similar protocols captured using <i>libpcap</i>.
struct _SwitchDiscovery {
	Discovery	baseclass;			/// Base class object
	GSource*	source;				/// GSource for the pcap data
	void		(*finalize)(AssimObj* self);	/// Saved parent class destructor
	gpointer	switchid;			/// Current switch identification information
	gssize		switchidlen;			/// Length of 'switchid'
	gpointer	portid;				/// Current port id information.
	gssize		portidlen;			/// Length of 'portid'
};

WINEXPORT SwitchDiscovery* switchdiscovery_new(ConfigContext*swconfig, gint priority
,	GMainContext* mcontext, NetGSource*iosrc, ConfigContext* config, gsize objsize);

///@}

#endif /* _SWITCHDISCOVERY_H */
