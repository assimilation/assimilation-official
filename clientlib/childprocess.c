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
#include <sys/wait.h>
#include <string.h>
#include <glib.h>
#ifdef HAVE_UNISTD_H
#	include <unistd.h>
#endif
#include <gmainfd.h>
#include <logsourcefd.h>
#include <childprocess.h>

FSTATIC void	 _childprocess_setup_child(gpointer childprocess_object);
FSTATIC gboolean _childprocess_timeout(gpointer childprocess_object);
FSTATIC void	 _childprocess_childexit(GPid pid, gint status, gpointer childprocess_object);
FSTATIC void	 _childprocess_childexit(GPid pid, gint status, gpointer childprocess_object);
FSTATIC void	 _childprocess_finalize(AssimObj* self);

#define	CHILDSTATE_RUNNING	0

#ifdef WIN32
#ifndef WEXITSTATUS
#	define WEXITSTATUS(w)  ((int) ((w) & 0x40000000)) 
#	define WIFEXITED(w)    ((w) & 0x40000000) == 0) 
#	define WIFSIGNALED(w)  ((w) & 0x40000000) != 0) 
#	define WTERMSIG(w)     ((w) & 0x3FFFFFFF) 
#endif
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
,		char** envp		///< Environment for the ChildProcess
,		const char* curdir	///< Current directory to start the child in
,		void (*notify)(ChildProcess*, enum HowDied, int rc, int signal, gboolean core_dumped)
					///< Function to call if/when the child terminates
,		gboolean save_stdout	///< TRUE to save stdout, FALSE to log it
,		const char*logdomain	///< Glib log domain
,		const char*logprefix	///< Prefix to prepend to log entries
,		GLogLevelFlags loglevel	///< Glib Log level
,		guint32 timeout_seconds)///< How long to wait before killing it - zero for no timeout
{
	AssimObj*	aself;
	ChildProcess*	self;
	gint		stdoutfd;
	gint		stderrfd;
	GError*		failcode = NULL;

	if (cpsize < sizeof(ChildProcess)) {
		cpsize = sizeof(ChildProcess);
	}
	aself = assimobj_new(cpsize);
	g_return_val_if_fail(aself != NULL, NULL);
	self = NEWSUBCLASS(ChildProcess, aself);
	aself->_finalize = _childprocess_finalize;
	g_spawn_async_with_pipes(
		curdir,				// Current directory
		argv,				// Arguments
		envp,				// environment
		G_SPAWN_DO_NOT_REAP_CHILD,	// GSpawnFlags flags,
		_childprocess_setup_child,	// GSpawnChildSetupFunc child_setup,
		self,				// gpointer user_data,
		&self->child_pid,		// GPid *child_pid,
		NULL,				// gint *standard_input,
		&stdoutfd,			// gint *standard_output,
		&stderrfd,			// gint *standard_error,
		&failcode);			// GError **error

	self->stderr_src = logsourcefd_new(0, stderrfd, G_PRIORITY_HIGH, g_main_context_default()
	,		                   logdomain, loglevel, logprefix);

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
		self->timeoutsrc_id = 0;
	}else{
		self->timeoutsrc_id = g_timeout_add_seconds(timeout_seconds
		,			                   _childprocess_timeout, self);
	}
	self->child_state = CHILDSTATE_RUNNING;
	return self;
}

/// Routine to free/destroy/finalize our ChildProcess objects.
FSTATIC void
_childprocess_finalize(AssimObj* aself)
{
	ChildProcess*	self = CASTTOCLASS(ChildProcess, aself);
	g_source_unref(&self->stdout_src->baseclass);
	self->stdout_src = NULL;
	g_source_unref(&self->stderr_src->baseclass.baseclass);
	self->stderr_src = NULL;
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
	{SIGKILL,	10}	// Give them the axe
	// If it didn't die after this, then we give up
	// - something is seriously hung...
};

/// Function to handle child timeouts.
/// It implements a very simple, linear state machine...
FSTATIC gboolean
_childprocess_timeout(gpointer childprocess_object)
{
	ChildProcess*	self = CASTTOCLASS(ChildProcess, childprocess_object);
	if (self->child_state < DIMOF(signalmap)) {
		(void)kill(-self->child_pid, signalmap[self->child_state].signal);
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
	gboolean	signalled = FALSE;
	int		exitrc = 0;
	int		signal = 0;
	enum HowDied	howwedied = NOT_EXITED;
	(void)pid;

	// If it refused to die, then the status is invalid
	if (self->child_state >= DIMOF(signalmap)) {
		howwedied = EXITED_HUNG;
	}else if (self->child_state != CHILDSTATE_RUNNING) {
 		// Then we tried to kill it...
		howwedied = EXITED_TIMEOUT;
	}else{
		signalled = WIFSIGNALED(status);
		if (signalled) {
			signal = WTERMSIG(status);
			howwedied = EXITED_SIGNAL;
		}else{
			exitrc = WEXITSTATUS(status);
			howwedied = (exitrc == 0 ? EXITED_ZERO : EXITED_NONZERO);
		}
	}
	self->notify(self, howwedied, exitrc, signal, WCOREDUMP(status));
}
