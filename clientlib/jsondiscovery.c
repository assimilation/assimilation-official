/**
 * @file
 * @brief Class defining discovery objects that output JSON discovery information to stdout.
 * @details It is possible that code like this will wind up in the LRM.
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

#include <projectcommon.h>
#ifdef	HAVE_UNISTD_H
#	include <unistd.h>
#endif
#include <memory.h>
#define DISCOVERY_SUBCLASS
#include <frameset.h>
#include <configcontext.h>
#include <cstringframe.h>
#include <frametypes.h>
#include <framesettypes.h>
#include <jsondiscovery.h>
#include <assert.h>
#include <fsprotocol.h>
///@defgroup JsonDiscoveryClass JSON discovery class.
/// JSONDiscovery class - supporting the discovery of various things through scripts that
/// produce JSON output to stdout.  Parameters are passed to these scripts through the environment.
/// @{
/// @ingroup DiscoveryClass

FSTATIC guint		_jsondiscovery_discoverintervalsecs(const Discovery* self);
FSTATIC void		_jsondiscovery_finalize(AssimObj* self);
FSTATIC gboolean	_jsondiscovery_discover(Discovery* dself);
FSTATIC void		_jsondiscovery_childwatch(ChildProcess*, enum HowDied, int rc, int signal, gboolean core_dumped);
FSTATIC void		_jsondiscovery_fullpath(JsonDiscovery* self);
DEBUGDECLARATIONS;

/// Return how often we are scheduled to perform this particular discovery action
FSTATIC guint
_jsondiscovery_discoverintervalsecs(const Discovery* dself)	///<[in] Object whose interval to return
{
	const JsonDiscovery* self = CASTTOCONSTCLASS(JsonDiscovery, dself);
	return self->_intervalsecs;
}

/// Finalizing function for Discovery objects
FSTATIC void
_jsondiscovery_finalize(AssimObj* dself)	///<[in/out] Object to finalize (free)
{
	JsonDiscovery* self = CASTTOCLASS(JsonDiscovery, dself);
	if (self->jsonparams) {
		UNREF(self->jsonparams);
	}
	if (self->logprefix) {
		g_free(self->logprefix);
		self->logprefix = NULL;
	}
	if (self->_fullpath) {
		g_free(self->_fullpath);
		self->_fullpath = NULL;
	}
	_discovery_finalize(dself);
}

/// Perform the requested discovery action
FSTATIC gboolean
_jsondiscovery_discover(Discovery* dself)
{
	JsonDiscovery*	self = CASTTOCLASS(JsonDiscovery, dself);
	gchar*		argv[3];
	static char	discoverword [] =  "discover";
	ConfigContext*	cfg = self->baseclass._config;
	if (NULL != self->child) {
		g_warning("%s.%d: JSON discovery process still running - skipping this iteration."
		,	  __FUNCTION__, __LINE__);
		return TRUE;
	}
	++ self->baseclass.discovercount;
	if (cfg->getaddr(cfg, CONFIGNAME_CMADISCOVER) == NULL) {
		DEBUGMSG2("%s.%d: don't have [%s] address yet - continuing." 
		,	  __FUNCTION__, __LINE__, CONFIGNAME_CMADISCOVER);
	}
	argv[0] = self->_fullpath;
	argv[1] = discoverword;
	argv[2] = NULL;

	DEBUGMSG1("Running Discovery [%s]", argv[0]);

	self->child = childprocess_new(0	// object size (0 == default size)
,		argv			// char** argv
,		NULL			// char** envp
,		self->jsonparams	// ConfigContext*envmod
,		NULL			// const char* curdir
,		_jsondiscovery_childwatch
		//gboolean	(*notify)(ChildProcess*, enum HowDied, int rc, int signal, gboolean core_dumped)
,		TRUE			//	gboolean save_stdout
,		G_LOG_DOMAIN		// const char * logdomain
,		self->logprefix		// const char * logprefix
,		G_LOG_LEVEL_MESSAGE	//	GLogLevelFlags loglevel
,		0			//guint32 timeout_seconds;
,		self			// gpointer user_data
,		CHILD_LOGERRS
,		NULL
	);
	if (NULL == self->child) {
		// Can't call childwatch w/o valid child...
		return FALSE;
	}
	
	// Don't want us going away while we have a child out there...
	REF2(self);
	return TRUE;
}
/// Watch our child - we get called when our child process exits
FSTATIC void
_jsondiscovery_childwatch(ChildProcess* child			///< The @ref ChildProcess object for our process
,	enum HowDied			status			///< How did our child exit/die?
,	int				rc			///< exit code (for normal exit)
,	int				signal			///< signal - if it was killed by a signal
,	gboolean			core_dumped)		///< TRUE if our child dropped a core file
{
	JsonDiscovery*	self = CASTTOCLASS(JsonDiscovery, child->user_data);
	gchar*		jsonout = NULL;
	gsize		jsonlen = 0;

	(void)core_dumped;
	(void)rc;
	(void)signal;
	if (status != EXITED_ZERO) {
		// We don't need to log anything...  It's being done for us...
		goto quitchild;
	}
	jsonout = g_strdup(child->stdout_src->textread->str);
	jsonlen = strlen(jsonout);
	if (jsonlen == 0) {
		g_warning("JSON discovery [%s] produced no output.", self->_fullpath);
		goto quitchild;
	}
	DEBUGMSG3("Got %zd bytes of JSON TEXT: [%s]", jsonlen, jsonout);
	if (DEBUG) {
		ConfigContext* jsobj = configcontext_new_JSON_string(jsonout);
		if (jsobj == NULL) {
			g_warning("JSON discovery [%s - %zd bytes] produced bad JSON."
			,	self->_fullpath, jsonlen);
			FREE(jsonout); jsonout = NULL;
			goto quitchild;
		}else{
			// Good output!
			UNREF(jsobj);
		}
	}
	self->baseclass.sendjson(&self->baseclass, jsonout, jsonlen);

quitchild:
	UNREF(self->child);
	child = NULL;
	// We did a 'ref' in _jsondiscovery_discover above to keep us from disappearing while child was running.
	UNREF2(self);
}


/// JsonDiscovery constructor.
JsonDiscovery*
jsondiscovery_new(const char *  discoverytype,	///<[in] type of this JSON discovery object
		  const char *	instancename,	///<[in] instance name of this particular discovery object
		  gint		intervalsecs,	///<[in] How often to run this discovery
		  ConfigContext*jsoninst,	///<[in] JSON data describing this discovery instance
		  NetGSource*	iosource,	///<[in/out] I/O object
		  ConfigContext*context,	///<[in/out] Configuration context
		  gsize		objsize)	///<[in] number of bytes to malloc for the object (or zero)
{
	const char *	basedir = NULL;
	ConfigContext*	jsonparams;
	JsonDiscovery*	ret;
	char *		fullpath;

	BINDDEBUG(JsonDiscovery);
	g_return_val_if_fail(jsoninst != NULL, NULL);
	g_return_val_if_fail(*discoverytype != '/', NULL);
	jsonparams = jsoninst->getconfig(jsoninst, "parameters");
	g_return_val_if_fail(jsonparams != NULL, NULL);
	basedir = context->getstring(context, "JSONAGENTROOT");
	if (NULL == basedir) {
		basedir = JSONAGENTROOT;
	}
	fullpath = g_build_filename(basedir, discoverytype, NULL);
	if (	!g_file_test(fullpath, G_FILE_TEST_IS_REGULAR)
	||	!g_file_test(fullpath, G_FILE_TEST_IS_EXECUTABLE)) {
		g_warning("%s.%d: No such JSON discovery agent [%s]", __FUNCTION__, __LINE__
		,	fullpath);
		g_free(fullpath); fullpath = NULL;
		return NULL;
	}
	ret=NEWSUBCLASS(JsonDiscovery
	,		discovery_new(instancename, iosource, context
			,	      objsize < sizeof(JsonDiscovery) ? sizeof(JsonDiscovery) : objsize));
	g_return_val_if_fail(ret != NULL, NULL);
	ret->_fullpath = fullpath;
	ret->baseclass.discoverintervalsecs	= _jsondiscovery_discoverintervalsecs;
	ret->baseclass.baseclass._finalize	= _jsondiscovery_finalize;
	ret->baseclass.discover			= _jsondiscovery_discover;
	ret->jsonparams = jsonparams;
	REF(ret->jsonparams);
	ret->_intervalsecs = intervalsecs;
	ret->logprefix = g_strdup_printf("Discovery %s: ", instancename);
	DEBUGMSG2("%s.%d: FULLPATH=[%s] discoverytype[%s]"
	,	__FUNCTION__, __LINE__, ret->_fullpath, discoverytype);
	discovery_register(&ret->baseclass);
	return ret;
}
///@}
