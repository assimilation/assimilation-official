/**
 * @file
 * @brief Basic utility functins for the CMA.  Small enough to leave in the
 * client code.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 *
 */

#include <projectcommon.h>
#include <string.h>
#include <cmalib.h>
#include <frameset.h>
#include <intframe.h>
#include <addrframe.h>
#include <cstringframe.h>
#include <frametypes.h>
#include <cmalib.h>


/**
 * Create a @ref FrameSet to send and expect heartbeats from the same sets of addresses.
 * Keep in mind the entire packet needs to fit in a UDP packet (< 64K).
 * The port, hbtime, deadtime, and warntime parameters apply to all given addresses.
 */
FrameSet*
create_sendexpecthb(ConfigContext* config	///<[in] Provides deadtime, port, etc.
		,   guint16 msgtype		///<[in] message type to create
		,   NetAddr* addrs		///<[in/out] Addresses to include
		,   int addrcount)		///<[in] Count of 'addrs' provided
{
	FrameSet* ret = frameset_new(msgtype);
	int	count = 0;

	// Put the port in the message (if asked)
	if (config->getint(config, CONFIGNAME_HBPORT) > 0) {
		gint	port = config->getint(config, CONFIGNAME_HBPORT);
		IntFrame * intf = intframe_new(FRAMETYPE_PORTNUM, 2);
		intf->setint(intf, port);
		frameset_append_frame(ret, &intf->baseclass);
		intf->baseclass.baseclass.unref(intf); intf = NULL;
	}
	// Put the heartbeat interval in the message (if asked)
	if (config->getint(config, CONFIGNAME_HBTIME) > 0) {
		gint	hbtime = config->getint(config, CONFIGNAME_HBTIME);
		IntFrame * intf = intframe_new(FRAMETYPE_HBINTERVAL, 4);
		intf->setint(intf, hbtime);
		frameset_append_frame(ret, &intf->baseclass);
		intf->baseclass.baseclass.unref(intf); intf = NULL;
	}
	// Put the heartbeat deadtime in the message (if asked)
	if (config->getint(config, CONFIGNAME_DEADTIME) > 0) {
		gint deadtime = config->getint(config, CONFIGNAME_DEADTIME);
		IntFrame * intf = intframe_new(FRAMETYPE_HBDEADTIME, 4);
		intf->setint(intf, deadtime);
		frameset_append_frame(ret, &intf->baseclass);
		intf->baseclass.baseclass.unref(intf); intf = NULL;
	}
	// Put the heartbeat warntime in the message (if asked)
	if (config->getint(config, CONFIGNAME_WARNTIME) > 0) {
		gint warntime = config->getint(config, CONFIGNAME_WARNTIME);
		IntFrame * intf = intframe_new(FRAMETYPE_HBWARNTIME, 4);
		intf->setint(intf, warntime);
		frameset_append_frame(ret, &intf->baseclass);
		intf->baseclass.baseclass.unref(intf); intf = NULL;
	}

	// Put all the addresses we were given in the message.
	for (count=0; count < addrcount; ++count) {
		AddrFrame* hbaddr = addrframe_new(FRAMETYPE_IPADDR, 0);
		hbaddr->setnetaddr(hbaddr, &addrs[count]);
		frameset_append_frame(ret, &hbaddr->baseclass);
		hbaddr->baseclass.baseclass.unref(hbaddr); hbaddr = NULL;
	}
	return  ret;
}


/// Create a FRAMESETTYPE_SETCONFIG @ref FrameSet.
/// We create it from a ConfigContext containing <i>only</i> values we want to go into
/// the SETCONFIG message.  We ignore frames in the ConfigContext (shouldn't be any).
/// We are effectively a "friend" function to the ConfigContext object - either that
/// or we cheated in order to iterate through its hash tables ;-)
FrameSet*
create_setconfig(ConfigContext * cfg)
{
	FrameSet*	fs = frameset_new(FRAMESETTYPE_SETCONFIG);
	GHashTableIter	iter;
	gpointer	key;
	gpointer	data;

	// First we go through the integer values (if any)
	// Next we go through the string values (if any)
	// Lastly we go through the NetAddr values (if any)

	// Integer values
	if (!cfg->_values) {
		return NULL;
	}
	g_hash_table_iter_init(&iter, cfg->_values);
	while (g_hash_table_iter_next(&iter, &key, &data)) {
		char *		name = key;
		CstringFrame*	n;

		switch (cfg->gettype(cfg, key)) {
			case CFG_INT64:
			case CFG_STRING:
			case CFG_NETADDR:
					break;
			default:	// Completely ignore everything else
					continue;
		}

		n = cstringframe_new(FRAMETYPE_PARAMNAME, 0);
		// Put the name into the frameset
		n->baseclass.setvalue(&n->baseclass, g_strdup(name), strlen(name)+1
		,		      frame_default_valuefinalize);
		frameset_append_frame(fs, &n->baseclass);
		n->baseclass.baseclass.unref(n); n = NULL;

		// Now put the value in...
		switch(cfg->gettype(cfg, key)) {
			case CFG_EEXIST:
			case CFG_NULL:
			case CFG_BOOL:
			case CFG_FLOAT:
			case CFG_ARRAY:
			case CFG_CFGCTX:
			case CFG_FRAME:
				break;	// Ignore these...

			case CFG_INT64: {
				gint64		value = cfg->getint(cfg, name);
				IntFrame*	v = intframe_new(FRAMETYPE_CINTVAL, 8);
				v->setint(v, value);
				frameset_append_frame(fs, &v->baseclass);
				v->baseclass.baseclass.unref(v);
				break;
			}
			case CFG_STRING: {
				const char *	value = cfg->getstring(cfg, name);
				CstringFrame*	v = cstringframe_new(FRAMETYPE_CSTRINGVAL, 0);
				v->baseclass.setvalue(&v->baseclass, g_strdup(value)
				,		      strlen(value)+1, frame_default_valuefinalize);
				frameset_append_frame(fs, &v->baseclass);
				v->baseclass.baseclass.unref(v);
				break;
			}
			case CFG_NETADDR: {
				NetAddr *	value = cfg->getaddr(cfg, name);
				AddrFrame*	v = addrframe_new(FRAMETYPE_IPADDR, 0);
				// The port doesn't come through when going across the wire
				if (value->port(value) != 0) {
					IntFrame*	p = intframe_new(FRAMETYPE_PORTNUM, 4);
					p->setint(p, value->port(value));
					frameset_append_frame(fs, &p->baseclass);
					p->baseclass.baseclass.unref(p); p = NULL;
				}
				v->setnetaddr(v, value);
				frameset_append_frame(fs, &v->baseclass);
				v->baseclass.baseclass.unref(v); v = NULL;
				break;
			}
		}
	}
	return fs;
}
