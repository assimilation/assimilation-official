/**
 * @file
 * @brief Implements the @ref ConfigContext class.
 * @details This file provides a place to remember and pass configuration defaults around.
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
FSTATIC void	_configcontext_finalize(ConfigContext* self);
FSTATIC void	_configcontext_free(void* thing);
FSTATIC gint	_configcontext_getintvalue(ConfigContext*, const char *name);
FSTATIC void	_configcontext_setintvalue(ConfigContext*, const char *name, gint value);
FSTATIC const char* _configcontext_getstringvalue(ConfigContext*, const char *name);
FSTATIC void	_configcontext_setstringvalue(ConfigContext*, const char *name, const char *value);

static struct configintdefaults {
	const char *	name;
	int		value;
}	idefaults [] = CONFIGINTDEFAULTS;

/// Construct a new ConfigContext object - with some values defaulted
ConfigContext*
configcontext_new(gsize objsize)	///< size of ConfigContext structure (or zero for min size)
{
	ConfigContext * newcontext = NULL;
	unsigned char	addrbody[] = CONFIG_DEFAULT_ADDR;
	int		j;

	if (objsize < sizeof(ConfigContext)) {
		objsize = sizeof(ConfigContext);
	}
	newcontext = MALLOCCLASS(ConfigContext, objsize);
	memset(newcontext, 0x00, objsize);
	newcontext->setsignframe =	_configcontext_setsignframe;
	newcontext->setmgmtaddr	=	_configcontext_setmgmtaddr;
	newcontext->setintvalue	=	_configcontext_setintvalue;
	newcontext->getintvalue	=	_configcontext_getintvalue;
	newcontext->setstringvalue=	_configcontext_setstringvalue;
	newcontext->getstringvalue=	_configcontext_getstringvalue;
	newcontext->_finalize	=	_configcontext_finalize;
	newcontext->_refcount	=	1;
	newcontext->_intvalues = g_hash_table_new_full(g_str_hash, g_str_equal, _configcontext_free, NULL);
	newcontext->_strvalues = g_hash_table_new_full(g_str_hash, g_str_equal
				,	_configcontext_free, _configcontext_free);
	if (NULL == newcontext) {
		goto errout;
	}
	newcontext->collectivemgmtaddr = netaddr_new(0, 0, CONFIG_DEFAULT_ADDRTYPE, addrbody, sizeof(addrbody));
	if (NULL == newcontext->collectivemgmtaddr) {
		goto errout;
	}
	newcontext->signframe = signframe_new(CONFIG_DEFAULT_SIGNFRAME_TYPE, 0);
	if (NULL == newcontext->signframe) {
		goto errout;
	}
	for (j=0; j < (int)DIMOF(idefaults); ++j) {
		newcontext->setintvalue(newcontext, idefaults[j].name, idefaults[j].value);
	}
	return newcontext;
errout:
	if (newcontext) {
		newcontext->_finalize(newcontext);
		newcontext = NULL;
	}
	g_return_val_if_reached(NULL);
}

FSTATIC void
_configcontext_setsignframe(ConfigContext* self, SignFrame* signframe)
{
	g_return_if_fail(signframe != NULL);
	self->signframe->baseclass.unref(CASTTOCLASS(Frame, self->signframe));
	signframe->baseclass.ref(CASTTOCLASS(Frame, signframe));
	self->signframe = signframe;
}

FSTATIC gint
_configcontext_getintvalue(ConfigContext* self, const char *name)
{
	gpointer	lookupkey = NULL;
	gpointer	lookupvalue = NULL;

	g_hash_table_lookup_extended(self->_intvalues, name, &lookupkey, &lookupvalue);
	if (lookupkey == NULL) {
		return -1;
	}
	return GPOINTER_TO_INT(lookupvalue);
}

FSTATIC void
_configcontext_setintvalue(ConfigContext* self, const char *name, gint value)
{
	char *	cpname = g_strdup(name);
	g_hash_table_insert(self->_intvalues, cpname, GINT_TO_POINTER(value));
}

FSTATIC const char*
_configcontext_getstringvalue(ConfigContext* self, const char *name)
{
	return (const char *)g_hash_table_lookup(self->_strvalues, name);
}

FSTATIC void
_configcontext_setstringvalue(ConfigContext* self, const char *name, const char *value)
{
	char *	cpname = g_strdup(name);
	char *	cpvalue = g_strdup(value);
	g_hash_table_insert(self->_strvalues, cpname, cpvalue);
}

FSTATIC void
_configcontext_setmgmtaddr(ConfigContext* self, NetAddr* addr)
{
	g_return_if_fail(addr != NULL);
	self->collectivemgmtaddr->unref(self->collectivemgmtaddr);
	self->collectivemgmtaddr = addr;
	addr->ref(addr);
}


FSTATIC void
_configcontext_free(gpointer thing)
{
	FREE(thing);
}

FSTATIC void
_configcontext_finalize(ConfigContext* self)
{
	if (self->collectivemgmtaddr) {
		self->collectivemgmtaddr->unref(self->collectivemgmtaddr);
		self->collectivemgmtaddr = NULL;
	}
	if (self->signframe) {
		self->signframe->baseclass.unref(CASTTOCLASS(Frame, self->signframe));
		self->signframe = NULL;
	}
	memset(self, 0x00, sizeof(*self));
	FREECLASSOBJ(self); self = NULL;
}
