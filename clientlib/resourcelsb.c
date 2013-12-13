/**
 * @file
 * @brief Implements the ResourceLSB class.
 * @details Constructs an LSB resource agent object (aka ResourceLSB object).
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
#include <resourcelsb.h>

DEBUGDECLARATIONS

///@defgroup ResourceLSB ResourceLSB class
/// Class implementing resource commands
///@{
///@ingroup ResourceCmd

FSTATIC void _resourcelsb_finalize(AssimObj* aself);
FSTATIC void _resourcelsb_execute(ResourceCmd* self);
FSTATIC void _resourcelsb_metadata(ResourceLSB* self);
FSTATIC void _resourcelsb_validate_all(ResourceLSB* self);
FSTATIC void _resourcelsb_child_notify(ChildProcess*, enum HowDied, int, int, gboolean);


static void (*_resourcelsb_save_finalize)(AssimObj*) = NULL;

/// Constructor for ResourceLSB class.
/// Its main function is to validate that this type of LSB resource agent exists.
/// It will return NULL if this type of LSB RA doesn't exist.

ResourceCmd*
resourcelsb_new(
		guint structsize		///< Structure size (or zero)
,		ConfigContext* request		///< Request to instantiate
,		gpointer user_data		///< User data for 'callback'
,		ResourceCmdCallback callback)	///< Callback when complete
{
	ResourceCmd*		cself;
	ResourceLSB*		self;
	const char *		restype;
	char *			lsbpath;

	BINDDEBUG(ResourceCmd);
	restype = request->getstring(request, REQTYPENAMEFIELD);
	if (NULL == restype) {
		g_warning("%s.%d: No "REQTYPENAMEFIELD" field in LSB agent request."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}
	if (strchr(restype, '/') != NULL) {
		g_warning("%s.%d: "REQTYPENAMEFIELD" field in LSB agent contains a slash."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}
	
	lsbpath = g_build_filename(LSB_ROOT, restype, NULL);
	if (	!g_file_test(lsbpath, G_FILE_TEST_IS_REGULAR)
	||	!g_file_test(lsbpath, G_FILE_TEST_IS_EXECUTABLE)) {
		g_warning("%s.%d: No LSB Resource agent [%s]", __FUNCTION__, __LINE__
		,	lsbpath);
		g_free(lsbpath); lsbpath = NULL;
		return NULL;
	}
	
	if (structsize < sizeof(ResourceLSB)) {
		structsize = sizeof(ResourceLSB);
	}
	cself = resourcecmd_constructor(structsize, request, user_data, callback);
	if (!_resourcelsb_save_finalize) {
		_resourcelsb_save_finalize = cself->baseclass._finalize;
	}
	cself->baseclass._finalize = _resourcelsb_finalize;
	cself->execute = _resourcelsb_execute;
	self = NEWSUBCLASS(ResourceLSB, cself);
	self->lsbpath = lsbpath;
	self->loggingname = g_strdup_printf("%s:%s: "
	,	self->baseclass.resourcename, self->baseclass.operation);
	self->argv[0] = g_strdup(self->lsbpath);
	if (strcmp(self->baseclass.operation, MONITOROP) == 0) {
		self->argv[1] = g_strdup(STATUSOP);
	}else{
		self->argv[1] = g_strdup(self->baseclass.operation);
	}
	self->argv[2] = 0;
	self->child = NULL;
	return cself;
}

/// Finalize function for ResourceLSB objects
void
_resourcelsb_finalize(AssimObj* aself)
{
	ResourceLSB*	self = CASTTOCLASS(ResourceLSB, aself);
	guint		j;

	DEBUGMSG2("Finalizing ResourceLSB @ %p: %s", self, self->loggingname);
	if (self->lsbpath) {
		g_free(self->lsbpath);
		self->lsbpath = NULL;
	}
	for (j=0; j < 3; ++j) {
		g_free(self->argv[j]);
		self->argv[j] = NULL;
	}
	if (self->child) {
		DEBUGMSG5("%s.%d: UNREF child: (self=%p %s)", __FUNCTION__,__LINE__
		,	self->child, self->loggingname);
		UNREF(self->child);
	}else{
		DEBUGMSG5("%s.%d: NO CHILD TO UNREF (self=%p %s)", __FUNCTION__,__LINE__,self
		,	self->loggingname);
	}
	if (self->loggingname) {
		g_free(self->loggingname);
		self->loggingname = NULL;
	}
	_resourcelsb_save_finalize(aself);
}


/// Do the deed, dude!
FSTATIC void
_resourcelsb_execute(ResourceCmd* cmdself)
{
	ResourceLSB*		self = CASTTOCLASS(ResourceLSB, cmdself);
	enum ChildErrLogMode	logmode;

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
	if (strcmp(self->baseclass.operation, METADATAOP) == 0) {
		_resourcelsb_metadata(self);
		return;
	}
	if (strcmp(self->baseclass.operation, VALIDATEOP) == 0) {
		_resourcelsb_validate_all(self);
		return;
	}
	logmode = (self->baseclass.callback ? CHILD_NOLOG : CHILD_LOGALL);

	self->baseclass.starttime = g_get_monotonic_time();
	self->baseclass.is_running = TRUE;
	REF2(self);	// We can't go away while we're running no matter what...
			// (this is undone after calling our callback function).
	DEBUGMSG5("%s.%d: REF resourcelsb: %p", __FUNCTION__,__LINE__,self);

	self->child = childprocess_new
	(	0				///< cpsize
	,	self->argv			///< char** argv,
	,	NULL				///< const char** envp
	,	NULL				///< ConfigContext* envmod
	,	NULL				///< const char* curdir
	,	_resourcelsb_child_notify 
		///< void (*notify)(ChildProcess*,enum HowDied,int rc,int signal,gboolean core_dumped)
	,	FALSE				///< gboolean save_stdout
	,	NULL				///< const char * logdomain
	,	self->loggingname		///< const char * logprefix
	,	G_LOG_LEVEL_INFO		///< GLogLevelFlags loglevel
	,	self->baseclass.timeout_secs	///< guint32 timeout_seconds,
	,	self				///< gpointer user_data
	,	logmode				///< enum ChildErrLogMode errlogmode
	,	self->loggingname		///< const char * loggingname
	);
	DEBUGMSG("%s.%d: spawned child: %p", __FUNCTION__,__LINE__,self->child);
}

/// Return overly-simplified faked-up metadata for an LSB resource
/// @todo We really ought to scan it for comments describing the init script - the LSB requires them,
/// but we should use them if present, and give some dumb default if they're not.
FSTATIC void
_resourcelsb_metadata(ResourceLSB* self)
{
	char *	metadata;
	const char * restype = self->baseclass.request->getstring(self->baseclass.request
	,			REQTYPENAMEFIELD);

	metadata = g_strdup_printf(
	"<?xml version=\"1.0\"?>\n"
	"<!DOCTYPE resource-agent SYSTEM \"ra-api-1.dtd\">\n"
	"<resource-agent name=\"%s\" version=\"1.0\">\n"
  	"  <version>1.0</version>\n"
  	"  <longdesc lang=\"en\">%s LSB init script found at %s</longdesc>\n"
  	"  <shortdesc lang=\"en\">%s</shortdesc>\n"
  	"  <parameters/>\n"
  	"  <actions>\n"
	"\t<action name=\"start\" timeout=\"120\"/>\n"
	"\t<action name=\"stop\" timeout=\"120\"/>\n"
	"\t<action name=\"meta-data\" timeout=\"120\"/>\n"
	"\t<action name=\"restart\" timeout=\"120\"/>\n"
	"\t<action name=\"validate-all\" timeout=\"120\"/>\n"
  	"  </actions>\n"
	"</resource-agent>\n"
	,	restype
	,	restype,	self->lsbpath
	,	restype);

	if (self->baseclass.callback) {
		DEBUGMSG2("%s.%d: Calling callback - exittype: EXITED_ZERO", __FUNCTION__,__LINE__);
		self->baseclass.callback(self->baseclass.request
		,	self->baseclass.user_data
		,	EXITED_ZERO	// exittype
		,	0		// rc
		,	0		// signal
		,	FALSE		// core_dumped
		,	metadata);	// string returned
	}
	g_free(metadata); metadata = NULL;
}

/// Fake validate-all action - just return success...
FSTATIC void
_resourcelsb_validate_all(ResourceLSB* self)
{
	if (self->baseclass.callback) {
		DEBUGMSG2("%s.%d: Calling callback - exittype: EXITED_ZERO", __FUNCTION__,__LINE__);
		self->baseclass.callback(self->baseclass.request
		,	self->baseclass.user_data
		,	EXITED_ZERO	// exittype
		,	0		// rc
		,	0		// signal
		,	FALSE		// core_dumped
		,	NULL);		// string returned
	}
}

//http://refspecs.linuxbase.org/LSB_3.1.1/LSB-Core-generic/LSB-Core-generic/iniscrptact.html
static int	status_rc_map[] = {
	0,	// 0
	7,	// 1	program is dead and /var/run exists	=> program is not running
	7,	// 2	program is dead and /var/lock exists	=> program is not running
	7,	// 3	program not running			=> program is not running
	1,	// 4	status is unknown			=> generic or unspecified error
};

/// We get called when our child exits, times out and is killed, or times out and
/// can't be killed
FSTATIC void
_resourcelsb_child_notify(ChildProcess* child
,	enum HowDied	exittype
,	int		rc
,	int		signal
,	gboolean	core_dumped)
{
	ResourceLSB*	self = CASTTOCLASS(ResourceLSB, child->user_data);
	char *		outread = NULL;

	self->baseclass.endtime = g_get_monotonic_time();
	if (self->child->stdout_src->textread
	&&	self->child->stdout_src->textread->str) {
		outread = self->child->stdout_src->textread->str;
	}else{
		outread = NULL;
	}

	DEBUGMSG2("%s.%d: Exit happened exittype:%d, rc:%d", __FUNCTION__, __LINE__, exittype, rc);
	// status exit codes are weird...
	if (exittype == EXITED_NONZERO && rc < (int)DIMOF(status_rc_map)
	&&		strcmp(self->baseclass.operation, MONITOROP) == 0) {
		rc = status_rc_map[rc];
		DEBUGMSG2("%s.%d: Exit happened exittype:%d, MAPPED rc:%d "
		,	__FUNCTION__, __LINE__, exittype, rc);
	}
		
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
	DEBUGMSG5("%s.%d: UNREF resourcelsb: %p", __FUNCTION__,__LINE__,self);
	UNREF2(self);  // Undo the ref we did before executing
}
///@}
