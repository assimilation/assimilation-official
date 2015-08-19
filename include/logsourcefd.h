/**
 * @file
 * @brief Implements a gmainloop source for reading file descriptor pipes
 * @details This class implements a base class for reading file descriptor pipes and
 * logging whatever it reads.  It is notable that this class is <i>not</i> a subclass of @ref AssimObj.
 *
 *
 * @author Copyright &copy; 2013 - Alan Robertson <alanr@unix.sh>
 * @n
 *  The Assimilation software is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This file is part of the Assimilation Project.
 *  The Assimilation software is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the:e clie
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
 */

#ifndef _LOGSOURCEFd_H
#	define _LOGSOURCEFd_H
#include <projectcommon.h>
#include <gmainfd.h>

///@{
/// @ingroup LogSourceFd
typedef struct _LogSourceFd LogSourceFd;

struct _LogSourceFd {
	GMainFd		baseclass;		///< Our base class - <i>NOT</i> an AssimObj
	char *		logdomain;		///< What log domain to log to
	char *		prefix;			///< What prefix to print before our log entries
	GLogLevelFlags	loglevel;		///< What level to log these outputs to
	int		charcount;		///< How many characters have been logged (read).
						///< (this does not count the prefix, etc.)
	int		linecount;		///< How many lines have been logged
};
// We use g_source_ref() and g_source_unref() to manage reference counts


WINEXPORT LogSourceFd*	logsourcefd_new(gsize cpsize, int fd, int priority, GMainContext* context, const char * logdomain
,	GLogLevelFlags loglevel, const char * prefix);

///@}
#endif/*LOGSOURCEFD_H*/
