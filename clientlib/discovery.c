/**
 * @file
 * @brief Abstract class (more or less) defining discovery objects
 * @details It is only instantiated by derived classes.
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
#define	DISCOVERY_SUBCLASS
#include <discovery.h>
#include <cstringframe.h>
#include <frametypes.h>
#include <fsprotocol.h>
#include <string.h>
#include <assert.h>
///@defgroup DiscoveryClass Discovery class
/// Discovery abstract base class - supporting the discovery of various local things by our subclasses.
/// @{
/// @ingroup C_Classes

FSTATIC char *		_discovery_instancename(const Discovery* self);
FSTATIC void		_discovery_flushcache(Discovery* self);
FSTATIC guint		_discovery_discoverintervalsecs(const Discovery* self);
FSTATIC gboolean	_discovery_rediscover(gpointer vself);
FSTATIC void		_discovery_ghash_destructor(gpointer gdiscovery);
FSTATIC void		_discovery_sendjson(Discovery* self, char * jsonout, gsize jsonlen);

DEBUGDECLARATIONS

/// internal function return the type of Discovery object
FSTATIC char *
_discovery_instancename(const Discovery* self)	///<[in] object whose instance name to return
{
	return self->_instancename;
}

/// default (do-nothing) 'flush cache' function
FSTATIC void
_discovery_flushcache(Discovery* self)	///< object whose cache we're suppossed to flush...
{
	(void)self;
}

/// default function - return zero for discovery interval
FSTATIC guint
_discovery_discoverintervalsecs(const Discovery* self)	///<[in] Object whose interval to return
{
	(void)self;
	return 0;
}
static GHashTable * _discovery_timers = NULL;

/// Finalizing function for Discovery objects
FSTATIC void
_discovery_finalize(AssimObj* gself)	///<[in/out] Object to finalize (free)
{
	Discovery*	self = CASTTOCLASS(Discovery, gself);
	char *		instancename = self->_instancename;
	
	if (self->_timerid > 0) {
		g_source_remove(self->_timerid);
		self->_timerid = 0;
	}
	if (self->_config) {
		UNREF(self->_config);
	}
	if (_discovery_timers && instancename) {
		self->_instancename = NULL;	// Avoid infinite recursion...
		g_hash_table_remove(_discovery_timers, instancename);
	}
	if (instancename) {
		g_free(instancename);
		self->_instancename = instancename = NULL;
	}
	
	FREECLASSOBJ(self); self=NULL;
}

/// Discovery Destructor function for the GHashTable.
/// This function gets called every time a @ref Discovery gets deleted from our _discovery_timers
/// hash table.
/// It has the potential for infinite mutual recursion with discovery_finalize() - which we prevent.
FSTATIC void
_discovery_ghash_destructor(gpointer gdiscovery)
{
	Discovery*	self = CASTTOCLASS(Discovery, gdiscovery);
	// We take steps in discovery_finalize() to avoid infinite recursion...
	UNREF(self);
}

/// GSourceFunc function to invoke discover member function at the timed interval.
/// This function is called by the g_main_loop mechanism when the rediscover timeout elapses.
FSTATIC gboolean
_discovery_rediscover(gpointer vself)	///<[in/out] Object to perform discovery on
{
	Discovery*	self = CASTTOCLASS(Discovery, vself);

	return self->discover(self);
}

/// Discovery constructor.
/// Note that derived classes <i>must</i> set the discover member function - or things might crash.
/// That is certainly what will happen if you try and construct one of these objects directly and
/// then use it.
Discovery*
discovery_new(const char *	instname,	///<[in] instance name
	      NetGSource*	iosource,	///<[in/out] I/O object
	      ConfigContext*	context,	///<[in/out] configuration context
	      gsize objsize)			///<[in] number of bytes to malloc for the object (or zero)
{
	gsize	size = objsize < sizeof(Discovery) ? sizeof(Discovery) : objsize;
	Discovery * ret = NEWSUBCLASS(Discovery, assimobj_new(size));
	g_return_val_if_fail(ret != NULL, NULL);
	BINDDEBUG(Discovery);
	ret->_instancename		= g_strdup(instname);
	ret->instancename		= _discovery_instancename;
	ret->discoverintervalsecs	= _discovery_discoverintervalsecs;
	ret->baseclass._finalize	= _discovery_finalize;
	ret->sendjson			= _discovery_sendjson;
	ret->discover			= NULL;
	ret->_timerid			= 0;
	ret->_iosource			= iosource;
	ret->_config			= context;
	REF(ret->_config);
	return ret;
}


/// Function for registering a discovery object with the discovery infrastructure.
/// It runs the discover function, then schedules it for repeated discovery - if appropriate.
/// It "knows" how often to rediscover things by calling the discoverintervalsecs() member
/// function.  If that function returns a value greater than zero, then this discovery object
/// will be "re-discovered" according to the number of seconds returned.
///
void
discovery_register(Discovery* self)	///<[in/out] Discovery object to register
{
	gint	timeout;
	if (NULL == _discovery_timers) {
		_discovery_timers = g_hash_table_new_full(g_str_hash, g_str_equal
		,	NULL, _discovery_ghash_destructor);
		assert(_discovery_timers != NULL);
	}
	self->discover(self);
	timeout = self->discoverintervalsecs(self);
	if (timeout > 0) {
		self->_timerid = g_timeout_add_seconds(timeout, _discovery_rediscover, self);
	}
	REF(self);
	g_hash_table_replace(_discovery_timers, self->instancename(self), self);
}
FSTATIC void
discovery_unregister(const char* instance)
{
	if (_discovery_timers) {
		g_hash_table_remove(_discovery_timers, instance);
	}
}

/// Unregister all discovery methods in preparation for shutting down - to make valgrind happy :-D
void
discovery_unregister_all(void)
{
	if (_discovery_timers != NULL) {
		GHashTable*	timers = _discovery_timers;
		_discovery_timers = NULL;
		g_hash_table_remove_all(timers);
		g_hash_table_destroy(timers); timers = NULL;
	}else{
		DEBUGMSG1("Discovery timers were NULL");
	}
}
/// Send JSON that we discovered to the CMA - with some caching going on
FSTATIC void
_discovery_sendjson(Discovery* self, char * jsonout, gsize jsonlen)
{
	FrameSet*	fs;
	CstringFrame*	jsf;
	Frame*		fsf;
	ConfigContext*	cfg = self->_config;
	NetGSource*	io = self->_iosource;
	NetAddr*	cma;
	const char *	basename = self->instancename(self);

	g_return_if_fail(cfg != NULL && io != NULL);

	DEBUGMSG2("%s.%d: discovering %s: _sentyet == %d"
	,	__FUNCTION__, __LINE__, basename, self->_sentyet);
	// Primitive caching - don't send what we've already sent.
	if (self->_sentyet) {
		const char *	oldvalue = cfg->getstring(cfg, basename);
		if (oldvalue != NULL && strcmp(jsonout, oldvalue) == 0) {
			DEBUGMSG2("%s.%d: %s sent this value - don't send again."
			,	__FUNCTION__, __LINE__, basename);
			g_free(jsonout);
			return;
		}
		DEBUGMSG2("%s.%d: %s this value is different from previous value"
		,	__FUNCTION__, __LINE__, basename);
	}
	DEBUGMSG2("%s.%d: Sending %"G_GSIZE_FORMAT" bytes of JSON text"
	,	__FUNCTION__, __LINE__, jsonlen);
	cfg->setstring(cfg, basename, jsonout);
	cma = cfg->getaddr(cfg, CONFIGNAME_CMADISCOVER);
	if (cma == NULL) {
	        DEBUGMSG2("%s.%d: %s address is unknown - skipping send"
		,	__FUNCTION__, __LINE__, CONFIGNAME_CMADISCOVER);
		g_free(jsonout);
		return;
	}
	self->_sentyet = TRUE;

	fs = frameset_new(FRAMESETTYPE_JSDISCOVERY);
	jsf = cstringframe_new(FRAMETYPE_JSDISCOVER, 0);
	fsf = &jsf->baseclass;	// base class object of jsf
	fsf->setvalue(fsf, jsonout, jsonlen+1, frame_default_valuefinalize); // jsonlen is strlen(jsonout)
	frameset_append_frame(fs, fsf);
	DEBUGMSG2("%s.%d: Sending a %"G_GSIZE_FORMAT" bytes JSON frameset"
	,	__FUNCTION__, __LINE__, jsonlen);
	io->_netio->sendareliablefs(io->_netio, cma, DEFAULT_FSP_QID, fs);
	++ self->reportcount;
	UNREF(fsf);
	UNREF(fs);
}

///@}
