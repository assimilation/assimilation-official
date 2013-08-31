/**
 * @file
 * @brief Implements the ChildProcess c-class for creating and tracking child processes
 * @details forks off child processes, checking their return code, logging their standard error
 * and timing them to make sure they don't take too long.  If they take too long, they are killed.
 * These child processes are also spawned as independent process groups so that if they fork children
 * that we can easily kill their child processes as well.
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
#include <glib.h>
#ifdef HAVE_UNISTD_H
#	include <unistd.h>
#endif
#include <gmainfd.h>
#include <logsourcefd.h>
#include <childprocess.h>
#include <misc.h>

DEBUGDECLARATIONS

///@defgroup ChildProcess ChildProcess class.
/// Class for creating and monitoring child processes in the gmainloop environment.
/// It logs stderr, and can either save or log stdout - creator's choice.
///@{
///@ingroup C-Classes
///@ingroup AssimObj
FSTATIC void	 _childprocess_setup_child(gpointer childprocess_object);
FSTATIC gboolean _childprocess_timeout(gpointer childprocess_object);
FSTATIC void	 _childprocess_childexit(GPid pid, gint status, gpointer childprocess_object);
FSTATIC void	 _childprocess_finalize(AssimObj* self);
FSTATIC gchar*	 _childprocess_toString(gconstpointer);

#define	CHILDSTATE_RUNNING	0

#ifdef WIN32
#ifndef WEXITSTATUS
	/* The first four definitions below courtesy of ITAGAKI Takahiro
	 *		itagaki(dot)takahiro(at)gmail(dot)com
	 * From the postgresql mailing list: Dec 26, 2006 - 18:31
	 * (FWIW: PostgreSQL is released under the PostgreSQL license
	 *	(similar to the BSD/MIT licenses))
	 */
#	define WEXITSTATUS(w)	((int) ((w) & 0x40000000)) 
#	define WIFEXITED(w)	(((w) & 0x40000000) == 0) 
#	define WIFSIGNALED(w)	(((w) & 0x40000000) != 0) 
#	define WTERMSIG(w)	((w) & 0x3FFFFFFF)
#	define WCOREDUMP(w)	(FALSE)
#include <Windows.h>
#include <WinBase.h>
#endif
#else
#include <sys/wait.h>
#endif

/**
 * @ref ChildProcess constructor.
 * Here's what we're going to do:
 * 1) Create child process using g_spawn_async_with_pipes()
 * 2) ...In child process become our own process group
 * 3) Create LogSourceFd object for stderr
 * 4) Create LogSourceFd or GMainFd object for stdout
 * 5) Set timer (if any)
 * 6) Initialize the child state to running
 * 7) Return.
 */
WINEXPORT ChildProcess*
childprocess_new(gsize cpsize		///< Size of created ChildProcess object
,		char** argv		///< NULL-terminated argv for the ChildProcess
,		const char** envp	///< Environment for the ChildProcess
,		ConfigContext* envmod	///< Modifications to the ChildProcess environment
,		const char* curdir	///< Current directory to start the child in
,		void (*notify)(ChildProcess*, enum HowDied, int rc, int signal, gboolean core_dumped)
					///< Function to call if/when the child terminates
,		gboolean save_stdout	///< TRUE to save stdout, FALSE to log it
,		const char*logdomain	///< Glib log domain
,		const char*logprefix	///< Prefix to prepend to log entries
,		GLogLevelFlags loglevel	///< Glib Log level
,		guint32 timeout_seconds	///< How long to wait before killing it - zero for no timeout
,		gpointer user_data	///< Data our user wants us to keep
,		enum ChildErrLogMode logmode ///< How to log child exits
,		const char* logname)	///< Name to use when logging child exits as requested
{
	AssimObj*	aself;
	ChildProcess*	self;
	gint		stdoutfd;
	gint		stderrfd;
	GError*		failcode = NULL;
	gchar**		childenv = NULL;

	BINDDEBUG(ChildProcess);
	g_return_val_if_fail(logprefix != NULL, NULL);
	if (cpsize < sizeof(ChildProcess)) {
		cpsize = sizeof(ChildProcess);
	}
	aself = assimobj_new(cpsize);
	g_return_val_if_fail(aself != NULL, NULL);
	self = NEWSUBCLASS(ChildProcess, aself);
	aself->_finalize = _childprocess_finalize;
	aself->toString = _childprocess_toString;
	childenv = assim_merge_environ(envp, envmod);
	g_spawn_async_with_pipes(
		curdir,				// Current directory
		argv,				// Arguments
		childenv,			// environment
		G_SPAWN_DO_NOT_REAP_CHILD,	// GSpawnFlags flags,
		_childprocess_setup_child,	// GSpawnChildSetupFunc child_setup,
		self,				// gpointer user_data,
		&self->child_pid,		// GPid *child_pid,
		NULL,				// gint *standard_input,
		&stdoutfd,			// gint *standard_output,
		&stderrfd,			// gint *standard_error,
		&failcode);			// GError **error
	DEBUGMSG2("%s.%d: Spawned process with user_data = %p", __FUNCTION__, __LINE__, self);

	self->stderr_src = logsourcefd_new(0, stderrfd, G_PRIORITY_HIGH, g_main_context_default()
	,		                   logdomain, loglevel, logprefix);
	self->user_data = user_data;
	self->logmode = logmode;
	if (NULL == logname) {
		logname = argv[0];
	}
	self->loggingname = g_strdup(logname);
	assim_free_environ(childenv);
	childenv = NULL;

	if (!save_stdout) {
		LogSourceFd*	logsrc;
		logsrc = logsourcefd_new(0, stdoutfd, G_PRIORITY_HIGH
		,		g_main_context_default(), logdomain, loglevel, logprefix);
		self->stdout_src = &logsrc->baseclass;
	}else{
		self->stdout_src = gmainfd_new(0, stdoutfd, G_PRIORITY_HIGH, g_main_context_default());
	}
	self->childsrc_id = g_child_watch_add(self->child_pid, _childprocess_childexit, self);

	self->notify = notify;

	if (0 == timeout_seconds) {
		DEBUGMSG2("No timeout for process with user_data = %p", self);
		self->timeoutsrc_id = 0;
	}else{
		self->timeoutsrc_id = g_timeout_add_seconds(timeout_seconds
		,			                   _childprocess_timeout, self);
		DEBUGMSG3("%s.%d: Set %d second timeout %d for process with user_data = %p"
		,	__FUNCTION__, __LINE__, timeout_seconds, self->timeoutsrc_id, self);
	}
	self->child_state = CHILDSTATE_RUNNING;
	DEBUGMSG5("%s.%d: REF child: %p", __FUNCTION__,__LINE__, self);
	REF(self);	// We do this because we need to still be here when the process exits
	return self;
}

