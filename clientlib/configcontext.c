/**
 * @file
 * @brief Implements the @ref ConfigContext class.
 * @details This file provides a place to remember and pass configuration values around.
 *
 * @author &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <configcontext.h>
#include <memory.h>

FSTATIC void	_configcontext_setmgmtaddr(ConfigContext*, NetAddr*);
FSTATIC void	_configcontext_setsignframe(ConfigContext* self, SignFrame* signframe);
FSTATIC void	_configcontext_ref(ConfigContext* self);
FSTATIC void	_configcontext_unref(ConfigContext* self);
FSTATIC void	_configcontext_finalize(AssimObj* self);
FSTATIC void	_configcontext_free(void* thing);
FSTATIC void	_configcontext_freeNetAddr(void* thing);
FSTATIC void	_configcontext_freeFrame(void* thing);
FSTATIC gint	_configcontext_getint(ConfigContext*, const char *name);
FSTATIC void	_configcontext_setint(ConfigContext*, const char *name, gint value);
FSTATIC const char* _configcontext_getstring(ConfigContext*, const char *name);
FSTATIC void	_configcontext_setstring(ConfigContext*, const char *name, const char *value);
FSTATIC NetAddr*_configcontext_getaddr(ConfigContext*, const char *);
FSTATIC void	_configcontext_setaddr(ConfigContext*, const char *name, NetAddr*);
FSTATIC Frame*	_configcontext_getframe(ConfigContext*, const char *name);
FSTATIC void	_configcontext_setframe(ConfigContext*, const char *name, Frame*);
/// @defgroup ConfigContext ConfigContext class
/// A base class for remembering configuration values of various types.
///@{
///@ingroup C_Classes

/// Construct a new ConfigContext object - with no values defaulted
ConfigContext*
configcontext_new(gsize objsize)	///< size of ConfigContext structure (or zero for min size)
{
	AssimObj * baseobj = NULL;
	ConfigContext * newcontext = NULL;

	if (objsize < sizeof(ConfigContext)) {
		objsize = sizeof(ConfigContext);
	}
	baseobj = assimobj_new(objsize);
	if (NULL == baseobj) {
		goto errout;
	}
	newcontext = NEWSUBCLASS(ConfigContext, baseobj);
	newcontext->setint	=	_configcontext_setint;
	newcontext->getint	=	_configcontext_getint;
	newcontext->setstring=		_configcontext_setstring;
	newcontext->getstring=		_configcontext_getstring;
	newcontext->getframe=		_configcontext_getframe;
	newcontext->setframe=		_configcontext_setframe;
	newcontext->getaddr=		_configcontext_getaddr;
	newcontext->setaddr=		_configcontext_setaddr;
	baseobj->_finalize	=	_configcontext_finalize;
	return newcontext;
errout:
	if (baseobj) {
		baseobj->_finalize(CASTTOCLASS(AssimObj,newcontext));
		newcontext = NULL;
		baseobj = NULL;
	}
	g_return_val_if_reached(NULL);
}

/// Get an integer value
FSTATIC gint
_configcontext_getint(ConfigContext* self	///<[in] ConfigContext object
	,	      const char *name)		///<[in] Name to get the associated int value of
{
	gpointer	lookupkey = NULL;
	gpointer	lookupvalue = NULL;

	if (NULL == self->_intvalues) {
		return -1;
	}
	g_hash_table_lookup_extended(self->_intvalues, name, &lookupkey, &lookupvalue);
	if (lookupkey == NULL) {
		return -1;
	}
	return GPOINTER_TO_INT(lookupvalue);
}

/// Set a name to an integer value
FSTATIC void
_configcontext_setint(ConfigContext* self	///<[in/out] ConfigContext Object
	,	      const char *name		///<[in] Name to set the associated int value of
	,	      gint value)		///<[in] Int value to set the 'name' to
{
	char *	cpname = g_strdup(name);
	if (NULL == self->_intvalues) {
		self->_intvalues = g_hash_table_new_full(g_str_hash, g_str_equal, _configcontext_free, NULL);
	}
	g_hash_table_insert(self->_intvalues, cpname, GINT_TO_POINTER(value));
}

/// Return the value of a string name
FSTATIC const char*
_configcontext_getstring(ConfigContext* self	///<[in] ConfigContext object
		,	 const char *name)	///<[in] Name to get the associated string value of
{
	if (NULL == self->_strvalues) {
		return NULL;
	}
	return (const char *)g_hash_table_lookup(self->_strvalues, name);
}

/// Set a name to a string value
FSTATIC void
_configcontext_setstring(ConfigContext* self	///<[in/out] ConfigContext object
			,const char *name	///<[in] Name to set the string value of (we copy it)
			,const char *value)	///<[in] Value to set 'name' to (we copy it)
{
	char *	cpname = g_strdup(name);
	char *	cpvalue = g_strdup(value);
	if (NULL == self->_strvalues) {
		self->_strvalues = g_hash_table_new_full(g_str_hash, g_str_equal
		,	_configcontext_free, _configcontext_free);
	}
	g_hash_table_insert(self->_strvalues, cpname, cpvalue);
}


/// Return the NetAddr value of a name
FSTATIC  NetAddr*
_configcontext_getaddr(ConfigContext* self	///<[in] ConfigContext object
		,      const char *name)	///<[in] Name to get the NetAddr value of
{
	gpointer	addr;
	if (NULL == self->_addrvalues) {
		return NULL;
	}
	addr = g_hash_table_lookup(self->_addrvalues, name);
	return addr == NULL ? NULL : CASTTOCLASS(NetAddr, addr);
}

/// Set the NetAddr value of a name
FSTATIC void
_configcontext_setaddr(ConfigContext* self	///<[in/out] ConfigContext object
		,      const char * name	///<[in] Name to set to 'addr' (we copy it)
		,      NetAddr* addr)		///<[in/out] Address to set it to (we hold a ref to it)
{
	char *	cpname;
	g_return_if_fail(addr != NULL);
	cpname = g_strdup(name);
	addr->baseclass.ref(addr);
	if (NULL == self->_addrvalues) {
		self->_addrvalues = g_hash_table_new_full(g_str_hash, g_str_equal
		,	_configcontext_free, _configcontext_freeNetAddr);
	}
	g_hash_table_insert(self->_addrvalues, cpname, addr);
}

/// Return the @ref Frame value of a name
FSTATIC Frame*
_configcontext_getframe(ConfigContext* self	///<[in] ConfigContext object
		,       const char *name)	///<[in] Name to retrieve the @ref Frame value of
{
	gpointer	frame;
	if (NULL == self->_framevalues) {
		return NULL;
	}
	frame = g_hash_table_lookup(self->_framevalues, name);
	return frame == NULL ? NULL : CASTTOCLASS(Frame, frame);
}

/// Set the signature frame to the given SignFrame
FSTATIC void
_configcontext_setframe(ConfigContext* self	///<[in/out] ConfigContext object
		,	const char * name	///<[in] name to set value of (we copy it)
		,	Frame* frame)		///<[in/out] @ref Frame value to set 'name' to
						/// (we hold a ref to it)
{
	char *	cpname;
	g_return_if_fail(frame != NULL);
	cpname = g_strdup(name);
	frame->baseclass.ref(frame);
	if (NULL == self->_addrvalues) {
		self->_framevalues = g_hash_table_new_full(g_str_hash, g_str_equal
		,	_configcontext_free, _configcontext_freeFrame);
	}
	g_hash_table_insert(self->_framevalues, cpname, frame);
}

/// Free a malloced object (likely a string)
FSTATIC void
_configcontext_free(gpointer thing)	///<[in/out] Thing being freed
{
	FREE(thing);
}

/// Free a Frame object
FSTATIC void
_configcontext_freeFrame(gpointer thing) ///<[in/out] @ref Frame being freed
{
	Frame*	f = CASTTOCLASS(Frame, thing);
	f->baseclass.unref(f);
}

/// Free a NetAddr object
FSTATIC void
_configcontext_freeNetAddr(gpointer thing) ///<[in/out] @ref NetAddr being freed
{
	NetAddr* a = CASTTOCLASS(NetAddr, thing);
	a->baseclass.unref(a);
}

/// Finalize (free) ConfigContext object
FSTATIC void
_configcontext_finalize(AssimObj* oself)	///<[in/out] ConfigContext object being freed
{
	ConfigContext * self = CASTTOCLASS(ConfigContext, oself);
	if (self->_intvalues) {
		g_hash_table_destroy(self->_intvalues); self->_intvalues = NULL;
	}
	if (self->_strvalues) {
		g_hash_table_destroy(self->_strvalues); self->_strvalues = NULL;
	}
	if (self->_framevalues) {
		g_hash_table_destroy(self->_framevalues); self->_framevalues = NULL;
	}
	if (self->_addrvalues) {
		g_hash_table_destroy(self->_addrvalues); self->_addrvalues = NULL;
	}
	memset(self, 0x00, sizeof(*self));
	FREECLASSOBJ(self); self = NULL;
}
///@}
