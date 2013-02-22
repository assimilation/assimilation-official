/**
 * @file
 * @brief Define replacement functions.
 * @details Provides replacement functions for those systems which are lacking various things we like.
 *
 * This file is part of the Assimilation Project.
 *
 * @author Copyright &copy; 2011, 2012, 2013 - Alan Robertson <alanr@unix.sh>
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

#ifndef HAVE_G_GET_MONOTONIC_TIME
#	include <time.h>
#endif /*HAVE_G_GET_MONOTONIC_TIME*/

#ifndef HAVE_G_GET_REAL_TIME

/// Local replacement for g_get_real_time() - for old releases of glib
WINEXPORT gint64
g_get_real_time(void)
{
	GTimeVal	tv;
	guint64		ret;

	g_get_current_time(&tv);

	ret = (gint64)tv.tv_sec * (gint64)1000000UL;
	ret += (gint64)tv.tv_usec;
	return ret;
	
}
#endif/*HAVE_G_GET_REAL_TIME*/

#ifndef HAVE_G_GET_MONOTONIC_TIME
#ifdef CLOCK_MONOTONIC
#	define CLOCKARG	CLOCK_MONOTONIC
#else
#	define CLOCKARG	CLOCK_REALTIME
#endif

/// Local replacement for g_get_monotonic_time() - for old releases of glib
WINEXPORT gint64
g_get_monotonic_time(void)
{
	struct timespec	ts;
	const gint64	million = 1000000UL;
	const gint64	thousand = 1000UL;
	if (clock_gettime(CLOCKARG, &ts) < 0) {
		(void)clock_gettime(CLOCK_REALTIME, &ts); // Should never fail...
	}
	return ((gint64)ts.tv_sec * million) + (((gint64)ts.tv_nsec)/thousand);
}
#endif/*HAVE_G_GET_MONOTONIC_TIME*/