/// Routine to free/destroy/finalize our ChildProcess objects.
FSTATIC void
_childprocess_finalize(AssimObj* aself)
{
	ChildProcess*	self = CASTTOCLASS(ChildProcess, aself);
	if (self->stdout_src) {
		g_source_destroy(&self->stdout_src->baseclass);
		g_source_unref(&self->stdout_src->baseclass);
		//self->stdout_src->finalize(self->stdout_src);
		self->stdout_src = NULL;
	}
	if (self->stderr_src) {
		g_source_destroy(&self->stderr_src->baseclass.baseclass);
		g_source_unref(&self->stderr_src->baseclass.baseclass);
		//self->stderr_src->baseclass.finalize(&self->stderr_src->baseclass);
		self->stderr_src = NULL;
	}
	if (self->loggingname) {
		g_free(self->loggingname);
		self->loggingname = NULL;
	}
	if (self->timeoutsrc_id > 0)  {
		g_source_remove(self->timeoutsrc_id);
		DEBUGMSG3("%s:%d: Removed timeout for process with user_data = %p"
		,	__FUNCTION__, __LINE__, self);
		self->timeoutsrc_id = 0;
	}
	_assimobj_finalize(aself);
	self = NULL;
	aself = NULL;
}

/// Function to perform setup for child between fork and exec (for UNIX-like systems)
/// It doesn't get called under Windows.
FSTATIC void
_childprocess_setup_child(gpointer childprocess_object)
{
#ifdef WIN32
	(void)childprocess_object;
#else
	ChildProcess*	self = CASTTOCLASS(ChildProcess, childprocess_object);
#	ifdef HAVE_SETPGID
	setpgid(0,0);
#	else
	setpgrp(0, 0);
#	endif
	(void)self;
#endif
}

/// Map of timeout actions and intervals...
static const struct {
	int	signal;
	int	next_timeout;
}signalmap[] = {
	{SIGTERM,	5},	// Give them a chance to clean up
#ifndef WIN32
	{SIGKILL,	10}	// Give them the axe
#endif
	// If it didn't die after this, then we give up
	// - something is seriously hung...
};

/// Function to handle child timeouts.
/// It implements a very simple, linear state machine...
FSTATIC gboolean
_childprocess_timeout(gpointer childprocess_object)
{
	ChildProcess*	self;
	DEBUGMSG("%s:%d Called from timeout for process with user_data = %p"
	,	__FUNCTION__, __LINE__, childprocess_object);
	self = CASTTOCLASS(ChildProcess, childprocess_object);
	if ((unsigned)(self->child_state) < DIMOF(signalmap)) {
#ifdef WIN32
		TerminateProcess(self->child_pid, -1);
#else
		(void)kill(self->child_pid, signalmap[self->child_state].signal);
#endif
		self->timeoutsrc_id = g_timeout_add_seconds
		(	signalmap[self->child_state].next_timeout
		,	_childprocess_timeout, self);
		self->child_state += 1;
	}else{
		_childprocess_childexit(self->child_pid, 0xffffffff, self);
	}
	return FALSE;
}

