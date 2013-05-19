/**
 * @file
 * @brief Implements ResourceQueue class
 * @details Supports the implementation of the Resource Queue class - for queueuing resource requests.
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
#include <resourcequeue.h>
DEBUGDECLARATIONS

///@{
///@ingroup ResourceQueue
/// Class implementing the ResourceQueue class - allowing us to support repeating operations and
/// ensure that only one operation at a time happens on any given resource.

#define	uSPERSEC	((guint64)1000000)

typedef struct _RscQElem RscQElem;
struct _RscQElem {
	gint64			queuetime;	///< Time this particular request entered the queue.
						///< If it's a repeating request, that's when it
						///< was last enqueued.
	ResourceCmd*		cmd;		///< The request
	ResourceQueue*		parent;		///< Our parent ResourceQueue
	GQueue*			ourQ;		///< Which Queue are we in?
	ResourceCmdCallback	callback;	///< Who to call when it completes
	gpointer		user_data;	///< user_data for callback
	gint			repeatinterval;	///< How often to repeat?  0 == single-shot
	gint64			requestid;	///< Request ID
	gboolean		cancelme;	///< Cancel after current request completes
};



/**
 *	self->resources is a hash table of GQueue indexed by the resource name.
 *	The resource name duplicates a field in the ResourceCmd.
 *	Each GQueue element has a RscQElem* as its data element.
 *	As a given ResourceCmd completes, we remove its RscQElem from its queue.
 *	If it repeats, then we put it on the end of its queue with a delay before executing.
 *	If it won't repeat, then we call its callback and UNREF it.
 */
FSTATIC void _resource_queue_hash_data_destructor(gpointer dataptr);
FSTATIC void _resource_queue_hash_key_destructor(gpointer dataptr);
FSTATIC void _resource_queue_cmd_remove(ResourceQueue* self, RscQElem* qelem);
FSTATIC gboolean _resource_queue_Qcmd(ResourceQueue* self, ConfigContext* request
,		ResourceCmdCallback callback, gpointer user_data);
FSTATIC gboolean _resource_queue_cancel(ResourceQueue* self, ConfigContext* request);
FSTATIC gboolean _resource_queue_cmd_append(ResourceQueue* self, ResourceCmd* cmd
,		ResourceCmdCallback cb, gpointer user_data);
FSTATIC void _resource_queue_finalize(AssimObj* aself);
FSTATIC RscQElem* _resource_queue_qelem_new(ResourceCmd* cmd, ResourceQueue* parent
,		ResourceCmdCallback cb, gpointer user_data, GQueue* Q);
FSTATIC void _resource_queue_qelem_finalize(RscQElem* self);
FSTATIC gboolean _resource_queue_runqueue(gpointer pself);
FSTATIC void _resource_queue_endnotify(ConfigContext* request, gpointer user_data
,		enum HowDied exittype, int rc, int signal, gboolean core_dumped
,		const char* stringresult);

/// Construct a new ResourceQueue system (you probably only need one)
ResourceQueue*
resourcequeue_new(guint structsize)
{
	AssimObj*		aself;
	ResourceQueue*		self;
	BINDDEBUG(ResourceQueue);

	if (structsize < sizeof(ResourceQueue)) {
		structsize = sizeof(ResourceQueue);
	}
	aself = assimobj_new(structsize);
	self = NEWSUBCLASS(ResourceQueue, aself);
	aself->_finalize = _resource_queue_finalize;
	
	self->Qcmd = _resource_queue_Qcmd;
	self->cancel = _resource_queue_cancel;
	self->resources = g_hash_table_new_full(g_str_hash, g_str_equal
	,		_resource_queue_hash_key_destructor, _resource_queue_hash_data_destructor);
	self->timerid = g_timeout_add_seconds(5, _resource_queue_runqueue, self);

	return self;
}

/// Finalize a ResourceQueue -- RIP
FSTATIC void
_resource_queue_finalize(AssimObj* aself)
{
	ResourceQueue*	self = CASTTOCLASS(ResourceQueue, aself);

	if (self->resources) {
		g_hash_table_destroy(self->resources);
		self->resources = NULL;
	}
	_assimobj_finalize(&self->baseclass);
	self = NULL;
}
/// Append a ResourceQuee
FSTATIC gboolean
_resource_queue_Qcmd(ResourceQueue* self
,	ConfigContext* request
,	ResourceCmdCallback callback
,	gpointer user_data)
{
	ResourceCmd*	cmd;
	gboolean	ret;

	// Will replace NULL with our qelem object
	cmd = resourcecmd_new(request, NULL, _resource_queue_endnotify);

	if (cmd == NULL) {
		return FALSE;
	}

	ret = _resource_queue_cmd_append(self, cmd, callback, user_data);
	UNREF(cmd);
	return ret;
}

