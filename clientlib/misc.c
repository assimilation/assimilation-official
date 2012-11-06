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
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <misc.h>


/// Make us into a proper daemon.
void
daemonize_me(	gboolean stay_in_foreground,	///<[in] TRUE to not make a background job
		const char* dirtorunin)		///<[in] Directory to cd to or NULL for default (/)
{
	struct rlimit		nofile_limits;
	unsigned		j;
	int			nullfd;
	int			nullperms[] = { O_RDONLY, O_WRONLY, O_WRONLY};
	getrlimit(RLIMIT_NOFILE, &nofile_limits);

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
	chdir(dirtorunin ? dirtorunin : "/" );
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
	}
#else
	(void)stay_in_foreground;
#endif
}
