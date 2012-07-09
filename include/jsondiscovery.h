/**
 * @file
 * @brief class defining object discovered by invoking commands that return JSON as their output.
 * @details This implements the code necessary to create a child process to run the command
 * and also return the result.
 *
 * @author &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _JSONDISCOVERY_H
#define _JSONDISCOVERY_H
#include <projectcommon.h>
#include <discovery.h>
///@{
/// @ingroup DiscoveryClass

/// TODO: Total hack - full pathname coded in!
#define JSONAGENTROOT	"/home/alanr/monitor/src/discovery_agents"

typedef struct _JsonDiscovery JsonDiscovery;
/// @ref JsonDiscovery abstract C-class - it supports discovering "things" through running commands outputting JSON
struct _JsonDiscovery {
	Discovery	baseclass;	///< Base discovery object
	char *		instancename;	///< Instance name
	char *		_fullpath;	///< Full pathname of the discovery agent
	char *		_tmpfilename;	///< Pathname of a temporary file name containing JSON output
	GPid		_child_pid;	///< Non-zero if we currently have a child active
	guint		_sourceid;	///< Gmainloop source id of our child watch source.
	guint		_intervalsecs;	///< How often to run this discovery method?
	ConfigContext*	jsonparams;	///< Parameters to the resource agent.
	const char *	(*fullpath)(JsonDiscovery*);///< Return full pathname of agent
};
WINEXPORT JsonDiscovery* jsondiscovery_new(const char * discoverytype,
					   const char * instancename,
					   int intervalsecs,
					   ConfigContext* jsonparams,
					   NetGSource*, ConfigContext*, gsize);
///@}
#endif /* _JSONDISCOVERY_H */
