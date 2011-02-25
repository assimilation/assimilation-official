/**
 * @file
 * @brief Implements UDP network I/O (NetIOudp) class.
 * @details It knows how to construct UDP sockets, write to them, bind them, and get packets from them.
 * This is a subclass of the @ref NetIO class.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _NETIOUDP_H
#define _NETIOUDP_H
#include <glib.h>
#include <netio.h>
typedef struct _NetIOudp NetIOudp;

/// This is a UDP NetIO object.
/// It can perform network writes and reads, binds, etc. for UDP sockets
/// It is a class from which we might eventually make subclasses (but I'm not quite sure why),
/// and is managed by our @ref ProjectClass system.
///@{
/// @ingroup NetIOudp
struct _NetIOudp {
	NetIO		baseclass;	///< Base class (NetIO) object.
	GDestroyNotify	_finalize;	///< Saved (base class) finalize routine
};
NetIOudp*	netioudp_new(gsize objsize);
///@}

#endif /* _NETIOUDP_H */
