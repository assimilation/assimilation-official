/**
 * @file
 * @brief Implements the netioudp class - providing UDP specialization of the netio class.
 * @details It primarily contains the constructor for the class, since all other netio member
 * functions seem suitable for this class as well.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#include <unistd.h>
#include <memory.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <address_family_numbers.h>
#include <proj_classes.h>
#include <netioudp.h>
#include <frameset.h>


/// @defgroup NetIOudp NetIOudp class
///@{
///@ingroup NetIO
/// A NetIOudp object performs network writes and reads on UDP sockets.
/// It is a class from which we might eventually make subclasses (but it doesn't seem likely),
/// and is managed by our @ref ProjectClass system.
/// Except for the constructor, it is identical to the NetIO class.

/// Construct new UDP NetIO object (and its socket, etc)
NetIOudp*
netioudp_new(gsize objsize)	/// Size of NetIOudp object, or zero.
{
	NetIO*		iret;
	NetIOudp*	ret;
	gint		sockfd;

	if (objsize < sizeof(NetIOudp)) {
		objsize = sizeof(NetIOudp);
	}
	iret = netio_new(objsize);
	proj_class_register_subclassed(iret, "NetIOudp");
	ret = CASTTOCLASS(NetIOudp, iret);
	sockfd = socket(AF_INET6, SOCK_DGRAM, IPPROTO_UDP);
#ifdef WIN32
	{
		u_long iMode=1;
		ioctlsocket(sockfd, FIONBIO, &iMode);
	}
	ret->baseclass.giosock = g_io_channel_win32_new_socket(sockfd);
#else
	fcntl(sockfd, F_SETFL, O_NONBLOCK);
	ret->baseclass.giosock = g_io_channel_unix_new(sockfd);
#endif
	g_io_channel_set_close_on_unref(ret->baseclass.giosock, TRUE);
	return ret;
}
///@}
