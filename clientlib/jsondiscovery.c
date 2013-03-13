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
FSTATIC void		_jsondiscovery_childwatch(GPid, gint, gpointer);
FSTATIC void		_jsondiscovery_send(JsonDiscovery* self, char * jsonout, gsize jsonlen);
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
	g_free(self->_fullpath);
	self->_fullpath = NULL;
	if (self->_tmpfilename) {
		g_free(self->_tmpfilename);
		self->_tmpfilename = NULL;
	}
	if (self->jsonparams) {
		UNREF(self->jsonparams);
	}
	g_warn_if_fail(self->_sourceid == 0);
	_discovery_finalize(dself);
}

/// Perform the requested discovery action
FSTATIC gboolean
_jsondiscovery_discover(Discovery* dself)
{
	JsonDiscovery* self = CASTTOCLASS(JsonDiscovery, dself);
	GError*		errs;
	gchar*		argv[4];
	gsize		j;
	ConfigContext*	cfg = self->baseclass._config;
	if (self->_sourceid != 0) {
		g_warning("%s: JSON discovery process still running - skipping this iteration."
		,	  __FUNCTION__);
		return TRUE;
	}
	++ self->baseclass.discovercount;
	if (cfg->getaddr(cfg, CONFIGNAME_CMADISCOVER) == NULL) {
		DEBUGMSG2("%s.%d: don't have [%s] address yet - continuing." 
		,	  __FUNCTION__, __LINE__, CONFIGNAME_CMADISCOVER);
	}
	self->_tmpfilename = strdup("/var/tmp/discovery-XXXXXXXXXXX.json");
	close(g_mkstemp_full(self->_tmpfilename, 0, 0644));
	argv[0] = strdup("/bin/sh");
	argv[1] = strdup("-c");
	argv[2] = g_strdup_printf("%s > %s", self->_fullpath, self->_tmpfilename);
	argv[3] = NULL;
	g_return_val_if_fail(self->_fullpath != NULL, FALSE);

	DEBUGMSG1("Running Discovery [%s] [%s] [%s]", argv[0], argv[1], argv[2]);
	
	if (!g_spawn_async(NULL, argv, NULL, G_SPAWN_DO_NOT_REAP_CHILD
	,		   NULL, NULL, &self->_child_pid, &errs)) {
		g_warning("JSON discovery fork error: %s", errs->message);
	}else{
		self->_sourceid = g_child_watch_add_full(G_PRIORITY_HIGH, self->_child_pid, _jsondiscovery_childwatch
		,					 self, NULL);
		// Don't want us going away while we have a child out there...
		REF2(self);
	}
	for (j=0; j < DIMOF(argv) && argv[j]; ++j) {
		g_free(argv[j]); argv[j] = NULL;
	}
	return TRUE;
}
/// Watch our child - we get called when our child process exits
FSTATIC void
_jsondiscovery_childwatch(GPid pid, gint status, gpointer gself)
{
	JsonDiscovery*	self = CASTTOCLASS(JsonDiscovery, gself);
	gchar*		jsonout = NULL;
	gsize		jsonlen = 0;
	GError*		err;


	if (status != 0) {
		g_warning("JSON discovery from %s failed with status 0x%x (%d)", self->_fullpath, status, status);
		goto quitchild;
	}
	if (!g_file_get_contents(self->_tmpfilename, &jsonout, &jsonlen, &err)) {
		g_warning("Could not get JSON contents of %s [%s]", self->_fullpath, err->message);
		goto quitchild;
	}
	if (jsonlen == 0) {
		g_warning("JSON discovery [%s] produced no output.", self->_fullpath);
		goto quitchild;
	}
	//g_debug("Got %d bytes of JSON TEXT: [%s]", jsonlen, jsonout);
	_jsondiscovery_send(self, jsonout, jsonlen);

quitchild:
	g_spawn_close_pid(pid);
	g_source_remove(self->_sourceid);
	self->_sourceid = 0;
	memset(&(self->_child_pid), 0, sizeof(self->_child_pid));
	if (self->_tmpfilename) {
		g_unlink(self->_tmpfilename);
		g_free(self->_tmpfilename);
		self->_tmpfilename = NULL;
	}
	// We did a 'ref' in _jsondiscovery_discover above to keep us from disappearing while child was running.
	UNREF2(self);
}

