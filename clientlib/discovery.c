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
///@defgroup DiscoveryClass Discovery class
/// Discovery abstract base class - supporting the discovery of various local things by our subclasses.
/// @{
/// @ingroup C_Classes

FSTATIC const char *	_discovery_discoveryname(const Discovery* self);
FSTATIC guint		_discovery_discoverintervalsecs(const Discovery* self);
FSTATIC gboolean	_discovery_rediscover(gpointer vself);

/// internal function return the type of Discovery object
FSTATIC const char *
_discovery_discoveryname(const Discovery* self)	///<[in] object whose type to return
{
	return proj_class_classname(self);
}

/// default function - return zero for discovery interval
FSTATIC guint
_discovery_discoverintervalsecs(const Discovery* self)	///<[in] Object whose interval to return
{
	(void)self;
	return 0;
}
static GSList * _discovery_timers = NULL;

/// Finalizing function for Discovery objects
FSTATIC void
_discovery_finalize(AssimObj* gself)	///<[in/out] Object to finalize (free)
{
	Discovery* self = CASTTOCLASS(Discovery, gself);
	
	self->_timerid = -1;
	_discovery_timers = g_slist_remove(_discovery_timers, self);
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
discovery_new(NetGSource*	iosource,	///<[in/out] I/O object
	      ConfigContext*	context,	///<[in/out] configuration context
	      gsize objsize)			///<[in] number of bytes to malloc for the object (or zero)
{
	gsize	size = objsize < sizeof(Discovery) ? sizeof(Discovery) : objsize;
	Discovery * ret = NEWSUBCLASS(Discovery, assimobj_new(size));
	g_return_val_if_fail(ret != NULL, NULL);
	ret->discoveryname		= _discovery_discoveryname;
	ret->discoverintervalsecs	= _discovery_discoverintervalsecs;
	ret->baseclass._finalize	= _discovery_finalize;
	ret->discover			= NULL;
	ret->_timerid			= -1;
	ret->_iosource			= iosource;
	ret->_config			= context;
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
	self->discover(self);
	timeout = self->discoverintervalsecs(self);
	if (timeout > 0) {
		self->_timerid = g_timeout_add_seconds(timeout, _discovery_rediscover, self);
	}
	_discovery_timers = g_slist_prepend(_discovery_timers, self);
	self->baseclass.ref(self);
}

/// Unregister all discovery methods in preparation for shutting down - to make valgrind happy :-D
void
discovery_unregister_all(void)
{
	GSList * this;
	GSList * next;

	for (this = _discovery_timers; this; this = next) {
		Discovery*	d = CASTTOCLASS(Discovery, this->data);
		next = this->next;
		d->baseclass.unref(d);
	}
}

///@}
