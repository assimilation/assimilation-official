/**
 * @file
 * @brief Implements base class for our object system.
 * @details 
 * This class implements reference counting and a toString member function.
 *
 * @author &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <memory.h>
#include <projectcommon.h>
#include <assimobj.h>

/// @defgroup AssimObj AssimObj class
/// @brief Implements the base object class for our object system.
/// @details 
/// Implements reference counting and a basic toString function.
/// @ingroup C_Classes
/// @{

FSTATIC void _assimobj_ref(gpointer self);
FSTATIC void _assimobj_unref(gpointer self);
void _assimobj_finalize(AssimObj* self);
FSTATIC char * _assimobj_toString(gconstpointer self);

FSTATIC void
_assimobj_ref(gpointer vself)
{
	AssimObj* self = CASTTOCLASS(AssimObj, vself);
	g_return_if_fail(self->_refcount > 0);
	self->_refcount += 1;
}
FSTATIC void
_assimobj_unref(gpointer vself)
{
	AssimObj* self = CASTTOCLASS(AssimObj, vself);
	g_return_if_fail(self->_refcount > 0);
	self->_refcount -= 1;
	if (self->_refcount == 0) {
		self->_finalize(self); self=NULL;
	}
}

void
_assimobj_finalize(AssimObj* self)
{
	FREECLASSOBJ(self);
}

FSTATIC char *
_assimobj_toString(gconstpointer vself)
{
	const AssimObj* self = CASTTOCONSTCLASS(AssimObj,vself);
	return g_strdup_printf("{%s object at 0x%p}", proj_class_classname(self), self);
}

AssimObj*
assimobj_new(guint objsize)
{
	AssimObj* self;
	if (objsize < sizeof(AssimObj)) {
		objsize = sizeof(AssimObj);
	}
	self = MALLOCCLASS(AssimObj, objsize);
	self->_refcount = 1;
	self->ref = _assimobj_ref;
	self->unref = _assimobj_unref;
	self->_finalize = _assimobj_finalize;
	self->toString = _assimobj_toString;
	return self;
}
///@}
