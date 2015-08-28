/**
 * @file
 * @brief Implements the ResourceCmd factory/parent class
 * @details Detemines which subclass a particular constructor request is for, then
 * executes the relevant subclass constructor.  After that, our only involvement
 * is in the destructor.
 *
 * @author  Alan Robertson <alanr@unix.sh> - Copyright &copy; 2013 - Assimilation Systems Limited
 * @n
 *  This file is part of the Assimilation Project.
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
#include <string.h>
#define	RESOURCECMD_SUBCLASS
#include <resourcecmd.h>
#include <resourceocf.h>
#include <resourcelsb.h>
#include <resourcenagios.h>

DEBUGDECLARATIONS

///@defgroup ResourceCmd ResourceCmd class
/// Class implementing resource commands
///@{
///@ingroup C_Classes
///@ingroup AssimObj

/**
 *	List of all known ResourceCmd subclass names and their constructor functions
 *	This is for our 'factory'-like function resourcecmd_new().
 */
static const struct {
	const char *		classname;
	ResourceCmd* (*constructor) (
			guint structsize
,			ConfigContext* request
,			gpointer user_data
,			ResourceCmdCallback callback);
}subclasses[] = {
	{"ocf", resourceocf_new},	//< OCF resource agents
	{"lsb", resourcelsb_new},	//< LSB (/etc/init.d) resource agents
	{"nagios", resourcenagios_new}	//< NAGIOS resource agents
};
FSTATIC void _resourcecmd_finalize(AssimObj*);
FSTATIC void _resourcecmd_execute(ResourceCmd* self);	///< Moan and complain - abstract class

/**
 * Our ResourceCmd Factory object - constructs an object of the proper subclass for the given
 * instantiation parameters.  We only pay attention to the REQCLASSNAMEFIELD field at the
 * top level of the request ConfigContext object.
 */
ResourceCmd*
resourcecmd_new(ConfigContext* request		///< Request to instantiate
,		gpointer user_data		///< User data for 'callback'
,		ResourceCmdCallback callback)	///< Callback when complete

{
	guint		j;
	const char *	cname;

	if (NULL == request) {
		g_warning("%s.%d: NULL resourcecmd request" , __FUNCTION__, __LINE__);
		return NULL;
	}
	cname = request->getstring(request, REQCLASSNAMEFIELD);

	if (NULL == cname) {
		char *	reqstr = request->baseclass.toString(&request->baseclass);
		g_warning("%s.%d: No class name in request [%s]", __FUNCTION__, __LINE__
		,	reqstr);
		g_free(reqstr); reqstr = NULL;
		return NULL;
	}

	for (j=0; j < DIMOF(subclasses) && subclasses[j].classname; ++j) {
		if (strcmp(cname, subclasses[j].classname) == 0) {
			return subclasses[j].constructor(0, request, user_data, callback);
		}
	}
	g_warning("%s.%d: Invalid resource class [%s]", __FUNCTION__, __LINE__, cname);
	return NULL;
}

/// Finalize function for ResourceCmd objects
void
_resourcecmd_finalize(AssimObj* aself)
{
	ResourceCmd*	self = CASTTOCLASS(ResourceCmd, aself);

	if (self->request) {
		UNREF(self->request);
	}
	self->user_data = NULL;
	self->callback = NULL;
	_assimobj_finalize(aself);
}


/// Constructor (_new function) for ResourceCmd "abstract" class
ResourceCmd*
resourcecmd_constructor(
		guint structsize		///< Structure size (or zero)
,		ConfigContext* request		///< Request to instantiate
,		gpointer user_data		///< User data for 'callback'
,		ResourceCmdCallback callback)	///< Callback when complete
{
	AssimObj*	aself;
	ResourceCmd*	self;
	const char*		rscname;
	const char*		operation;

	BINDDEBUG(ResourceCmd);
	if (structsize < sizeof(ResourceCmd)) {
		structsize = sizeof(ResourceCmd);
	}
	rscname = request->getstring(request, CONFIGNAME_INSTANCE);
	if (NULL == rscname) {
		char *	reqstr = request->baseclass.toString(&request->baseclass);
		g_warning("%s.%d: No resource name in request [%s]", __FUNCTION__, __LINE__
		,	reqstr);
		g_free(reqstr); reqstr = NULL;
		return NULL;
	}
	operation = request->getstring(request, REQOPERATIONNAMEFIELD);
	if (NULL == operation) {
		char *	reqstr = request->baseclass.toString(&request->baseclass);
		g_warning("%s.%d: No "REQOPERATIONNAMEFIELD" name in request [%s]"
		,	__FUNCTION__, __LINE__ , reqstr);
		g_free(reqstr); reqstr = NULL;
		return NULL;
	}
	aself = assimobj_new(structsize);
	self = NEWSUBCLASS(ResourceCmd, aself);

	self->request = request;
	REF(self->request);
	self->user_data = user_data;
	self->callback = callback;
	self->execute = _resourcecmd_execute;
	self->resourcename = rscname;
	self->operation = operation;

	aself->_finalize = _resourcecmd_finalize;
	return self;
}
/// Moan and complain - we're an abstract class
FSTATIC void
_resourcecmd_execute(ResourceCmd* self)
{
	(void)self;
	g_warning("%s.%d: Abstract class -- cannot execute."
	,	__FUNCTION__, __LINE__);
}
///@}
