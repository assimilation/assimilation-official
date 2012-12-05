/**
 * @file
 * @brief Implements the Reliable UDP network I/O transport (ReliableUDP) class.
 * @details It knows how to construct UDP sockets, write to them, bind them, and get packets from them.
 * This is a subclass of the @ref NetIOUDP class.
 *
 *
 * This file is part of the Assimilation Project.
 *
 * @author &copy; Copyright 2011, 2012 - Alan Robertson <alanr@unix.sh>
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

#ifndef _RELIABLE_UDP_H
#define _RELIABLE_UDP_H
#include <projectcommon.h>
#include <glib.h>
#include <netioudp.h>
#include <netaddr.h>
#include <frameset.h>
#include <fsprotocol.h>

///@{
/// @ingroup ReliableUDP
typedef struct _ReliableUDP ReliableUDP;
/// NetIOudp  is a @ref NetIOudp subclass specialized to provide reliable UDP connections.
/// It can perform network writes and reads, binds, etc. for UDP sockets
/// It is a class from which one could make subclasses, and is managed by our @ref ProjectClass system.
struct _ReliableUDP {
	NetIOudp	baseclass;	///< Base class (NetIO) object.
	FsProtocol*	_protocol;	///< Queuing, ordering, retransmission and ACKing discipline
	double		_rcvloss;	///< Fraction of input packets to lose
	double		_xmitloss;	///< Fraction of output packets to lose
	gboolean	_shouldlosepkts;///< TRUE if we should force packet loss - FALSE is default :-D
	gboolean	(*sendreliable)		///< Send a single FrameSet via @ref ReliableUDP
							///< @pre must have non-NULL _signframe
			    (ReliableUDP*self,		///<[in/out] 'this' object pointer
			     NetAddr* dest,		///<[in] destination address
			     guint16 queueid,		///<[in] The queue id to send it to
			     FrameSet* frameset)	///<[in] The FrameSet to send
						   ;	// ";" is here to work around a doxygen bug
	gboolean	(*sendreliableM)	///< Send a multiple FrameSets via @ref ReliableUDP
							///< @pre must have non-NULL _signframe
			    (ReliableUDP*self,		///<[in/out] 'this' object pointer
			     NetAddr* dest,		///<[in] destination address
			     guint16 queueid,		///<[in] The queue id to send it to
			     GSList* fslist)		///<[in] The list of FrameSets to send
						   ;	// ";" is here to work around a doxygen bug
	gboolean	(*ackmessage)		///< ACK a message
				(ReliableUDP* self,	///<[in/out] 'this' object pointer
				 NetAddr* dest,		///<[in] destination address
				 FrameSet* frameset)	///<[in] The FrameSet to ACK - note that it must
				 			///< have a sequence number.  Good thing to remember
							///< that the client (that is <i>you</i> has to 
							///< ACK or NAK packets or they won't get ACKed -
							///< which will totally ball things up...
						   ;	// ";" is here to work around a doxygen bug
	gboolean	(*nackmessage)		///< NAK a message
				(ReliableUDP* self,	///<[in/out] 'this' object pointer
				 NetAddr* dest,		///<[in] destination address
				 FrameSet* frameset)	///<[in] The FrameSet to NAK - note that it must
				 			///< have a sequence number
						   ;	// ";" is here to work around a doxygen bug
	void		(*setpktloss)		/// Force loss of packets FOR TESTING ONLY
			    (ReliableUDP* self,		///<[in/out] 'this' object pointer
			     double rcvloss,		/// Fraction of input packets to "lose" at random
			     double xmitloss)		/// Fraction of output packets to "lose" at random
						   ;	// ";" is here to work around a doxygen bug
	void		(*enablepktloss)	/// Enable or disable testing packet loss
			     (ReliableUDP* self,	///<[in/out] 'this' object pointer
			      gboolean enable)		/// TRUE to enable packet loss
						   ;	// ";" is here to work around a doxygen bug
	void		(*flushall)		///< Flush packets in queues to this address
			      (ReliableUDP* self,	///< 'this' object pointer
			       const NetAddr* destaddr, ///< Address we're flushing for
			       enum ioflush flushtype)  ///< Flush input, output or both
						   ;	// ";" is here to work around a doxygen bug
};
WINEXPORT ReliableUDP* reliableudp_new(gsize objsize, ConfigContext* config, PacketDecoder* decoder);
///@}

#endif /* _RELIABLE_UDP_H */
