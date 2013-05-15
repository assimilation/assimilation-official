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

/**
 *	self->resources is a hash table of GQueue indexed by the resource name.
 *	The resource name is a pointer into a field in the ResourceCmd.
 *	Each GQueue element has a ResourceCmd* as its data element.
 *	As a given ResourceCmd completes, we remove it from its queue.
 *	If it repeats, then we put it on the end of its queue with a delay before executing.
 *		Should we have a different data structure for when it's due to run again?
 *		Or should we add the "time to run again" to the ResourceCmd structure?
 *		What else do we need to keep track of?  Is it running?  That makes sense to
 *			add to the ResourceCmd structure...
 *
 */
FSTATIC void _resource_queue_hash_data_destructor(gpointer dataptr);
FSTATIC void _resource_queue_hash_key_destructor(gpointer dataptr);
FSTATIC void _resource_queue_cmd_remove(ResourceQueue* self, ResourceCmd* cmd);
FSTATIC void _resource_queue_cmd_append(ResourceQueue* self, ResourceCmd* cmd);
FSTATIC void _resource_queue_finalize(AssimObj* aself);

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

	self->resources = g_hash_table_new_full(g_str_hash, g_str_equal
	,		_resource_queue_hash_key_destructor, _resource_queue_hash_data_destructor);

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

/// Append a ResourceCmd to a ResourceQueue
FSTATIC void
_resource_queue_cmd_append(ResourceQueue* self, ResourceCmd* cmd)
{
	GQueue*	q;

	q = g_hash_table_lookup(self->resources, cmd->resourcename);
	if (NULL == q) {
		q = g_queue_new();
		g_hash_table_insert(self->resources, g_strdup(cmd->resourcename), q);
	}
	REF(cmd);
	g_queue_push_tail(q, cmd);
}

/// Remove the first instance of a ResourceCmd from a ResourceQueue
FSTATIC void
_resource_queue_cmd_remove(ResourceQueue* self, ResourceCmd* cmd)
{
	GQueue*	q;

	q = g_hash_table_lookup(self->resources, cmd->resourcename);
	g_return_if_fail(q != NULL);

	if (g_queue_remove(q, cmd)) {
		UNREF(cmd);
	}else{
		g_return_if_reached();
	}
	if (g_queue_get_length(q) == 0) {
		g_hash_table_remove(self->resources, cmd->resourcename);
	}
}

/// Function for destroying data when an element is removed from self->resources hash table
FSTATIC void
_resource_queue_hash_data_destructor(gpointer dataptr)
{
	GQueue* 	q = (GQueue*) dataptr;
	GList*		l;

	for (l=q->head; NULL != l; l=l->next) {
		ResourceCmd*	cmd = CASTTOCLASS(ResourceCmd, l->data);
		UNREF(cmd);
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

///@}
