/**
 * @file
 * @brief Implements Configuration Context class
 * @details This class holds all the information concerning our basic configuration -
 * things like our signature @ref SignFrame, the public key of our master, and the
 * address of the Collective Management Authority and so on...
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

#ifndef _CONFIGCONTEXT_H
#define _CONFIGCONTEXT_H
#include <projectcommon.h>
#include <assimobj.h>
#include <netaddr.h>
#include <signframe.h>
#include <address_family_numbers.h>

///@{
/// @ingroup ConfigContext

/// This is the base @ref ConfigContext object providing configuration context for our clients,
/// and is managed by our @ref ProjectClass system.
/// It provides the analog of global variables for remembering configuration defaults, etc,
/// but in a hash table, with capabilities to go to and from JSON.

typedef struct _ConfigContext ConfigContext;

enum ConfigValType {
	CFG_EEXIST,	// Name does not exist
	CFG_NULL,	// JSON null object
	CFG_BOOL,	// JSON boolean object
	CFG_INT64,	// Signed 64-bit Integer
	CFG_STRING,	// String
	CFG_FLOAT,	// Floating point
	CFG_ARRAY,	// JSON Array
	CFG_CFGCTX,	// ConfigContext (recursive) object
	CFG_NETADDR,	// NetAddr object
	CFG_FRAME,	// Frame object
};
typedef struct _ConfigValue ConfigValue;
struct _ConfigValue {
	AssimObj		baseclass;
	enum ConfigValType	valtype;
	union {
		gint64		intvalue;	// Or boolean
		double		floatvalue;
		GSList*		arrayvalue;	// Each element pointing to a ConfigValue object
		char*		strvalue;	// A string
		ConfigContext*	cfgctxvalue;	// Another ConfigContext object
		NetAddr*	addrvalue;	// A NetAddr value
		Frame*		framevalue;	// A Frame value
	}u;
};

struct _ConfigContext {
	AssimObj	baseclass;
	GHashTable*	_values;						///< table of Values
	gint64		(*getint)(const ConfigContext*, const char *name);	///< Get integer value
	void		(*setint)(ConfigContext*, const char *name, gint value);///< Set integer value
	gboolean	(*appendint)(ConfigContext*, const char *name, gint value);///< Set integer value
	gboolean	(*getbool)(const ConfigContext*, const char *name);	///< Get boolean value
	void		(*setbool)(ConfigContext*, const char *name, gboolean);	///< Set bool value
	gboolean	(*appendbool)(ConfigContext*, const char *name, gboolean);	///< Set bool value
	double		(*getdouble)(const ConfigContext*, const char *name);	///< Get double value
	void		(*setdouble)(ConfigContext*, const char *name, double value);
	gboolean	(*appenddouble)(ConfigContext*, const char *name, double value);
										///< Set double value
	GSList*		(*getarray)(const ConfigContext*, const char *name);	///< Get array value
	void		(*setarray)(ConfigContext*, const char *name, GSList*);	///< Set array value
	const char*	(*getstring)(const ConfigContext*, const char *name);	///< Get String value
	void		(*setstring)(ConfigContext*, const char *name, const char *value);
	gboolean	(*appendstring)(ConfigContext*, const char *name, const char *value);
										///< Set String value
	Frame*		(*getframe)(const ConfigContext*, const char*);		///< Get Frame value
	void		(*setframe)(ConfigContext*, const char*,Frame*);	///< Set Frame value
	NetAddr*	(*getaddr)(const ConfigContext*, const char* name);	///< Get NetAddr value
	void		(*setaddr)(ConfigContext*,const char *,NetAddr*);	///< Set NetAddr value
	gboolean	(*appendaddr)(ConfigContext*,const char *,NetAddr*);	///< Set NetAddr value
	ConfigContext*	(*getconfig)(const ConfigContext*, const char* name);	///< Get ConfigContext value
	void		(*setconfig)(ConfigContext*,const char*,ConfigContext*);///< Set ConfigContext value
	gboolean	(*appendconfig)(ConfigContext*,const char*,ConfigContext*);///< Set ConfigContext value
	enum ConfigValType
			(*gettype)(const ConfigContext*, const char *);	///< Return type
	ConfigValue*	(*getvalue)(const ConfigContext*, const char *);///< Return ConfigValue Object
	void		(*delkey)(const ConfigContext*, const char *);	///< Delete the object with the given key
	guint		(*keycount)(const ConfigContext*);		///< Return number of keys in object
	GSList*		(*keys)(const ConfigContext*);			///< Return list of keys
};
WINEXPORT ConfigContext*	configcontext_new(gsize objsize); // ConfigContext constructor
WINEXPORT ConfigContext*	configcontext_new_JSON_string(const char * jsontext);// Constructor
WINEXPORT char * configcontext_elem_toString(ConfigValue* val);

#define	CONFIG_DEFAULT_DEADTIME	30		///< Default "deadtime"
#define	CONFIG_DEFAULT_HBTIME	3		///< Default heartbeat interval
#define	CONFIG_DEFAULT_WARNTIME	10		///< Default warning time
#define	CONFIG_DEFAULT_CMAPORT	1984		///< Default CMA port
#define	CONFIG_DEFAULT_ADDR	{127,0,0,1}
#define	CONFIG_DEFAULT_ADDRTYPE	ADDR_FAMILY_IPV4
#define	CONFIG_DEFAULT_SIGNFRAME_TYPE	G_CHECKSUM_SHA256

#define CONFIGNAME_INTERVAL	"repeat"	///< How long to wait between events
#define CONFIGNAME_WARNTIME	"warn"		///< How long w/o heartbeats before whining?
#define CONFIGNAME_TIMEOUT	"timeout"	///< How before declaring a serious problem...
#define CONFIGNAME_INITDELAY	"init_delay"	///< How long to wait before starting
#define CONFIGNAME_CMAPORT	"cmaport"	///< Default Port for contacting the CMA
#define CONFIGNAME_CMAINIT	"cmainit"	///< Initial startup contact address for the CMA
						///< (could be a multicast address)
#define CONFIGNAME_CMAADDR	"cmaaddr"	///< Address of the Collective Management authority
#define CONFIGNAME_CMADISCOVER	"cmadisc"	///< Address of where to send discovery reports
#define CONFIGNAME_CMAFAIL	"cmafail"	///< Address of where to send failure reports
#define	CONFIGNAME_TYPE		"type"		///< Type of resource or discovery
#define CONFIGNAME_INSTANCE	"instance"	///< Instance name for discovery
#define CONFIGNAME_DEVNAME	"device"	///< Name of NIC for discovery
#define CONFIGNAME_SWPROTOS	"swprotocols"	///< List of switch protocols as an array of strings
#define CONFIGNAME_OUTSIG	"outsig"	///< SignFrame to use to sign/verify packets
#define CONFIGNAME_CRYPT	"crypt"		///< Frame to use for encrypting/decrypting packets
#define CONFIGNAME_COMPRESS	"compress"	///< Frame to use for compressing/decompressing
#define CONFIGNAME_CPRS_THRESH	"compression_threshold"	///< Threshold for compressing (integer)
#define CONFIGNAME_COMPRESSTYPE	"compression_method"	///< Compression method (string)

/// Default values for some (integer) configuration values
#define	CONFIGINTDEFAULTS {					\
	{CONFIGNAME_DEADTIME,	CONFIG_DEFAULT_DEADTIME},	\
	{CONFIGNAME_WARNTIME,	CONFIG_DEFAULT_WARNTIME},	\
	{CONFIGNAME_HBTIME,	CONFIG_DEFAULT_HBTIME},		\
	{CONFIGNAME_CMAPORT,	CONFIG_DEFAULT_CMAPORT},		\
	}
///@}
#endif /* _CONFIGCONTEXT_H */
