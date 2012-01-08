/**
 * @file
 * @brief Defines interfaces a project Class system for class hierarchies in 'C'
 * @details We have a variety of classes and subclasses which we use, and this
 * class system permits us to track them and catch errors in casting, parameter passing, etc.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <glib.h>

#ifdef _MSC_VER
#define EXP_FUNC __declspec( dllexport )
#else 
#define EXP_FUNC
#endif
EXP_FUNC gpointer	proj_class_new(gsize objsize, const char * static_classname);
EXP_FUNC void		proj_class_dissociate(gpointer object);
EXP_FUNC void		proj_class_free(gpointer object);
EXP_FUNC void		proj_class_register_object(gpointer object, const char * static_classname);
EXP_FUNC gpointer	proj_class_castas(gpointer object, const char * castclass);
EXP_FUNC gconstpointer	proj_class_castasconst(gconstpointer object, const char * castclass);
EXP_FUNC void		proj_class_register_subclassed(gpointer object, const char * static_subclassname);
EXP_FUNC void		proj_class_quark_add_superclass_relationship(GQuark superclass, GQuark subclass);
EXP_FUNC gboolean	proj_class_quark_is_a(GQuark objectclass, GQuark testclass);
EXP_FUNC const char *	proj_class_classname(gconstpointer object);


EXP_FUNC void proj_class_dump_live_objects(void);
EXP_FUNC guint32 proj_class_live_object_count(void);

///@{
///@ingroup ProjectClass

/// Allocate memory for a C-class object of base class <i>class</i> (not to be further subclassed) - and register it with our C-Class system
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
/// Safely cast 'obj' to const C-class 'class' - verifying that it was registerd as being of type <i>class</i>
/// @param Cclass class to cast <i>obj</i> (the object) to.
/// @param obj the object to be cast to type <i>class</i>
#define CASTTOCONSTCLASS(Cclass, obj)		((const Cclass *) proj_class_castasconst(obj, #Cclass))

/// Free a C-class object.
/// @param obj the object to be freed.  Should be registered as a class object.
#define FREECLASSOBJ(obj)		{proj_class_free(obj); obj = NULL;}
///@}
