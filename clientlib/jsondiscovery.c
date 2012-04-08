/**
 * @file
 * @brief Class defining discovery objects that output JSON discovery information to stdout.
 * @details It is possible that code like this will wind up in the LRM.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#include <unistd.h>
#include <memory.h>
#include <projectcommon.h>
#define DISCOVERY_SUBCLASS
#include <frameset.h>
#include <configcontext.h>
#include <cstringframe.h>
#include <frametypes.h>
#include <framesettypes.h>
#include <jsondiscovery.h>
///@defgroup JsonDiscoveryClass Discovery of things through commands producing JSON output to stdout
/// JSONDiscovery class - supporting the discovery of various things through scripts that produce JSON output.
/// @{
/// @ingroup DiscoveryClass

FSTATIC const char *	_jsondiscovery_discoveryname(const Discovery* self);
FSTATIC guint		_jsondiscovery_discoverintervalsecs(const Discovery* self);
FSTATIC void		_jsondiscovery_finalize(AssimObj* self);
FSTATIC gboolean	_jsondiscovery_discover(Discovery* dself);
FSTATIC void		_jsondiscovery_childwatch(GPid, gint, gpointer);
FSTATIC void		_jsondiscovery_send(JsonDiscovery* self, char * jsonout, gsize jsonlen);

/// internal function return the type of Discovery object
FSTATIC const char *
_jsondiscovery_discoveryname(const Discovery* dself)	///<[in] object whose type to return
{
	const JsonDiscovery* self = CASTTOCONSTCLASS(JsonDiscovery, dself);
	return self->pathname;
}

/// default function - return zero for discovery interval
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
	g_free(self->pathname);
	self->pathname = NULL;
	g_warn_if_fail(self->_sourceid == 0);
	_discovery_finalize(dself);
}

FSTATIC gboolean
_jsondiscovery_discover(Discovery* dself)
{
	JsonDiscovery* self = CASTTOCLASS(JsonDiscovery, dself);
	GError*		errs;
	gchar*		argv[4];
	int		j;
	if (self->_sourceid != 0) {
		g_warning("JSON discovery process still running - skipping this iteration.");
		return TRUE;
	}
	self->_tmpfilename = strdup("/var/tmp/discovery-XXXXXXXXXXX.json");
	close(g_mkstemp_full(self->_tmpfilename, 0, 0644));
	argv[0] = strdup("/bin/sh");
	argv[1] = strdup("-c");
	argv[2] = g_strdup_printf("%s > %s", self->pathname, self->_tmpfilename);
	argv[3] = NULL;
	
	if (!g_spawn_async(NULL, argv, NULL, G_SPAWN_DO_NOT_REAP_CHILD
	,		   NULL, NULL, &self->_child_pid, &errs)) {
		g_warning("JSON discovery fork error: %s", errs->message);
	}else{
		self->_sourceid = g_child_watch_add_full(G_PRIORITY_LOW, self->_child_pid, _jsondiscovery_childwatch
		,					 self, NULL);
		// Don't want us going away while we have a child out there...
		self->baseclass.baseclass.ref(self);
	}
	for (j=0; j < 3; ++j) {
		g_free(argv[j]); argv[j] = NULL;
	}
	return TRUE;
}
FSTATIC void
_jsondiscovery_childwatch(GPid pid, gint status, gpointer gself)
{
	JsonDiscovery*	self = CASTTOCLASS(JsonDiscovery, gself);
	gchar*		jsonout = NULL;
	gsize		jsonlen = 0;
	GError*		err;


	if (status != 0) {
		g_warning("JSON discovery from %s failed with status 0x%x (%d)", self->pathname, status, status);
		goto quitchild;
	}
	if (!g_file_get_contents(self->_tmpfilename, &jsonout, &jsonlen, &err)) {
		g_warning("Could not get JSON contents of %s [%s]", self->pathname, err->message);
		goto quitchild;
	}
	if (jsonlen == 0) {
		g_warning("JSON discovery [%s] produced no output.", self->pathname);
		goto quitchild;
	}
	g_message("Got %d bytes of JSON TEXT: [%s]", jsonlen, jsonout);
	
	g_message("Sending %d bytes of JSON text", jsonlen);
	_jsondiscovery_send(self, jsonout, jsonlen);

quitchild:
	///@todo should this be g_source_destroy instead??
	g_spawn_close_pid(pid);
	//g_source_remove(self->_sourceid); ???
	self->_sourceid = 0;
	memset(&(self->_child_pid), 0, sizeof(self->_child_pid));
//	if (jsonout) {
//		g_free(jsonout);
//	}
	if (self->_tmpfilename) {
		g_unlink(self->_tmpfilename);
		g_free(self->_tmpfilename);
		self->_tmpfilename = NULL;
	}
	// We did a 'ref' in _jsondiscovery_discover above to keep us from disappearing while child was running.
	self->baseclass.baseclass.unref(self);
}
FSTATIC void
_jsondiscovery_send(JsonDiscovery* self, char * jsonout, gsize jsonlen)
{
	FrameSet*	fs;
	CstringFrame*	jsf;
	Frame*		fsf;
	ConfigContext*	cfg = self->baseclass._config;
	NetGSource*	io = self->baseclass._iosource;
	NetAddr*	cma;

	g_return_if_fail(cfg != NULL && io != NULL);
	cma = cfg->getaddr(cfg, CONFIGNAME_CMADISCOVER);
	g_return_if_fail(cma != NULL);

	fs = frameset_new(FRAMESETTYPE_JSDISCOVERY);
	jsf = cstringframe_new(FRAMETYPE_JSDISCOVER, 0);
	fsf = CASTTOCLASS(Frame, jsf);	// jsf cast as/to its base class (Frame)
	fsf->setvalue(fsf, jsonout, jsonlen+1, frame_default_valuefinalize); // jsonlen is strlen(jsonout)
	frameset_append_frame(fs, fsf);
	io->sendaframeset(io, cma, fs);
	fsf->baseclass.unref(fsf); fsf = NULL; jsf = NULL;
	fs->unref(fs); fs = NULL;
}

/// JsonDiscovery constructor.
JsonDiscovery*
jsondiscovery_new(const char *	pathname,	///<[in] pathname of program (script) to run
		  gint		intervalsecs,	///<[in] How often to run this discovery
		  NetGSource*	iosource,	///<[in/out] I/O object
		  ConfigContext*context,	///<[in/out] Configuration context
		  gsize		objsize)	///<[in] number of bytes to malloc for the object (or zero)
{
	JsonDiscovery* ret=NEWSUBCLASS(JsonDiscovery
	,		   discovery_new(iosource, context
			    ,		 objsize < sizeof(JsonDiscovery) ? sizeof(JsonDiscovery) : objsize));
	g_return_val_if_fail(ret != NULL, NULL);
	ret->baseclass.discoveryname		= _jsondiscovery_discoveryname;
	ret->baseclass.discoverintervalsecs	= _jsondiscovery_discoverintervalsecs;
	ret->baseclass.baseclass._finalize	= _jsondiscovery_finalize;
	ret->baseclass.discover			= _jsondiscovery_discover;
	ret->pathname = g_strdup(pathname);
	ret->_intervalsecs = intervalsecs;
	discovery_register(CASTTOCLASS(Discovery, ret));
	g_debug("jsondiscovery_new: registered %p", ret);
	return ret;
}
///@}
