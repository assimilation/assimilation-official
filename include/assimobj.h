/**
 * @file
 * @brief  This file defines our base object class: AssimObj.
 * This class provides reference counting and a toString member function.
 *
 * This file is part of the Assimilation Project.
 *
 * @author Copyright &copy; 2011, 2012 - Alan Robertson <alanr@unix.sh>
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
extern	gboolean	badfree;			// for debugging
///@}
#endif /* ASSIMOBJ_H */
