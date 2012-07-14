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
#include <stdlib.h>

FSTATIC void	_configcontext_ref(ConfigContext* self);
FSTATIC void	_configcontext_unref(ConfigContext* self);
FSTATIC void	_configcontext_finalize(AssimObj* self);
FSTATIC enum ConfigValType	_configcontext_gettype(ConfigContext*, const char *name);
FSTATIC GSList*	_configcontext_keys(ConfigContext*);
FSTATIC gint	_configcontext_getint(ConfigContext*, const char *name);
FSTATIC void	_configcontext_setint(ConfigContext*, const char *name, gint value);
FSTATIC gboolean _configcontext_getbool(ConfigContext*, const char *name);
FSTATIC void	_configcontext_setbool(ConfigContext*, const char *name, gboolean value);
FSTATIC const char* _configcontext_getstring(ConfigContext*, const char *name);
FSTATIC void	_configcontext_setstring(ConfigContext*, const char *name, const char *value);
FSTATIC NetAddr*_configcontext_getaddr(ConfigContext*, const char *);
FSTATIC void	_configcontext_setaddr(ConfigContext*, const char *name, NetAddr*);
FSTATIC Frame*	_configcontext_getframe(ConfigContext*, const char *name);
FSTATIC void	_configcontext_setframe(ConfigContext*, const char *name, Frame*);
FSTATIC ConfigContext*
		_configcontext_getconfig(ConfigContext*, const char*);
FSTATIC void	_configcontext_setconfig(ConfigContext*,const char *,ConfigContext*);
FSTATIC gint	_configcontext_key_compare(gconstpointer a, gconstpointer b);



FSTATIC char *	_configcontext_toString(gconstpointer aself);
FSTATIC char * _configcontext_elem_toString(ConfigValue* val);
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
FSTATIC void _configcontext_value_finalize(gpointer vself);
FSTATIC void _key_free(gpointer vself);

FSTATIC void
_key_free(gpointer vself)
{
	//g_message("Freeing pointer at %p", vself);
	g_free(vself);
}

/**
 * @defgroup ConfigContext ConfigContext class
 * A base class for remembering configuration values of various types.
 * @{
 * @ingroup C_Classes
 */

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
	newcontext->getbool	=	_configcontext_getbool;
	newcontext->setbool	=	_configcontext_setbool;
	newcontext->setstring	=	_configcontext_setstring;
	newcontext->getstring	=	_configcontext_getstring;
	newcontext->getframe	=	_configcontext_getframe;
	newcontext->setframe	=	_configcontext_setframe;
	newcontext->getaddr	=	_configcontext_getaddr;
	newcontext->setaddr	=	_configcontext_setaddr;
	newcontext->setconfig	=	_configcontext_setconfig;
	newcontext->getconfig	=	_configcontext_getconfig;
	newcontext->gettype	=	_configcontext_gettype;
	newcontext->keys	=	_configcontext_keys;
	newcontext->_values	=	g_hash_table_new_full(g_str_hash, g_str_equal, _key_free
					,		      _configcontext_value_finalize);
	baseobj->_finalize	=	_configcontext_finalize;
	baseobj->toString	=	_configcontext_toString;
	return newcontext;
errout:
	if (baseobj) {
		baseobj->_finalize(CASTTOCLASS(AssimObj,newcontext));
		newcontext = NULL;
		baseobj = NULL;
	}
	g_return_val_if_reached(NULL);
}

