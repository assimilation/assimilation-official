// vim: smartindent number
/**
 * @file
 * @brief Implements the @ref ConfigContext class.
 * @details This file provides a place to remember and pass configuration values around.
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
#include <configcontext.h>
#include <memory.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#define BROKEN_G_SLIST_FREE_FULL	1
#undef BROKEN_G_SLIST_FREE_FULL

#ifdef	BROKEN_G_SLIST_FREE_FULL
#	undef g_slist_free_full	
#	define g_slist_free_full	assim_slist_free_full
#endif

FSTATIC void	_configcontext_finalize(AssimObj* self);
FSTATIC enum ConfigValType	_configcontext_gettype(const ConfigContext*, const char *name);
FSTATIC ConfigValue*	_configcontext_getvalue(const ConfigContext*, const char *name);
FSTATIC GSList*	_configcontext_keys(const ConfigContext*);
FSTATIC guint	_configcontext_keycount(const ConfigContext*);
FSTATIC void	_configcontext_delkey(const ConfigContext*, const char *);
FSTATIC gint64	_configcontext_getint(const ConfigContext*, const char *name);
FSTATIC void	_configcontext_setint(ConfigContext*, const char *name, gint value);
FSTATIC gboolean _configcontext_appendint(ConfigContext*, const char *name, gint value);
FSTATIC double	_configcontext_getdouble(const ConfigContext*, const char *name);
FSTATIC void	_configcontext_setdouble(ConfigContext*, const char *name, double value);
FSTATIC gboolean _configcontext_appenddouble(ConfigContext*, const char *name, double value);
FSTATIC gboolean _configcontext_getbool(const ConfigContext*, const char *name);
FSTATIC void	_configcontext_setbool(ConfigContext*, const char *name, gboolean value);
FSTATIC gboolean _configcontext_appendbool(ConfigContext*, const char *name, gboolean value);
FSTATIC const char* _configcontext_getstring(const ConfigContext*, const char *name);
FSTATIC void	_configcontext_setstring(ConfigContext*, const char *name, const char *value);
FSTATIC gboolean _configcontext_appendstring(ConfigContext*, const char *name, const char *value);
FSTATIC GSList*	_configcontext_getarray(const ConfigContext*, const char *name);
FSTATIC void	_configcontext_setarray(ConfigContext*, const char *name, GSList*value);
FSTATIC NetAddr*_configcontext_getaddr(const ConfigContext*, const char *);
FSTATIC void	_configcontext_setaddr(ConfigContext*, const char *name, NetAddr*);
FSTATIC gboolean _configcontext_appendaddr(ConfigContext* self, const char * name, NetAddr* value);
FSTATIC Frame*	_configcontext_getframe(const ConfigContext*, const char *name);
FSTATIC void	_configcontext_setframe(ConfigContext*, const char *name, Frame*);
FSTATIC ConfigContext*
		_configcontext_getconfig(const ConfigContext*, const char*);
FSTATIC char*	_configcontext_getstr(const ConfigContext*, const char*);
FSTATIC gboolean _configcontext_appendconfig(ConfigContext*,const char *,ConfigContext*);
FSTATIC void	_configcontext_setconfig(ConfigContext*,const char *,ConfigContext*);
FSTATIC gint	_configcontext_key_compare(gconstpointer a, gconstpointer b);



FSTATIC char *	_configcontext_toString(gconstpointer aself);
FSTATIC char *	JSONquotestring(char * s);
FSTATIC ConfigContext*	_configcontext_JSON_parse_string(const char * json);
FSTATIC GScanner*	_configcontext_JSON_GScanner_new(void);
FSTATIC ConfigContext*	_configcontext_JSON_parse_objandEOF(GScanner* scan);
FSTATIC ConfigContext*	_configcontext_JSON_parse_object(GScanner* scan);
FSTATIC ConfigContext*	_configcontext_JSON_parse_members(GScanner* scan, ConfigContext* cfg);
FSTATIC ConfigContext*	_configcontext_JSON_parse_pair(GScanner* scan, ConfigContext* cfg);
FSTATIC ConfigValue*	_configcontext_JSON_parse_value(GScanner* scan);
FSTATIC gboolean	_configcontext_JSON_parse_array(GScanner* scan, GSList** retval);
FSTATIC ConfigValue* _configcontext_value_new(enum ConfigValType);
FSTATIC void _configcontext_value_vfinalize(gpointer vself);
FSTATIC void _configcontext_value_finalize(AssimObj* aself);
FSTATIC void _key_free(gpointer vself);
FSTATIC void _configcontext_JSON_errmsg(GScanner*, gchar*, gboolean);

#ifdef BROKEN_G_SLIST_FREE_FULL
void assim_slist_free_full(GSList* list, void (*)(gpointer));
#endif

/**
 * @defgroup ConfigContext ConfigContext class
 * A base class for remembering configuration values of various types in a hash table
 * with capabilities to go to and from JSON.
 * @{
 * @ingroup C_Classes
 * @ingroup AssimObj
 */

