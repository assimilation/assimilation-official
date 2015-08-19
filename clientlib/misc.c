/**
 * @file 
 * @brief Miscellaneous library functions - doing varied interesting things.
 * These include:
 * - daemonize_me - do the things to make this process into a daemon
 * - setpipebuf - set the buffer size of a pipe
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

#define _GNU_SOURCE /* Needed for the F_[SG]ETPIPE_SZ definitions */
#include <projectcommon.h>
#include <stdlib.h>
#ifdef HAVE_UNISTD_H
#	include <unistd.h>
#endif
#ifdef HAVE_SYS_UTSNAME_H
#	include <sys/utsname.h>
#endif
#include <errno.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#ifdef HAVE_FCNTL_H
#	include <fcntl.h>
#endif
#ifndef WIN32
#include <sys/time.h>
#include <sys/resource.h>
#endif
#include <signal.h>
#include <misc.h>

void assimilation_logger(const gchar *log_domain, GLogLevelFlags log_level,
			 const gchar *message, gpointer user_data);
const char *	assim_syslogid = "assim"; /// Should be overridden with the name to appear in the logs
FSTATIC void catch_pid_signal(int signum);
FSTATIC char *	_shell_array_value(GSList* arrayvalue);
FSTATIC gboolean _assim_proxy_io_watch(GIOChannel*, GIOCondition, gpointer);

/// Function to get system name (uname -n in UNIX terms)
#ifdef HAVE_UNAME
char *
proj_get_sysname(void)
{
	struct utsname	un;	// System name, etc.
	uname(&un);
	return g_strdup(un.nodename);
}
#else
#	ifdef HAVE_GETCOMPUTERNAME
char *
proj_get_sysname(void)
{
//	BOOL WINAPI GetComputerName(_Out_ LPTSTR lpBuffer, _Inout_  LPDWORD lpnSize);

	char sn[MAX_COMPUTERNAME_LENGTH + 1];
	DWORD snsize = sizeof(sn);
	BOOL ret;

	ret = GetComputerName((LPSTR) sn, &snsize);
	if(ret) {
		return g_strdup(sn);
	}

	return g_strdup("GetComputerName failed");
}
#	else
#	error "Need some function to get our computer name!"
#	endif
#endif

#ifndef WIN32
/// Make us into a proper daemon.
void
daemonize_me(	gboolean stay_in_foreground,	///<[in] TRUE to not make a background job
		const char* dirtorunin,		///<[in] Directory to cd to or NULL for default (/)
		char* pidfile,			///<[in] Pathname of pidfile or NULL for no pidfile
		int minclosefd)			///<[in] Minimum file descriptor to close or 0
{
	struct rlimit		nofile_limits;
	int			nullperms[] = { O_RDONLY, O_WRONLY, O_WRONLY};
	unsigned		j;
	getrlimit(RLIMIT_NOFILE, &nofile_limits);

	// g_warning("%s.%d: pid file is %s", __FUNCTION__, __LINE__, pidfile);
	if (pidfile) {
		if (are_we_already_running(pidfile, NULL) == PID_RUNNING) {
			g_message("Already running.");
			exit(0);
		}
	}

#ifdef HAS_FORK
	if (!stay_in_foreground) {
		int	k;
		int	childpid;

		(void)setsid();

		
		for (k=0; k < 2; ++k) {
			childpid = fork();
			if (childpid < 0) {
				g_error("Cannot fork [%s %d]", g_strerror(errno), errno);
				exit(1);
			}
			if (childpid > 0) {
				exit(0);
			}
			// Otherwise, we're the child.
			// NOTE: probably can't drop a core in '/'
		}
	}
#endif
	if (chdir(dirtorunin ? dirtorunin : "/" )) {
		g_warning("%s.%d: Cannot change directory to [%s]", __FUNCTION__
		,	__LINE__, dirtorunin);
	}
	umask(027);
	// Need to do this after forking and before closing our file descriptors
	if (pidfile) {
		if (are_we_already_running(pidfile, NULL) == PID_RUNNING) {
			g_message("%s.%d: Already running.", __FUNCTION__, __LINE__);
			exit(0);
		}
		// Exit if we can't create the requested pidfile
		if (!create_pid_file(pidfile)) {
			exit(1);
		}
	}
	// Now make sure we don't have any funky file descriptors hanging around here...
	if (!stay_in_foreground) {
		int			nullfd;
		for (j=0; j < DIMOF(nullperms); ++j) {
			close(j);
			nullfd = open("/dev/null", nullperms[j]);

			if (nullfd < 0) {
				g_error("%s.%d: Cannot open /dev/null(!)", __FUNCTION__, __LINE__);
				exit(1);
			}

			// Even more paranoia
			if (nullfd != (int)j) {
				if (dup2(nullfd, j) != (int)j) {
					g_error("dup2(%d,%d) failed.  World coming to end.", nullfd, j);
				}
				(void)close(nullfd);
			}
		}
	}
	if (minclosefd < (int)DIMOF(nullperms)) {
		minclosefd = DIMOF(nullperms);
	}
	// A bit paranoid - but not so much as you might think...
	for (j=minclosefd; j < nofile_limits.rlim_cur; ++j) {
		close(j);
	}
}
#else
void
daemonize_me(	gboolean stay_in_foreground,	///<[in] TRUE to not make a background job
		const char* dirtorunin,		///<[in] Directory to cd to or NULL for default (/)
		const char* pidfile)		///<[in] Pathname of pidfile or NULL for no pidfile
{
	if (pidfile) {
		if (are_we_already_running(pidfile, NULL) == PID_RUNNING) {
			g_message("Already running.");
			exit(0);
		}
	}
			// Exit if we can't create the requested pidfile
	if (!create_pid_file(pidfile)) {
		exit(1);
	}
}
#endif

