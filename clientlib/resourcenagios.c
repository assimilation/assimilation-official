/**
 * @file
 * @brief Implements the ResourceNAGIOS class.
 * @details Constructs a NAGIOS Plugins resource agent object (aka ResourceNAGIOS object).
 *
 * @author  Carrie Oswald <carrieao@comcast.net> 
 * Copyright &copy; 2015 - Assimilation Systems Limited
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
#include <resourcenagios.h>

DEBUGDECLARATIONS

///@defgroup ResourceNAGIOS ResourceNAGIOS class
/// Class implementing resource commands
///@{
///@ingroup ResourceCmd

FSTATIC void _resourcenagios_finalize(AssimObj* aself);
FSTATIC void _resourcenagios_execute(ResourceCmd* self);
FSTATIC void _resourcenagios_child_notify(ChildProcess*, enum HowDied, int, int, gboolean);

FSTATIC char** _resourcenagios_create_argv(char* argv0, GSList* argv_in);
FSTATIC void _resourcenagios_init_environ(ResourceNAGIOS* self);

static void (*_resourcenagios_save_finalize)(AssimObj*) = NULL;

/// Constructor for ResourceNAGIOS class.
/// Its main function is to validate that this type of NAGIOS resource agent exists.
/// It will return NULL if this type of NAGIOS RA doesn't exist.

ResourceCmd*
resourcenagios_new(
		guint structsize		///< Structure size (or zero)
,		ConfigContext* request		///< Request to instantiate
,		gpointer user_data		///< User data for 'callback'
,		ResourceCmdCallback callback)	///< Callback when complete
{
	ResourceCmd*		cself;
	ResourceNAGIOS*		self;
	const char *		restype;
	char *			nagioscmd = NULL;
	enum ConfigValType	envtype;
	enum ConfigValType	argvtype;
	GSList*			incoming_argv;
	GSList*			nagiospath;

	BINDDEBUG(ResourceCmd);
	restype = request->getstring(request, CONFIGNAME_TYPE);
	if (NULL == restype) {
		g_warning("%s.%d: No "CONFIGNAME_TYPE" field in NAGIOS agent request."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}
	if (strchr(restype, '/') != NULL) {
		g_warning("%s.%d: "CONFIGNAME_TYPE" field in NAGIOS agent contains a slash."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}
	
	envtype = request->gettype(request, REQENVIRONNAMEFIELD);
	if (envtype != CFG_EEXIST && envtype != CFG_CFGCTX) {
		g_warning("%s.%d: "REQENVIRONNAMEFIELD" field in NAGIOS request is invalid."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}

	argvtype = request->gettype(request, REQARGVNAMEFIELD);
	if (argvtype != CFG_EEXIST && argvtype != CFG_ARRAY) {
		g_warning("%s.%d: "REQARGVNAMEFIELD" field in NAGIOS request is invalid (not an array)."
		,       __FUNCTION__, __LINE__);
		return NULL;
	}

	nagiospath = request->getarray(request, REQNAGIOSPATH);
	if (NULL == nagiospath) {
		g_warning("%s.%d: "REQNAGIOSPATH" field in NAGIOS request is missing."
		,       __FUNCTION__, __LINE__);
		return NULL;
	}

	// Search for the the requested agent in the given path (REQNAGIOSPATH)
	for (;nagiospath; nagiospath = g_slist_next(nagiospath)) {
		ConfigValue*	thisval;
		thisval = CASTTOCLASS(ConfigValue, nagiospath->data);
		if (thisval->valtype != CFG_STRING) {
			g_warning("%s.%d: Malformed "REQNAGIOSPATH" in NAGIOS request."
			,       __FUNCTION__, __LINE__);
			return NULL;
		}
		nagioscmd = g_build_filename(thisval->u.strvalue, restype, NULL);
		if (	!g_file_test(nagioscmd, G_FILE_TEST_IS_REGULAR)
		||	!g_file_test(nagioscmd, G_FILE_TEST_IS_EXECUTABLE)) {
			g_free(nagioscmd); nagioscmd = NULL;
		}else{
			break;
		}
	}
	if (NULL == nagioscmd) {
		g_warning("%s.%d: No such NAGIOS agent: %s"
		,       __FUNCTION__, __LINE__, restype);
		return NULL;
	}
	
	incoming_argv = request->getarray(request, REQARGVNAMEFIELD);

	if (structsize < sizeof(ResourceNAGIOS)) {
		structsize = sizeof(ResourceNAGIOS);
	}
	cself = resourcecmd_constructor(structsize, request, user_data, callback);
	if (NULL == cself) {
		return NULL;
	}
	if (!_resourcenagios_save_finalize) {
		_resourcenagios_save_finalize = cself->baseclass._finalize;
	}
	cself->baseclass._finalize = _resourcenagios_finalize;
	cself->execute = _resourcenagios_execute;
	self = NEWSUBCLASS(ResourceNAGIOS, cself);
	self->nagioscmd = nagioscmd;
	self->environment = configcontext_new(0);
	self->baseclass.loggingname = g_strdup_printf("%s:%s: "
	,	self->baseclass.resourcename, self->baseclass.operation);
	self->argv = _resourcenagios_create_argv(self->nagioscmd, incoming_argv);
	_resourcenagios_init_environ(self);
	self->child = NULL;
	return cself;
}

/// Create command line arguments for our child process
FSTATIC char **
_resourcenagios_create_argv(char *        argv0,          ///< The string we want for argv[0] in our result
	GSList*       argv_in)        ///< Linked list of all our other arguments
{
	int     incoming_count = g_slist_length(argv_in);
	int     argc;
	char**  result;

	// Needs to be +2, not +1 as noted above
	result = (char **) malloc((incoming_count+2)*sizeof(char *));

	// Make our return result (argument list)
	result[0] = g_strdup(argv0);
	for (argc=1; argc <= incoming_count && argv_in; ++argc, argv_in = g_slist_next(argv_in)) {
		ConfigValue*    elem = CASTTOCLASS(ConfigValue, argv_in->data);
		char *          nextval;
		switch (elem->valtype) {
			case CFG_STRING:
				nextval = g_strdup(elem->u.strvalue);
				break;
			case CFG_NETADDR: {
				NetAddr*	addr = elem->u.addrvalue;
				nextval = addr->baseclass.toString(&addr->baseclass);
				}
				break;
			default:
				nextval = configcontext_elem_toString(elem);
				break;
		}
		result[argc] = nextval;
	}
	result[argc] = NULL;
	if (DEBUG >= 3) {
		int	j;
		g_warning("%s.%d: Dumping %d Arguments for %s:", __FUNCTION__, __LINE__
			  , argc+1, argv0);
		for (j=0; result[argc]; ++j) {
			g_warning("%s.%d: arg[%d] = %s", __FUNCTION__, __LINE__, j, result[j]);
		}
	}
	return result;
}

// Initialize all the NAGIOS environment variables
FSTATIC void
_resourcenagios_init_environ(ResourceNAGIOS* self)
{
	ConfigContext*	p = self->baseclass.request->getconfig(self->baseclass.request
	,				REQENVIRONNAMEFIELD);
	GSList*		names;
	GSList*		thisname;
	
	names = p ? p->keys(p) : NULL;

	// If there are no parameters given, that 'names' *will* be NULL!
	// That's how an empty list comes out in a GSList...
	for(thisname = names; NULL != thisname; thisname=thisname->next) {
		const char *		mapname;
		const char *		value;
		if (NULL == thisname->data) {
			continue;
		}
		mapname = (const char*)thisname->data;
		value = p->getstring(p, (char*)thisname->data);

		if (NULL == value) {
			// Ignore non-string values
			continue;
		}
		self->environment->setstring(self->environment, mapname, value);
	}
	if (NULL != names) {
		g_slist_free(names);
		names = NULL;
	}

	// Last but not least!
	self->environment->setstring(self->environment, "NAGIOS_RESOURCE_INSTANCE"
	,	self->baseclass.resourcename);
}

/// Finalize function for ResourceNAGIOS objects
void
_resourcenagios_finalize(AssimObj* aself)
{
	ResourceNAGIOS*	self = CASTTOCLASS(ResourceNAGIOS, aself);

	DEBUGMSG2("Finalizing ResourceNAGIOS @ %p: %s", self, self->baseclass.loggingname);
	if (self->nagioscmd) {
		g_free(self->nagioscmd);
		self->nagioscmd = NULL;
	}
	if (self->child) {
		DEBUGMSG5("%s.%d: UNREF child: (self=%p %s)", __FUNCTION__,__LINE__
		,	self->child, self->baseclass.loggingname);
		UNREF(self->child);
	}else{
		DEBUGMSG("%s.%d: NO CHILD TO UNREF (self=%p %s)", __FUNCTION__,__LINE__,self
		,	self->baseclass.loggingname);
	}
	if (self->environment) {
		UNREF(self->environment);
	}
	if (self->argv) {
		char **	thisarg;
		for (thisarg = self->argv; *thisarg; ++thisarg) {
			g_free(*thisarg);
		}
		g_free(self->argv);
		self->argv = NULL;
	}
	_resourcenagios_save_finalize(aself);
}

/// Do the deed, dude!
FSTATIC void
_resourcenagios_execute(ResourceCmd* cmdself)
{
	ResourceNAGIOS*		self = CASTTOCLASS(ResourceNAGIOS, cmdself);
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

	/* save_stdout = _resourcenagios_outputs_string(self->baseclass.operation); */
	save_stdout = TRUE;
	self->baseclass.starttime = g_get_monotonic_time();

	self->child = childprocess_new
	(	0				///< cpsize
	,	self->argv			///< char** argv,
	,	NULL				///< const char** envp
	,	self->environment		///< ConfigContext* envmod
	,	NULL				///< const char* curdir
	,	_resourcenagios_child_notify 
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
		DEBUGMSG5("%s.%d: REF resourcenagios: %p", __FUNCTION__,__LINE__,self);
		DEBUGMSG("%s.%d: spawned child: %p", __FUNCTION__,__LINE__,self->child);
	}else{
		DEBUGMSG("%s.%d FAILED execution(%s:%s)", __FUNCTION__, __LINE__
		,	self->baseclass.resourcename, self->baseclass.operation);
	}
}

/// We get called when our child exits, times out and is killed, or times out and
/// can't be killed
FSTATIC void
_resourcenagios_child_notify(ChildProcess* child
,	enum HowDied	exittype
,	int		rc
,	int		signal
,	gboolean	core_dumped)
{
	ResourceNAGIOS*	self = CASTTOCLASS(ResourceNAGIOS, child->user_data);
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
	/// We may eventually need to map exit codes between the Nagios-API exit codes
	/// and our idea of what exit codes mean.

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
	DEBUGMSG5("%s.%d: UNREF resourcenagios: %p", __FUNCTION__,__LINE__,self);
	UNREF2(self);  // Undo the ref we did before executing
}
/// @}
