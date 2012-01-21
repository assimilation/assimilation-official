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
	int		_refcount;			///< Reference count (private)
	void		(*ref)(ConfigContext*);		///< Increment reference count
	void		(*unref)(ConfigContext*);	///< Decrement reference count
	void		(*_finalize)(ConfigContext*);	///< Free object (private)
	GHashTable*	_intvalues;			///< Integer value table
	GHashTable*	_strvalues;			///< String value table
	GHashTable*	_framevalues;			///< Frame value table
	GHashTable*	_addrvalues;			///< NetAddr value table
	gint		(*getint)(ConfigContext*, const char *name);	///< Get integer value
	void		(*setint)(ConfigContext*, const char *name, gint value);	///< Set integer value
	const char*	(*getstring)(ConfigContext*, const char *name);	///< Get String value
	void		(*setstring)(ConfigContext*, const char *name, const char *value);
	Frame*		(*getframe)(ConfigContext*, const char*);	///< Get Frame value
	void		(*setframe)(ConfigContext*, const char*,Frame*);///< Set Frame value
	NetAddr*	(*getaddr)(ConfigContext*, const char* name);	///< Get NetAddr value
	void		(*setaddr)(ConfigContext*,const char *,NetAddr*);///< Set NetAddr value
};
WINEXPORT ConfigContext*	configcontext_new(gsize objsize); ///< ConfigContext constructor

#define	CONFIG_DEFAULT_DEADTIME	30		///< Default "deadtime"
#define	CONFIG_DEFAULT_HBTIME	3		///< Default heartbeat interval
#define	CONFIG_DEFAULT_WARNTIME	10		///< Default warning time
#define	CONFIG_DEFAULT_ADDR	{127,0,0,1}
#define	CONFIG_DEFAULT_ADDRTYPE	ADDR_FAMILY_IPV4
#define	CONFIG_DEFAULT_SIGNFRAME_TYPE	G_CHECKSUM_SHA256

#define CONFIGNAME_DEADTIME	"deadtime"	///< How long w/o heartbeats before declaring a system dead?
#define CONFIGNAME_WARNTIME	"warntime"	///< How long w/o heartbeats before whining?
#define CONFIGNAME_HBTIME	"hbtime"	///< How long to wait between heartbeats?
#define CONFIGNAME_CMAADDR	"cmaaddr"	///< Address of the Collective Management authority
#define CONFIGNAME_OUTSIG	"outsig"	///< SignFrame to use to sign outbound packets

/// Default values for some (integer) configuration values
#define	CONFIGINTDEFAULTS {					\
	{CONFIGNAME_DEADTIME,	CONFIG_DEFAULT_DEADTIME},	\
	{CONFIGNAME_WARNTIME,	CONFIG_DEFAULT_WARNTIME},	\
	{CONFIGNAME_HBTIME,	CONFIG_DEFAULT_HBTIME},		\
	}
///@}
#endif /* _CONFIGCONTEXT_H */
