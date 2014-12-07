/**
 * @file
 * @brief Implements the netioudp class - providing UDP specialization of the netio class.
 * @details It primarily contains the constructor for the class, since all other netio member
 * functions seem suitable for this class as well.
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
#include <sys/types.h>
#ifdef _MSC_VER
#	include <winsock2.h>
#else
#	include <unistd.h>
#	include <sys/socket.h>
#	include <netinet/in.h>
#endif
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
netioudp_new(gsize objsize		///<[in] Size of NetIOudp object, or zero.
	,    ConfigContext* config	///<[in/out] config info
	,    PacketDecoder* decoder)	///<[in/out] packet decoder
{
	NetIO*		iret;
	NetIOudp*	ret;
	gint		sockfd;

	if (objsize < sizeof(NetIOudp)) {
		objsize = sizeof(NetIOudp);
	}
	iret = netio_new(objsize, config, decoder);
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
	ret->baseclass.giosock = g_io_channel_unix_new(sockfd);
#endif
	g_io_channel_set_close_on_unref(ret->baseclass.giosock, TRUE);
	return ret;
}

///@}