/// Finalize (free) a ConfigContext object
FSTATIC void
_configcontext_finalize(AssimObj* aself)
{
	ConfigContext*	self = CASTTOCLASS(ConfigContext, aself);
	
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

/// Return a GSList of all the keys in a ConfigContext object
FSTATIC GSList*
_configcontext_keys(ConfigContext* cfg)
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
_configcontext_gettype(ConfigContext* self, const char *name)
{
	gpointer	ret = g_hash_table_lookup(self->_values, name);
	ConfigValue*	cfg;
	if (ret == NULL) {
		return CFG_EEXIST;
	}
	cfg = CASTTOCLASS(ConfigValue, ret);
	return cfg->valtype;
}

/// Get an integer value
FSTATIC gint
_configcontext_getint(ConfigContext* self	///<[in] ConfigContext object
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

/// Get an boolean value
FSTATIC gboolean
_configcontext_getbool(ConfigContext* self	///<[in] ConfigContext object
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

/// Return the value of a string name
FSTATIC const char*
_configcontext_getstring(ConfigContext* self	///<[in] ConfigContext object
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


/// Return the NetAddr value of a name
FSTATIC  NetAddr*
_configcontext_getaddr(ConfigContext* self	///<[in] ConfigContext object
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

	addr->baseclass.ref(addr);
	val->u.addrvalue = addr;
	g_hash_table_replace(self->_values, cpname, val);
}

/// Return the @ref Frame value of a name
FSTATIC Frame*
_configcontext_getframe(ConfigContext* self	///<[in] ConfigContext object
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

	frame->baseclass.ref(frame);
	val->u.framevalue = frame;
	g_hash_table_replace(self->_values, cpname, val);
}

/// Return a the a ConfigContext value associated with a given name
FSTATIC ConfigContext*
_configcontext_getconfig(ConfigContext* self , const char* name)
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

	value->baseclass.ref(value);
	val->u.cfgctxvalue = value;
	g_hash_table_replace(self->_values, cpname, val);
}

/// Create a ConfigValue object (containing an object and its type)
FSTATIC ConfigValue*
_configcontext_value_new(enum ConfigValType t)
{
	ConfigValue*	ret;

	ret = MALLOCBASECLASS(ConfigValue);
	if (ret) {
		ret->valtype = t;
		memset(&ret->u, 0, sizeof(ret->u));
	}
	return ret;
}

/// Finalize (free) a ConfigValue object
FSTATIC void
_configcontext_value_finalize(gpointer vself)
{
	ConfigValue*	self;

	self = CASTTOCLASS(ConfigValue, vself);
	switch (self->valtype) {
		case CFG_STRING:
			g_free(self->u.strvalue); self->u.strvalue = NULL;
			break;
		case CFG_CFGCTX: {
			AssimObj*	obj = &self->u.cfgctxvalue->baseclass;
			obj->unref(obj); obj = NULL; self->u.cfgctxvalue = NULL;
			break;
		}
		case CFG_NETADDR: {
			AssimObj*	obj = &self->u.addrvalue->baseclass;
			obj->unref(obj); obj = NULL; self->u.addrvalue = NULL;
			break;
		}
		case CFG_FRAME: {
			AssimObj*	obj = &self->u.framevalue->baseclass;
			obj->unref(obj); obj = NULL; self->u.framevalue = NULL;
			break;
		}

		default: {
			// Do nothing
			break;
		}
	}
	self->valtype = CFG_EEXIST;
	FREECLASSOBJ(self);
	vself = NULL;
}

///@}

#define	JSONQUOTES	"\\\""
/// Escape characters in a string according to JSON conventions...
FSTATIC char *
JSONquotestring(char * s)
{
	GString*	ret;
	char *		str;
	ret = g_string_sized_new(strlen(s)+5);
	g_string_append_c(ret, '"');
	
	for (str=s; *str; ++str ) {
		if (strchr(JSONQUOTES, *str )) {
			g_string_append_c(ret, '\\');
		}
		g_string_append_c(ret, *str);
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
	GHashTableIter	iter;
	const char *	comma = "";
	gpointer	gkey;
	gpointer	gvalue;
	
	if (!self->_values) {
		return NULL;
	}
	/// @todo - return this string with keys in canonical (sorted) order
	/// - at least for tests - unsure if this will be needed.
	g_hash_table_iter_init(&iter, self->_values);
	while (g_hash_table_iter_next(&iter, &gkey, &gvalue)) {
		ConfigValue*	val = CASTTOCLASS(ConfigValue, gvalue);
		gchar*		elem = _configcontext_elem_toString(val);
		g_string_append_printf(gsret, "%s\"%s\":%s", comma, (const char *)gkey, elem);
		g_free(elem);
		comma=",";
	}
	g_string_append(gsret, "}");
	return g_string_free(gsret, FALSE);
}
FSTATIC char *
_configcontext_elem_toString(ConfigValue* val)
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
				gchar*	elem = _configcontext_elem_toString(val);
				g_string_append_printf(ret, "%s%s", acomma, elem);
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

			tostring = NULL; g_free(tostring);
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
	config.skip_comment_single = FALSE;
	config.scan_comment_multi = FALSE;
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
	}
	return retval;
}

#define TOKEN_COLON	':'
#define	GULP	(void)g_scanner_get_next_token(scan)

#define SYNERROR(scan, token, symbol, msg)	\
		{g_warning("In Function %s line %d", __FUNCTION__, __LINE__);g_scanner_unexp_token(scan, token, "keyword", "keyword", symbol, msg, TRUE);}

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
		ret->baseclass.unref(ret); ret = NULL;
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
		ret->baseclass.unref(ret); ret = NULL;
		return ret;
	}

	if (g_scanner_get_next_token(scan) != G_TOKEN_RIGHT_CURLY) {
		// Syntax error...
		SYNERROR(scan, G_TOKEN_RIGHT_CURLY, NULL, NULL);
		ret->baseclass.unref(ret); ret = NULL;
		abort();
		return ret;
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
		abort();
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
			if ((encoded = netaddr_string_new(scan->value.v_string, 0)) != NULL) {
				val = _configcontext_value_new(CFG_NETADDR);
				val->u.addrvalue = encoded;
                                encoded = NULL;
			}else{
				val = _configcontext_value_new(CFG_STRING);
				val->u.strvalue = g_strdup(scan->value.v_string);
			}
			return val;
		}

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
			abort();
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
				g_slist_free_full(*retval, _configcontext_value_finalize);
				*retval = NULL;
				return FALSE;
			}
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
