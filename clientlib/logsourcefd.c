/**
 * @file
 * @brief Implements a gmainloop source for logging file descriptor contents
 * @details This class implements a base class for reading file descriptor pipes and logging
 * whatever we've read.  It is notable that this class is <i>not</i> a subclass of @ref AssimObj.
 *
 * @author Copyright &copy; 2013 - Alan Robertson <alanr@unix.sh>
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
#include <gmainfd.h>
#include <logsourcefd.h>
#include <string.h>

FSTATIC void logsourcefd_newtext(GMainFd*, const char *, int len);
FSTATIC void logsourcefd_finalize(GMainFd* fdself);

/// Construct a new @ref GMainFd object and return it.
LogSourceFd*
logsourcefd_new(gsize cpsize
,		int	fd
,		int	priority
,		GMainContext* context
,		const char * logdomain
,		GLogLevelFlags	loglevel
,		const char *	prefix)

{
	GMainFd*	fdself;
	LogSourceFd*	self;

	if (cpsize < sizeof(LogSourceFd)) {
		cpsize = sizeof(LogSourceFd);
	}
	fdself = gmainfd_new(cpsize, fd, priority, context);
	g_return_val_if_fail(fdself != NULL, NULL);
	self = NEWSUBCLASS(LogSourceFd, fdself);

	fdself->newtext = logsourcefd_newtext;
	fdself->finalize = logsourcefd_finalize;
	self->logdomain	= g_strdup(logdomain);
	self->prefix	= g_strdup(prefix);
	self->loglevel	= loglevel;
	return self;
}

/// Just stash away our new string - appending to what's already there
FSTATIC void
logsourcefd_newtext(GMainFd* fdself, const char * string, int len)
{
	GString*	thisline = NULL;
	LogSourceFd*	self = CASTTOCLASS(LogSourceFd, fdself);
	const int	prefixlen = strlen(self->prefix);
	int		j;

	self->charcount += len;
	for (j=0; j < len; ++j) {
		if (string[j] == '\n') {
			self->linecount += 1;
			if (thisline) {
				g_log(self->logdomain, self->loglevel, "%s%s", self->prefix, thisline->str);
				g_string_free(thisline, TRUE);
				thisline = NULL;
			}
			continue;
		}
		if (thisline == NULL) {
			thisline = g_string_sized_new(prefixlen + (len-j));
			thisline = g_string_append_c(thisline, string[j]);
		}else{
			thisline = g_string_append_c(thisline, string[j]);
		}
	}
	if (thisline) {
		g_log(self->logdomain, self->loglevel, "%s%s", self->prefix, thisline->str);
		g_string_free(thisline, TRUE);
		thisline = NULL;
	}
}



/// @ref LogSourceFd finalize routine
FSTATIC void
logsourcefd_finalize(GMainFd* fdself)
{
	LogSourceFd*	self = CASTTOCLASS(LogSourceFd, fdself);
	if (self->logdomain) {
		g_free(self->logdomain);
		self->logdomain = NULL;
	}
	if (self->prefix) {
		g_free(self->prefix);
		self->prefix = NULL;
	}
}
