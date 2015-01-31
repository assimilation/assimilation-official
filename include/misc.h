
/**
 * @file
 * @brief Defines miscellaneous interfaces.
 * @details Defines a variety of miscellaneous non-class interfaces.
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
#ifndef _MISC_H
#include <projectcommon.h>
#include <configcontext.h>
#ifndef WIN32
#include <syslog.h>
#endif
#include <stdio.h>

#define STD_PID_DIR	"/var/run"

extern const char*	assim_syslogid;

/// Status of pid file and/or running processes referred to by it - analogous to "service status"
typedef enum {
	PID_NOTRUNNING,	//< Nothing seems to be running for this pidfile
	PID_DEAD,	//< The pid file exists, but its process doesn't
	PID_NOTUS,	//< Something is running, but we don't think it's one of us
	PID_RUNNING,	//< The pid file exists, and looks like one of us
} PidRunningStat;
char *	proj_get_sysname(void);			///< Return a malloced string of the system name

/** Make a daemon process out of this process*/
WINEXPORT char *get_default_pid_fileName(const char *procname);
WINEXPORT void daemonize_me(gboolean stay_in_foreground	///< TRUE == don't fork
,		  const char * dirtorunin	///< Directory to cd to before running
,		  char* pidfile			///< pathname of pid file, or NULL
,		  int	minclosefd);		///< minimum file descriptor to close - or zero
WINEXPORT void assimilation_openlog(const char* logname);				///< Open logs in our style (syslog)
WINEXPORT PidRunningStat are_we_already_running(const char * pidfile, int* pid);	///< Determine service status
WINEXPORT guint	pidrunningstat_to_status(PidRunningStat);		///< Convert PidRunningStat to an exit code for status
gboolean	create_pid_file(const char * pidfile);			///< Create pid file - return TRUE on success
WINEXPORT void	remove_pid_file(const char * pidfile);			///< Remove pid file we created (if we created one)
WINEXPORT int	kill_pid_service(const char * pidfile, int signal);	///< Issue given signal to the pidfile-indicated running process
WINEXPORT void	rmpid_and_exit_on_signal(const char * pidfile, int signal);	///< Issue given signal to the pidfile-indicated running process
WINEXPORT gchar** assim_merge_environ(const gchar *const* env, ConfigContext*);///< Create new env merged from ConfigContext
WINEXPORT void	assim_free_environ(gchar ** env);		///< Free environment created by assim_merge_environ
WINEXPORT gsize	setpipebuf(int fd, gsize bufsize);		///< Set pipe buffer size (if possible)
WINEXPORT gsize	getpipebuf(int fd);				///< Return pipe buffer size
WINEXPORT void	assim_g_notify_unref(gpointer assimobj);	///< Unref for glib notify
WINEXPORT guint	assim_set_io_watch(int fd, GIOCondition condition, GIOFunc func, gpointer user_data);

WINEXPORT	
#endif /* MISC_H */
///@}