static gboolean	syslog_opened = FALSE;
void
assimilation_openlog(const char* logname)
{
#ifndef WIN32
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
	g_log_set_fatal_mask (NULL, G_LOG_LEVEL_ERROR);
	openlog(assim_syslogid, syslog_options, syslog_facility);
	syslog_opened = TRUE;
#endif
}
void
assimilation_logger(const gchar *log_domain,	///< What domain are we logging to?
		    GLogLevelFlags log_level,	///< What is our log level?
		    const gchar *message,	///< What should we log
		    gpointer ignored)		///< Ignored
{
#ifdef WIN32
#define LOG_INFO 6
#define LOG_DEBUG 7
#define LOG_NOTICE 5
#define LOG_WARNING 4
#define LOG_ERR 3
#define LOG_CRIT 2
#define LOG_ALERT 1
#define LOG_EMERG 0
#endif
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
#ifndef WIN32
	syslog(syslogprio, "%s:%s %s", prefix
	,	log_domain == NULL ? "" : log_domain
	,	message);
#else
	{
		char msg[256];
		g_snprintf(msg, sizeof(msg), "%s: %s:%s %s\n",assim_syslogid, prefix
			,	log_domain == NULL ? "" : log_domain
			,	message);
		OutputDebugString((LPCSTR) msg);
	}
#endif
	fprintf(stderr, "%s: %s:%s %s\n", assim_syslogid, prefix
	,	log_domain == NULL ? "" : log_domain
	,	message);
}

#ifdef WIN32
#define SEP '\\'
//@todo: these will be replaced when windows functionality cathes up
#define	PROCSELFEXE	"/"
#define	PROCOTHEREXE	"/"
#else
#define SEP '/'
#define	PROCSELFEXE	"/proc/self/exe"
#define	PROCOTHEREXE	"/proc/%d/exe"
#endif
#define	MAXPIDLEN	16
#define	MAXPATH		256

static gboolean		created_pid_file = FALSE;

