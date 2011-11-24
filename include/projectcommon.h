/**
 * @file
 * @brief Project common header file.
 * @details Every source file is supposed to include this header file.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#ifndef _PROJECTCOMMON_H
#define _PROJECTCOMMON_H
#define	DIMOF(a)	(sizeof(a)/sizeof(a[0]))	///< Return dimension of array.
#define	MALLOC0(nbytes)	g_try_malloc0(nbytes)		///< should it just call g_malloc?
#define	MALLOC(nbytes)	g_try_malloc(nbytes)		///< should it just call g_malloc?
#define	MALLOCTYPE(t)	(g_try_new0(t, 1))		///< malloc an object of type 't'.
							///< Or should it just call g_new0?
#define	FREE(m)		g_free(m)			///< Our interface to free

#define	FSTATIC		/* Static function */
#define	FMT_64BIT	"%ll"				///< Format designator for a 64 bit integer
#include <glib.h>
#include <proj_classes.h>

#endif /* _PROJECTCOMMON_H */
