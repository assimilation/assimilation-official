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
///@ingroup C_Classes
///@ingroup AssimObj

FSTATIC void _resourceocf_finalize(AssimObj* aself);
FSTATIC void _resourceocf_execute(ResourceCmd* self);
FSTATIC void _resourceocf_child_notify(ChildProcess*, enum HowDied, int, int, gboolean);

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
	const char *		operation;
	enum ConfigValType	envtype;

	BINDDEBUG(ResourceCmd);
	restype = request->getstring(request, REQTYPENAMEFIELD);
	if (NULL == restype) {
		g_warning("%s.%d: No "REQTYPENAMEFIELD" field in OCF agent request."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}
	operation = request->getstring(request, REQOPERATIONNAMEFIELD);
	if (NULL == operation) {
		g_warning("%s.%d: No "REQOPERATIONNAMEFIELD" field in OCF agent request."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}
	
	envtype = request->gettype(request, REQENVIRONNAMEFIELD);
	if (envtype != CFG_EEXIST && envtype != CFG_CFGCTX) {
		g_warning("%s.%d: "REQENVIRONNAMEFIELD" field in OCF request is invalid."
		,	__FUNCTION__, __LINE__);
		return NULL;
	}

	ocfpath = g_build_filename(OCF_ROOT, OCF_RES_D, restype, NULL);
	if (	!g_file_test(ocfpath, G_FILE_TEST_IS_REGULAR)
	||	!g_file_test(ocfpath, G_FILE_TEST_IS_EXECUTABLE)) {
		g_warning("%s.%d: No OCF Resource agent [%s]", __FUNCTION__, __LINE__
		,	ocfpath);
		g_free(ocfpath); ocfpath = NULL;
		return NULL;
	}
	
	if (structsize < sizeof(ResourceCmd)) {
		structsize = sizeof(ResourceCmd);
	}
	cself = resourcecmd_constructor(structsize, request, user_data, callback);
	if (!_resourceocf_save_finalize) {
		_resourceocf_save_finalize = cself->baseclass._finalize;
	}
	self = NEWSUBCLASS(ResourceOCF, cself);
	self->ocfpath = ocfpath;
	self->operation = operation;
	self->environ = request->getconfig(request, REQENVIRONNAMEFIELD);
	self->loggingname = g_strdup_printf("%s:%s"
	,	self->baseclass.resourcename, self->operation);
	self->argv[0] = g_strdup(self->ocfpath);
	self->argv[1] = g_strdup(self->operation);
	self->argv[2] = 0;
	self->child = NULL;
	

	return cself;
}

/// Finalize function for ResourceCmd objects
void
_resourceocf_finalize(AssimObj* aself)
{
	ResourceOCF*	self = CASTTOCLASS(ResourceOCF, aself);
	guint		j;

	if (self->ocfpath) {
		g_free(self->ocfpath);
		self->ocfpath = NULL;
	}
	for (j=0; j < DIMOF(self->argv); ++j) {
		if (self->argv[j]) {
			g_free(self->argv[j]);
			self->argv[j] = NULL;
		}
	}
	if (self->loggingname) {
		g_free(self->loggingname);
		self->loggingname = NULL;
	}
	if (self->child) {
		UNREF(self->child);
	}
	_resourceocf_save_finalize(aself);
}
/// Do the deed, dude!
FSTATIC void
_resourceocf_execute(ResourceCmd* cmdself)
{
	ResourceOCF*	self = CASTTOCLASS(ResourceOCF, cmdself);
	self->child = childprocess_new
(	0				///< cpsize
,	self->argv			///< char** argv,
,	NULL				///< const char** envp
,	self->environ			///< ConfigContext* envmod
,	NULL				///< const char* curdir
,	_resourceocf_child_notify 
	///< void (*notify)(ChildProcess*,enum HowDied,int rc,int signal,gboolean core_dumped)
,	FALSE 				///< gboolean save_stdout
,	NULL				///< const char * logdomain
,	NULL				///< const char * logprefix
,	G_LOG_LEVEL_WARNING		///< GLogLevelFlags loglevel
,	self->baseclass.timeout_secs	///< guint32 timeout_seconds,
,	self				///< gpointer user_data
,	CHILD_LOGERRS			///< enum ChildErrLogMode errlogmode
,	self->loggingname		///< const char * loggingname
	);
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

	if (!self->baseclass.callback) {
		return;
	}
	self->baseclass.callback(self->baseclass.request
	,	self->baseclass.user_data
	,	exittype
	,	rc
	,	signal
	,	core_dumped
	,	NULL);
}
///@}