#ifdef BROKEN_G_SLIST_FREE_FULL
void
assim_slist_free_full(GSList* list, void (*datafree)(gpointer))
{
	GSList*	this = NULL;
	GSList*	next = NULL;
	//fprintf(stderr, "Freeing GSList at %p\n", list);

	for (this=list; this; this=next) {
		next=this->next;
		//fprintf(stderr, "........Freeing GSList data at %p\n", this->data);
		if (this->data) {
			datafree(this->data);
		}else{
			fprintf(stderr, "........NO GSList data (NULL) at %p\n"
			,	this->data);
		}
		//fprintf(stderr, "........Freeing GSList element at %p\n", this);
		memset(this, 0, sizeof(*this));
		g_slist_free_1(this);
	}
}
#endif

FSTATIC void
_key_free(gpointer vself)
{
	//g_message("Freeing key pointer at %p\n", vself);
	g_free(vself);
}


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
	newcontext = NEWSUBCLASS(ConfigContext, baseobj);
	newcontext->getint	=	_configcontext_getint;
	newcontext->setdouble	=	_configcontext_setdouble;
	newcontext->getdouble	=	_configcontext_getdouble;
	newcontext->setint	=	_configcontext_setint;
	newcontext->appendint	=	_configcontext_appendint;
	newcontext->getbool	=	_configcontext_getbool;
	newcontext->setbool	=	_configcontext_setbool;
	newcontext->appendbool	=	_configcontext_appendbool;
	newcontext->getstring	=	_configcontext_getstring;
	newcontext->setstring	=	_configcontext_setstring;
	newcontext->appendstring =	_configcontext_appendstring;
	newcontext->getframe	=	_configcontext_getframe;
	newcontext->setframe	=	_configcontext_setframe;
	newcontext->getaddr	=	_configcontext_getaddr;
	newcontext->setaddr	=	_configcontext_setaddr;
	newcontext->appendaddr	=	_configcontext_appendaddr;
	newcontext->getconfig	=	_configcontext_getconfig;
	newcontext->setconfig	=	_configcontext_setconfig;
	newcontext->appendconfig =	_configcontext_appendconfig;
	newcontext->getarray	=	_configcontext_getarray;
	newcontext->setarray	=	_configcontext_setarray;
	newcontext->gettype	=	_configcontext_gettype;
	newcontext->getvalue	=	_configcontext_getvalue;
	newcontext->keys	=	_configcontext_keys;
	newcontext->keycount	=	_configcontext_keycount;
	newcontext->delkey	=	_configcontext_delkey;
	newcontext->_values	=	g_hash_table_new_full(g_str_hash, g_str_equal, _key_free
					,		      _configcontext_value_vfinalize);
	baseobj->_finalize	=	_configcontext_finalize;
	baseobj->toString	=	_configcontext_toString;
	return newcontext;
}

/// Finalize (free) a ConfigContext object
FSTATIC void
_configcontext_finalize(AssimObj* aself)
{
	ConfigContext*	self = CASTTOCLASS(ConfigContext, aself);
#if 0
	{
		char *	s = self->baseclass.toString(&self->baseclass);
		g_warning("%s.%d: Finalizing %p: %s", __FUNCTION__, __LINE__, aself, s);
		g_free(s); s = NULL;
	}
#endif
	
	if (self->_values) {
		g_hash_table_destroy(self->_values);
		self->_values = NULL;
	}
	FREECLASSOBJ(self);
}

/// Compare two string keys (for GSList sorting)
FSTATIC gint
_configcontext_key_compare(gconstpointer a, gconstpointer b)
{
	return strcmp((const char *)a, (const char*)b);
}

/// Delete the key with the given value
FSTATIC void
_configcontext_delkey(const ConfigContext* cfg, const char * key)
{
	g_hash_table_remove(cfg->_values, key);
}
/// Return the number of keys in a ConfigContext object
FSTATIC guint
_configcontext_keycount(const ConfigContext* cfg)
{
	GHashTableIter	iter;
	gpointer	key;
	gpointer	data;
	guint		ret = 0;

	g_hash_table_iter_init(&iter, cfg->_values);
	while (g_hash_table_iter_next(&iter, &key, &data)) {
		++ret;
	}
	return ret;
}

/// Return a GSList of all the keys in a ConfigContext object
FSTATIC GSList*
_configcontext_keys(const ConfigContext* cfg)
{
	GSList*		keylist = NULL;
	GHashTableIter	iter;
	gpointer	key;
	gpointer	data;

	if (!cfg->_values) {
		return NULL;
	}

	g_hash_table_iter_init(&iter, cfg->_values);
	while (g_hash_table_iter_next(&iter, &key, &data)) {
		keylist = g_slist_prepend(keylist, key);
	}
	keylist= g_slist_sort(keylist, _configcontext_key_compare);
	return keylist;
}


/// Return a the type of value associated with a given name
FSTATIC enum ConfigValType
_configcontext_gettype(const ConfigContext* self, const char *name)
{
	ConfigValue*	cfg = self->getvalue(self, name);
	if (cfg == NULL) {
		return CFG_EEXIST;
	}
	return cfg->valtype;
}

