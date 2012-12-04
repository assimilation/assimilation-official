/**
 * @file
 * @brief Defines an abstract Network I/O class
 * @details This is an abstract class and should not be instantiated directly.
 * It defines capabilities for sending and receiving @ref FrameSet "FrameSet"s.
 *
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

#ifndef _NETIO_H
#define _NETIO_H
#include <projectcommon.h>
#include <assimobj.h>
#include <glib.h>
#include <netaddr.h>
#include <frame.h>
#include <signframe.h>
#include <configcontext.h>
#include <packetdecoder.h>

///@{
/// @ingroup NetIO
typedef struct _NetIO NetIO;

/// This is a basic @ref NetIO abstract class for doing network I/O.
/// It is an abstract class from which you <b>must</b> make subclasses,
/// and is managed by our @ref ProjectClass system.
struct _NetIO {
	AssimObj	baseclass;
	GIOChannel*	giosock;			///< Glib GIOChannel for this socket
	gint		_maxpktsize;			///< Maximum packet size for this transport
	ConfigContext*	_configinfo;			///< I/O and other configuration information
	PacketDecoder*	_decoder;			///< Decodes packets into FrameSets
	SignFrame*	_signframe;			///< Signature frame to use in signing FrameSets
	Frame*		_cryptframe;			///< Encryption frame to use in encrypting FrameSets
	Frame*		_compressframe;			///< Compression frame to use in compressing FrameSets
	gboolean	(*bindaddr)			///<[in] Bind this NetIO to the given address
				(NetIO* self,		///<[in/out] Object to bind
				 const NetAddr*,	///<[in] Address to bind it to
				 gboolean silent)	///<[in] TRUE if no message on failure
				;			// (separate line to work around doxygen bug)
	NetAddr*	(*boundaddr)(const NetIO* self);///<[in] Object to return bound address/port of
	gboolean	(*mcastjoin)			///<Join multicast group
				(NetIO* self,		///<[in/out] Object to bind
				 const NetAddr*,	///<[in] Mcast addr to join
				 const NetAddr*);	///<[in] local if addr or NULL
	gboolean	(*setmcast_ttl)
				(NetIO* self,		///<[in/out] Object to set mcast TTL for
				 guint8 ttl);		///<[in] Multicast TTL value
	gint		(*getfd)			///<[in] Return file/socket descriptor
				(const NetIO* self);	///<[in] 'this' Object
	void		(*setblockio)			///<[in] Set blocking/non-blocking mode
				(const NetIO* self,	///<[in/out] 'this' Object.
				 gboolean blocking)	///<[in] TRUE if you want it to block
				;
	gsize		(*getmaxpktsize)		///< Return maximum packet size for this NetIO
				(const NetIO* self);	///< 'this' object
	gsize		(*setmaxpktsize)		///< Set maximum packet size
				(NetIO*,		///< 'this' object
				 gsize);		///< size to set max pkt size to
	void		(*sendaframeset)		///< Send a FrameSet list to a @ref NetIO
							///< @pre must have non-NULL _signframe
				(NetIO* self,		///<[in/out] 'this' object pointer
				 const NetAddr* dest,	///<[in] destination address
				 FrameSet* frameset)	///<[in] FrameSet to send
						   ;	// ";" is here to work around a doxygen bug
	void		(*sendframesets)		///< Send a FrameSet list to a @ref NetIO
							///< @pre must have non-NULL _signframe
				(NetIO* self,		///<[in/out] 'this' object pointer
				 const NetAddr* dest,	///<[in] destination address
				 GSList* framesets)	///<[in] List of FrameSets to send
						   ;	// ";" is here to work around a doxygen bug
#if 0
	void		(*sendamessage)			///< RELIABLY send a single FrameSet to a @ref NetIO
				(NetIO* self,		///<[in/out] 'this' object pointer
				 const NetAddr* dest,	///<[in] destination address
				 FrameSet* frameset)	///<[in] The FrameSet to send
						   ;	// ";" is here to work around a doxygen bug
	void		(*sendmessages)			///< RELIABLY Send a FrameSet list to a @ref NetIO
							///< @pre must have non-NULL _signframe
				(NetIO* self,		///<[in/out] 'this' object pointer
				 const NetAddr* dest,	///<[in] destination address
				 GSList* framesets)	///<[in] List of FrameSets to send
						   ;	// ";" is here to work around a doxygen bug
#endif
	GSList*		(*recvframesets)		///< Receive a single datagram's framesets
							///<@return GSList of FrameSets from packet
				(NetIO*,		///<[in/out] 'this' object
				 NetAddr** src);	///[out] source address of return result
	SignFrame*	(*signframe)			///< return a copied SignFrame for use in sending
				(NetIO*self);		///<[in]
	Frame*		(*cryptframe)			///< return a copied encryption frame for sending
				(NetIO*self);		///<[in] 'this' object
	Frame*		(*compressframe)		///< return a copied compression frame for sending
				(NetIO*self)		///<[in] 'this' object
						   ;	// ";" is here to work around a doxygen bug
};
WINEXPORT NetIO*	netio_new(gsize objsize, ConfigContext*, PacketDecoder*);
							///< Don't call this directly! - this is an abstract class...
WINEXPORT gboolean	netio_is_dual_ipv4v6_stack(void);
///@}

#endif /* _NETIO_H */
