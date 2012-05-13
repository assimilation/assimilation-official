/**
 * @file
 * @brief Implements a Class system for class hierarchies in 'C'
 * @details We have a variety of classes and subclasses which we use, and this
 * class system permits us to track them and catch errors in casting, parameter passing, etc.
 *
 * @author &copy; 2011,2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <projectcommon.h>
#include <assimobj.h>

#undef	NULL_FOR_BAD_CAST
#ifdef	NULL_FOR_BAD_CAST
#	define	BADCASTMSG	g_critical
#else
#	define	BADCASTMSG	g_error
#endif

/// @defgroup C_Classes C-Classes

/**
 * @defgroup ProjectClass C-Class Management
 *@{
 */
/*
 *	This code depends pretty heavily on Glib hash tables and Glib Quarks.
 *
 *	Quarks are a litle odd, and a little confusing at first - but handy.
 *	A Quark is an object which is an integer which uniquely identifies a particular collection of characters
 *      making up a C-style string.
 *	That is, if you have the string "abc" in your code in three places,
 *      all places will see the quark as being the same.
 *
 *      Two strings which have the same quark have the same content.
 *      The quark which has the value zero is the non-existent quark (goes with NULL pointer).
 *
 *	Our type system then is just two sets of associations (or mappings):
 *		The first is the object -> class-quark mapping
 *			which is keyed by object _addresses_ (ObjectClassAssociation) - not the objects pointed to
 *			The associated values are the quarks of the classes of the objects at those addresses.
 *				{object-address, object class quark}, keyed by object-address
 *				
 *		
 *		The second is the subclass-quark -> superclass-quark mapping,
 *			which is keyed by quarks of classes.
 *			Each associated value is the quark of a superclass.
 *				{subclass-quark, superclass-quark}, keyed by subclass-quark
 */


static GHashTable*	ObjectClassAssociation= NULL;	///< Map of objects -> class quarks
static GHashTable*	SuperClassAssociation = NULL;	///< Map of subclass-quarks -> superclass-quarks
static GHashTable*	DebugClassAssociation = NULL;	///< Map of class -> debug variables
static GHashTable*	FreedClassAssociation = NULL;	///< Map of class -> freed 
static guint32		proj_class_obj_count = 0;
static guint32		proj_class_max_obj_count = 0;
gboolean		badfree = FALSE;

FSTATIC void _init_proj_class_module(void);
FSTATIC void proj_class_change_debug(const char * Cclass, gint incr);

/// Initialize our object system tables.
FSTATIC void
_init_proj_class_module(void)
{
	ObjectClassAssociation  = g_hash_table_new(NULL, NULL); // same as g_direct_hash(), g_direct_equal().
	FreedClassAssociation	= g_hash_table_new(NULL, NULL); // same as g_direct_hash(), g_direct_equal().
	SuperClassAssociation   = g_hash_table_new(NULL, NULL); // same as g_direct_hash(), g_direct_equal().
	DebugClassAssociation   = g_hash_table_new(g_str_hash, g_str_equal);
}
/// Shut down (finalize) our object class system.  Only do on shutdown to make valgrind happy :-D
void
proj_class_finalize_sys(void)
{
	g_hash_table_destroy(ObjectClassAssociation);	ObjectClassAssociation = NULL;
	g_hash_table_destroy(FreedClassAssociation);	FreedClassAssociation = NULL;
	g_hash_table_destroy(SuperClassAssociation);	SuperClassAssociation = NULL;
	g_hash_table_destroy(DebugClassAssociation);	DebugClassAssociation = NULL;
}

/// Log the creation of a new object, and its association with a given type.
/// This involves locating (or registering) the class, and creating an
/// association of the object with a given class (type).
void
proj_class_register_object(gpointer object,			///< Object to be registered
			   const char * static_classname)	///< Class to register it as
{
	
	GQuark	classquark = g_quark_from_static_string(static_classname);	// Quark for the given classname

	if (NULL == ObjectClassAssociation) {
		_init_proj_class_module();
	}
	if (NULL != g_hash_table_lookup(ObjectClassAssociation, object)) {
		g_error("Attempt to re-allocate memory already allocated at address %p", object);
	}
	g_hash_table_insert(ObjectClassAssociation, GINT_TO_POINTER(object), GINT_TO_POINTER(classquark));
	++ proj_class_obj_count;
	if (proj_class_obj_count > proj_class_max_obj_count) {
		proj_class_max_obj_count = proj_class_obj_count;
	}
}

void
proj_class_register_debug_counter(const char * classname, guint * debugcount)
{
	if (NULL == ObjectClassAssociation) {
		_init_proj_class_module();
	}
	// Sleazy - the double cast is to make the 'const' go away - but safe
	// since we aren't going to modify the strings we were given...
	g_hash_table_replace(DebugClassAssociation, GINT_TO_POINTER(GPOINTER_TO_INT(classname)), debugcount);
	
}