/// See if the pid file suggests we are already running or not
PidRunningStat
are_we_already_running( const char * pidfile	///< The pathname of our expected pid file
,			int* pidarg)		///< Pid of the process (if running)
{
	char *	pidcontents;				// Contents of the pid file
	int	pid;					// Pid from the pid file
	char*	ourexepath;				// Pathname of our executable
	char*	ourexecmd;				// command name of our executable
	char*	pidexepath;				// Pathname of the 'pid' executable
	char*	pidexecmd;				// command name the 'pid' executable
#ifdef WIN32
	char    w_ourexepath[MAXPATH];
	int     nSize = MAXPATH-1, ret;
#endif
	char	pidexename[sizeof(PROCOTHEREXE)+16];	// Name of /proc entry for 'pid'

	//g_debug("%s.%d: PID file path [%s]", __FUNCTION__, __LINE__, pidfile);
	if (pidarg) {
		*pidarg = 0;
	}

	// Does the pid file exist?
	if (!g_file_test(pidfile, G_FILE_TEST_IS_REGULAR)) {
		//g_debug("%s.%d: PID file [%s] does not exist", __FUNCTION__, __LINE__, pidfile);
		return PID_NOTRUNNING;
	}
	// Can we read it?
	if (!g_file_get_contents(pidfile, &pidcontents, NULL, NULL)) {
		//g_debug("%s.%d: PID file [%s] cannot be read", __FUNCTION__, __LINE__, pidfile);
		return PID_NOTRUNNING;
	}
	// We assume it's passably well-formed...
	pid = atoi(pidcontents);
	g_free(pidcontents); pidcontents = NULL;
	// Is it a legitimate pid value?
	if (pid < 2) {
		//g_debug("%s.%d: PID file [%s] contains pid %d", __FUNCTION__, __LINE__, pidfile, pid);
		return PID_NOTRUNNING;
	}
	if (pidarg) {
		*pidarg = pid;
	}
	// Is it still running?
#ifdef WIN32
	if(TerminateProcess((void *)pid, 0) == 0) 
#else
	if (kill(pid, 0) < 0 && errno != EPERM)
#endif
	{
		//g_debug("%s.%d: PID %d is not running", __FUNCTION__, __LINE__, pid);
		return PID_DEAD;
	}
	// Now let's see if it's "us" - our process
	// That is, is it the same executable as we are?

	// So, what is the pathname of our executable?
#ifndef WIN32
	ourexepath = g_file_read_link(PROCSELFEXE, NULL);
#else
	ret = GetModuleFileName(NULL, w_ourexepath, nSize);
	if(ret == 0) {
		//g_debug("%s.%d: GetModuleFileName failed %d", __FUNCTION__, __LINE__, GetLastError());
		return(PID_DEAD);
	}
	ourexepath = g_strdup(w_ourexepath);
#endif
	if (NULL == ourexepath) {
		return PID_RUNNING;
	}
	if (strrchr(ourexepath, SEP) != NULL) {
		ourexecmd = strrchr(ourexepath, SEP)+1;
	}else{
		ourexecmd = ourexepath;
	}
	g_snprintf(pidexename, sizeof(pidexename), PROCOTHEREXE, pid);

	// What is the pathname of the executable that holds the pid lock?
	pidexepath = g_file_read_link(pidexename, NULL);
	if (pidexepath == NULL) {
		g_free(ourexepath); ourexepath = NULL;
		return (errno != EPERM ? PID_NOTUS : PID_RUNNING);
	}
	if (strrchr(pidexepath, SEP) != NULL) {
		pidexecmd = strrchr(pidexepath, SEP)+1;
	}else{
		pidexecmd = pidexepath;
	}
	// Is it the same executable as we are?
	if (strcmp(ourexecmd, pidexecmd) == 0) {
		//g_debug("%s.%d: Link  %s is the same as %s", __FUNCTION__, __LINE__, ourexepath
		//,	pidexepath);
		g_free(ourexepath); ourexepath = NULL;
		g_free(pidexepath); pidexepath = NULL;
		return PID_RUNNING;
	}
	//g_debug("%s.%d: Link %s is NOT the same as %s", __FUNCTION__, __LINE__, ourexecmd
	//,	pidexecmd);
	g_free(ourexepath); ourexepath = NULL;
	g_free(pidexepath); pidexepath = NULL;
	return PID_NOTUS;
}

