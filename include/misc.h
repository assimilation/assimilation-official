
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
#include <syslog.h>
#include <stdio.h>

extern const char*	assim_syslogid;

/// Status of pid file and/or running processes referred to by it
typedef enum {
	PID_NOTRUNNING,	//< Nothing seems to be running for this pidfile
	PID_DEAD,	//< The pid file exists, but its process doesn't
	PID_NOTUS,	//< Something is running, but we don't think it's one of us
	PID_RUNNING,	//< The pid file exists, and looks like one of us
} PidRunningStat;

void daemonize_me(gboolean stay_in_foreground, const char * dirtorunin);
void assimilation_openlog(const char* logname);
PidRunningStat are_we_already_running(const char * pidfile);
gboolean	create_pid_file(const char * pidfile);

#endif /* MISC_H */
///@}
