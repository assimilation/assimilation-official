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
#include <compressframe.h>
#include <configcontext.h>
#include <packetdecoder.h>

///@{
/// @ingroup NetIO
typedef struct _NetIOstats NetIOstats;
struct _NetIOstats {
	guint64		recvcalls;	///< How many recvfrom calls have we done?
	guint64		pktsread;	///< How many packets have been successfully read?
	guint64		fsreads;	///< How many @ref FrameSet  were successfully read?
	guint64		sendcalls;	///< How many sendto calls have we done?
	guint64		pktswritten;	///< How many packets have been successfully written?
	guint64		fswritten;	///< How many @ref FrameSet  were successfully written?
	guint64		reliablesends;	///< How many reliable FrameSets have we sent?
	guint64		reliablereads;	///< How many reliable FrameSets have we read?
	guint64		ackssent;	///< How many ACKs have we sent?
	guint64		acksrecvd;	///< How many ACKs have we received?
};
typedef struct _NetIO NetIO;

/// This is a basic @ref NetIO abstract class for doing network I/O.
/// It is an abstract class from which you <b>must</b> make subclasses,
/// and is managed by our @ref ProjectClass system.
struct _NetIO {
	AssimObj	baseclass;
	NetIOstats	stats;				///< Net I/O stats
	GIOChannel*	giosock;			///< Glib GIOChannel for this socket
	gint		_maxpktsize;			///< Maximum packet size for this transport
	ConfigContext*	_configinfo;			///< I/O and other configuration information
	PacketDecoder*	_decoder;			///< Decodes packets into FrameSets
	SignFrame*	_signframe;			///< Signature frame to use in signing FrameSets
	CompressFrame*	_compressframe;			///< Compression frame to use in compressing FrameSets
	GHashTable*	aliases;			///< IP address aliases for received packets
	double		_rcvloss;			///< private: Receive loss fraction
	double		_xmitloss;			///< private: Transmit loss fraction
	gboolean	_shouldlosepkts;		///< private: TRUE to enable packet loss...
	gboolean	is_encrypted;			///< TRUE if we're sending encrypted packets
	gboolean	(*input_queued)		///<[in] TRUE if input is queued ready to be read
				(const NetIO* self);	///< The Object to examine
	gboolean	(*bindaddr)		///<[in] Bind this NetIO to the given address
				(NetIO* self,		///<[in/out] Object to bind
				 const NetAddr*,	///<[in] Address to bind it to
				 gboolean silent)	///<[in] TRUE if no message on failure
				;			// (separate line to work around doxygen bug)
	NetAddr*	(*boundaddr)(const NetIO* self);///<[in] Object to return bound address/port of
	gboolean	(*mcastjoin)		///<Join multicast group
				(NetIO* self,		///<[in/out] Object to bind
				 const NetAddr*,	///<[in] Mcast addr to join
				 const NetAddr*);	///<[in] local if addr or NULL
	gboolean	(*setmcast_ttl)		///< Set ipv4 multicast TTL
				(NetIO* self,		///<[in/out] Object to set mcast TTL for
				 guint8 ttl)		///<[in] Multicast TTL value
						   ;	// ";" is here to work around a doxygen bug
	void		(*addalias)(NetIO*, NetAddr*, NetAddr*);///< Add an alias to our received address alias table
	
