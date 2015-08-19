/**
 * @file
 * @brief Implements Child Process class
 * @details This class implements child processes with timeouts, logging, and so on.
 *
 * This file is part of the Assimilation Project.
 *
 * @author Alan Robertson <alanr@unix.sh> - Copyright &copy; 2013 - Assimilation Systems Limited
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

#ifndef _CHILDPROCESS_H
#	define _CHILDPROCESS_H
#include <projectcommon.h>
#include <configcontext.h>
#include <assimobj.h>
#include <logsourcefd.h>

///@{
/// @ingroup ChildProcess
typedef struct _ChildProcess ChildProcess;

enum HowDied {
	NOT_EXITED = 0,			///< Still running - should never be returned...
	EXITED_ZERO = 1,		///< Exited with zero return code
	EXITED_NONZERO = 2,		///< Exited with nonzero return code
	EXITED_SIGNAL = 3,		///< Exited with a signal
	EXITED_TIMEOUT = 4,		///< Timed out and was killed
	EXITED_HUNG = 5,		///< Timed out and would not die
	EXITED_INVAL = 6,		///< Was not attempted - invalid request
};

enum ChildErrLogMode {
	CHILD_NOLOG = 0,		///< Don't log anything when it quits
	CHILD_LOGSIGNAL = 1,		///< Log only death by signal or timeout
	CHILD_LOGERRS = 2,		///< Log signal, timeouts, or non-zero exits
	CHILD_LOGALL = 3		///< Log all exits - normal or abnormal
};
	

struct _ChildProcess {
	AssimObj	baseclass;	///< Our base class
	GPid		child_pid;	///< The GPid returned from spawning this object
	GMainFd*	stdout_src;	///< GSource for logging/saving the standard output of child
	LogSourceFd*	stderr_src;	///< GSource for logging the standard error of this child
	guint		timeout;	///< Timeout value for this child
	guint		timeoutsrc_id;	///< GSource id for the timeout for this child to complete
	guint		childsrc_id;	///< GSource id for the child process
	gint		child_state;	///< State for the child process
	char *		loggingname;	///< Name to use when logging process exits
	enum ChildErrLogMode logmode;	///< Which types of exits should we log
	char **		argv;		///< Argument list for this child (malloced)
	char **		envp;		///< Environment list for this child (malloced)
	char *		curdir;		///< Starting directory for this child (malloced)
	void		(*notify)(ChildProcess*, enum HowDied, int rc, int signal, gboolean core_dumped);
					///< Called when it exits
	gpointer	user_data;	///< User data given to us when the object was created.
	
};

WINEXPORT ChildProcess*	childprocess_new(gsize cpsize, char** argv, const char** envp, ConfigContext* envmod
,			const char* curdir
,			void (*notify)(ChildProcess*, enum HowDied, int rc, int signal, gboolean core_dumped)
,			gboolean save_stdout, const char * logdomain, const char * logprefix
,			GLogLevelFlags loglevel, guint32 timeout_seconds, gpointer user_data
,			enum ChildErrLogMode errlogmode, const char * loggingname);

///@}
#endif/*CHILDPROCESS_H*/
