/**
 * @file
 * @brief Basic utility functins for the CMA.  Small enough to leave in the
 * client code.
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

#include <projectcommon.h>
#include <string.h>
#include <cmalib.h>
#include <frameset.h>
#include <intframe.h>
#include <ipportframe.h>
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
	ConfigContext*	msgcfg = configcontext_new(0);
	char*		json;
	CstringFrame*	jsframe;
	int	count = 0;

	// Put the heartbeat interval in the message (if asked)
	if (config->getint(config, CONFIGNAME_INTERVAL) > 0) {
		gint	hbtime = config->getint(config, CONFIGNAME_INTERVAL);
		IntFrame * intf = intframe_new(FRAMETYPE_HBINTERVAL, 4);
		intf->setint(intf, hbtime);
		frameset_append_frame(ret, &intf->baseclass);
		UNREF2(intf);
		msgcfg->setint(msgcfg, CONFIGNAME_INTERVAL, hbtime);
	}else{
		msgcfg->setint(msgcfg, CONFIGNAME_INTERVAL, CONFIG_DEFAULT_HBTIME);
	}
	// Put the heartbeat deadtime in the message (if asked)
	if (config->getint(config, CONFIGNAME_TIMEOUT) > 0) {
		gint deadtime = config->getint(config, CONFIGNAME_TIMEOUT);
		IntFrame * intf = intframe_new(FRAMETYPE_HBDEADTIME, 4);
		intf->setint(intf, deadtime);
		frameset_append_frame(ret, &intf->baseclass);
		UNREF2(intf);
		msgcfg->setint(msgcfg, CONFIGNAME_TIMEOUT, deadtime);
	}else{
		msgcfg->setint(msgcfg, CONFIGNAME_TIMEOUT, CONFIG_DEFAULT_DEADTIME);
	}
	// Put the heartbeat warntime in the message (if asked)
	if (config->getint(config, CONFIGNAME_WARNTIME) > 0) {
		gint warntime = config->getint(config, CONFIGNAME_WARNTIME);
		IntFrame * intf = intframe_new(FRAMETYPE_HBWARNTIME, 4);
		intf->setint(intf, warntime);
		frameset_append_frame(ret, &intf->baseclass);
		UNREF2(intf);
		msgcfg->setint(msgcfg, CONFIGNAME_WARNTIME, warntime);
	}else{
		msgcfg->setint(msgcfg, CONFIGNAME_WARNTIME, CONFIG_DEFAULT_WARNTIME);
	}
	json = msgcfg->baseclass.toString(&msgcfg->baseclass);
	UNREF(msgcfg);
	jsframe = cstringframe_new(FRAMETYPE_RSCJSON, 0);
	jsframe->baseclass.setvalue(&jsframe->baseclass, json
	,		      strlen(json)+1, frame_default_valuefinalize);
	frameset_append_frame(ret, &jsframe->baseclass);
	UNREF2(jsframe);
	

	// Put all the addresses we were given in the message.
	for (count=0; count < addrcount; ++count) {
		IpPortFrame* hbaddr = ipportframe_netaddr_new(FRAMETYPE_IPPORT, &addrs[count]);
		frameset_append_frame(ret, &hbaddr->baseclass);
		UNREF2(hbaddr);
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
	char*		json;
	CstringFrame*	jsframe;

	if (!cfg || !cfg->_values) {
		g_warning("%s.%d: NULL ConfigContext parameter", __FUNCTION__, __LINE__);
		return NULL;
	}
	json = cfg->baseclass.toString(&cfg->baseclass);
	if (json == NULL) {
		g_warning("%s.%d: Invalid ConfigContext parameter", __FUNCTION__, __LINE__);
		return NULL;
	}
	jsframe = cstringframe_new(FRAMETYPE_CONFIGJSON, 0);
	jsframe->baseclass.setvalue(&jsframe->baseclass, json
	,		      strlen(json)+1, frame_default_valuefinalize);
	frameset_append_frame(fs, &jsframe->baseclass);
	UNREF2(jsframe);

	return fs;
}
