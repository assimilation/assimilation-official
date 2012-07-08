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
#include <assimobj.h>
#include <netgsource.h>
#include <configcontext.h>
///@{
/// @ingroup DiscoveryClass

typedef struct _Discovery Discovery;
/// @ref DiscoveryClass abstract C-class - it supports discovering "things" through subclasses for different kinds of things.
struct _Discovery {
	AssimObj	baseclass;				///< Base object class
	char*		(*instancename)(const Discovery* self);	///< Which object is this?
	void		(*flushcache)(Discovery* self);		///< Flush any cache held
	gboolean	(*discover)(Discovery* self);		///< Perform the discovery
	guint		(*discoverintervalsecs)	(const Discovery* self);	///< How often to re-discover?
										///< (in seconds)
	guint64		reportcount;	///< How many times have we reported
										///< anything new upstream.
	guint64		discovercount;	///< How many times have we discovered
					///< something.
	char*		_instancename;	///< Timer id for repeating discovery
	guint		_timerid;	///< Timer id for repeating discovery
	NetGSource*	_iosource;	///< How to send packets
	ConfigContext*	_config;	///< Configuration Parameters -
					///< has address of CMA.
	gboolean	_sentyet;	///< TRUE if we've sent this yet.
};

WINEXPORT Discovery* discovery_new(const char *,NetGSource*, ConfigContext*, gsize objsize);
WINEXPORT void discovery_register(Discovery* self);
WINEXPORT void discovery_unregister_all(void);
WINEXPORT void discovery_unregister(const char *);
#ifdef DISCOVERY_SUBCLASS
WINEXPORT void		_discovery_finalize(AssimObj* self);
#endif


///@}

#endif /* _DISCOVERY_H */
