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

ConfigContext*
configcontext_new(gsize objsize)	///< size of ConfigContext structure (or zero for min size)
{
	ConfigContext * newcontext = NULL;
	unsigned char addrbody[] = CONFIG_DEFAULT_ADDR;

	if (objsize < sizeof(ConfigContext)) {
		objsize = sizeof(ConfigContext);
	}
	newcontext = MALLOCCLASS(ConfigContext, objsize);
	memset(newcontext, 0x00, objsize);
	newcontext->deadtime		= CONFIG_DEFAULT_DEADTIME;
	newcontext->hbtime		= CONFIG_DEFAULT_HBTIME;
	newcontext->warntime		= CONFIG_DEFAULT_WARNTIME;
	newcontext->setsignframe =	_configcontext_setsignframe;
	newcontext->setmgmtaddr	=	_configcontext_setmgmtaddr;
	newcontext->_finalize	=	_configcontext_finalize;
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

FSTATIC void
_configcontext_setmgmtaddr(ConfigContext* self, NetAddr* addr)
{
	g_return_if_fail(addr != NULL);
	self->collectivemgmtaddr->unref(self->collectivemgmtaddr);
	self->collectivemgmtaddr = addr;
	addr->ref(addr);
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
