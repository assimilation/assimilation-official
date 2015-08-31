/**
 * @file
 * @brief Implements the resource command abstract class
 * @details Defines the API for operating on resources.
 * It is a factory class which defines these APIs/interfaces, and the parent class of all
 * resource types.
 * It knows which subclass of resource object to create - and fails on invalid subclass types
 *
 * @author  Alan Robertson <alanr@unix.sh> - Copyright &copy; 2013 - Assimilation Systems Limited
 * @n
 *  This file is part of the Assimilation Project.
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

#ifndef _RESOURCECMD_H
#define _RESOURCECMD_H
#include <projectcommon.h>
#include <assimobj.h>
#include <configcontext.h>
#include <childprocess.h>
/**@{
 * @ingroup ResourceCmd
 * It does not implement any queueing, repeating events or such things.
 * It creates an object which will execute the resource action immediately when asked.
 * If this class invoked without any sort of queueing mechanism, or other safeguards
 * it can break the semantics of the underlying resources.
 *
 * Resources are expected to assume that no more than one resource action can be active
 * at a time for any given resource instance.
 *
 */

typedef	void(*ResourceCmdCallback)(ConfigContext* request, gpointer user_data
,			enum HowDied reason, int rc, int signal, gboolean core_dumped
,			const char * stringresult);

typedef struct _ResourceCmd	ResourceCmd;

struct _ResourceCmd{
	AssimObj		baseclass;	///< Base object: implements ref, unref, toString
	gint64			starttime;	///< Time to start it next
						///< (or when it started if it's now running)
	gint64			endtime;	///< Time when it completed
	ConfigContext*		request;	///< The request
	gpointer		user_data;	///< User data for the request
	ResourceCmdCallback	callback;	///< Callback to call when request is complete
	void (*execute)(ResourceCmd* self);	///< Execute this resource command
	const char *		resourcename;	///< Name of this resource
	const char *		operation;	///< Operation being performed
	char*			loggingname;	///< Malloced
	guint32			timeout_secs;	///< Timeout for this operation (secs)
	gboolean		is_running;	///< TRUE if this resource agent is running.
	gboolean		last_success;	///< TRUE if previous operation was successful
};

ResourceCmd* resourcecmd_new(ConfigContext* request, gpointer user_data
,			 ResourceCmdCallback callback);
#define	REQCLASSNAMEFIELD	"class"
#define	REQPROVIDERNAMEFIELD	"provider"
#define	REQOPERATIONNAMEFIELD	"operation"
#define	REQENVIRONNAMEFIELD	"environ"
#define	REQREPEATNAMEFIELD	"repeat"
#define	REQCANCELONFAILFIELD	"cancel_on_fail"
#define	REQIDENTIFIERNAMEFIELD	"reqid"
#define	REQREASONENUMNAMEFIELD	"reason_enum"
#define	REQRCNAMEFIELD		"rc"
#define	REQSIGNALNAMEFIELD	"signal"
#define	REQCOREDUMPNAMEFIELD	"coredumped"
#define	REQSTRINGRETNAMEFIELD	"stringret"
#define	REQARGVNAMEFIELD	"argv"

#define	MONITOROP	"monitor"
#define	METADATAOP	"meta-data"

#ifdef RESOURCECMD_SUBCLASS
WINEXPORT ResourceCmd* resourcecmd_constructor(guint structsize, ConfigContext* request, gpointer user_data
,			 ResourceCmdCallback callback);
WINEXPORT void _resourcecmd_finalize(AssimObj* aself);
#endif
///@}
#endif/*_RESOURCECMD_H*/
