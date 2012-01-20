/**
 * @file
 * @brief Implements Configuration Context class
 * @details This class holds all the information concerning our basic configuration -
 * things like our signature @ref SignFrame, the public key of our master, and the
 * address of the Collective Management Authority and so on...
 *
 * @author &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _CONFIGCONTEXT_H
#define _CONFIGCONTEXT_H
#include <projectcommon.h>
#include <netaddr.h>
#include <signframe.h>
#include <address_family_numbers.h>
typedef struct _ConfigContext ConfigContext;

///@{
/// @ingroup ConfigContext

/// This is the base @ref ConfigContext object providing configuration context for our clients,
/// and is managed by our @ref ProjectClass system.
/// It provides the analog of global variables for remembering configuration defaults, etc.
struct _ConfigContext {
	guint32		deadtime;
	guint32		hbtime;
	guint32		warntime;
	NetAddr*	collectivemgmtaddr;
	SignFrame*	signframe;
	void		(*setmgmtaddr)(ConfigContext*, NetAddr*);
	void		(*setsignframe)(ConfigContext*, SignFrame*);
	void		(*_finalize)(ConfigContext*);
};
WINEXPORT ConfigContext*	configcontext_new(gsize objsize);

#define	CONFIG_DEFAULT_DEADTIME	10
#define	CONFIG_DEFAULT_HBTIME	1
#define	CONFIG_DEFAULT_WARNTIME	3
#define	CONFIG_DEFAULT_ADDR	{127,0,0,1}
#define	CONFIG_DEFAULT_ADDRTYPE	ADDR_FAMILY_IPV4
#define	CONFIG_DEFAULT_SIGNFRAME_TYPE	G_CHECKSUM_SHA256
///@}
#endif /* _CONFIGCONTEXT_H */