/// Create a pid file for the current process
gboolean
create_pid_file(const char * pidfile)
{
	char		pidbuf[16];
	GError*		errptr = NULL;
	PidRunningStat	pstat;
	
#if _MSC_VER
WINIMPORT
__out
void *
__stdcall
GetCurrentProcess();
#define GETPID GetCurrentProcessId()
#else
#define GETPID getpid()
#endif
	//g_debug("%s.%d: Creating pid file %s for pid %d", __FUNCTION__, __LINE__, pidfile, GETPID);
	pstat = are_we_already_running(pidfile, NULL);
	if (PID_RUNNING == pstat) {
		return FALSE;
	}
	g_snprintf(pidbuf, sizeof(pidbuf), "%6d\n", GETPID);
	if (pstat == PID_DEAD || pstat == PID_NOTUS) {
		//g_debug("%s.%d: Unlinking dead pid file %s", __FUNCTION__, __LINE__, pidfile);
		g_unlink(pidfile);
	}

	if (g_file_set_contents(pidfile, pidbuf, strlen(pidbuf), &errptr)) {
		//g_debug("%s.%d: Successfully set file %s to content [%s]"
		//,	__FUNCTION__, __LINE__, pidfile, pidbuf);
#ifndef WIN32
		if (chmod(pidfile, 0644) < 0) {
			g_warning("%s.%d: Could not chmod pid file %s to 0644", __FUNCTION__, __LINE__
			,	pidfile);
		}
#endif
		created_pid_file = TRUE;
		return TRUE;
	}
	g_critical("%s.%d: Cannot create pid file [%s]. Reason: %s"
	,	__FUNCTION__, __LINE__, pidfile, errptr->message);
	fprintf(stderr, "%s.%d: Cannot create pid file [%s]. Reason: %s\n"
	,	__FUNCTION__, __LINE__, pidfile, errptr->message);
	return FALSE;
}
/// get default pid file name
char *
get_default_pid_fileName(const char *procname) {
	char *p_pidfile;
#ifndef WIN32
	p_pidfile = g_build_filename(STD_PID_DIR, procname, NULL);
#else
	const char * const *dirs = g_get_system_config_dirs();
	p_pidfile = g_build_filename(dirs[0], procname, NULL);
#endif
	//g_debug("%s.%d: pidfile = %s", __FUNCTION__, __LINE__, p_pidfile);
	return(p_pidfile);
}
/// Remove the pid file that goes with this service iff we created one during this invocation
void
remove_pid_file(const char * pidfile)
{
	if (created_pid_file) {
		g_unlink(pidfile);
	}
}

/// kill the service that goes with our current pid file - return negative iff pidfile pid is running and kill fails
int
kill_pid_service(const char * pidfile, int signal)
{
	int	service_pid = 0;
	PidRunningStat	pidstat;

	pidstat = are_we_already_running(pidfile, &service_pid);
	if (pidstat == PID_RUNNING) {
#ifndef WIN32
		return kill((pid_t)service_pid, signal);
#else
		if(TerminateProcess((HANDLE) service_pid, signal) != 0) {
			g_unlink(pidfile);
			return(-1);
		}
#endif
	}
	g_unlink(pidfile);	// No harm in removing it...
	return 0;
}

static const char *	saved_pidfile = NULL;
/// Remove PID file and exit when a signal is received
void
rmpid_and_exit_on_signal(const char * pidfile, int signal_in)
{
#ifndef WIN32
	struct sigaction	sigact;
#endif

	if (pidfile != NULL) {
		saved_pidfile = pidfile;
	}
#ifndef WIN32
        memset(&sigact, 0,  sizeof(sigact));
        sigact.sa_handler = catch_pid_signal;
        sigaction(signal_in, &sigact, NULL);
#else
	signal(signal_in, catch_pid_signal);
#endif
}
FSTATIC void
catch_pid_signal(int unused_signum)
{
	(void)unused_signum;
	g_unlink(saved_pidfile);
	exit(0);
}

/// Convert PidRunningStat to an exit code for status
guint
pidrunningstat_to_status(PidRunningStat stat) ///< Status to convert
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