/// Append a ResourceCmd to a ResourceQueue
FSTATIC gboolean
_resource_queue_cmd_append(ResourceQueue* self, ResourceCmd* cmd
,		ResourceCmdCallback cb, gpointer user_data)
{
	GQueue*	q;
	RscQElem* qelem;

	gint64			requestid;

	requestid = cmd->request->getint(cmd->request, REQIDENTIFIERNAMEFIELD);
	if (requestid <= 0) {
		g_warning("%s.%d: Request rejected - no request id."
		,	__FUNCTION__, __LINE__);
		return FALSE;
	}
	q = g_hash_table_lookup(self->resources, cmd->resourcename);
	if (NULL == q) {
		q = g_queue_new();
		g_hash_table_insert(self->resources, g_strdup(cmd->resourcename), q);
	}
	qelem = _resource_queue_qelem_new(cmd, self, cb, user_data, q);
	cmd->user_data = qelem;
	qelem->requestid = requestid;
	g_queue_push_tail(q, qelem);
	if (self->timerid < 0) {
		self->timerid = g_timeout_add_seconds(1, _resource_queue_runqueue, self);
	}
	return TRUE;
}

FSTATIC gboolean
_resource_queue_cancel(ResourceQueue* self, ConfigContext* request)
{
	gint64		requestid;
	const char*	resourcename;
	GHashTableIter	iter;
	RscQElem*	qelem = NULL;
	gpointer	pkey;
	gpointer	pvalue;
	requestid = request->getint(request, REQIDENTIFIERNAMEFIELD);
	if (requestid <= 0) {
		return FALSE;
	}

	resourcename = request->getstring(request, REQRSCNAMEFIELD);

	if (NULL == resourcename) {
		g_hash_table_iter_init(&iter, self->resources);
		while(g_hash_table_iter_next(&iter, &pkey, &pvalue)) {
			GQueue*	q = (GQueue*) pvalue;
			GList*	l;
			for (l=q->head; NULL != l; l=l->next) {
				RscQElem*	qe = CASTTOCLASS(RscQElem, l->data);
				if (qe->requestid == requestid) {
					qelem = qe;
					goto finalize;
				}
			}
		}
	}else{
		GQueue*	q = g_hash_table_lookup(self->resources, resourcename);
		if (NULL != q) {
			GList*	l;
			for (l=q->head; NULL != l; l=l->next) {
				RscQElem*	qe = CASTTOCLASS(RscQElem, l->data);
				if (qe->requestid == requestid) {
					qelem = qe;
					break;
				}
			}
		}
	}

	finalize:
	if (qelem) {
		_resource_queue_cmd_remove(self, qelem);
	}
	return NULL != qelem;


}

/// Remove the first instance of a ResourceCmd from a ResourceQueue
FSTATIC void
_resource_queue_cmd_remove(ResourceQueue* self, RscQElem* qelem)
{
	GQueue*	q = qelem->ourQ;

	if (g_queue_remove(q, qelem)) {
		if (g_queue_get_length(q) == 0) {
			g_hash_table_remove(self->resources, qelem->cmd->resourcename);
		}
	}else{
		g_return_if_reached();
	}
	_resource_queue_qelem_finalize(qelem);
}

/// Create a new RscQElem object
FSTATIC RscQElem*
_resource_queue_qelem_new(ResourceCmd* cmd, ResourceQueue* parent
,		ResourceCmdCallback callback, gpointer user_data, GQueue* Q)
{
	RscQElem*	self = MALLOCCLASS(RscQElem, sizeof(RscQElem));
	gint64		repeat;
	gint64		initdelay;
	self->queuetime = g_get_monotonic_time();
	self->cmd = cmd;
	REF(cmd);
	self->parent = parent;
	self->callback = callback;
	self->user_data = user_data;
	self->ourQ = Q;
	self->cancelme = FALSE;
	repeat = cmd->request->getint(cmd->request, REQREPEATNAMEFIELD);
	self->repeatinterval = (repeat > 0 ? repeat : 0);
	initdelay = cmd->request->getint(cmd->request, REQINITDELAYNAMEFIELD);
	initdelay = (initdelay > 0 ? initdelay : 0);
	cmd->starttime = self->queuetime + (initdelay*uSPERSEC);
	return self;
}