/// Increment debug level for this class and all its subclasses by one.
/// NULL class <i>Cclass</i> name means all classes.
void
proj_class_incr_debug(const char * Cclass)
{
	proj_class_change_debug(Cclass, +1);
}

/// Decrement debug level for this class and all its subclasses by one.
/// NULL class <i>Cclass</i> name means all classes.
void
proj_class_decr_debug(const char * Cclass)
{
	proj_class_change_debug(Cclass, -1);
}

/// Change debug level for this class and all its subclasses by 'incr'.
/// NULL class <i>Cclass</i> name means all classes.
FSTATIC void
proj_class_change_debug(const char * Cclass, gint incr)
{
	GHashTableIter	iter;
	gpointer	classname;
	gpointer	gdebugptr;
	GQuark		CclassQuark = g_quark_from_static_string(Cclass);

	g_hash_table_iter_init(&iter, DebugClassAssociation);

	// Search through all our debug pointers.
	// Modify (+/-) the debug variables for each class that 'is_a' Cclass object.
	while (g_hash_table_iter_next(&iter, &classname, &gdebugptr)) {
		guint*	debug = gdebugptr;
		GQuark	classQ = g_quark_from_static_string(classname);
		if (Cclass == NULL || proj_class_quark_is_a(classQ, CclassQuark)) {
			if (incr < 0 && (guint)-incr >= *debug) {
				*debug = 0;
			}else{
				*debug += incr;
			}
		}
	}
}

/// Log the creation of a subclassed object from a superclassed object.
/// The subclass name given must be the immediate subclass of the class of the object, not through multiple levels of subclassing.
gpointer
proj_class_register_subclassed(gpointer object,				///< Object (currently registered as superclass)
			       const char * static_subclassname)	///< Subclass to register it as
{
	
	GQuark	subclassquark = g_quark_from_static_string(static_subclassname);	// Quark for the given classname
	GQuark	superclassquark;

	if (NULL == ObjectClassAssociation) {
		_init_proj_class_module();
	}
	superclassquark = GPOINTER_TO_INT(g_hash_table_lookup(ObjectClassAssociation, object));
	if (0 == superclassquark) {
		g_error("Attempt to subclass an object that's not a class object %p", object);
	}
	///todo create a superclass/subclass hierarchy...
	proj_class_quark_add_superclass_relationship(superclassquark, subclassquark);
	g_hash_table_replace(ObjectClassAssociation, object, GINT_TO_POINTER(subclassquark));
	return object;
}

/// Malloc a new object and register it in our class system.
gpointer
proj_class_new(gsize objsize,				///< Size of object to be allocated
	       const char * static_classname)		///< Static string giving name of class
{
	gpointer	ret = MALLOC0(objsize);

	if (ret != NULL) {
		proj_class_register_object(ret, static_classname);
	}
	return ret;
}
/// Dissociate an object from the C class system (typically coupled with freeing it).
/// If it's not a registered C-class object, we abort.
/// Better a semi-predictable abort than a random and unpredictable crash.
void
proj_class_dissociate(gpointer object) ///< Object be 'dissociated' from class
{
	GQuark		objquark = GPOINTER_TO_INT(g_hash_table_lookup(ObjectClassAssociation, object));
	-- proj_class_obj_count;
	if (objquark == 0) {
		GQuark		freedquark = GPOINTER_TO_INT(g_hash_table_lookup(FreedClassAssociation, object));
		const char * 	oldclass = (freedquark == 0 ? "(unknown class)" : g_quark_to_string(freedquark));
		BADCASTMSG("Attempt to free memory not currently shown as allocated to a class object - former class: %s"
		,	oldclass);
		badfree = TRUE;
	}else{
		//g_warning("Freeing object %p of type %s", object, proj_class_classname(object));
		g_hash_table_insert(FreedClassAssociation, GINT_TO_POINTER(object), GINT_TO_POINTER(objquark));
		g_hash_table_remove(ObjectClassAssociation, object);
	}
}

/// Free a registered object from our class system.
/// If it's not a registered C-class object, we abort.
/// Better a semi-predictable abort than a random and unpredictable crash.
void
proj_class_free(gpointer object) ///< Object be freed
{
	proj_class_dissociate(object);
	FREE(object);
}

/// Return TRUE if the given <i>object</i> <b>ISA</b> <i>castclass</i> object.
gboolean
proj_class_is_a(gconstpointer object,		///<[i] Object to be queried
		const char * Cclass)		///<[i] Class to be queried
{
	GQuark		objquark;
	GQuark		classquark;

	if (NULL == object) {
		return TRUE;
	}

	objquark = GPOINTER_TO_INT(g_hash_table_lookup(ObjectClassAssociation, object));
	classquark = g_quark_from_static_string(Cclass);

	if (objquark != classquark || classquark == 0) {
		if (!proj_class_quark_is_a(objquark, classquark)) {
			return FALSE;
		}
	}
	return TRUE;
}