/// Return a the value structure associated with a given name
FSTATIC ConfigValue*
_configcontext_getvalue(const ConfigContext* self, const char *name)
{
	gpointer	ret = g_hash_table_lookup(self->_values, name);
	if (ret != NULL) {
		return CASTTOCLASS(ConfigValue, ret);
	}
	return NULL;
}

/// Get an integer value
FSTATIC gint64
_configcontext_getint(const ConfigContext* self	///<[in] ConfigContext object
	,	      const char *name)		///<[in] Name to get the associated int value of
{
	gpointer	ret = g_hash_table_lookup(self->_values, name);
	ConfigValue*	cfg;

	if (ret == NULL) {
		return -1;
	}
	cfg = CASTTOCLASS(ConfigValue, ret);
	if (cfg->valtype != CFG_INT64) {
		return -1;
	}

	return cfg->u.intvalue;
}

/// Set a name to an integer value
FSTATIC void
_configcontext_setint(ConfigContext* self	///<[in/out] ConfigContext Object
	,	      const char *name		///<[in] Name to set the associated int value of
	,	      gint value)		///<[in] Int value to set the 'name' to
{
	ConfigValue* val = _configcontext_value_new(CFG_INT64);
	char *	cpname = g_strdup(name);

	val->u.intvalue = value;
	g_hash_table_replace(self->_values, cpname, val);
}
FSTATIC gboolean
_configcontext_appendint(ConfigContext*self, const char *name, gint value)
{
	ConfigValue* array = self->getvalue(self, name);
	ConfigValue* appendvalue;
	g_return_val_if_fail(array != NULL && array->valtype == CFG_ARRAY, FALSE);
	appendvalue = _configcontext_value_new(CFG_INT64);
	appendvalue->u.intvalue = value;
	array->u.arrayvalue = g_slist_append(array->u.arrayvalue, appendvalue);
	return TRUE;
}
FSTATIC double
_configcontext_getdouble(const ConfigContext*self, const char *name)
{
	ConfigValue* doubleval = self->getvalue(self, name);
	// @TODO: Ought to return NaN (Not a Number) instead of -G_MAXDOUBLE on failure...
	g_return_val_if_fail(doubleval != NULL && doubleval->valtype == CFG_FLOAT, -G_MAXDOUBLE);
	return doubleval->u.floatvalue;
}
FSTATIC void
_configcontext_setdouble(ConfigContext*self, const char *name, double value)
{
	ConfigValue* doubleval = _configcontext_value_new(CFG_FLOAT);
	doubleval->u.floatvalue = value;
	g_hash_table_replace(self->_values, g_strdup(name), doubleval);
}
FSTATIC gboolean
_configcontext_appenddouble(ConfigContext*self, const char *name, double value)
{
	ConfigValue* array = self->getvalue(self, name);
	ConfigValue* appendvalue;
	g_return_val_if_fail(array != NULL && array->valtype == CFG_ARRAY, FALSE);
	appendvalue = _configcontext_value_new(CFG_FLOAT);
	appendvalue->u.floatvalue = value;
	array->u.arrayvalue = g_slist_append(array->u.arrayvalue, appendvalue);
	return TRUE;
}

/// Get an boolean value
FSTATIC gboolean
_configcontext_getbool(const ConfigContext* self	///<[in] ConfigContext object
	,	      const char *name)		///<[in] Name to get the associated int value of
{
	gpointer	ret = g_hash_table_lookup(self->_values, name);
	ConfigValue*	cfg;

	if (ret == NULL) {
		return -1;
	}
	cfg = CASTTOCLASS(ConfigValue, ret);
	if (cfg->valtype != CFG_BOOL) {
		return -1;
	}

	return (gboolean)cfg->u.intvalue;
}

/// Set a name to an integer value
FSTATIC void
_configcontext_setbool(ConfigContext* self	///<[in/out] ConfigContext Object
	,	      const char *name		///<[in] Name to set the associated int value of
	,	      gint value)		///<[in] Int value to set the 'name' to
{
	ConfigValue* val = _configcontext_value_new(CFG_BOOL);
	char *	cpname = g_strdup(name);

	val->u.intvalue = value;
	g_hash_table_replace(self->_values, cpname, val);
}

FSTATIC gboolean
_configcontext_appendbool(ConfigContext* self, const char *name, gboolean value)
{
	ConfigValue* array = self->getvalue(self, name);
	ConfigValue* appendvalue;
	g_return_val_if_fail(array != NULL && array->valtype == CFG_ARRAY, FALSE);
	appendvalue = _configcontext_value_new(CFG_BOOL);
	appendvalue->u.intvalue = value;
	array->u.arrayvalue = g_slist_append(array->u.arrayvalue, appendvalue);
	return TRUE;
}

/// Return the value of a string name
FSTATIC const char*
_configcontext_getstring(const ConfigContext* self	///<[in] ConfigContext object
		,	 const char *name)	///<[in] Name to get the associated string value of
{
	gpointer	ret = g_hash_table_lookup(self->_values, name);
	ConfigValue*	cfg;

	if (ret == NULL) {
		return NULL;
	}
	cfg = CASTTOCLASS(ConfigValue, ret);
	if (cfg->valtype != CFG_STRING) {
		return NULL;
	}
	return cfg->u.strvalue;
}

