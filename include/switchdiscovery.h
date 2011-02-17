/**
 * @file
 * @brief Semi-Abstract class (yes, really) defining discovery objects
 * @details It is only instantiated by derived classes.
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
struct _SwitchDiscovery {
	Discovery	baseclass;
	GSource*	source;
	void		(*finalize)(Discovery* self); /// Parent class destructor
	gpointer	switchid;
	gint		switchidlen;
	gpointer	portid;
	gint		portidlen;
};

SwitchDiscovery* switchdiscovery_new(gsize, const char *, guint, gint, GMainContext*);

///@}

#endif /* _SWITCHDISCOVERY_H */