/// Function called when the child (finally) exits...
FSTATIC void
_childprocess_childexit(GPid pid, gint status, gpointer childprocess_object)
{
	ChildProcess*	self = CASTTOCLASS(ChildProcess, childprocess_object);
	gboolean	signalled = WIFSIGNALED(status);
	int		exitrc = 0;
	int		signal = 0;
	gboolean	logexit = FALSE;
	enum HowDied	howwedied = NOT_EXITED;
	(void)pid;

	if (self->timeoutsrc_id > 0)  {
		g_source_remove(self->timeoutsrc_id);
		DEBUGMSG3("%s.%d: Removed timeout %d for process with user_data = %p"
		,	__FUNCTION__, __LINE__, self->timeoutsrc_id, self);
		self->timeoutsrc_id = 0;
	}
	// If it refused to die, then the status is invalid
	if ((guint)(self->child_state) >= DIMOF(signalmap)) {
		howwedied = EXITED_HUNG;
	}else if ((guint)self->child_state != CHILDSTATE_RUNNING) {
 		// Then we tried to kill it...
		howwedied = EXITED_TIMEOUT;
		signal = signalled ? WTERMSIG(status) : 0;
	}else{
		if (signalled) {
			signal = WTERMSIG(status);
			howwedied = EXITED_SIGNAL;
		}else{
			exitrc = WEXITSTATUS(status);
			howwedied = (exitrc == 0 ? EXITED_ZERO : EXITED_NONZERO);
		}
	}
	switch (howwedied) {
		case EXITED_SIGNAL:	/*FALLTHROUGH*/
		case EXITED_TIMEOUT:	/*FALLTHROUGH*/
		case EXITED_HUNG:
			logexit = self->logmode  > CHILD_NOLOG;
			break;
		case EXITED_NONZERO:
			logexit = self->logmode  >= CHILD_LOGERRS;
			break;
		case EXITED_ZERO:
			logexit = self->logmode  >= CHILD_LOGALL;
			break;
		default:
			// We'll never produce any other values above
			/*NOTREACHED*/
			logexit = TRUE;
			break;
	}
	if (logexit) {
		switch (howwedied) {
		case EXITED_SIGNAL:
			g_warning("Child process [%s] died from signal %d%s."
			,	self->loggingname, signal, WCOREDUMP(status) ? " (core dumped)" : "");
			break;
		case EXITED_TIMEOUT:
			if (signalled) {
				g_warning("Child process [%s] timed out after %d seconds [signal %d%s]."
				,	self->loggingname, self->timeout, signal
				,	WCOREDUMP(status) ? " (core dumped)" : "");
			}else{
				g_warning("Child process [%s] timed out after %d seconds."
				,	self->loggingname, self->timeout);
			}
			break;
		case EXITED_HUNG:
			g_warning("Child process [%s] timed out after %d seconds and could not be killed."
			,	self->loggingname, self->timeout);
			break;
		case EXITED_NONZERO:
			g_message("Child process [%s] exited with return code %d."
			,	self->loggingname, exitrc);
			break;
		case EXITED_ZERO:
			g_message("Child process [%s] exited normally.", self->loggingname);
			break;
		default:/*NOTREACHED*/
			break;
		}
	}

	DEBUGMSG2("%s.%d: Exit happened howwedied:%d", __FUNCTION__, __LINE__
	,	howwedied);
	if (!self->stdout_src->atEOF) {
		//DEBUGMSG3("Child %d [%s] EXITED but output is not at EOF", pid
		//,	self->loggingname);
		self->stdout_src->readmore(self->stdout_src);
	}
	if (!self->stderr_src->baseclass.atEOF) {
		self->stderr_src->baseclass.readmore(&self->stderr_src->baseclass);
	}
	self->notify(self, howwedied, exitrc, signal, WCOREDUMP(status));
	self->child_state = -1;
	DEBUGMSG5("%s.%d: UNREF child: %p", __FUNCTION__,__LINE__, self);
	UNREF(self);	// Undo the REF(self) in our constructor
}

FSTATIC char *
_childprocess_toString(gconstpointer aself)
{
	const ChildProcess*	self = CASTTOCONSTCLASS(ChildProcess, aself);
	ConfigContext*	cfg = configcontext_new(0);
	char*		ret;

	cfg->setint(cfg, "child_pid", self->child_pid);
	cfg->setint(cfg, "timeout", self->timeout);
	cfg->setint(cfg, "timeoutsrc_id", self->timeoutsrc_id);
	cfg->setint(cfg, "childsrc_id", self->timeoutsrc_id);
	cfg->setint(cfg, "child_state", self->child_state);
	cfg->setstring(cfg, "loggingname", self->loggingname);
	ret = cfg->baseclass.toString(&cfg->baseclass);
	UNREF(cfg);
	return ret;
}
///@}