/// Set a name to a string value
FSTATIC void
_configcontext_setstring(ConfigContext* self	///<[in/out] ConfigContext object
			,const char *name	///<[in] Name to set the string value of (we copy it)
			,const char *value)	///<[in] Value to set 'name' to (we copy it)
{
	ConfigValue* val = _configcontext_value_new(CFG_STRING);

	val->u.strvalue = g_strdup(value);
	g_hash_table_replace(self->_values, g_strdup(name), val);
}

FSTATIC gboolean
_configcontext_appendstring(ConfigContext* self, const char *name, const char *value)
{
	ConfigValue* array = self->getvalue(self, name);
	ConfigValue* appendvalue;
	g_return_val_if_fail(array != NULL && array->valtype == CFG_ARRAY, FALSE);
	appendvalue = _configcontext_value_new(CFG_STRING);
	appendvalue->u.strvalue = g_strdup(value);
	array->u.arrayvalue = g_slist_append(array->u.arrayvalue, appendvalue);
	return TRUE;
}

FSTATIC GSList*
_configcontext_getarray(const ConfigContext* self, const char *name)
{
	gpointer	ret = g_hash_table_lookup(self->_values, name);
	ConfigValue*	cfg;

	if (ret == NULL) {
		return NULL;
	}
	cfg = CASTTOCLASS(ConfigValue, ret);
	if (cfg->valtype != CFG_ARRAY) {
		g_warning("getarray called on object of type %d", cfg->valtype);
		return NULL;
	}
	//g_warning("getarray[%s] on %s gives %p", name, self->baseclass.toString(self), cfg->u.arrayvalue);
	return cfg->u.arrayvalue;
}
FSTATIC void
_configcontext_setarray(ConfigContext*self, const char *name, GSList*value)
{
	char *	cpname = g_strdup(name);
	ConfigValue* val = _configcontext_value_new(CFG_ARRAY);
	val->u.arrayvalue = value;

	/// @todo WHAT ABOUT OBJECT LIFE??
	g_hash_table_replace(self->_values, cpname, val);
}

/// Return the NetAddr value of a name
FSTATIC  NetAddr*
_configcontext_getaddr(const ConfigContext* self	///<[in] ConfigContext object
		,      const char *name)	///<[in] Name to get the NetAddr value of
{
	gpointer	ret = g_hash_table_lookup(self->_values, name);
	ConfigValue*	cfg;

	if (ret == NULL) {
		return NULL;
	}
	cfg = CASTTOCLASS(ConfigValue, ret);
	if (cfg->valtype != CFG_NETADDR) {
		return NULL;
	}
	return cfg->u.addrvalue;
}

/// Set the NetAddr value of a name
FSTATIC void
_configcontext_setaddr(ConfigContext* self	///<[in/out] ConfigContext object
		,      const char * name	///<[in] Name to set to 'addr' (we copy it)
		,      NetAddr* addr)		///<[in/out] Address to set it to (we hold a ref to it)
{
	char *	cpname = g_strdup(name);
	ConfigValue* val = _configcontext_value_new(CFG_NETADDR);

	REF(addr);
	val->u.addrvalue = addr;
	g_hash_table_replace(self->_values, cpname, val);
}

FSTATIC gboolean
_configcontext_appendaddr(ConfigContext* self, const char * name, NetAddr* value)
{
	ConfigValue* array = self->getvalue(self, name);
	ConfigValue* appendvalue;
	g_return_val_if_fail(array != NULL && array->valtype == CFG_ARRAY, FALSE);
	appendvalue = _configcontext_value_new(CFG_NETADDR);
	REF(value);
	appendvalue->u.addrvalue = value;
	array->u.arrayvalue = g_slist_append(array->u.arrayvalue, appendvalue);
	return TRUE;
}

/// Return the @ref Frame value of a name
FSTATIC Frame*
_configcontext_getframe(const ConfigContext* self	///<[in] ConfigContext object
		,       const char *name)	///<[in] Name to retrieve the @ref Frame value of
{
	gpointer	ret = g_hash_table_lookup(self->_values, name);
	ConfigValue*	cfg;

	if (ret == NULL) {
		return NULL;
	}
	cfg = CASTTOCLASS(ConfigValue, ret);
	if (cfg->valtype != CFG_FRAME) {
		return NULL;
	}
	return cfg->u.framevalue;
}

/// Set the signature frame to the given SignFrame
FSTATIC void
_configcontext_setframe(ConfigContext* self	///<[in/out] ConfigContext object
		,	const char * name	///<[in] name to set value of (we copy it)
		,	Frame* frame)		///<[in/out] @ref Frame value to set 'name' to
						/// (we hold a ref to it)
{
	char *	cpname = g_strdup(name);
	ConfigValue* val = _configcontext_value_new(CFG_FRAME);

	REF(frame);
	val->u.framevalue = frame;
	g_hash_table_replace(self->_values, cpname, val);
}

