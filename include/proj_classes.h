/**
 * @file
 * @brief Defines interfaces a project Class system for class hierarchies in 'C'
 * @details We have a variety of classes and subclasses which we use, and this
 * class system permits us to track them and catch errors in casting, parameter passing, etc.
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
#include <projectcommon.h>
#include <assimobj.h>
#include <glib.h>

WINEXPORT gpointer	proj_class_new(gsize objsize, const char * static_classname);
WINEXPORT void		proj_class_dissociate(gpointer object);
WINEXPORT void		proj_class_free(gpointer object);
WINEXPORT void		proj_class_register_object(gpointer object, const char * static_classname);
WINEXPORT gboolean	proj_class_is_a(gconstpointer object, const char * castclass);
WINEXPORT gpointer	proj_class_castas(gpointer object, const char * castclass);
WINEXPORT gconstpointer	proj_class_castasconst(gconstpointer object, const char * castclass);
WINEXPORT gpointer	proj_class_register_subclassed(gpointer object, const char * static_subclassname);
WINEXPORT void		proj_class_quark_add_superclass_relationship(GQuark superclass, GQuark subclass);
WINEXPORT gboolean	proj_class_quark_is_a(GQuark objectclass, GQuark testclass);
WINEXPORT const char *	proj_class_classname(gconstpointer object);
WINEXPORT void		proj_class_register_debug_counter(const char * Cclass, guint*debugcount);
WINEXPORT void		proj_class_incr_debug(const char * Cclass);
WINEXPORT void		proj_class_decr_debug(const char * Cclass);
WINEXPORT void		proj_class_debug_dump(const char * prefix, const AssimObj* obj, const char *suffix);

WINEXPORT void proj_class_dump_live_objects(void);
WINEXPORT guint32 proj_class_live_object_count(void);
WINEXPORT guint32 proj_class_max_object_count(void);
WINEXPORT void proj_class_finalize_sys(void);

///@{
///@ingroup ProjectClass

/// Allocate memory for a C-class object of base class <i>class</i> G(not to be further subclassed) - and register it with our C-Class system
/// @param Cclass	name of class to malloc data for.  Amount malloced will be <i>sizeof(class)</i>, return type is <i>class</i>*.
/// @returns sizeof(class) bytes of newly allocated heap data of type <i>class</i>*.  Don't forget to give it to @ref FREECLASSOBJ eventually.
#define MALLOCBASECLASS(Cclass)	((Cclass *) proj_class_new(sizeof(Cclass), #Cclass))

/// Allocate memory for an object (which might be further subclassed) - and register it with our C-Class system
/// @param Cclass name of class to malloc data for
/// @param size number of bytes to malloc
/// @returns <i>size</i> bytes of newly allocated heap data of type <i>class</i>*.  Don't forget to give it to @ref FREECLASSOBJ eventually.
#define MALLOCCLASS(Cclass, size)	((Cclass *) proj_class_new(size, #Cclass))

/// Safely cast 'obj' to C-class 'class' - verifying that it was registerd as being of type <i>class</i>
/// @param Cclass class to cast <i>obj</i> (the object) to.
/// @param obj the object to be cast to type <i>class</i>
#define CASTTOCLASS(Cclass, obj)		((Cclass *) proj_class_castas(obj, #Cclass))
#define NEWSUBCLASS(Cclass, obj)		((Cclass *) proj_class_register_subclassed(obj, #Cclass))
/// Safely cast 'obj' to const C-class 'class' - verifying that it was registered as being of type <i>class</i>
/// @param Cclass class to cast <i>obj</i> (the object) to.G
/// @param obj the object to be cast to type <i>class</i>
#define CASTTOCONSTCLASS(Cclass, obj)		((const Cclass *) proj_class_castasconst(obj, #Cclass))
#define OBJ_IS_A(obj, Cclass)			proj_class_is_a(obj, Cclass)

/// Free a C-class object.
/// @param obj the object to be freed.  Should be registered as a class object.
#define FREECLASSOBJ(obj)		{proj_class_free(obj); obj = NULL;}
#define UNREF(obj)		{(obj)->baseclass.unref(&(obj)->baseclass); (obj) = NULL;}
#define UNREF2(obj)		{(obj)->baseclass.baseclass.unref(&(obj)->baseclass.baseclass); (obj) = NULL;}
#define UNREF3(obj)		{(obj)->baseclass.baseclass.baseclass.unref(&(obj)->baseclass.baseclass.baseclass); (obj) = NULL;}
#define UNREF4(obj)		{(obj)->baseclass.baseclass.baseclass.baseclass.unref(&(obj)->baseclass.baseclass.baseclass.baseclass); (obj) = NULL;}

#define DEBUGVAR		__class_debug_count
#define DEBUGDECLARATIONS	static gboolean __class_debug_registered = FALSE;	\
				static guint    __class_debug_count = 0;
/// BINDDEBUG is for telling the class system where the debug variable for this class is - put it in the base constructor for the class.
#define BINDDEBUG(Cclass)	{if (!__class_debug_registered) {proj_class_register_debug_counter(#Cclass, &__class_debug_count); __class_debug_registered = TRUE;};}


#define DEBUG	(DEBUGVAR)

#define DEBUGMSG(...) {if (DEBUG) {g_debug(__VA_ARGS__);};}
#define DEBUGMSGn(n, ...) {if (DEBUG >= (n)) {g_debug(__VA_ARGS__);};}
#define DEBUGMSG1(...) DEBUGMSG (   __VA_ARGS__)
#define DEBUGMSG2(...) DEBUGMSGn(2, __VA_ARGS__)
#define DEBUGMSG3(...) DEBUGMSGn(3, __VA_ARGS__)
#define DEBUGMSG4(...) DEBUGMSGn(4, __VA_ARGS__)
#define DEBUGMSG5(...) DEBUGMSGn(5, __VA_ARGS__)
#define	DUMP(prefix, obj, suffix)	{proj_class_debug_dump(prefix, obj, suffix);}
#define	DUMP1(prefix, obj, suffix)	{if (DEBUG>=1) {DUMP(prefix, obj, suffix);};}
#define	DUMP2(prefix, obj, suffix)	{if (DEBUG>=2) {DUMP(prefix, obj, suffix);};}
#define	DUMP3(prefix, obj, suffix)	{if (DEBUG>=3) {DUMP(prefix, obj, suffix);};}
#define	DUMP4(prefix, obj, suffix)	{if (DEBUG>=4) {DUMP(prefix, obj, suffix);};}
#define	DUMP5(prefix, obj, suffix)	{if (DEBUG>=5) {DUMP(prefix, obj, suffix);};}


///@}
