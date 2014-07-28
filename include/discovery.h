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
	void		(*sendjson)(Discovery*, char*, gsize);	///< Send JSON string
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
	guint64		starttime;	///< When this operation was started
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