/// Merge ConfigContext into possibly NULL current environment, returning a new environment
WINEXPORT gchar **
assim_merge_environ(const gchar * const* env	///< Initial environment -- or NULL
,		ConfigContext* update)	///< Updates to merge into this environment
{
	int		j;
	int		initenvcount;
	int		updatecount = 0;
	gchar**		result;
	int		resultelem = 0;
	gchar**		newenv = NULL;

	if (NULL == env) {
		// The result of g_get_environ() has to be freed later...
		// Store malloced copy in 'newenv' so that 'env' parameter can be const...
		newenv = g_get_environ();
		env = (const gchar* const*) newenv;
	}
	
	for (initenvcount = 0; env[initenvcount]; ++initenvcount) {
		; /* Nothing - just count */
	}
	if (update) {
		updatecount = update->keycount(update);
	}

	// This is the worst case for the size needed...
	result = (gchar**) g_malloc((updatecount+initenvcount+1)* sizeof(gchar*));

	if (update) {
		GSList*		updatekeys = NULL;
		GSList*		thiskeylist;

	
		updatekeys = update->keys(update);

		// Put all our update keys in first...
		for (thiskeylist = updatekeys; thiskeylist; thiskeylist=thiskeylist->next) {
			char *	thiskey = (char *)thiskeylist->data;
			enum ConfigValType vtype= update->gettype(update, thiskey);
			GString *	gsvalue = g_string_new("");

			g_string_printf(gsvalue, "%s=", thiskey);

			switch (vtype) {
				case CFG_BOOL:
					// Do we want true/false -- or 1/0 ??
					g_string_append(gsvalue, update->getbool(update, thiskey) ? "true" : "false");
					break;
	
				case CFG_INT64:
					g_string_append_printf(gsvalue, FMT_64BIT"d", update->getint(update,thiskey));
					break;

				case CFG_STRING:
					g_string_append(gsvalue, update->getstring(update, thiskey));
					break;
				case CFG_NETADDR: {
						NetAddr* addr = update->getaddr(update,thiskey);
						char *	s = addr->baseclass.toString(&addr->baseclass);
						g_string_append(gsvalue, s);
						g_free(s);
						// No need to unref 'addr' - it's not a copy
						break;
					}
				case CFG_ARRAY: 
					g_string_append(gsvalue, _shell_array_value(
					(	update->getarray(update,thiskey))));
					break;
				default:
					g_string_free(gsvalue, TRUE);
					gsvalue = NULL;
					thiskeylist->data = thiskey = NULL;
					continue;
			}
			result[resultelem] = g_string_free(gsvalue, FALSE);
			gsvalue = NULL;
			++resultelem;
			// The keys in the key list are NOT copies.  Don't free them!!
			// g_free(thiskey);
			thiskeylist->data = thiskey = NULL;
		}
		// Done with 'updatekeys'
		g_slist_free(updatekeys);
		updatekeys = NULL;

	}

	// Now, add all the env vars not overridden by 'update'
	for (j = 0; env[j]; ++j) {
		char *	envname;
		char *	eqpos;
		eqpos = strchr(env[j], '=');
		if (NULL == eqpos || eqpos == env[j]) {
			continue;
		}
		envname = g_strndup(env[j], eqpos - env[j]);
		// Make sure it isn't overridden before including it...
		if (NULL == update || (update->gettype(update, envname) == CFG_EEXIST)) {
			result[resultelem] = g_strdup(env[j]);
			++resultelem;
		}
		g_free(envname);
	}
	result[resultelem] = NULL;

	if (newenv) {
		g_strfreev(newenv);
	}
	newenv = NULL;
	env = NULL;
	return result;
}

/// Return the value of an array in a shell-compatible way - to put in an environment variable
FSTATIC char *
_shell_array_value(GSList*	arrayvalue)
{
	GString*	gsvalue = g_string_new("");
	const char *	space	= "";
	GSList*		thiselem;

	for (thiselem = arrayvalue; thiselem; thiselem=thiselem->next) {
		ConfigValue*	elem = CASTTOCLASS(ConfigValue, thiselem->data);
		if (elem->valtype != CFG_STRING) {
			continue;
		}
		g_string_append_printf(gsvalue, "%s%s", space, elem->u.strvalue);
		space = " ";
	}
	return g_string_free(gsvalue, FALSE);
}

/// Free the result of assim_merge_env
WINEXPORT void
assim_free_environ(gchar ** env) ///< The result of assim_merge_environ -- to be freed
{
	g_strfreev(env);
}