/// "Safely" cast an object to a <i>const</i> object of the given C-class.

/// "Safely" cast an object to a given C-class.
/// What we mean by that, is that before returning, we verify that the object in question
/// <b>ISA</b> <i>castclass</i> object.
/// If it's not, we abort.  Better a semi-predictable abort than a random and unpredictable crash.
gpointer
proj_class_castas(gpointer     object,		///< Object to be "cast" as "castclass"
		  const char * castclass)	///< Class to cast "object" as
{
	if (!OBJ_IS_A(object, castclass)) {
		const char *	objclass =  proj_class_classname(object);
		GQuark		freedquark = GPOINTER_TO_INT(g_hash_table_lookup(FreedClassAssociation, object));
		const char * 	oldclass = (freedquark == 0 ? "(unknown class)" : g_quark_to_string(freedquark));
		BADCASTMSG("Attempt to cast %s pointer at address %p to %s (formerly a %s)", objclass, object, castclass
		,	oldclass);
		object = NULL;
		badfree = TRUE;
	}
	return object;
}

/// "Safely" cast an object to a <i>const</i> object of the given C-class.
/// What we mean by that, is that before returning, we verify that the object in question
/// <b>ISA</b> <i>castclass</i> object.
/// If it's not, we abort.  Better a semi-predictable abort than a random and unpredictable crash.
gconstpointer
proj_class_castasconst(gconstpointer object,	///< Object to be "cast" to "castclass"
		  const char * castclass)	///< Class to cast "object" as
{
	if (!proj_class_is_a(object, castclass)) {
		const char *objclass =  proj_class_classname(object);
		BADCASTMSG("Attempt to cast %s pointer at address %p to %s", objclass, object, castclass);
		object = NULL;
	}
	return object;
}

/// Return the class name of one of our managed objects

/// Return the class name of one of our managed objects
const char *
proj_class_classname(gconstpointer object) ///< pointer to the object whose name we want to find
{
	GQuark		objquark = GPOINTER_TO_INT(g_hash_table_lookup(ObjectClassAssociation, object));
	return (objquark == 0 ? "(unknown class)" : g_quark_to_string(objquark));
	
}

/// Register a superclass/subclass relationship in our type system (using Quarks of the classes))
void
proj_class_quark_add_superclass_relationship(GQuark superclass,	///< Quark for Superclass
					     GQuark subclass)	///< Quark for Subclass
{
	g_hash_table_insert(SuperClassAssociation, GINT_TO_POINTER(subclass), GINT_TO_POINTER(superclass));
	
}
/// Determine whether an 'objectclass' ISA member of 'testclass' - with quarks of types as arguments
/// Since this little C-class system only supports single-inheritance, this isn't exactly rocket science.
gboolean
proj_class_quark_is_a(GQuark objectclass,	///< Object to be tested
		      GQuark testclass)		///< Class/Superclass to test object against
{
	while (objectclass != 0) {
		if (objectclass == testclass) {
			return TRUE;
		}
		objectclass = GPOINTER_TO_INT(g_hash_table_lookup(GINT_TO_POINTER(SuperClassAssociation), GINT_TO_POINTER(objectclass)));
	}
	return FALSE;
}

/// Dump all live C class objects (address and Class)
void
proj_class_dump_live_objects(void)
{
	GHashTableIter	iter;
	gpointer	object;
	gpointer	quarkp;

	g_debug("START of live C Class object dump:");
	if (ObjectClassAssociation) {
		g_hash_table_iter_init(&iter, ObjectClassAssociation);
		while (g_hash_table_iter_next(&iter, &object, &quarkp)) {
			if (OBJ_IS_A(object, "AssimObj")) {
				AssimObj*	obj = CASTTOCLASS(AssimObj, object);
				char *		str = obj->toString(obj);
				g_debug("       %s object %s at %p ref count %d"
				,		proj_class_classname(obj), str, obj, obj->_refcount);
				g_free(str);
			}else{
				g_debug("       %s object at %p", proj_class_classname(object), object);
			}
		}
	}
	g_debug("END of live C Class object dump.");
}


/// Return the count of live C class objects
guint32
proj_class_live_object_count(void)
{
	GHashTableIter	iter;
	gpointer	object;
	gpointer	quarkp;
	guint32		count = 0;
	

	if (ObjectClassAssociation) {
		g_hash_table_iter_init(&iter, ObjectClassAssociation);
		while (g_hash_table_iter_next(&iter, &object, &quarkp)) {
			count += 1;
		}
	}
	g_assert(count == proj_class_obj_count);
	return count;
}

/// Return the maximum number of live C class objects that we've ever had
guint32
proj_class_max_object_count(void)
{
	return proj_class_max_obj_count;
}

///@}
