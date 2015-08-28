/**
 * @file
 * @brief Implements the LSB (Linux Standard Base aka SysV Init script) resource class
 * @details Implements the Open Cluster Framework resource agent API
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

#ifndef _RESOURCELSB_H
#define _RESOURCELSB_H
#include <projectcommon.h>
#include <assimobj.h>
#include <configcontext.h>
#include <resourcecmd.h>
#include <childprocess.h>
/**@{
 * @ingroup ResourceLSB
 * It does not implement any queueing, repeating events or such things.
 * It creates an object which will execute the resource action immediately when asked.
 * If this class invoked without any sort of queueing mechanism, or other safeguards
 * it can break the semantics of the underlying resources.
 *
 * Resources are expected to assume that no more than one resource action can be active
 * at a time for any given resource instance.
 *
 */


typedef struct _ResourceLSB	ResourceLSB;

struct _ResourceLSB{
	ResourceCmd		baseclass;	///< Base object: implements ref, unref, toString
	char *			lsbpath;
	ChildProcess*		child;
	char*			argv[3];	///< malloced
};

#define LSB_ROOT	"/etc/init.d"
#define STATUSOP	"status"
#define VALIDATEOP	"validate-all"

// This 'constructor' creates a subclass object, but returns a superclass object type.
WINEXPORT ResourceCmd* resourcelsb_new(guint structsize, ConfigContext* request
,			gpointer user_data, ResourceCmdCallback callback);
///@}
#endif/*_RESOURCELSB_H*/
