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
#include <jsondiscovery.h>
///@defgroup JsonDiscoveryClass Discovery of things through commands producing JSON output to stdout
/// JSONDiscovery class - supporting the discovery of various things through scripts that produce JSON output.
/// @{
/// @ingroup DiscoveryClass

FSTATIC const char *	_jsondiscovery_discoveryname(const Discovery* self);
FSTATIC guint		_jsondiscovery_discoverintervalsecs(const Discovery* self);
FSTATIC void		_jsondiscovery_finalize(Discovery* self);
FSTATIC gboolean	_jsondiscovery_discover(Discovery* dself);
FSTATIC void		_jsondiscovery_childwatch(GPid, gint, gpointer);
FSTATIC void		_jsondiscovery_notify(gpointer gself);

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
_jsondiscovery_finalize(Discovery* dself)	///<[in/out] Object to finalize (free)
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
	argv[0] = strdup("/bin/sh");
	argv[1] = strdup("-c");
	argv[2] = g_strdup_printf("%s > %s", self->pathname, self->_tmpfilename);
	argv[3] = NULL;
	
	if (!g_spawn_async(NULL, argv, NULL, G_SPAWN_DO_NOT_REAP_CHILD
	,				NULL, NULL, &self->_child_pid, &errs)) {
		g_warning("JSON discovery fork error: %s", errs->message);
	}else{
		self->_sourceid = g_child_watch_add_full(G_PRIORITY_LOW, self->_child_pid, _jsondiscovery_childwatch
	,					 self, _jsondiscovery_notify);
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

	(void)pid;

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

quitchild:
	///@todo should this be g_source_destroy instead??
	g_source_remove(self->_sourceid);
	self->_sourceid = 0;
	memset(&(self->_child_pid), 0, sizeof(self->_child_pid));
#if 0
	g_unlink(self->pathname);
#else
	unlink(self->pathname);
#endif
}
FSTATIC void
_jsondiscovery_notify(gpointer gself)
{
	JsonDiscovery* self = CASTTOCLASS(JsonDiscovery, gself);
	g_message("Destroying jsondiscovery object at %p", gself);
	self->baseclass.baseclass.unref(self);
}

/// JsonDiscovery constructor.
JsonDiscovery*
jsondiscovery_new(const char *	pathname,	///<[in] pathname of program (script) to run
		  gint		intervalsecs,	///<[in] How often to run this discovery
		  gsize		objsize)	///<[in] number of bytes to malloc for the object (or zero)
{
	JsonDiscovery* ret =NEWSUBCLASS(JsonDiscovery
	,		    discovery_new(objsize < sizeof(JsonDiscovery) ? sizeof(JsonDiscovery) : objsize));
	g_return_val_if_fail(ret != NULL, NULL);
	ret->baseclass.discoveryname		= _jsondiscovery_discoveryname;
	ret->baseclass.discoverintervalsecs	= _jsondiscovery_discoverintervalsecs;
	ret->baseclass.finalize			= _jsondiscovery_finalize;
	ret->baseclass.discover			= _jsondiscovery_discover;
	ret->pathname = g_strdup(pathname);
	ret->_intervalsecs = intervalsecs;
	return ret;
}
///@}