/// Send what we discovered to the CMA - with some caching going on
FSTATIC void
_jsondiscovery_send(JsonDiscovery* self, char * jsonout, gsize jsonlen)
{
	FrameSet*	fs;
	CstringFrame*	jsf;
	Frame*		fsf;
	ConfigContext*	cfg = self->baseclass._config;
	NetGSource*	io = self->baseclass._iosource;
	NetAddr*	cma;
	const char *	basename = self->baseclass.instancename(&self->baseclass);

	g_return_if_fail(cfg != NULL && io != NULL);

	DEBUGMSG2("%s.%d: discovering %s: _sentyet == %d"
	,	__FUNCTION__, __LINE__, basename, self->baseclass._sentyet);
	// Primitive caching - don't send what we've already sent.
	if (self->baseclass._sentyet) {
		const char *	oldvalue = cfg->getstring(cfg, basename);
		if (oldvalue != NULL && strcmp(jsonout, oldvalue) == 0) {
			DEBUGMSG2("%s.%d: %s sent this value - don't send again."
			,	__FUNCTION__, __LINE__, basename);
			g_free(jsonout);
			return;
		}
		DEBUGMSG2("%s.%d: %s this value is different from previous value"
		,	__FUNCTION__, __LINE__, basename);
	}
	DEBUGMSG2("%s.%d: Sending %"G_GSIZE_FORMAT" bytes of JSON text"
	,	__FUNCTION__, __LINE__, jsonlen);
	cfg->setstring(cfg, basename, jsonout);
	cma = cfg->getaddr(cfg, CONFIGNAME_CMADISCOVER);
	if (cma == NULL) {
	        DEBUGMSG2("%s.%d: %s address is unknown - skipping send"
		,	__FUNCTION__, __LINE__, CONFIGNAME_CMADISCOVER);
		g_free(jsonout);
		return;
	}
	self->baseclass._sentyet = TRUE;

	fs = frameset_new(FRAMESETTYPE_JSDISCOVERY);
	jsf = cstringframe_new(FRAMETYPE_JSDISCOVER, 0);
	fsf = &jsf->baseclass;	// base class object of jsf
	fsf->setvalue(fsf, jsonout, jsonlen+1, frame_default_valuefinalize); // jsonlen is strlen(jsonout)
	frameset_append_frame(fs, fsf);
	DEBUGMSG2("%s.%d: Sending a %"G_GSIZE_FORMAT" bytes JSON frameset"
	,	__FUNCTION__, __LINE__, jsonlen);
	io->_netio->sendareliablefs(io->_netio, cma, DEFAULT_FSP_QID, fs);
	++ self->baseclass.reportcount;
	UNREF(fsf);
	UNREF(fs);
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

	BINDDEBUG(JsonDiscovery);
	g_return_val_if_fail(jsoninst != NULL, NULL);
	g_return_val_if_fail(*discoverytype != '/', NULL);
	jsonparams = jsoninst->getconfig(jsoninst, "parameters");
	g_return_val_if_fail(jsonparams != NULL, NULL);
	ret=NEWSUBCLASS(JsonDiscovery
	,		discovery_new(instancename, iosource, context
			,	      objsize < sizeof(JsonDiscovery) ? sizeof(JsonDiscovery) : objsize));
	g_return_val_if_fail(ret != NULL, NULL);
	ret->baseclass.discoverintervalsecs	= _jsondiscovery_discoverintervalsecs;
	ret->baseclass.baseclass._finalize	= _jsondiscovery_finalize;
	ret->baseclass.discover			= _jsondiscovery_discover;
	ret->jsonparams = jsonparams;
	REF(ret->jsonparams);
	ret->_intervalsecs = intervalsecs;
	basedir = context->getstring(context, "JSONAGENTROOT");
	if (NULL == basedir) {
		basedir = JSONAGENTROOT;
	}
        ret->_fullpath = g_strdup_printf("%s%s%s", basedir, "/", discoverytype);
	DEBUGMSG2("%s.%d: FULLPATH=[%s] discoverytype[%s]"
	,	__FUNCTION__, __LINE__, ret->_fullpath, discoverytype);
	discovery_register(&ret->baseclass);
	return ret;
}
///@}