	gint		(*getfd)		///<[in] Return file/socket descriptor
				(const NetIO* self);	///<[in] 'this' Object
	void		(*setblockio)		///<[in] Set blocking/non-blocking mode
				(const NetIO* self,	///<[in/out] 'this' Object.
				 gboolean blocking)	///<[in] TRUE if you want it to block
						   ;	// ";" is here to work around a doxygen bug
	gsize		(*getmaxpktsize)	///< Return maximum packet size for this NetIO
				(const NetIO* self);	///< 'this' object
	gsize		(*setmaxpktsize)	///< Set maximum packet size
				(NetIO*,		///< 'this' object
				 gsize);		///< size to set max pkt size to
	void		(*sendaframeset)	///< Send a FrameSet list to a @ref NetIO
							///< @pre must have non-NULL _signframe
				(NetIO* self,		///<[in/out] 'this' object pointer
				 const NetAddr* dest,	///<[in] destination address
				 FrameSet* frameset)	///<[in] FrameSet to send
						   ;	// ";" is here to work around a doxygen bug
	void		(*sendframesets)	///< Send a FrameSet list to a @ref NetIO
							///< @pre must have non-NULL _signframe
				(NetIO* self,		///<[in/out] 'this' object pointer
				 const NetAddr* dest,	///<[in] destination address
				 GSList* framesets)	///<[in] List of FrameSets to send
						   ;	// ";" is here to work around a doxygen bug
	GSList*		(*recvframesets)	///< Receive a single datagram's framesets
							///<@return GSList of FrameSets from packet
				(NetIO*,		///<[in/out] 'this' object
				 NetAddr** src);	///[out] source address of return result
	gboolean	(*sendareliablefs)	///< Reliably send a single FrameSet (if possible)
							///< @pre must have non-NULL _signframe
			    (NetIO*self,		///<[in/out] 'this' object pointer
			     NetAddr* dest,		///<[in] destination address
			     guint16 queueid,		///<[in] The queue id to send it to
			     FrameSet* frameset)	///<[in] The FrameSet to send
						   ;	// ";" is here to work around a doxygen bug
	gboolean	(*sendreliablefs)	///< Reliably send multiple FrameSets (if possible)
							///< @pre must have non-NULL _signframe
			    (NetIO*self,		///<[in/out] 'this' object pointer
			     NetAddr* dest,		///<[in] destination address
			     guint16 queueid,		///<[in] The queue id to send it to
			     GSList* fslist)		///<[in] The list of FrameSets to send
						   ;	// ";" is here to work around a doxygen bug
	gboolean	(*ackmessage)		///< User-level ACK of a message sent reliably
				(NetIO* self,	///<[in/out] 'this' object pointer
				 NetAddr* dest,		///<[in] destination address
				 FrameSet* frameset)	///<[in] The FrameSet to ACK - note that it must
				 			///< have a sequence number.  Good thing to remember
							///< that the client (that is <i>you</i> has to 
							///< ACK packets or they won't get ACKed -
							///< which will totally ball things up...
						   ;	// ";" is here to work around a doxygen bug
	gboolean	(*supportsreliable)	///< return TRUE if this object supports reliable transport
				(NetIO* self)		///<[in/out] 'this' object pointer
						   ;	// ";" is here to work around a doxygen bug
	gboolean	(*outputpending)	///< return TRUE if this object has output pending
				(NetIO* self)		///<[in/out] 'this' object pointer
						   ;	// ";" is here to work around a doxygen bug
	void		(*closeconn)		///< Flush packets in queues to this address
			      (NetIO* self,	///< 'this' object pointer
			       guint16 qid,		///< Queue id for this connection
			       const NetAddr* destaddr) ///< Address we're flushing for
						   ;	// ";" is here to work around a doxygen bug
	SignFrame*	(*signframe)		///< return a copied SignFrame for use in sending
				(NetIO*self);		///<[in]
	CompressFrame*	(*compressframe)	///< return a copied compression frame for sending
				(NetIO*self)		///<[in] 'this' object
						   ;	// ";" is here to work around a doxygen bug
	void		(*setpktloss)		///< Set desired fraction of packet loss - TESTING ONLY!
				(NetIO* self,		///<[in/out] 'this' object
				 double rcv,		///< Packet receive loss fraction (0:1]
				 double xmit)		///< Packet transmission loss (0:1]
						   ;	// ";" is here to work around a doxygen bug
	void		(*enablepktloss)	///< enable packet loss (as set above)
				(NetIO* self,		///<[in/out] 'this' object	
				 gboolean enable)	///<TRUE == enable, FALSE == disable
						   ;	// ";" is here to work around a doxygen bug
};
WINEXPORT NetIO*	netio_new(gsize objsize, ConfigContext*, PacketDecoder*);
							///< Don't call directly! - this is an abstract class...
WINEXPORT gboolean	netio_is_dual_ipv4v6_stack(void);
///@}

#endif /* _NETIO_H */
