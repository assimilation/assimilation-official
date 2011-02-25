/**
 * @file
 * @brief Semi-Abstract class (yes, really) defining discovery objects
 * @details It is only instantiated by derived classes.
 * The basic idea of the Discovery base class is that we will want to discover a number of things locally
 * and the way we can keep track of all the kinds of things we can discover, how often we should
 * poll to re-discover them and so on is through this common base class.
 *
 * We may also eventually add some class-common caching routines as well.
 *
 * Examples of things we probably eventually want to discover are:
 * - Local switch configuration (LLDP/CDP) - implemented by the SwitchDiscovery class.
 * - Local peers through the ARP cache (or whatever is analogous for ipv6)
 * - Local network configuration (via ifconfig/ip et al)
 * - Local network port usage
 * - Local services running
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _DISCOVERY_H
#define _DISCOVERY_H
#include <projectcommon.h>
///@{
/// @ingroup DiscoveryClass

typedef struct _Discovery Discovery;
/// @ref Discovery abstract C-class - it supports discovering "things" through subclasses for different kinds of things.
struct _Discovery {
	const char*	(*discoveryname)	(const Discovery* self);	///< Which discovery object is this?
	gboolean	(*discover)		(Discovery* self);		///< Perform the discovery
	void		(*finalize)		(Discovery* self);		///< called during object destruction
	guint		(*discoverintervalsecs)	(const Discovery* self);	///< How often to re-discover this? (in seconds)
	guint		_timerid;						///< Timer id for repeating discovery
};

Discovery* discovery_new(gsize objsize);
void discovery_register(Discovery* self);

///@}

#endif /* _DISCOVERY_H */
