/**
 * @file
 * @brief  This file defines our base object class: AssimObj.
 * This class provides reference counting and a toString member function.
 *
 * @author &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _ASSIMOBJ_H
#define _ASSIMOBJ_H
#include <projectcommon.h>

///@{
/// @ingroup AssimObj
typedef struct _AssimObj	AssimObj;

struct _AssimObj {
	int		_refcount;			///< Reference count (private)
	void		(*_finalize)(AssimObj*);	///< Free object (private)
	void		(*ref)(gpointer);		///< Increment reference count
	void		(*unref)(gpointer);		///< Decrement reference count
	gchar*		(*toString)(gconstpointer);	///< Produce malloc-ed string representation
};
WINEXPORT AssimObj*		assimobj_new(guint objsize);
WINEXPORT void			_assimobj_finalize(AssimObj* self);
///@}
#endif /* ASSIMOBJ_H */