/// Return a the a ConfigContext value associated with a given name
FSTATIC ConfigContext*
_configcontext_getconfig(const ConfigContext* self , const char* name)
{
	gpointer	ret = g_hash_table_lookup(self->_values, name);
	ConfigValue*	cfg;

	if (ret == NULL) {
		return NULL;
	}
	cfg = CASTTOCLASS(ConfigValue, ret);
	if (cfg->valtype != CFG_CFGCTX) {
		return NULL;
	}
	return cfg->u.cfgctxvalue;
}
/// Save/Set a ConfigContext value associated with a given name
FSTATIC void
_configcontext_setconfig(ConfigContext* self,const char *name, ConfigContext* value)
{
	char *	cpname = g_strdup(name);
	ConfigValue* val = _configcontext_value_new(CFG_CFGCTX);

	REF(value);
	val->u.cfgctxvalue = value;
	g_hash_table_replace(self->_values, cpname, val);
}
FSTATIC gboolean
_configcontext_appendconfig(ConfigContext* self, const char * name,ConfigContext* value)
{
	ConfigValue* array = self->getvalue(self, name);
	ConfigValue* appendvalue;
	g_return_val_if_fail(array != NULL && array->valtype == CFG_ARRAY, FALSE);
	appendvalue = _configcontext_value_new(CFG_CFGCTX);
	REF(value);
	appendvalue->u.cfgctxvalue = value;
	array->u.arrayvalue = g_slist_append(array->u.arrayvalue, appendvalue);
	return TRUE;
}

/// Return a string value (toString) associated with a given name
FSTATIC char*
_configcontext_getstr(const ConfigContext* self , const char* name)
{
	ConfigValue* cfval =  self->getvalue(self, name);
	if (cfval == NULL) {
		return NULL;
	}
	return configcontext_elem_toString(cfval);
}

/// Create a ConfigValue object (containing an object and its type)
FSTATIC ConfigValue*
_configcontext_value_new(enum ConfigValType t)
{
	AssimObj*	aret;
	ConfigValue*	ret;

	aret = assimobj_new(sizeof(ConfigValue));
	ret = NEWSUBCLASS(ConfigValue, aret);
	ret->valtype = t;
	memset(&ret->u, 0, sizeof(ret->u));
	aret->_finalize = _configcontext_value_finalize;
	return ret;
}

/// Finalize (free) a ConfigValue object
FSTATIC void
_configcontext_value_vfinalize(void* vself)
{
	ConfigValue*	self;
	//fprintf(stderr, "configcontext_value_vfinalize(%p)\n", vself);
	self = CASTTOCLASS(ConfigValue, vself);
	UNREF(self);
	vself = NULL;
}
FSTATIC void
_configcontext_value_finalize(AssimObj* aself)
{
	ConfigValue*	self;

	//fprintf(stderr, "configcontext_value_finalize(%p)\n", aself);
	self = CASTTOCLASS(ConfigValue, aself);
	//fprintf(stderr, "configcontext_value_finalize(%p): %d\n"
	//,	aself, self->valtype);
	switch (self->valtype) {
		case CFG_STRING:
			g_free(self->u.strvalue); self->u.strvalue = NULL;
			break;
		case CFG_CFGCTX: {
			UNREF(self->u.cfgctxvalue);
			break;
		}
		case CFG_NETADDR: {
			UNREF(self->u.addrvalue);
			break;
		}
		case CFG_FRAME: {
			UNREF(self->u.framevalue);
			break;
		}
		case CFG_ARRAY: {
			GSList*	list = self->u.arrayvalue;
			g_slist_free_full(list, _configcontext_value_vfinalize);
			self->u.arrayvalue = NULL;
			break;
		}

		default: {
			// Do nothing
			break;
		}
	}
	self->valtype = CFG_EEXIST;
	memset(self, 0, sizeof(*self));
	FREECLASSOBJ(self);
	self = NULL;
	aself = NULL;
}


#define	JSONREPLACES		"\\\"\b\f\n\r\t"
#define	JSONREPLACEMENTS	"\\\"bfnrt"
/// Escape characters in a string according to JSON conventions...
FSTATIC char *
JSONquotestring(char * s)
{
	GString*	ret;
	char *		str;
	const char *	replacechars = JSONREPLACES;
	ret = g_string_sized_new(strlen(s)+5);
	g_string_append_c(ret, '"');
	
	
	for (str=s; *str; ++str ) {
		const char *	found;
		if (NULL != (found=strchr(replacechars, *str ))) {
			size_t offset = found-replacechars;
			g_string_append_c(ret, '\\');
			g_string_append_c(ret, JSONREPLACEMENTS[offset]);
		}else{
			g_string_append_c(ret, *str);
		}
	}
	g_string_append_c(ret, '"');
	return g_string_free(ret, FALSE);
}