/// Finalize (free) a RscQElem object
FSTATIC void
_resource_queue_qelem_finalize(RscQElem* self)
{
	DEBUGMSG3("%s.%d: UNREF(self->cmd, refcount=%d)"
	,	__FUNCTION__, __LINE__,	self->cmd->baseclass._refcount);
	UNREF(self->cmd);
	FREECLASSOBJ(self);
}

/// Function for destroying data when an element is removed from self->resources hash table
FSTATIC void
_resource_queue_hash_data_destructor(gpointer dataptr)
{
	GQueue* 	q = (GQueue*) dataptr;
	GList*		l;

	for (l=q->head; NULL != l; l=l->next) {
		RscQElem*	qelem = CASTTOCLASS(RscQElem, l->data);
		_resource_queue_qelem_finalize(qelem); l->data = NULL; qelem = NULL;
	}
	g_queue_clear(q);
	q = NULL;
	dataptr = NULL;
}

/// Function for destroying keys when an element is removed from self->resources hash table
FSTATIC void
_resource_queue_hash_key_destructor(gpointer keyptr)
{
	g_free(keyptr);
	keyptr = NULL;
}

/// Examine our queues and run anything that needs running.
/// (this code is more expensive than it could be, but in practice it may not matter)
FSTATIC gboolean
_resource_queue_runqueue(gpointer pself)
{
	ResourceQueue* self = CASTTOCLASS(ResourceQueue, pself);
	GHashTableIter	iter;
	gpointer	key;
	gpointer	value;
	gint64		now = g_get_monotonic_time();
	gboolean	anyelems = FALSE;

	g_hash_table_iter_init(&iter, self->resources);

	while(g_hash_table_iter_next(&iter, &key, &value)) {
		GQueue*	rsc_q = (GQueue*)value;
		GList*	qelem;
		gboolean	any_running = FALSE;
		for (qelem=rsc_q->head; NULL != qelem; qelem=qelem->next) {
			RscQElem*	qe = CASTTOCLASS(RscQElem, qelem->data);
			anyelems = TRUE;
			if (qe->cmd->is_running) {
				any_running = TRUE;
				break;
			}
		}
		if (any_running) {
			continue;
		}
		DEBUGMSG2("%s.%d: No resource jobs are running.", __FUNCTION__, __LINE__);
		for (qelem=rsc_q->head; NULL != qelem; qelem=qelem->next) {
			RscQElem*	qe = CASTTOCLASS(RscQElem, qelem->data);
			if (now >= qe->cmd->starttime) {
				qe->cmd->execute(qe->cmd);
				break;
			}
		}
	}
	if (!anyelems) {
		g_source_remove(self->timerid);
		self->timerid = -1;
	}
	return anyelems;
}

/// Called when an operation completes - it calls requestor's callback if no repeat,
/// and requeues it if it is going to repeat
FSTATIC void
_resource_queue_endnotify
(	ConfigContext*	request
,	gpointer	user_data
,	enum HowDied	exittype
,	int		rc
,	int		signal
,	gboolean	core_dumped
,	const char*	stringresult)
{
	RscQElem*	self = CASTTOCLASS(RscQElem, user_data);


	g_queue_remove(self->ourQ, self);
	DEBUGMSG1("%s.%d: EXIT happened exittype:%d repeat:%d, cancelme:%d", __FUNCTION__, __LINE__
	,	exittype,  self->repeatinterval, self->cancelme);

	// Should this request repeat?
	if (EXITED_ZERO == exittype && self->repeatinterval > 0 && !self->cancelme) {
		DEBUGMSG1("%s.%d: Repeat request id " FMT_64BIT "d.", __FUNCTION__, __LINE__
		,	self->requestid);
		self->queuetime = g_get_monotonic_time();
		self->cmd->starttime = self->queuetime + (self->repeatinterval*uSPERSEC);
		g_queue_push_tail(self->ourQ, self);
		_resource_queue_runqueue(self->parent);
	}else{
		DEBUGMSG1("%s.%d: Don't repeat request id " FMT_64BIT "d.", __FUNCTION__, __LINE__
		,	self->requestid);
		self->callback(request, self->user_data, exittype, rc, signal, core_dumped
		,		stringresult);
		if (g_queue_get_length(self->ourQ) == 0) {
			g_hash_table_remove(self->parent->resources, self->cmd->resourcename);
		}
		_resource_queue_runqueue(self->parent);
		_resource_queue_qelem_finalize(self);
		self = NULL;
	}
}

///@}
