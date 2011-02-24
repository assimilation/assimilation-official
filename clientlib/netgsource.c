/**
 * @file
 * @brief Implements NetIO GSource object
 * @details This file contains the header definitions for NetIOGSource objects
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#include <glib.h>
#include <netgsource.h>

/// This is our basic NetGSource object.
/// It is used for reading from network sockets, and managing flow control to them.
/// It is a class from which we might eventually make subclasses,
/// and is managed by our @ref ProjectClass system.
///@{
/// @ingroup NetGSource

FSTATIC gboolean _netgsource_prepare(GSource* source, gint* timeout);
FSTATIC gboolean _netgsource_check(GSource* source);
FSTATIC gboolean _netgsource_dispatch(GSource* source, GSourceFunc callback, gpointer user_data);
FSTATIC void     _netgsource_finalize(GSource* source);

static GSourceFuncs _netgsource_gsourcefuncs = {
	_netgsource_prepare,
	_netgsource_check,
	_netgsource_dispatch,
	_netgsource_finalize,
	NULL,
	NULL
};
/// Create a new (abstract) NetGSource object
NetGSource*
netgsource_new(NetIO* iosrc, NetGSourceDispatch dispatch, gpointer userdata, gsize objsize)
{
	GSource*	gsret;
	NetGSource*	ret;
	GSourceFuncs*	gsf;

	if (objsize < sizeof(NetGSource)) {
		objsize = sizeof(NetGSource);
	}
	gsf  = MALLOCBASECLASS(GSourceFuncs);
	*gsf = _netgsource_gsourcefuncs;
	
	gsret = g_source_new(gsf, objsize);
	proj_class_register_object(gsret, "GSource");
	proj_class_register_subclassed(gsret, "NetGSource");
	ret = CASTTOCLASS(NetGSource, gsret);

	ret->_gsfuncs = gsf;
	ret->_dispatch = dispatch;
	ret->_userdata = userdata;
	ret->_netio = iosrc;
	ret->_socket = iosrc->getfd(iosrc);
	ret->finalize = NULL;

	return ret;
}

/// GSource dispatch routine for NetGSource - always returns TRUE
FSTATIC gboolean
_netgsource_prepare(GSource* source, gint* timeout)
{
	return TRUE;
}

/// GSource dispatch routine for NetGSource.
/// @return TRUE if if a packet is present, FALSE otherwise
FSTATIC gboolean
_netgsource_check(GSource* gself)
{
	NetGSource*	self = CASTTOCLASS(NetGSource, gself);
	// revents: received events...
	// @todo: should check for errors in revents
	return 0 != self->_gfd.revents;
}
///
FSTATIC gboolean
_netgsource_dispatch(GSource* gself, GSourceFunc ignore_callback, gpointer ignore_userdata)
{
	NetGSource*	self = CASTTOCLASS(NetGSource, gself);
	GSList*		gsl;
	NetAddr*	srcaddr;
	while(NULL != (gsl = self->_netio->recvframesets(self->_netio, &srcaddr))) {
		self->_dispatch(self, gsl, srcaddr, self->_userdata);
		///< @todo Figure out the lifetime of packets and addresses
		/// probably need to add some reference counters.
	}
	return TRUE;
}

FSTATIC void
_netgsource_finalize(GSource* gself)
{
	NetGSource*	self = CASTTOCLASS(NetGSource, gself);

	if (self->finalize) {
		self->finalize(self->_userdata);
	}else{
		if (self->_userdata) {
			/// If this next call crashes, you should have supplied your own
			/// finalize routine (and maybe you should anyway)
			FREECLASSOBJ(self->_userdata);
			self->_userdata = NULL;
		}
	}
	if (self->_gsfuncs) {
		FREECLASSOBJ(self->_gsfuncs);
		self->_gsfuncs = NULL;
	}
}
///@}