/// Convert a ConfigContext to a printable string (in JSON notation)
FSTATIC char *
_configcontext_toString(gconstpointer aself)
{
	const ConfigContext*	self = CASTTOCONSTCLASS(ConfigContext, aself);

	GString*	gsret = g_string_new("{");
	GSList*		keyelem;
	GSList*		nextkeyelem;
	const char *	comma = "";
	
	if (!self->_values) {
		return NULL;
	}
	for (keyelem = self->keys(self); keyelem; keyelem = nextkeyelem) {
		char *		thiskey = keyelem->data;
		ConfigValue*	val = self->getvalue(self, thiskey);
		gchar*		elem = configcontext_elem_toString(val);
		g_string_append_printf(gsret, "%s\"%s\":%s", comma, thiskey, elem);
		g_free(elem);
		comma=",";
		nextkeyelem = keyelem->next;
		g_slist_free1(keyelem);
		keyelem = NULL;
	}
	g_string_append(gsret, "}");
	return g_string_free(gsret, FALSE);
}
/// Convert a ConfigContext element (ConfigValue) to a String
WINEXPORT char *
configcontext_elem_toString(ConfigValue* val)
{
	switch (val->valtype) {
		case CFG_BOOL:
			return g_strdup(val->u.intvalue? "true" : "false");

		case CFG_INT64:
			return g_strdup_printf(FMT_64BIT"d", val->u.intvalue);

		case CFG_FLOAT:
			return g_strdup_printf("%g", val->u.floatvalue);

		case CFG_STRING: {
			//g_message("Got string pointer: %p", val->u.strvalue);
			//g_message("Got string: %s", val->u.strvalue);
			return JSONquotestring(val->u.strvalue);
		}

		case CFG_CFGCTX: {
			return val->u.cfgctxvalue->baseclass.toString(val->u.cfgctxvalue);
		}
		case CFG_ARRAY: {
			const char *	acomma = "";
			GString*	ret = g_string_new("[");
			GSList*		this;

			for (this = val->u.arrayvalue; this; this = this->next) {
				ConfigValue*	val = CASTTOCLASS(ConfigValue, this->data);
				gchar*	elem = configcontext_elem_toString(val);
				g_string_append_printf(ret, "%s%s", acomma, elem);
				g_free(elem);
				acomma=",";
			}
			g_string_append(ret, "]");
			return g_string_free(ret, FALSE);
		}
		case CFG_NETADDR: {	/// @todo - make NetAddrs into things that we
					/// can recognize and make back into a NetAddr
					/// when we parse the JSON.
			AssimObj*	obj = CASTTOCLASS(AssimObj, val->u.addrvalue);
			char*		tostring = obj->toString(obj);
			gchar*		retstr = JSONquotestring(tostring);
			g_free(tostring); tostring = NULL;
			return retstr;
		}
		case CFG_FRAME: {
			AssimObj*	obj = CASTTOCLASS(AssimObj, val->u.framevalue);
			char*		tostring = obj->toString(obj);
			gchar*		retstr = JSONquotestring(tostring);

			FREE(tostring); tostring=NULL;
			return retstr;
		}
		case CFG_EEXIST:
		case CFG_NULL:
			return g_strdup("null");

	}//endswitch
	/*NOTREACHED*/
	return g_strdup("null");
}
///
///	Output a scanning error message for our JSON parsing
FSTATIC void
_configcontext_JSON_errmsg(GScanner* _unused_scanner, gchar*message, gboolean _unused_isError)
{
	(void)_unused_scanner;
	(void)_unused_isError;
	g_warning("%s.%d: JSON syntax error: %s", __FUNCTION__, __LINE__, message);
}

///
///	Create a GScanner object that is set up to scan JSON text.
///	See <a href="http://www.json.org/">JSON web site</a> for details
///	on JSON syntax.
FSTATIC GScanner*
_configcontext_JSON_GScanner_new(void)
{
	static GScannerConfig	config;
	GScanner*		retval;
	// Legal JSON keywords are true, false, and null
	// There are no 'identifiers' as such.
	static char		firstchars[] = "tfn";
	static char		subsequentchars[] = "aelrsu";
	static char		whitespace[] = " \t\n\r\f";
	static char		hash_comment[] = "#\n";
	static char		True[] = "true";
	static char		False[] = "false";
	static char		Null[] = "null";
	memset(&config, 0, sizeof(config));

	// For more info on what these settings do, see
	// http://developer.gnome.org/glib/2.32/glib-Lexical-Scanner.html

	config.cset_skip_characters = whitespace;
	config.cset_identifier_first = firstchars;
	config.cset_identifier_nth = subsequentchars;
	config.case_sensitive = TRUE;
	config.skip_comment_multi = FALSE;
	config.scan_comment_multi = FALSE;
	config.cpair_comment_single = hash_comment;	// NOTE: JSON extension: Allow # comments 
	config.skip_comment_single = TRUE;		// Ignore # comments
	config.scan_identifier = TRUE;
	config.scan_identifier_1char = FALSE;
	config.scan_identifier_NULL = FALSE;
	config.scan_symbols = TRUE; // ???
	config.scan_binary = FALSE;
	config.scan_octal = FALSE;
	config.scan_float = TRUE;
	config.scan_hex = FALSE;
	config.scan_hex_dollar = FALSE;
	config.scan_string_sq = FALSE;
	config.scan_string_dq = TRUE;
	config.numbers_2_int = TRUE;
	config.int_2_float = FALSE;
	config.identifier_2_string = FALSE;
	config.char_2_token = TRUE;
	config.symbol_2_token = FALSE; // ???
	config.scope_0_fallback = TRUE;
	config.store_int64 = TRUE;

	retval =  g_scanner_new(&config);
	if (retval) {
		g_scanner_scope_add_symbol(retval, 0, True, True);
		g_scanner_scope_add_symbol(retval, 0, False, False);
		g_scanner_scope_add_symbol(retval, 0, Null, Null);
		retval->msg_handler = _configcontext_JSON_errmsg;
	}
	return retval;
}

