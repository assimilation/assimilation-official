/**
 * @file
 * @brief Defines Listener interfaces for packets coming from the Collective Authority
 * @details Each of the packets thus received are acted on appropriately.
 * @todo It should authorize the sender of the FrameSet.
 *
 *
 * @author &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _AUTHLISTENER_H
#define _AUTHLISTENER_H
#include <projectcommon.h>
#include <netaddr.h>
#include <listener.h>
typedef struct _AuthListener AuthListener;
#include <netgsource.h>

///@{
/// @ingroup AuthListener
typedef struct _ObeyFrameSetTypeMap ObeyFrameSetTypeMap;


/// This is the @ref AuthListener object - which (authorizes and) obeys packets from the Authority
//
struct _AuthListener {
	Listener	baseclass;
	GHashTable*	actionmap;
};


typedef void    (*AuthListenerAction)(AuthListener*, FrameSet*, NetAddr*);
///	Structure associating @ref FrameSet types with actions to perform when they're received
struct _ObeyFrameSetTypeMap {
	int	framesettype;		///< @ref FrameSet type
	AuthListenerAction action;	///< What to do when we get it
};


/// Create an AuthListener
WINEXPORT AuthListener* authlistener_new(ObeyFrameSetTypeMap* map
,					 ConfigContext* config, gsize listen_objsize);
///@}
#endif /* _AUTHLISTENER_H */
