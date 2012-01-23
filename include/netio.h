/**
 * @file
 * @brief Defines an abstract Network I/O class
 * @details This is an abstract class and should not be instantiated directly.
 * It defines capabilities for sending and receiving @ref FrameSet "FrameSet"s.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _NETIO_H
#define _NETIO_H
#include <projectcommon.h>
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
	GIOChannel*	giosock;				///< Glib GIOChannel for this socket
	gint		_maxpktsize;
	ConfigContext*	_configinfo;
	PacketDecoder*	_decoder;
	SignFrame*	_signframe;
	Frame*		_cryptframe;
	Frame*		_compressframe;
	gboolean	(*bindaddr)			///<[in] Bind this NetIO to the given address
				(NetIO* self,		///<[in/out] Object to bind
				 const NetAddr*);	///<[in] Address to bind it to
	gint		(*getfd)			///<[in] Return file/socket descriptor
				(const NetIO* self);	///<[in] 'this' Object
	gsize		(*getmaxpktsize)		///< Return maximum packet size for this NetIO
				(const NetIO* self);	///< 'this' object
	gsize		(*setmaxpktsize)		///< Set maximum packet size
				(NetIO*,		///< 'this' object
				 gsize);		///< size to set max pkt size to
	void		(*sendaframeset)		///< Send a single FrameSet to a @ref NetIO
							///< @pre must have non-NULL _signframe
				(NetIO* self,		///<[in/out] 'this' object pointer
				 const NetAddr* dest,	///<[in] destination address
				 FrameSet* frameset)	///<[in] The FrameSet to send
						   ;	// ";" is here to work around a doxygen bug
	void		(*sendframesets)		///< Send a FrameSet list to a @ref NetIO
							///< @pre must have non-NULL _signframe
				(NetIO* self,		///<[in/out] 'this' object pointer
				 const NetAddr* dest,	///<[in] destination address
				 GSList* framesets)	///<[in] List of FrameSets to send
						   ;	// ";" is here to work around a doxygen bug
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
	void		(*finalize)			///< Finalize this NetIO object
				(NetIO* self);		///<[in] 'this' object
};
WINEXPORT NetIO*	netio_new(gsize objsize, ConfigContext*, PacketDecoder*);
							///< Don't call this directly! - this is an abstract class...
///@}

#endif /* _NETIO_H */
