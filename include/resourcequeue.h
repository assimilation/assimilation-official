/**
 * @file
 * @brief Implements the resource queue class
 * @details Creates an queue object managing resource objects.
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

#ifndef _RESOURCEQUEUE_H
#define _RESOURCEQUEUE_H
#include <projectcommon.h>
#include <assimobj.h>
#include <configcontext.h>
#include <resourcecmd.h>
/**@{
 * @ingroup ResourceQueue
 * This is the Queue object for creating and managing @ref ResourceCmd objects.
 *
 * We are given constructor parameters to Resource objects, and then we create queues for managing
 * work for that particular resource name, and then we execute the requested operations on the
 * resources as we are able.  We never execute a resource action until the previous resource
 * action on the the same resource name completes or times out.
 * Note that resource actions are performed asynchronously.
 * The request can contain a repeat interval in it.
 * Repeated requests are performed every "n" seconds - but that actually means
 * it is "n" seconds after the operation completes before it is queued to run again.
 * So if it takes 5 seconds to run and has a 5 second repeat interval, it will actually run
 * every 10 seconds.
 *
 */
typedef struct _ResourceQueue ResourceQueue;


struct _ResourceQueue {
	AssimObj	baseclass;	///< Base object: implements ref, unref, toString
	GHashTable*	resources;	///< Table of resource queues
	gint		timerid;	///< id of our run timer
	void (*settimeout)(ResourceQueue*, guint timeout);	//< Set default timeout
	guint (*gettimeout)(ResourceQueue*, guint timeout);	//< Return default timeout
	gboolean (*Qcmd)(ResourceQueue* self			//< Our R.Q. object
,			ConfigContext* request			//< The request to perform
,			ResourceCmdCallback callback		//< Callback to call when done
,			gpointer user_data);			//< User data to pass callback
	gboolean (*cancel)(ResourceQueue* self			//< Our R.Q. object
,			ConfigContext* request);		//< Request to cancel
	gboolean (*cancelall)(ResourceQueue* self);		//< Cancel all requests
};
WINEXPORT ResourceQueue* resourcequeue_new(guint structsize);		//< Construct new R.Q.

///@}
#endif/*_RESOURCEQUEUE_H*/
