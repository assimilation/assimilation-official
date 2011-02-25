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
#include <glib.h>
#include <netaddr.h>
#include <frame.h>
#include <signframe.h>

///@{
/// @ingroup NetIO
typedef struct _NetIO NetIO;

/// This is a basic @ref NetIO abstract class for doing network I/O.
/// It is an abstract class from which you <b>must</b> make subclasses,
/// and is managed by our @ref ProjectClass system.
struct _NetIO {
	GIOChannel*	giosock;				///< Glib GIOChannel for this socket
	SignFrame*	_signframe;
	Frame*		_cryptframe;
	Frame*		_compressframe;
	gint		_maxpktsize;
	gboolean	(*bindaddr)(NetIO*, const NetAddr*);	///< Bind this object to the given address
	gint		(*getfd)(const NetIO* self);		///< Return file/socket descriptor
	gsize		(*getmaxpktsize)(const NetIO* self);	///< Return maximum packet size
	gsize		(*setmaxpktsize)(NetIO*, gsize);	///< Set maximum packet size
	void		(*sendframesets)			///< Send a FrameSet list.
								///< @pre must have non-NULL _signframe
				(NetIO* self,			///<[in/out] 'this' object pointer
				 const NetAddr* destaddr,	///<[in] destination address
				 GSList* framesets)		///<[in] List of FrameSets to send
				 ;
	GSList*		(*recvframesets)(NetIO*, NetAddr** src);///< Receive a single datagram's framesets
	SignFrame*	(*signframe)(NetIO*self);		///< return a copied SignFrame
	Frame*		(*cryptframe)(NetIO*self);		///< return a copied encryption frame
	Frame*		(*compressframe)(NetIO*self);		///< return a copied compression frame
	void		(*set_signframe)(NetIO* self, SignFrame* sign);//< Set digital signature object
	void		(*set_cryptframe)(NetIO* self, Frame* crypt);//< Set encryption object
	void		(*set_compressframe)(NetIO* self, Frame* compress);//< Set compression object
	void		(*finalize)(NetIO* self);		///< Finalize this NetIO object
};
NetIO*	netio_new(gsize objsize); // Don't call this directly! - this is an abstract class...
///@}

#endif /* _NETIO_H */