/// Set the buffer size of a pipe (if possible)
WINEXPORT gsize
setpipebuf(int fd, gsize bufsize)
{
#ifdef F_SETPIPE_SZ
#	define	SYS_MAX_PIPE_SIZE	"/proc/sys/fs/pipe-max-size"
	if (fcntl(fd, F_SETPIPE_SZ, (int)bufsize) < 0) {
		int	sysfsfd = open(SYS_MAX_PIPE_SIZE, O_WRONLY);
		if (sysfsfd >= 0) {
			char	sizestr[32];
			int	rc;
			snprintf(sizestr, sizeof(sizestr), "%zd\n", (size_t)bufsize);
			// Try our best, and do the best we can...
			rc = write(sysfsfd, sizestr, sizeof(sizestr)-1);
			(void)rc;
			(void)close(sysfsfd);
			(void)fcntl(fd, F_SETPIPE_SZ, (int)bufsize);
		}
	}
#else
	(void)bufsize;
#endif
	// We've done the best we know how above, now check to see how it worked..
	return getpipebuf(fd);
}

/// Return the buffer size of a pipe - if not possible return 4096 (a good guess)
WINEXPORT gsize
getpipebuf(int fd)
{
#ifdef F_GETPIPE_SZ
	return (gsize)fcntl(fd, F_GETPIPE_SZ);
#else
	(void)fd;
	return 4096;
#endif
}
WINEXPORT void
assim_g_notify_unref(gpointer assimobj)
{
	AssimObj*	obj = CASTTOCLASS(AssimObj, assimobj);
	obj->unref(obj);
}

static GIOChannel*	_io_channel = NULL;
static GIOFunc		_io_functocall = NULL;
static gpointer		_io_add_watch_pointer	 = NULL;
#define			MAXCOND	(G_IO_IN|G_IO_OUT|G_IO_PRI|G_IO_HUP|G_IO_ERR|G_IO_NVAL)
/// Simiplified interface to g_io_add_watch for our Python code
WINEXPORT guint
assim_set_io_watch(int		fd,		//< File descriptor
		   GIOCondition	condition,	//< Desired Condition
		   GIOFunc	func,		//< Function to call
		   gpointer	user_data)	//< data to pass 'func'
{
	GIOChannel*	channel;
	guint		retval;
#ifdef WIN32
	channel = g_io_channel_win32_new_fd(fd);
#else
	channel = g_io_channel_unix_new(fd);
#endif
	_io_functocall 		= func;
	_io_add_watch_pointer	= user_data;
	_io_channel	 	= channel;
#ifdef DEBUG_CALLBACKS
	g_warning("%s.%d: calling g_io_add_watch(%p, 0x%04x, (proxy:%p (real:%p)), %p)"
	,	__FUNCTION__, __LINE__
	,	channel, condition, _assim_proxy_io_watch, func, user_data);
#endif
	retval =  g_io_add_watch(channel, condition, _assim_proxy_io_watch, user_data);
#ifdef DEBUG_CALLBACKS
	g_warning("%s.%d: return %d;", __FUNCTION__, __LINE__, retval);
#endif
	return retval;
}

#include <stdio.h>
/// This proxy function is here for debugging C<->Python problems...
FSTATIC gboolean
_assim_proxy_io_watch(GIOChannel*	source,	///< Source of this condition
		     GIOCondition	cond,	///< I/O Condition bit mask
		     gpointer		data)	///< user_data from 'watch'
{
	gboolean	retval;
	// Validate what we've been given
	// This only works if we have a single watch active...
	// For the moment, that's True...
	if (source != _io_channel || data != _io_add_watch_pointer
	||	(cond&(~MAXCOND)) != 0) {
		g_error("%s.%d: Called with invalid arguments (%p, 0x%04x, %p)"
		" saved values are (%p, %p)", __FUNCTION__, __LINE__
		,	source, cond, data
		,	_io_channel, _io_add_watch_pointer);
	}
#ifdef DEBUG_CALLBACKS
	g_warning("%s.%d: Calling %p(%p, 0x%04x, %p);"
	" saved values are (%p, %p)"
	,	__FUNCTION__, __LINE__
	,	_io_functocall, source, cond, data
	,	_io_channel, _io_add_watch_pointer);
#endif
	retval = _io_functocall(source, cond, data);
#ifdef DEBUG_CALLBACKS
	g_warning("%s.%d: return(%d);", __FUNCTION__, __LINE__, retval);
#endif
	return retval;
}
