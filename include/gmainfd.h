/**
 * @file
 * @brief Implements a gmainloop source for reading file descriptor pipes
 * @details This class implements a base class for reading file descriptor pipes and stashing the
 * results away in strings.  It is notable that this class is <i>not</i> a subclass of @ref AssimObj.
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

#ifndef _GMAINFd_H
#	define _GMAINFd_H
#include <projectcommon.h>
#include <assimobj.h>

///@{
/// @ingroup GMainFd
typedef struct _GMainFd GMainFd;

struct _GMainFd {
	GSource		baseclass;				///< Our base class - <i>NOT</i> an AssimObj
	GPollFD		gfd;					///< Poll/select object for gmainloop
	GString*	textread;				///< The text we've read so far.
	gboolean	atEOF;					///< TRUE if the file descriptor is at EOF
	int		gsourceid;
	void 		(*newtext)(GMainFd*, const char*, int);	///< Deal with newly read text
	void 		(*finalize)(GMainFd*);			///< finalize function
};
// We use g_source_ref() and g_source_unref() to manage reference counts


WINEXPORT GMainFd*	gmainfd_new(gsize cpsize, int fd, int priority, GMainContext* context);

///@}
#endif/*GMAINFD_H*/
