/**
 * @file
 * @brief Class for discovering Link-Level (switch) information (using CDP or LLDP or some future analogous protocol).
 * @details
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version
 * at your option, excluding the provision allowing for relicensing under the GPL at your option.
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
	void		(*finalize)(Discovery* self);	/// Saved parent class destructor
	gpointer	switchid;			/// Current switch identification information
	gssize		switchidlen;			/// Length of 'switchid'
	gpointer	portid;				/// Current port id information.
	gssize		portidlen;			/// Length of 'portid'
};

WINEXPORT SwitchDiscovery* switchdiscovery_new(gsize, const char *, guint, gint, GMainContext*);

///@}

#endif /* _SWITCHDISCOVERY_H */
