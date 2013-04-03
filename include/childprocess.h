/**
 * @file
 * @brief Implements Child Process class
 * @details This class implements child processes with timeouts, logging, and so on.
 *
 * This file is part of the Assimilation Project.
 *
 * @author Copyright &copy; 2013 - Alan Robertson <alanr@unix.sh>
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

#ifndef __CHILDPROCESS_H
#	define _CHILDPROCESS_H
#include <projectcommon.h>
#include <assimobj.h>

///@{
/// @ingroup ChildProcess
typedef struct _ChildProcess ChildProcess;
typedef struct _LogSourceFd LogSourceFd;

typedef enum HowDied {
	NOT_EXITED = 0,			///< Still running
	EXITED_ZERO = 1,		///< Exited with zero return code
	EXITED_NONZER0 = 2,		///< Exited with nonzero return code
	EXITED_SIGNAL = 3,		///< Exited with a signal
	EXITED_TIMEOUT = 4,		///< Timed out and was killed
	EXITED_HUNG = 5,		///< Timed out and would not die
};
	

struct _LogSourceFd {
	GSource		baseclass;	///< Our base class - <i>NOT</i> an AssimObj
	int		fd;		///< The open file descriptor we're reading and logging
	char *		log_prefix;	///< The prefix to use in logging this output (our input)
	int		severity;	///< Severity to use in loggin this output (our input)
};


struct _ChildProcess {
	AssimObj	baseclass;	///< Our base class
	GPid		child_pid;	///< The GPid returned from spawning this object
	LogSourceFd*	stdout_src;	///< GSource for logging the standard output of this child
	LogSourceFd*	stderr_src;	///< GSource for logging the standard error of this child
	guint		timeoutsrc_id;	///< GSource id for the timeout for this child to complete
	guint		childsrc_id;	///< GSource id for the child process
	int		child_state;	///< State for the child process
	char **		argv;		///< Argument list for this child (malloced)
	char **		envp;		///< Environment list for this child (malloced)
	char *		curdir;		///< Starting directory for this child (malloced)
	gboolean	(*notify)(ChildProcess*, enum HowDied, int rc, int signal, gboolean core_dumped); ///< Called when it exits
	
};

WINEXPORT ChildProcess*	childprocess_new(gsize cpsize, const char*const* argv, const char*const* envp, const char* curdir
,			gboolean	(*notify)(ChildProcess*, int rc, gboolean core_dumped));

///@}
#endif
