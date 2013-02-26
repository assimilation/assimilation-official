/**
 * @file 
 * @brief Miscellaneous library functions - doing varied interesting things.
 * These include:
 * - daemonize_me - do the things to make this process into a daemon
 *
 * This file is part of the Assimilation Project.
 *
 * @author Copyright &copy; 2012 - Alan Robertson <alanr@unix.sh>
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

#include <projectcommon.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <misc.h>

void assimilation_logger(const gchar *log_domain, GLogLevelFlags log_level,
			 const gchar *message, gpointer user_data);
const char *	assim_syslogid = "assim"; /// Should be overridden with the name to appear in the logs


/// Make us into a proper daemon.
void
daemonize_me(	gboolean stay_in_foreground,	///<[in] TRUE to not make a background job
		const char* dirtorunin,		///<[in] Directory to cd to or NULL for default (/)
		const char* pidfile)		///<[in] Pathname of pidfile or NULL for no pidfile
{
	struct rlimit		nofile_limits;
	unsigned		j;
	int			nullfd;
	int			nullperms[] = { O_RDONLY, O_WRONLY, O_WRONLY};
	getrlimit(RLIMIT_NOFILE, &nofile_limits);

	// g_warning("%s.%d: pid file is %s", __FUNCTION__, __LINE__, pidfile);
	if (pidfile) {
		if (are_we_already_running(pidfile) == PID_RUNNING) {
			g_message("Already running.");
			exit(0);
		}
	}

	if (!stay_in_foreground) {
		for (j=0; j < DIMOF(nullperms); ++j) {
			close(j);
			nullfd = open("/dev/null", nullperms[j]);
			// Even more paranoia
			if (nullfd != (int)j) {
				if (dup2(nullfd, j) != (int)j) {
					g_error("dup2(%d,%d) failed.  World coming to end.", nullfd, j);
				}
				(void)close(nullfd);
			}
		}
	}
	// A bit paranoid - but not so much as you might think...
	for (j=DIMOF(nullperms); j < nofile_limits.rlim_cur; ++j) {
		close(j);
	}
	// NOTE: probably can't drop a core in '/'
	umask(027);
#ifdef HAS_FORK
	if (!stay_in_foreground) {
		int	childpid;

		(void)setsid();

		childpid = fork();
		if (childpid < 0) {
			g_error("Cannot fork [%s %d]", g_strerror(errno), errno);
			exit(1);
		}
		if (childpid > 0) {
			exit(0);
		}
		// Otherwise, we're the child.
		chdir(dirtorunin ? dirtorunin : "/" );
	}
#else
	(void)stay_in_foreground;
#endif
	if (pidfile) {
		if (are_we_already_running(pidfile) == PID_RUNNING) {
			g_message("%s.%d: Already running.", __FUNCTION__, __LINE__);
			exit(0);
		}
		// Not sure what to do if we can't create the pid file at this point...
		(void)create_pid_file(pidfile);
	}
}

static gboolean	syslog_opened = FALSE;
void
assimilation_openlog(const char* logname)
{
	const int	syslog_options = LOG_PID|LOG_NDELAY;
	const int	syslog_facility = LOG_DAEMON;

	if (!syslog_opened) {
		g_log_set_handler (NULL, G_LOG_LEVEL_MASK | G_LOG_FLAG_FATAL | G_LOG_FLAG_RECURSION
		,	assimilation_logger, NULL);
	}
	assim_syslogid = strrchr(logname, '/');
	if (assim_syslogid && assim_syslogid[1] != '\0') {
		assim_syslogid += 1;
	}else{
		assim_syslogid = logname;
	}
	if (syslog_opened) {
		closelog();
	}
	g_log_set_fatal_mask (NULL, G_LOG_LEVEL_ERROR|G_LOG_LEVEL_CRITICAL);
	openlog(assim_syslogid, syslog_options, syslog_facility);
	syslog_opened = TRUE;
}
void
assimilation_logger(const gchar *log_domain,	///< What domain are we logging to?
		    GLogLevelFlags log_level,	///< What is our log level?
		    const gchar *message,	///< What should we log
		    gpointer ignored)		///< Ignored
{
	int		syslogprio = LOG_INFO;
	const char *	prefix = "INFO:";

	(void)ignored;
	if (!syslog_opened) {
		assimilation_openlog(assim_syslogid);
	}
	if (log_level & G_LOG_LEVEL_DEBUG) {
		syslogprio = LOG_DEBUG;
		prefix = "DEBUG";
	}
	if (log_level & G_LOG_LEVEL_INFO) {
		syslogprio = LOG_INFO;
		prefix = "INFO";
	}
	if (log_level & G_LOG_LEVEL_MESSAGE) {
		syslogprio = LOG_NOTICE;
		prefix = "NOTICE";
	}
	if (log_level & G_LOG_LEVEL_WARNING) {
		syslogprio = LOG_WARNING;
		prefix = "WARN";
	}
	if (log_level & G_LOG_LEVEL_CRITICAL) {
		syslogprio = LOG_ERR;
		prefix = "ERROR";
	}
	if (log_level & G_LOG_LEVEL_ERROR) {
		syslogprio = LOG_EMERG; // Or maybe LOG_CRIT ?
		prefix = "EMERG";
	}
	syslog(syslogprio, "%s:%s %s", prefix
	,	log_domain == NULL ? "" : log_domain
	,	message);
	fprintf(stderr, "%s: %s:%s %s\n", assim_syslogid, prefix
	,	log_domain == NULL ? "" : log_domain
	,	message);
}


#define	MAXPIDLEN	16
#define	MAXPATH		256
#define	PROCSELFEXE	"/proc/self/exe"
#define	PROCOTHEREXE	"/proc/%d/exe"

static gboolean		created_pid_file = FALSE;

/// See if the pid file suggests we are already running or not
PidRunningStat
are_we_already_running(const char * pidfile)	///< The pathname of our expected pid file
{
	char *	pidcontents;				// Contents of the pid file
	int	pid;					// Pid from the pid file
	char	pidexename[sizeof(PROCOTHEREXE)+16];	// Name of /proc entry for 'pid'
	char*	ourexepath;				// Pathname of our executable
	char*	ourexecmd;				// command name of our executable
	char*	pidexepath;				// Pathname of the 'pid' executable
	char*	pidexecmd;				// command name the 'pid' executable

	//g_debug("%s.%d: PID file path [%s]", __FUNCTION__, __LINE__, pidfile);

	// Does the pid file exist?
	if (!g_file_test(pidfile, G_FILE_TEST_IS_REGULAR)) {
		g_debug("%s.%d: PID file [%s] does not exist", __FUNCTION__, __LINE__, pidfile);
		return PID_NOTRUNNING;
	}
	// Can we read it?
	if (!g_file_get_contents(pidfile, &pidcontents, NULL, NULL)) {
		g_debug("%s.%d: PID file [%s] cannot be read", __FUNCTION__, __LINE__, pidfile);
		return PID_NOTRUNNING;
	}
	// We assume it's passably well-formed...
	pid = atoi(pidcontents);
	g_free(pidcontents); pidcontents = NULL;
	// Is it a legitimate pid value?
	if (pid < 2) {
		g_debug("%s.%d: PID file [%s] contains pid %d", __FUNCTION__, __LINE__, pidfile, pid);
		return PID_NOTRUNNING;
	}
	// Is it still running?
	if (kill(pid, 0) < 0 && errno != EPERM) {
		g_debug("%s.%d: PID %d is not running", __FUNCTION__, __LINE__, pid);
		return PID_DEAD;
	}
	// Now let's see if it's "us" - our process
	// That is, is it the same executable as we are?

	// So, what is the pathname of our executable?
	ourexepath = g_file_read_link(PROCSELFEXE, NULL);
	if (NULL == ourexepath) {
		return PID_RUNNING;
	}
	if (strrchr(ourexepath, '/') != NULL) {
		ourexecmd = strrchr(ourexepath, '/')+1;
	}else{
		ourexecmd = ourexepath;
	}
	snprintf(pidexename, sizeof(pidexename), PROCOTHEREXE, pid);

	// What is the pathname of the executable that holds the pid lock?
	pidexepath = g_file_read_link(pidexename, NULL);
	if (pidexepath == NULL) {
		g_free(ourexepath); ourexepath = NULL;
		return PID_RUNNING;
	}
	if (strrchr(pidexepath, '/') != NULL) {
		pidexecmd = strrchr(pidexepath, '/')+1;
	}else{
		pidexecmd = pidexepath;
	}
	// Is it the same executable as we are?
	if (strcmp(ourexecmd, pidexecmd) == 0) {
		g_debug("%s.%d: Link  %s is the same as %s", __FUNCTION__, __LINE__, ourexepath
		,	pidexepath);
		g_free(ourexepath); ourexepath = NULL;
		g_free(pidexepath); pidexepath = NULL;
		return PID_RUNNING;
	}
	g_debug("%s.%d: Link %s is NOT the same as %s", __FUNCTION__, __LINE__, ourexecmd
	,	pidexecmd);
	g_free(ourexepath); ourexepath = NULL;
	g_free(pidexepath); pidexepath = NULL;
	return PID_NOTUS;
}

/// Create a pid file for the current process
gboolean
create_pid_file(const char * pidfile)
{
	char		pidbuf[16];
	GError*		errptr;
	PidRunningStat	pstat;
	

	g_debug("%s.%d: Creating pid file %s for pid %d", __FUNCTION__, __LINE__, pidfile, getpid());
	pstat = are_we_already_running(pidfile);
	if (PID_RUNNING == pstat) {
		return FALSE;
	}
	snprintf(pidbuf, sizeof(pidbuf), "%6d\n", getpid());
	if (pstat == PID_DEAD || pstat == PID_NOTUS) {
		g_debug("%s.%d: Unlinking dead pid file %s", __FUNCTION__, __LINE__, pidfile);
		g_unlink(pidfile);
	}

	if (g_file_set_contents(pidfile, pidbuf, strlen(pidbuf), &errptr)) {
		g_debug("%s.%d: Successfully set file %s to content [%s]"
		,	__FUNCTION__, __LINE__, pidfile, pidbuf);
		//g_chmod(pidfile, 0644);
		created_pid_file = TRUE;
		return TRUE;
	}
	g_warning("%s.%d: Cannot create pid file [%s]. Reason: %s"
	,	__FUNCTION__, __LINE__, pidfile, errptr->message);
	return FALSE;
}

void
remove_pid_file(const char * pidfile)
{
	if (created_pid_file) {
		unlink(pidfile);
	}
}

///< Convert PidRunningStat to an exit code for status
guint
pidrunningstat_to_status(PidRunningStat stat)
{
	// These exit codes from the Linux Standard Base
	//	http://refspecs.linuxbase.org/LSB_3.1.1/LSB-Core-generic/LSB-Core-generic/iniscrptact.html
	switch (stat) {
		case PID_NOTRUNNING:
			return 3;		// LSB: program is not running`

		case PID_DEAD:	/*FALLTHROUGH*/
		case PID_NOTUS:	// This could be an excessively anal retentive check...
			return 1;		// LSB: program is dead and /var/run/pid exists

		case PID_RUNNING:
			return 0;		// LSB: program is running

		default: /*FALLTHROUGH*/
			break;
	}
	return 4;				// LSB: program or service status is unknown
}