#define TOKEN_COLON	':'
#define	GULP	(void)g_scanner_get_next_token(scan)

#define SYNERROR(scan, token, symbol, msg)	\
		{g_warning("%s.%d: JSON syntax error.", __FUNCTION__, __LINE__);g_scanner_unexp_token(scan, token, "keyword", "keyword", symbol, msg, TRUE);}

/// Construct a ConfigContext object from the given JSON string
ConfigContext*
configcontext_new_JSON_string(const char * jsontext)
{
	GScanner*	scanner = _configcontext_JSON_GScanner_new();
	ConfigContext*	ret;

	g_scanner_input_text(scanner, jsontext, strlen(jsontext));
	ret = _configcontext_JSON_parse_objandEOF(scanner);
	g_scanner_destroy(scanner);
	return ret;
}

/// Parse complete JSON object followed by EOF
FSTATIC ConfigContext*
_configcontext_JSON_parse_objandEOF(GScanner* scan)
{
	ConfigContext * ret = _configcontext_JSON_parse_object(scan);

	if (ret != NULL && g_scanner_get_next_token(scan) != G_TOKEN_EOF) {
		SYNERROR(scan, G_TOKEN_EOF, NULL, NULL);
		UNREF(ret);
	}
	return ret;
}

/// Parse a JSON object
FSTATIC ConfigContext*
_configcontext_JSON_parse_object(GScanner* scan)
{
	ConfigContext*	ret;
	ConfigContext*	membersret;
	if (g_scanner_peek_next_token(scan) != G_TOKEN_LEFT_CURLY) {
		GULP;
		SYNERROR(scan, G_TOKEN_LEFT_CURLY, NULL, NULL);
		return NULL;
	}
	GULP;	// Swallow '{'
	ret = configcontext_new(0);
	if (g_scanner_peek_next_token(scan) == G_TOKEN_RIGHT_CURLY) {
		// Empty 'object' - which is just fine...
		GULP;
		return ret;
	}
	
	membersret = _configcontext_JSON_parse_members(scan, ret);
	if (membersret == NULL) {
		UNREF(ret);
		return NULL;
	}

	if (g_scanner_get_next_token(scan) != G_TOKEN_RIGHT_CURLY) {
		// Syntax error...
		SYNERROR(scan, G_TOKEN_RIGHT_CURLY, NULL, NULL);
		UNREF(ret);
		return NULL;
	}
	return ret;
}
/// Parse a JSON (object) members (a list of "name" : "value" pairs)
FSTATIC ConfigContext*
_configcontext_JSON_parse_members(GScanner* scan, ConfigContext* cfg)
{
	while (g_scanner_peek_next_token(scan) == G_TOKEN_STRING) {
		_configcontext_JSON_parse_pair(scan, cfg);
		if (g_scanner_peek_next_token(scan) == G_TOKEN_COMMA) {
			GULP;
		}else{
			break;
		}
	}
	return cfg;
}

// Parse a JSON "name": value pair
FSTATIC ConfigContext*
_configcontext_JSON_parse_pair(GScanner* scan, ConfigContext* cfg)
{
	char *		name = NULL;
	ConfigValue*	value;
	// "name" : _value_	pairs
	//
	// Name is always a string -
	// Value can be any of:
	//	string
	//	number
	//	object
	//	array
	//	true (a symbol)
	//	false (a symbol)
	//	null (a symbol)
	if (g_scanner_peek_next_token(scan) != G_TOKEN_STRING) {
		return NULL;
	}
	GULP;
	// Get value of G_TOKEN_STRING
	name = g_strdup(scan->value.v_string);
	if (g_scanner_peek_next_token(scan) != TOKEN_COLON) {
		SYNERROR(scan, TOKEN_COLON, NULL, NULL);
		// Syntax error
		g_free(name); name = NULL;
		return NULL;
	}
	GULP;	// Swallow TOKEN_COLON
	if (g_scanner_peek_next_token(scan) == TOKEN_COLON) {
		return NULL;
	}
	// Next is a value...
	value = _configcontext_JSON_parse_value(scan);
	if (value == NULL) {
		// Syntax error - already noted by the lower layers...
		g_free(name); name = NULL;
		return NULL;
	}
	g_hash_table_replace(cfg->_values, name, value);
	return cfg;
}

