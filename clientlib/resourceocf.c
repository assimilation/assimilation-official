/**
 * @file
 * @brief Implements the ResourceOCF class.
 * @details Constructs an OCF resource agent object (aka ResourceOCF object).
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
#include <projectcommon.h>
#include <string.h>
#define	RESOURCECMD_SUBCLASS
#include <resourcecmd.h>
#include <resourceocf.h>

DEBUGDECLARATIONS

///@defgroup ResourceOCF ResourceOCF class
/// Class implementing resource commands
///@{
///@ingroup ResourceCmd

FSTATIC void _resourceocf_finalize(AssimObj* aself);
FSTATIC void _resourceocf_execute(ResourceCmd* self);
FSTATIC void _resourceocf_child_notify(ChildProcess*, enum HowDied, int, int, gboolean);
FSTATIC gboolean _resourceocf_outputs_string(const char * operation);

FSTATIC void _resourceocf_init_environ(ResourceOCF* self);

static void (*_resourceocf_save_finalize)(AssimObj*) = NULL;

/// Constructor for ResourceOCF class.
/// Its main function is to validate that this type of OCF resource agent exists.
/// It will return NULL if this type of OCF RA doesn't exist.

ResourceCmd*
resourceocf_new(
		guint structsize		///< Structure size (or zero)
,		ConfigContext* request		///< Request to instantiate
,		gpointer user_data		///< User data for 'callback'
,		ResourceCmdCallback callback)	///< Callback when complete
{
	ResourceCmd*		cself;
	ResourceOCF*		self;
	const char *		restype;
	char *			ocfpath;
	const char *		provider;
	enum ConfigValType	envtype;

	BINDDEBUG(ResourceCmd);
	restype = request->getstring(request, CONFIGNAME_TYPE);
	if (NULL == restype) {
		g_warning("%s.%d: No "CONFIGNAME_TYPE" field in OCF agent request."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}
	if (strchr(restype, '/') != NULL) {
		g_warning("%s.%d: "CONFIGNAME_TYPE" field in OCF agent contains a slash."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}
	provider = request->getstring(request, REQPROVIDERNAMEFIELD);
	if (NULL == provider) {
		g_warning("%s.%d: No "REQPROVIDERNAMEFIELD" field in OCF agent request."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}
	if (strchr(provider, '/') != NULL) {
		g_warning("%s.%d: "REQPROVIDERNAMEFIELD" field in OCF agent contains a slash."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}
	
	envtype = request->gettype(request, REQENVIRONNAMEFIELD);
	if (envtype != CFG_EEXIST && envtype != CFG_CFGCTX) {
		g_warning("%s.%d: "REQENVIRONNAMEFIELD" field in OCF request is invalid."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}

	ocfpath = g_build_filename(OCF_ROOT, OCF_RES_D, provider, restype, NULL);
	if (	!g_file_test(ocfpath, G_FILE_TEST_IS_REGULAR)
	||	!g_file_test(ocfpath, G_FILE_TEST_IS_EXECUTABLE)) {
		g_warning("%s.%d: No OCF Resource agent [%s]", __FUNCTION__, __LINE__
		,	ocfpath);
		g_free(ocfpath); ocfpath = NULL;
		return NULL;
	}
	
	if (structsize < sizeof(ResourceOCF)) {
		structsize = sizeof(ResourceOCF);
	}
	cself = resourcecmd_constructor(structsize, request, user_data, callback);
	if (NULL == cself) {
		return NULL;
	}
	if (!_resourceocf_save_finalize) {
		_resourceocf_save_finalize = cself->baseclass._finalize;
	}
	cself->baseclass._finalize = _resourceocf_finalize;
	cself->execute = _resourceocf_execute;
	self = NEWSUBCLASS(ResourceOCF, cself);
	self->ocfpath = ocfpath;
	self->environment = configcontext_new(0);
	self->baseclass.loggingname = g_strdup_printf("%s:%s: "
	,	self->baseclass.resourcename, self->baseclass.operation);
	self->argv[0] = g_strdup(self->ocfpath);
	self->argv[1] = g_strdup(self->baseclass.operation);
	self->argv[2] = 0;
	self->child = NULL;
	_resourceocf_init_environ(self);
	return cself;
}
// Initialize all the OCF environment variables
FSTATIC void
_resourceocf_init_environ(ResourceOCF* self)
{
	ConfigContext*	p = self->baseclass.request->getconfig(self->baseclass.request
	,				REQENVIRONNAMEFIELD);
	GSList*		names;
	GSList*		thisname;
	
	if (NULL == p) {
		g_warning("%s.%d: No proper "REQENVIRONNAMEFIELD" field in request"
		,	__FUNCTION__, __LINE__);
		return;
	}
	// If there are no parameters given, that 'names' *will* be NULL!
	// That's how an empty list comes out in a GSList...
	names = p->keys(p);


	for(thisname = names; NULL != thisname; thisname=thisname->next) {
		char *			mapname;
		const char *		value;
		if (NULL == thisname->data) {
			continue;
		}
		mapname = g_strdup_printf("OCF_RESKEY_%s", (char*)thisname->data);
		value = p->getstring(p, (char*)thisname->data);

		if (NULL == value) {
			// Ignore non-string values
			g_free(mapname); mapname = NULL;
			continue;
		}
		self->environment->setstring(self->environment, mapname, value);
		g_free(mapname); mapname = NULL;
	}
	if (NULL != names) {
		g_slist_free(names);
		names = NULL;
	}

	// Last but not least!
	self->environment->setstring(self->environment, "OCF_ROOT", OCF_ROOT);
	self->environment->setstring(self->environment, "OCF_RESOURCE_INSTANCE"
	,	self->baseclass.resourcename);
	// Unofficial but often needed value
	self->environment->setstring(self->environment, "HA_RSCTMP", HB_RSCTMPDIR);
}

/// Finalize function for ResourceOCF objects
void
_resourceocf_finalize(AssimObj* aself)
{
	ResourceOCF*	self = CASTTOCLASS(ResourceOCF, aself);
	guint		j;

	DEBUGMSG2("Finalizing ResourceOCF @ %p: %s", self, self->baseclass.loggingname);
	if (self->ocfpath) {
		g_free(self->ocfpath);
		self->ocfpath = NULL;
	}
	for (j=0; j < 3; ++j) {
		g_free(self->argv[j]);
		self->argv[j] = NULL;
	}
	if (self->child) {
		DEBUGMSG5("%s.%d: UNREF child: (self=%p %s)", __FUNCTION__,__LINE__
		,	self->child, self->baseclass.loggingname);
		UNREF(self->child);
	}else{
		DEBUGMSG("%s.%d: NO CHILD TO UNREF (self=%p %s)", __FUNCTION__,__LINE__,self
		,	self->baseclass.loggingname);
	}
	if (self->baseclass.loggingname) {
		g_free(self->baseclass.loggingname);
		self->baseclass.loggingname = NULL;
	}
	if (self->environment) {
		UNREF(self->environment);
	}
	_resourceocf_save_finalize(aself);
}

FSTATIC gboolean
_resourceocf_outputs_string(const char * operation)
{
	guint		j;
	const char *	oplist[] = {
		MONITOROP,
		METADATAOP
	};

	for (j=0; j < DIMOF(oplist); ++j) {
		if (strcmp(operation, oplist[j]) == 0) {
			return TRUE;
		}
	}
	return FALSE;
}

/// Do the deed, dude!
FSTATIC void
_resourceocf_execute(ResourceCmd* cmdself)
{
	ResourceOCF*		self = CASTTOCLASS(ResourceOCF, cmdself);
	enum ChildErrLogMode	logmode;
	gboolean		save_stdout;

	DEBUGMSG3("%s.%d Executing(%s:%s)", __FUNCTION__, __LINE__
	,	self->baseclass.resourcename, self->baseclass.operation);
	if (self->baseclass.is_running) {
		g_warning("%s.%d: %s:%s is currently running. New request ignored."
		,	__FUNCTION__, __LINE__
		,	self->baseclass.resourcename, self->baseclass.operation);
		return;
	}
	if (self->child) {
		// Oh... A repeating operation
		UNREF(self->child);
	}
	logmode = (self->baseclass.callback ? CHILD_NOLOG : CHILD_LOGALL);

	save_stdout = _resourceocf_outputs_string(self->baseclass.operation);
	self->baseclass.starttime = g_get_monotonic_time();

	self->child = childprocess_new
	(	0				///< cpsize
	,	self->argv			///< char** argv,
	,	NULL				///< const char** envp
	,	self->environment			///< ConfigContext* envmod
	,	NULL				///< const char* curdir
	,	_resourceocf_child_notify 
	///< void (*notify)(ChildProcess*,enum HowDied,int rc,int signal,gboolean core_dumped)
	,	save_stdout			///< gboolean save_stdout
	,	NULL				///< const char * logdomain
	,	self->baseclass.loggingname	///< const char * logprefix
	,	G_LOG_LEVEL_INFO		///< GLogLevelFlags loglevel
	,	self->baseclass.timeout_secs	///< guint32 timeout_seconds,
	,	self				///< gpointer user_data
	,	logmode				///< enum ChildErrLogMode errlogmode
	,	self->baseclass.loggingname	///< const char * loggingname
	);
	if (self->child) {
		self->baseclass.is_running = TRUE;
		REF2(self);	// We can't go away while we're running no matter what...
				// (this is undone after calling our callback function).
		DEBUGMSG5("%s.%d: REF resourceocf: %p", __FUNCTION__,__LINE__,self);
		DEBUGMSG("%s.%d: spawned child: %p", __FUNCTION__,__LINE__,self->child);
	}else{
		DEBUGMSG("%s.%d FAILED execution(%s:%s)", __FUNCTION__, __LINE__
		,	self->baseclass.resourcename, self->baseclass.operation);
	}
}

/// We get called when our child exits, times out and is killed, or times out and
/// can't be killed
FSTATIC void
_resourceocf_child_notify(ChildProcess* child
,	enum HowDied	exittype
,	int		rc
,	int		signal
,	gboolean	core_dumped)
{
	ResourceOCF*	self = CASTTOCLASS(ResourceOCF, child->user_data);
	char *		outread = NULL;

	self->baseclass.endtime = g_get_monotonic_time();
	if (self->child->stdout_src->textread
	&&	self->child->stdout_src->textread->str) {
		outread = self->child->stdout_src->textread->str;
	}else{
		outread = NULL;
	}

	if (outread && exittype != EXITED_ZERO
	&&	strcmp(self->baseclass.operation, MONITOROP) == 0) {
		g_warning("%s: %s", self->baseclass.loggingname, outread);
	}

	DEBUGMSG2("%s.%d: Exit happened exittype:%d", __FUNCTION__, __LINE__, exittype);
	if (self->baseclass.callback) {
		DEBUGMSG2("%s.%d: Calling callback - exittype:%d", __FUNCTION__,__LINE__,exittype);
		self->baseclass.callback(self->baseclass.request
		,	self->baseclass.user_data
		,	exittype
		,	rc
		,	signal
		,	core_dumped
		,	outread);
	}

	self->baseclass.is_running = FALSE;
	DEBUGMSG5("%s.%d: UNREF resourceocf: %p", __FUNCTION__,__LINE__,self);
	UNREF2(self);  // Undo the ref we did before executing
}
///@}
