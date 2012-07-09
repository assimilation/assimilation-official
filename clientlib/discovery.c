/**
 * @file
 * @brief Abstract class (more or less) defining discovery objects
 * @details It is only instantiated by derived classes.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#include <projectcommon.h>
#define	DISCOVERY_SUBCLASS
#include <discovery.h>
#include <assert.h>
///@defgroup DiscoveryClass Discovery class
/// Discovery abstract base class - supporting the discovery of various local things by our subclasses.
/// @{
/// @ingroup C_Classes

FSTATIC char *		_discovery_instancename(const Discovery* self);
FSTATIC void		_discovery_flushcache(Discovery* self);
FSTATIC guint		_discovery_discoverintervalsecs(const Discovery* self);
FSTATIC gboolean	_discovery_rediscover(gpointer vself);
FSTATIC void		_discovery_destructor(gpointer gdiscovery);

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
	
	if (self->_timerid > 0) {
		g_source_remove(self->_timerid);
		self->_timerid = 0;
	}
	if (_discovery_timers) {
		g_hash_table_remove(_discovery_timers, self->_instancename);
	}
	if (self->_instancename) {
		g_free(self->_instancename);
		self->_instancename = NULL;
	}
	
	FREECLASSOBJ(self); self=NULL;
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
	ret->discover			= NULL;
	ret->_timerid			= 0;
	ret->_iosource			= iosource;
	ret->_config			= context;
	return ret;
}


/// Discovery Destructor function for the GHashTable
FSTATIC void
_discovery_destructor(gpointer gdiscovery)
{
	Discovery*	discovery = CASTTOCLASS(Discovery, gdiscovery);
        g_return_if_fail(discovery != NULL);
	discovery->baseclass.unref(&discovery->baseclass);
	discovery = NULL;
	gdiscovery = NULL;
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
		,	NULL, _discovery_destructor);
		assert(_discovery_timers != NULL);
	}
	self->discover(self);
	timeout = self->discoverintervalsecs(self);
	if (timeout > 0) {
		self->_timerid = g_timeout_add_seconds(timeout, _discovery_rediscover, self);
	}
	self->baseclass.ref(self);
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

///@}