FSTATIC ConfigValue*
_configcontext_JSON_parse_value(GScanner* scan)
{
	guint	toktype = g_scanner_peek_next_token(scan);
	switch(toktype) {
		case G_TOKEN_STRING:{		// String
			/// @todo recognize NetAddr objects encoded as strings and reconstitute them
			ConfigValue* val;
			NetAddr* encoded;
			GULP;
			// See if we can convert it to a NetAddr...
			/// FIXME: Need to make the conversion to a NetAddr optional...
			if ((encoded = netaddr_string_new(scan->value.v_string)) != NULL) {
				val = _configcontext_value_new(CFG_NETADDR);
				val->u.addrvalue = encoded;
                                encoded = NULL;
			}else{
				val = _configcontext_value_new(CFG_STRING);
				val->u.strvalue = g_strdup(scan->value.v_string);
			}
			return val;
		}

		case '-': {			// Minus sign (negative number)
			ConfigValue* val;
			GULP;	// Throw away the negative sign
			toktype = g_scanner_peek_next_token(scan);
			if (toktype == G_TOKEN_INT) {
				val = _configcontext_value_new(CFG_INT64);
				GULP;
				val->u.intvalue = -scan->value.v_int64;
				return val;
			}else if (toktype == G_TOKEN_FLOAT) {
				val = _configcontext_value_new(CFG_FLOAT);
				GULP;
				val->u.floatvalue = -scan->value.v_float;
				return val;
			}else{
				g_warning("Got token type %u after -", g_scanner_get_next_token(scan));
				SYNERROR(scan, G_TOKEN_NONE, NULL, "Unexpected symbol after -.");
				return NULL;
			}
			return val;
		}
		break;

		case G_TOKEN_INT: {		// Integer
			ConfigValue* val = _configcontext_value_new(CFG_INT64);
			GULP;
			val->u.intvalue = scan->value.v_int64;
			return val;
		}
		break;

		case G_TOKEN_FLOAT: {		// Double value
			ConfigValue* val = _configcontext_value_new(CFG_FLOAT);
			GULP;
			val->u.floatvalue = scan->value.v_float;
			return val;
		}
		break;
	
		case G_TOKEN_SYMBOL: {		// true, false, null
			GULP;
			if (strcmp(scan->value.v_string, "true") == 0 || strcmp(scan->value.v_string, "false") == 0) {
				ConfigValue* val = _configcontext_value_new(CFG_BOOL);
				val->u.intvalue = (strcmp(scan->value.v_string, "true") == 0);
				return val;
			}else if (strcmp(scan->value.v_string, "null") == 0) {
				return _configcontext_value_new(CFG_NULL);
			}else{
				SYNERROR(scan, G_TOKEN_NONE, NULL, "- expecting JSON value");
				// Syntax error
				return NULL;
			}
		}
		break;
	

		case G_TOKEN_LEFT_CURLY:{	// Object
			ConfigValue* val;
			ConfigContext*	child;
			child = _configcontext_JSON_parse_object(scan);
			if (child == NULL) {
				// Syntax error - detected by child object
				return NULL;
			}
			val = _configcontext_value_new(CFG_CFGCTX);
			val->u.cfgctxvalue = child;
			return val;
		}
		break;


		case G_TOKEN_LEFT_BRACE: {	// Array
			ConfigValue*	val;
			GSList*		child = NULL;
			if (!_configcontext_JSON_parse_array(scan, &child)) {
				// Syntax error - detected by child object
				return NULL;
			}
			val = _configcontext_value_new(CFG_ARRAY);
			val->u.arrayvalue = child;
			return val;
		}
		break;

		// Things we don't support...
		default:
			// Syntax error
			g_warning("Got token type %u", g_scanner_get_next_token(scan));
			//GULP;
			SYNERROR(scan, G_TOKEN_NONE, NULL, "Unexpected symbol.");
			return NULL;
	}
	/*NOTREACHED*/
	g_warning("Got token type %u", g_scanner_get_next_token(scan));
	SYNERROR(scan, G_TOKEN_NONE, NULL, "Unexpected symbol.");
	return NULL;
}
FSTATIC gboolean
_configcontext_JSON_parse_array(GScanner* scan, GSList** retval)
{
	*retval = NULL;
	if (g_scanner_peek_next_token(scan) != G_TOKEN_LEFT_BRACE) {
		GULP;
		SYNERROR(scan, G_TOKEN_LEFT_BRACE, NULL, NULL);
		// Syntax error
		return FALSE;
	}
	GULP; // Swallow left square bracket (G_TOKEN_LEFT_BRACE)
	while (g_scanner_peek_next_token(scan) != G_TOKEN_RIGHT_BRACE
	&&     !g_scanner_eof(scan)) {
		ConfigValue * value;

		// Parse the value
		value = _configcontext_JSON_parse_value(scan);
		if (value == NULL) {
			if (*retval != NULL) {
				g_slist_free_full(*retval, _configcontext_value_vfinalize);
				*retval = NULL;
				return FALSE;
			}
		}else{
			*retval = g_slist_append(*retval, value);
		}
		// Expect a comma
		if (g_scanner_peek_next_token(scan) == G_TOKEN_COMMA) {
			GULP;
		}else if (g_scanner_peek_next_token(scan) != G_TOKEN_RIGHT_BRACE) {
			SYNERROR(scan, G_TOKEN_RIGHT_BRACE, NULL, NULL);
			GULP;
			return FALSE;
		}
	}
	if (g_scanner_peek_next_token(scan) == G_TOKEN_RIGHT_BRACE) {
		GULP;
		return TRUE;
	}
	SYNERROR(scan, G_TOKEN_RIGHT_BRACE, NULL, NULL);
	return FALSE;
}
/// @}
