/**
 * @file
 * @brief class defining object discovered by invoking commands that return JSON as their output.
 * @details This implements the code necessary to create a child process to run the command
 * and also return the result.
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

#ifndef _JSONDISCOVERY_H
#define _JSONDISCOVERY_H
#include <projectcommon.h>
#include <discovery.h>
///@{
/// @ingroup DiscoveryClass

#define JSONAGENTROOT	DISCOVERY_DIR

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
