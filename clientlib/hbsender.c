/**
 * @file
 * @brief Implements the @ref HbSender class - for sending heartbeats.
 * @details We are told what addresses to send to, and how often to send them.
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
#include <memory.h>
#include <glib.h>
#include <frameset.h>
#include <frame.h>
#include <hbsender.h>
/**
 */
FSTATIC void _hbsender_notify_function(gpointer data);
FSTATIC void _hbsender_finalize(HbSender * self);
FSTATIC void _hbsender_ref(HbSender * self);
FSTATIC void _hbsender_unref(HbSender * self);
FSTATIC void _hbsender_addlist(HbSender* self);
FSTATIC void _hbsender_dellist(HbSender* self);
FSTATIC void _hbsender_sendheartbeat(HbSender* self);
FSTATIC gboolean _hbsender_gsourcefunc(gpointer);

DEBUGDECLARATIONS

///@defgroup HbSender HbSender class.
/// Class for heartbeat Senders - We send heartbeats to the chosen few
///@{
///@ingroup C_Classes

static GSList*	_hb_senders = NULL;
static gint	_hb_sender_count = 0;

#define	ONESEC	1000000

/// Add an HbSender to our global list of HbSenders
FSTATIC void
_hbsender_addlist(HbSender* self)	///<[in]The sender to add
{
	_hb_senders = g_slist_prepend(_hb_senders, self);
	_hb_sender_count += 1;
}

/// Remove an HbSender from our global list of HbSenders
FSTATIC void
_hbsender_dellist(HbSender* self)	///<[in]The sender to remove from our list
{
	if (g_slist_find(_hb_senders, self) != NULL) {
		_hb_senders = g_slist_remove(_hb_senders, self);
		_hb_sender_count -= 1;
		return;
	}
	g_warn_if_reached();
}

/// A GSourceFunc to be used with g_timeout_add_seconds()
FSTATIC gboolean
_hbsender_gsourcefunc(gpointer gself) ///<[in/out] Pointer to 'self'
{
	HbSender* self = CASTTOCLASS(HbSender, gself);
	_hbsender_sendheartbeat(self);
	return TRUE;
}


/// Increment the reference count by one.
FSTATIC void
_hbsender_ref(HbSender* self)	///<[in/out] Object to increment reference count for
{
	self->_refcount += 1;
}

/// Decrement the reference count by one - possibly freeing up the object.
FSTATIC void
_hbsender_unref(HbSender* self)	///<[in/out] Object to decrement reference count for
{
	g_return_if_fail(self->_refcount > 0);
	self->_refcount -= 1;
	if (self->_refcount == 0) {
		_hbsender_dellist(self);
		self->_finalize(self);
		self = NULL;
	}
}
// Callback function from the GSource world - notifying us when we're getting shut down from their end
FSTATIC void
_hbsender_notify_function(gpointer data)
{
	HbSender* self = CASTTOCLASS(HbSender, data);
	self->timeout_source = 0;
}

/// Finalize an HbSender
FSTATIC void
_hbsender_finalize(HbSender * self) ///<[in/out] Sender to finalize
{
	if (self->_sendaddr) {
		UNREF(self->_sendaddr);
	}
	if (self->timeout_source != 0) {
		g_source_remove(self->timeout_source);
		self->timeout_source = 0;
	}
	memset(self, 0x00, sizeof(*self));
	FREECLASSOBJ(self);
}


/// Construct a new HbSender - setting up timeout data structures for it.
/// This can be used directly or by derived classes.
HbSender*
hbsender_new(NetAddr* sendaddr,		///<[in] Address to send to
	     NetGSource* outmethod,	///<[in] Mechanism for sending packets
	     guint  interval,		///<[in] How often to send, in seconds
	     gsize objsize)		///<[in] size of HbSender structure (0 for sizeof(HbSender))
{
	HbSender * newsender;
	BINDDEBUG(HbSender);
	if (objsize < sizeof(HbSender)) {
		objsize = sizeof(HbSender);
	}
	newsender = MALLOCCLASS(HbSender, objsize);
	if (newsender != NULL) {
		newsender->_sendaddr = sendaddr;
		REF(sendaddr);
		newsender->_refcount = 1;
		newsender->ref = _hbsender_ref;
		newsender->_outmethod = outmethod;
		newsender->unref = _hbsender_unref;
		newsender->_finalize = _hbsender_finalize;
		newsender->_expected_interval = interval;
		newsender->timeout_source = g_timeout_add_seconds_full
					    (G_PRIORITY_HIGH, interval, _hbsender_gsourcefunc
					,    newsender, _hbsender_notify_function);
		if (DEBUG) {
			char *	addrstr = sendaddr->baseclass.toString(&sendaddr->baseclass);
			g_debug("%s.%d: Start sending heartbeats to %s at interval "FMT_64BIT"d"
			,	__FUNCTION__, __LINE__, addrstr, newsender->_expected_interval);
			FREE(addrstr);
		}
		_hbsender_addlist(newsender);
		_hbsender_sendheartbeat(newsender);
	}
	return newsender;
}


/// Stop sending heartbeats to a particular address
void
hbsender_stopsend(NetAddr* sendaddr)///<[in/out] Sender to remove from list
{
	GSList*		obj;
	if (DEBUG) {
		char *	addrstr = sendaddr->baseclass.toString(sendaddr);
		g_debug("%s.%d: Stop sending heartbeats to %s"
		,	__FUNCTION__, __LINE__, addrstr);
		FREE(addrstr);
	}
	for (obj = _hb_senders; obj != NULL; obj=obj->next) {
		HbSender* sender = CASTTOCLASS(HbSender, obj->data);
		if (sendaddr->equal(sendaddr, sender->_sendaddr)) {
			// Send one last heartbeat - avoid unnecessary death reports
			_hbsender_sendheartbeat(sender);
			sender->unref(sender);
			return;
		}
	}
}
/// Send out a heartbeat
FSTATIC void
_hbsender_sendheartbeat(HbSender* self)
{
	FrameSet*	heartbeat = frameset_new(FRAMESETTYPE_HEARTBEAT);
	//g_debug("Sending a heartbeat...");
	if (DEBUG >= 4) {
		char *	addrstr = self->_sendaddr->baseclass.toString(self->_sendaddr);
		g_debug("%s.%d: Sending heartbeat to %s at interval "FMT_64BIT"d"
		,	__FUNCTION__, __LINE__, addrstr, self->_expected_interval);
		FREE(addrstr);
	}
	self->_outmethod->sendaframeset(self->_outmethod, self->_sendaddr, heartbeat);
	UNREF(heartbeat);
}
/// Stop sending heartbeats to anyone...
void
hbsender_stopallsenders(void)
{
	while (_hb_senders) {
		HbSender* sender = CASTTOCLASS(HbSender, _hb_senders->data);
		sender->unref(sender);
	}
}
///@}
