/**
 * @file
 * @brief Library of code to support initial creation of a nanoprobe process.
 * @details This includes the code to obey various CMA packets, and some functions to startup and shut down
 * a nanoprobe process.
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
 *
 */
#include <sys/utsname.h>
#include <projectcommon.h>
#include <string.h>
#include <frameset.h>
#include <framesettypes.h>
#include <frametypes.h>
#include <compressframe.h>
#include <cryptframe.h>
#include <intframe.h>
#include <cstringframe.h>
#include <addrframe.h>
#include <ipportframe.h>
#include <seqnoframe.h>
#include <packetdecoder.h>
#include <netgsource.h>
#include <authlistener.h>
#include <nvpairframe.h>
#include <ipportframe.h>
#include <hblistener.h>
#include <hbsender.h>
#include <configcontext.h>
#include <pcap_min.h>
#include <jsondiscovery.h>
#include <switchdiscovery.h>
#include <nanoprobe.h>


void (*nanoprobe_deadtime_agent)(HbListener*)			= NULL;
void (*nanoprobe_heartbeat_agent)(HbListener*)			= NULL;
void (*nanoprobe_warntime_agent)(HbListener*, guint64 howlate)	= NULL;
void (*nanoprobe_comealive_agent)(HbListener*, guint64 howlate)	= NULL;
NanoHbStats		nano_hbstats = {0U, 0U, 0U, 0U, 0U};

FSTATIC void		nanoobey_sendexpecthb(AuthListener*, FrameSet* fs, NetAddr*);
FSTATIC void		nanoobey_sendhb(AuthListener*, FrameSet* fs, NetAddr*);
FSTATIC void		nanoobey_expecthb(AuthListener*, FrameSet* fs, NetAddr*);
FSTATIC void		nanoobey_stopsendexpecthb(AuthListener*, FrameSet* fs, NetAddr*);
FSTATIC void		nanoobey_stopsendhb(AuthListener*, FrameSet* fs, NetAddr*);
FSTATIC void		nanoobey_stopexpecthb(AuthListener*, FrameSet* fs, NetAddr*);
FSTATIC void		nanoobey_setconfig(AuthListener*, FrameSet* fs, NetAddr*);
FSTATIC void		nanoobey_change_debug(gint plusminus, AuthListener*, FrameSet*, NetAddr*);
FSTATIC void		nanoobey_incrdebug(AuthListener*, FrameSet*, NetAddr*);
FSTATIC void		nanoobey_decrdebug(AuthListener*, FrameSet*, NetAddr*);
FSTATIC void		nanoobey_startdiscover(AuthListener*, FrameSet*, NetAddr*);
FSTATIC void		nanoobey_stopdiscover(AuthListener*, FrameSet*, NetAddr*);
FSTATIC void		nano_schedule_discovery(const char *name, guint32 interval,const char* json
			,	ConfigContext*, NetGSource* transport, NetAddr* fromaddr);
FSTATIC void		nano_stop_discovery(const char * discoveryname, NetGSource*, NetAddr*);
FSTATIC gboolean	nano_startupidle(gpointer gcruft);
FSTATIC	gboolean	nano_reqconfig(gpointer gcruft);
FSTATIC void		_real_heartbeat_agent(HbListener* who);
FSTATIC void		_real_deadtime_agent(HbListener* who);
FSTATIC void		_real_warntime_agent(HbListener* who, guint64 howlate);
FSTATIC void		_real_comealive_agent(HbListener* who, guint64 howlate);
FSTATIC void		_real_martian_agent(NetAddr* who);
FSTATIC HbListener*	_real_hblistener_new(NetAddr*, ConfigContext*);

HbListener* (*nanoprobe_hblistener_new)(NetAddr*, ConfigContext*) = _real_hblistener_new;
static NetAddr*		nanofailreportaddr = NULL;
static NetGSource*	nanotransport = NULL;

DEBUGDECLARATIONS

/// Default HbListener constructor.
/// Supply your own in nanoprobe_hblistener_new if you need to construct a subclass object.
FSTATIC HbListener*
_real_hblistener_new(NetAddr* addr, ConfigContext* context)
{
	return hblistener_new(addr, context, 0);
}

/// Construct a frameset reporting something - and send it upstream
void
nanoprobe_report_upstream(guint16 reporttype	///< FrameSet Type of report to create
,			  NetAddr* who		///< Who is being reported on
,			  const char * sysname	///< Name of system doing the reporting
,			  guint64 howlate)	///< How late was the heartbeat?
						///< This is optional - zero means ignore this parameter.
{
		FrameSet*	fs		= frameset_new(reporttype);

		// Construct and send a frameset reporting this event...
		if (howlate > 0) {
			IntFrame*	lateframe	= intframe_new(FRAMETYPE_ELAPSEDTIME, 8);
			lateframe->setint(lateframe, howlate);
			frameset_append_frame(fs, &lateframe->baseclass);
			UNREF2(lateframe);
		}
		// Add the address - if any...
		if (who != NULL) {
			AddrFrame*	peeraddr	= addrframe_new(FRAMETYPE_IPADDR, 0);
			peeraddr->setnetaddr(peeraddr, who);
			frameset_append_frame(fs, &peeraddr->baseclass);
			UNREF2(peeraddr);
		}
		// Add the system name - if any...
		if (sysname != NULL) {
			CstringFrame* usf = cstringframe_new(FRAMETYPE_HOSTNAME, 0);
			usf->baseclass.setvalue(&usf->baseclass, strdup(sysname), strlen(sysname)+1
			,			frame_default_valuefinalize);
			frameset_append_frame(fs, &usf->baseclass);
			UNREF2(usf);
		}
		UNREF(fs);
		DEBUGMSG1("%s - sending frameset of type %d", __FUNCTION__, reporttype);
}

/// Standard nanoprobe 'martian heartbeat received' agent.
FSTATIC void
_real_martian_agent(NetAddr* who)
{
	++nano_hbstats.martian_count;
	{
		char *		addrstring;

		/// @todo: need to limit the frequency of martian messages
		addrstring = who->baseclass.toString(who);
		g_warning("System at address %s is sending unexpected heartbeats.", addrstring);
		g_free(addrstring);

		nanoprobe_report_upstream(FRAMESETTYPE_HBMARTIAN, who, NULL, 0);
	}
}
/// Standard nanoprobe 'deadtime elapsed' agent.
/// Supply your own in nanoprobe_deadtime_agent if you want us to call it.
FSTATIC void
_real_deadtime_agent(HbListener* who)
{
	++nano_hbstats.dead_count;
	if (nanoprobe_deadtime_agent) {
		nanoprobe_deadtime_agent(who);
	}else{
		char *		addrstring;

		addrstring = who->listenaddr->baseclass.toString(who->listenaddr);
		g_warning("Peer at address %s is dead (has timed out).", addrstring);
		g_free(addrstring);

		nanoprobe_report_upstream(FRAMESETTYPE_HBDEAD, who->listenaddr, NULL, 0);
	}
}

/// Standard nanoprobe 'hearbeat received' agent.
/// Supply your own in nanoprobe_heartbeat_agent if you want us to call it.
FSTATIC void
_real_heartbeat_agent(HbListener* who)
{
	++nano_hbstats.heartbeat_count;
	if (nanoprobe_heartbeat_agent) {
		nanoprobe_heartbeat_agent(who);
	}
}


/// Standard nanoprobe 'warntime elapsed' agent - called when a heartbeat arrives after 'warntime' but before 'deadtime'.
/// Supply your own in nanoprobe_warntime_agent if you want us to call it.
FSTATIC void
_real_warntime_agent(HbListener* who, guint64 howlate)
{
	++nano_hbstats.warntime_count;
	if (nanoprobe_warntime_agent) {
		nanoprobe_warntime_agent(who, howlate);
	}else{
		char *	addrstring;
		guint64 mslate = howlate / 1000;
		addrstring = who->listenaddr->baseclass.toString(who->listenaddr);
		g_warning("Heartbeat from peer at address %s was "FMT_64BIT"d ms late.", addrstring, mslate);
		g_free(addrstring);
		nanoprobe_report_upstream(FRAMESETTYPE_HBLATE, who->listenaddr, NULL, howlate);
	}
}
/// Standard nanoprobe 'returned-from-the-dead' agent - called when a heartbeats arrive after 'deadtime'.
/// Supply your own in nanoprobe_comealive_agent if you want us to call it.
FSTATIC void
_real_comealive_agent(HbListener* who, guint64 howlate)
{
	++nano_hbstats.comealive_count;
	if (nanoprobe_comealive_agent) {
		nanoprobe_comealive_agent(who, howlate);
	}else{
		char *	addrstring;
		double secsdead = ((double)((howlate+50000) / 100000))/10.0; // Round to nearest tenth of a second
		addrstring = who->listenaddr->baseclass.toString(who->listenaddr);
		g_warning("Peer at address %s came alive after being dead for %g seconds.", addrstring, secsdead);
		g_free(addrstring);
		nanoprobe_report_upstream(FRAMESETTYPE_HBBACKALIVE, who->listenaddr, NULL, howlate);
	}
}

/**
 * Act on (obey) a @ref FrameSet telling us to send heartbeats.
 * Such FrameSets are sent when the Collective Authority wants us to send
 * Heartbeats to various addresses. This might be from a FRAMESETTYPE_SENDHB
 * FrameSet or a FRAMESETTYPE_SENDEXPECTHB FrameSet.
 * The send interval, and port number can come from the FrameSet or from the
 * @ref ConfigContext parameter we're given - with the FrameSet taking priority.
 *
 * If these parameters are in the FrameSet, they have to precede the FRAMETYPE_IPADDR
 * @ref AddrFrame in the FrameSet.
 */
void
nanoobey_sendhb(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,   FrameSet*	fs		///<[in] @ref FrameSet indicating who to send HBs to
	,   NetAddr*	fromaddr)	///<[in/out] Address this message came from
{

	GSList*		slframe;
	guint		addrcount = 0;
	ConfigContext*	config = parent->baseclass.config;
	int		port = 0;
	guint16		sendinterval = 0;


	g_return_if_fail(fs != NULL);
	(void)fromaddr;
	
	if (config->getint(config, CONFIGNAME_HBPORT) > 0) {
		port = config->getint(config, CONFIGNAME_HBPORT);
	}
	if (config->getint(config, CONFIGNAME_HBTIME) > 0) {
		sendinterval = config->getint(config, CONFIGNAME_HBTIME);
	}

	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		int	frametype = frame->type;
		switch(frametype) {
			IntFrame*	iframe;
			AddrFrame*	aframe;
			HbSender*	hb;

			case FRAMETYPE_PORTNUM:
				iframe = CASTTOCLASS(IntFrame, frame);
				port = iframe->getint(iframe);
				if (port <= 0 || port >= 65536) {
					g_warning("invalid port (%d) in %s"
					, port, __FUNCTION__);
					port = 0;
					continue;
				}
				break;
			case FRAMETYPE_HBINTERVAL:
				iframe = CASTTOCLASS(IntFrame, frame);
				sendinterval = iframe->getint(iframe);
				break;
			case FRAMETYPE_IPADDR:
				if (0 == sendinterval) {
					g_warning("Send interval is zero in %s", __FUNCTION__);
					continue;
				}
				if (0 == port) {
					g_warning("Port is zero in %s", __FUNCTION__);
					continue;
				}
				aframe = CASTTOCLASS(AddrFrame, frame);
				addrcount++;
				aframe->setport(aframe, port);
				hb = hbsender_new(aframe->getnetaddr(aframe), parent->baseclass.transport
				,	sendinterval, 0);
				(void)hb;
				//hb->unref(hb);
				break;
		}
	}
}
/**
 * Act on (obey) a @ref FrameSet telling us to expect heartbeats.
 * Such framesets are sent when the Collective Authority wants us to expect
 * Heartbeats from various addresses.  This might be from a FRAMESETTYPE_EXPECTHB
 * FrameSet or a FRAMESETTYPE_SENDEXPECTHB FrameSet.
 * The deadtime, warntime, and port number can come from the FrameSet or the
 * @ref ConfigContext parameter we're given - with the FrameSet taking priority.
 *
 * If these parameters are in the FrameSet, they have to precede the FRAMETYPE_IPADDR
 * @ref AddrFrame in the FrameSet.
 */
void
nanoobey_expecthb(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,   FrameSet*	fs		///<[in] @ref FrameSet indicating who to send HBs to
	,   NetAddr*	fromaddr)	///<[in/out] Address this message came from
{

	GSList*		slframe;
	ConfigContext*	config = parent->baseclass.config;
	guint		addrcount = 0;

	gint		port = 0;
	guint64		deadtime = 0;
	guint64		warntime = 0;

	(void)fromaddr;

	g_return_if_fail(fs != NULL);
	if (config->getint(config, CONFIGNAME_HBPORT) > 0) {
		port = config->getint(config, CONFIGNAME_HBPORT);
	}
	if (config->getint(config, CONFIGNAME_DEADTIME) > 0) {
		deadtime = config->getint(config, CONFIGNAME_DEADTIME);
	}
	if (config->getint(config, CONFIGNAME_WARNTIME) > 0) {
		warntime = config->getint(config, CONFIGNAME_WARNTIME);
	}

	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		int	frametype = frame->type;
		switch(frametype) {
			IntFrame*	iframe;

			case FRAMETYPE_PORTNUM:
				iframe = CASTTOCLASS(IntFrame, frame);
				port = iframe->getint(iframe);
				if (port <= 0 || port > 65535) {
					g_warning("invalid port (%d) in %s"
					, port, __FUNCTION__);
					port = 0;
					continue;
				}
				break;

			case FRAMETYPE_HBDEADTIME:
				iframe = CASTTOCLASS(IntFrame, frame);
				deadtime = iframe->getint(iframe);
				break;

			case FRAMETYPE_HBWARNTIME:
				iframe = CASTTOCLASS(IntFrame, frame);
				warntime = iframe->getint(iframe);
				break;

			case FRAMETYPE_IPADDR: {
				HbListener*	hblisten;
				AddrFrame*	aframe;
				NetGSource*	transport = parent->baseclass.transport;
				if (0 == port) {
					g_warning("Port is zero in %s", __FUNCTION__);
					continue;
				}
				aframe = CASTTOCLASS(AddrFrame, frame);
				addrcount++;
				aframe->setport(aframe, port);
				hblisten = hblistener_new(aframe->getnetaddr(aframe), config, 0);
				hblisten->baseclass.associate(&hblisten->baseclass, transport);
				if (deadtime > 0) {
					// Otherwise we get the default deadtime
					hblisten->set_deadtime(hblisten, deadtime);
				}
				if (warntime > 0) {
					// Otherwise we get the default warntime
					hblisten->set_warntime(hblisten, warntime);
				}
				hblisten->set_deadtime_callback(hblisten, _real_deadtime_agent);
				hblisten->set_heartbeat_callback(hblisten, _real_heartbeat_agent);
				hblisten->set_warntime_callback(hblisten, _real_warntime_agent);
				hblisten->set_comealive_callback(hblisten, _real_comealive_agent);
				// Intercept incoming heartbeat packets
				transport->addListener(transport, FRAMESETTYPE_HEARTBEAT
				,		    CASTTOCLASS(Listener, hblisten));
				// Unref this heartbeat listener, and forget our reference.
				UNREF2(hblisten);
				/*
				 * That still leaves two references to 'hblisten':
				 *   - in the transport dispatch table
				 *   - in the global heartbeat listener table
				 * And one reference to the previous 'hblisten' object:
				 *   - in the global heartbeat listener table
				 * Also note that we become the 'proxy' for all incoming heartbeats
				 * but we dispatch them to the right HbListener object.
				 * Since we've become the proxy for all incoming heartbeats, if
				 * we displace and free the old proxy, this all still works nicely,
				 * because the transport object gets rid of its old reference to the
				 * old 'proxy' object.
				 */
			}
			break;
		}
	}
}

/**
 * Act on (obey) a FRAMESETTYPE_SENDEXPECTHB @ref FrameSet.
 * This frameset is sent when the Collective Authority wants us to both send
 * Heartbeats to an address and expect heartbeats back from them.
 * The deadtime, warntime, send interval and port number can come from the
 * FrameSet or from the @ref ConfigContext parameter we're given.
 * If these parameters are in the FrameSet, they have to precede the FRAMETYPE_IPADDR
 * @ref AddrFrame in the FrameSet.
 */
void
nanoobey_sendexpecthb(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,   FrameSet*	fs		///<[in] @ref FrameSet indicating who to send HBs to
	,   NetAddr*	fromaddr)	///<[in/out] Address this message came from
{
	g_return_if_fail(fs != NULL && fs->fstype == FRAMESETTYPE_SENDEXPECTHB);

	// This will cause us to ACK the packet twice -- not a problem...
	nanoobey_sendhb  (parent, fs, fromaddr);
	nanoobey_expecthb(parent, fs, fromaddr);
}
/**
 * Act on (obey) a @ref FrameSet telling us to stop sending heartbeats.
 * Such FrameSets are sent when the Collective Authority wants us to stop heartbeating
 * a machine because of a machine coming alive or dying (reconfiguration).
 * This might be from a FRAMESETTYPE_STOPSENDHB
 * FrameSet or a FRAMESETTYPE_STOPSENDEXPECTHB FrameSet.
 */
void
nanoobey_stopsendhb(AuthListener* parent///<[in] @ref AuthListener object invoking us
	,   FrameSet*	fs		///<[in] @ref FrameSet indicating who to stop sending HBs to
	,   NetAddr*	fromaddr)	///<[in/out] Address this message came from
{
	GSList*		slframe;
	(void)parent;
	(void)fromaddr;

	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		switch(frame->type) {
			case FRAMETYPE_IPADDR: {
				// This is _so_ much simpler than the code to send them ;-)
				AddrFrame*	aframe = CASTTOCLASS(AddrFrame, frame);
				hbsender_stopsend(aframe->getnetaddr(aframe));
				break;
			}
		}//endswitch
	}//endfor
}

/**
 * Act on (obey) a @ref FrameSet telling us to stop expecting heartbeats.
 * Such FrameSets are sent when the Collective Authority wants us to stop listening to
 * a machine because of a machine coming alive or dying (reconfiguration).
 * This might be from a FRAMESETTYPE_STOPEXPECTHB
 * FrameSet or a FRAMESETTYPE_STOPSENDEXPECTHB FrameSet.
 */
void
nanoobey_stopexpecthb(AuthListener* parent///<[in] @ref AuthListener object invoking us
	,   FrameSet*	fs		///<[in] @ref FrameSet indicating who to stop expecting HBs from
	,   NetAddr*	fromaddr)	///<[in/out] Address this message came from
{
	GSList*		slframe;
	(void)parent;
	(void)fromaddr;

	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		switch(frame->type) {
			case FRAMETYPE_IPADDR: {
				// This is _so_ much simpler than the code to listen for heartbeats...
				AddrFrame*	aframe = CASTTOCLASS(AddrFrame, frame);
				hblistener_unlisten(aframe->getnetaddr(aframe));
				break;
			}
		}//endswitch
	}//endfor
}

/**
 * Act on (obey) a @ref FrameSet telling us to stop sending and expecting heartbeats.
 * Such FrameSets are sent when the Collective Authority wants us to communicating with
 * a machine because of a machine coming alive or dying (reconfiguration).
 */
void
nanoobey_stopsendexpecthb(AuthListener* parent///<[in] @ref AuthListener object invoking us
	,   FrameSet*	fs		///<[in] @ref FrameSet indicating who to stop talking to
	,   NetAddr*	fromaddr)	///<[in/out] Address this message came from
{
	nanoobey_stopexpecthb(parent, fs, fromaddr);
	nanoobey_stopsendhb  (parent, fs, fromaddr);
}

/*
 * Act on (obey) a <b>FRAMESETTYPE_SETCONFIG</b> @ref FrameSet.
 * This frameset is sent during the initial configuration phase.
 * It contains name value pairs to save into our configuration (ConfigContext).
 * These might be {string,string} pairs or {string,ipaddr} pairs, or
 * {string, integer} pairs.  We process them all.
 * The frame types that we receive for these are:
 * <b>FRAMETYPE_PARAMNAME</b> - parameter name to set
 * <b>FRAMETYPE_CSTRINGVAL</b> - string value to associate with name
 * <b>FRAMETYPE_CINTVAL</b> - integer value to associate with naem
 * <b>FRAMETYPE_PORTNUM</b> - port number for subsequent IP address
 * <b>FRAMETYPE_IPADDR</b> - IP address to associate with name
 */
void
nanoobey_setconfig(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,      FrameSet*	fs	///<[in] @ref FrameSet to process
	,      NetAddr*	fromaddr)	///<[in/out] Address this message came from
{
	GSList*		slframe;
	ConfigContext*	cfg = parent->baseclass.config;
	char *		paramname = NULL;
	guint16		port = 0;

	(void)fromaddr;

	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		int	frametype = frame->type;
		switch (frametype) {

			case FRAMETYPE_PARAMNAME: { // Parameter name to set
				paramname = frame->value;
				g_return_if_fail(paramname != NULL);
			}
			break;

			case FRAMETYPE_CSTRINGVAL: { // String value to set 'paramname' to
				g_return_if_fail(paramname != NULL);
				cfg->setstring(cfg, paramname, frame->value);
				paramname = NULL;
			}
			break;

			case FRAMETYPE_CINTVAL: { // Integer value to set 'paramname' to
				IntFrame* intf = CASTTOCLASS(IntFrame, frame);
				g_return_if_fail(paramname != NULL);
				cfg->setint(cfg, paramname, intf->getint(intf));
				paramname = NULL;
			}
			break;

			case FRAMETYPE_PORTNUM: { // Port number for subsequent FRAMETYPE_IPADDR
				IntFrame* intf = CASTTOCLASS(IntFrame, frame);
				g_return_if_fail(paramname != NULL);
				port = intf->getint(intf); // remember for later
			}
			break;

			case FRAMETYPE_IPADDR: { // NetAddr value to set 'paramname' to
				AddrFrame* af = CASTTOCLASS(AddrFrame, frame);
				NetAddr*	addr = af->getnetaddr(af);
				g_return_if_fail(paramname != NULL);
				if (port != 0) {
					addr->setport(addr, port);
					port = 0;
				}else{
					g_warning("Setting IP address [%s] without port", paramname);
				}
				cfg->setaddr(cfg, paramname, addr);
				paramname = NULL;
			}
			break;

		}//endswitch
	}//endfor
	if (cfg->getaddr(cfg, CONFIGNAME_CMAFAIL) != NULL) {
		if (nanofailreportaddr == NULL) {
			nanofailreportaddr = cfg->getaddr(cfg, CONFIGNAME_CMAFAIL);
		}else if (cfg->getaddr(cfg, CONFIGNAME_CMAFAIL) != nanofailreportaddr) {
			UNREF(nanofailreportaddr);
			nanofailreportaddr = cfg->getaddr(cfg, CONFIGNAME_CMAFAIL);
		}
		REF(nanofailreportaddr);
	}
}//nanoobey_setconfig

/**
 * Act on (obey) a @ref FrameSet telling us to increment or decrement debug levels
 * either on a specific set of classes, or on all classes.
 */
FSTATIC void
nanoobey_change_debug(gint plusminus		///<[in] +1 or -1 - for incrementing/decrementing
	,	      AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,	      FrameSet*	fs		///<[in] @ref FrameSet indicating who to send HBs to
	,	      NetAddr*	fromaddr)	///<[in/out] Address this message came from
{

	GSList*		slframe;
	guint		changecount = 0;

	(void)parent;
	(void)fromaddr;

	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		int	frametype = frame->type;
		switch (frametype) {
			case FRAMETYPE_CSTRINGVAL: { // String value to set 'paramname' to
				++changecount;
				if (plusminus < 0) {
					proj_class_decr_debug((char*)frame->value);
				}else{
					proj_class_incr_debug((char*)frame->value);
				}
			}
			break;
		}
	}
	if (changecount == 0) {
		if (plusminus < 0) {
			proj_class_decr_debug(NULL);
		}else{
			proj_class_incr_debug(NULL);
		}
	}
}
/**
 * Act on (obey) a @ref FrameSet telling us to increment debug levels
 * either on a specific set of classes, or on all classes.
 */
FSTATIC void
nanoobey_incrdebug(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,	      FrameSet*	fs		///<[in] @ref FrameSet indicating who to send HBs to
	,	      NetAddr*	fromaddr)	///<[in/out] Address this message came from
{
	nanoobey_change_debug(+1, parent, fs, fromaddr);
}
/**
 * Act on (obey) a @ref FrameSet telling us to decrement debug levels
 * either on a specific set of classes, or on all classes.
 */
FSTATIC void
nanoobey_decrdebug(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,	      FrameSet*	fs		///<[in] @ref FrameSet indicating who to send HBs to
	,	      NetAddr*	fromaddr)	///<[in/out] Address this message came from
{
	nanoobey_change_debug(-1, parent, fs, fromaddr);
}

/**
 * Act on (obey) a @ref FrameSet telling us to perform a possibly repeating discovery action.
 * <b>FRAMETYPE_DISCNAME</b> - Name of this particular discovery action
 * Everything else we need to know comes through as a JSON string.
 * Having the discovery name be separate is handy for putting them in a table.
 * Don't need the interval once it's started, so no reason to put it in the JSON.
 */
FSTATIC void
nanoobey_startdiscover(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,	      FrameSet*	fs		///<[in] @ref FrameSet giving operational details
	,	      NetAddr*	fromaddr)	///<[in/out] Address this message came from
{

	GSList*		slframe;
	guint		interval = 0;
	const char *	discoveryname = NULL;

	(void)parent;
	(void)fromaddr;
	

	DEBUGMSG2("%s - got frameset", __FUNCTION__);
	// Loop over the frames, looking for those we know what to do with ;-)
	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		int	frametype = frame->type;

		switch (frametype) {
			case FRAMETYPE_DISCNAME: { // Discovery instance name
				CstringFrame* strf = CASTTOCLASS(CstringFrame, frame);
				g_return_if_fail(strf != NULL);
				g_return_if_fail(discoveryname == NULL);
				discoveryname = strf->baseclass.value;
				DEBUGMSG2("%s - got DISCOVERYNAME %s", __FUNCTION__, discoveryname);
			}
			break;

			case FRAMETYPE_DISCINTERVAL: { // Discovery interval
				IntFrame* intf = CASTTOCLASS(IntFrame, frame);
				interval = intf->getint(intf);
				DEBUGMSG2("%s - got DISCOVERYINTERVAL %d", __FUNCTION__, interval);
			}
			break;

			case FRAMETYPE_DISCJSON: { // Discovery JSON string (parameters)
				CstringFrame* strf = CASTTOCLASS(CstringFrame, frame);
				const char *  jsonstring;
				g_return_if_fail(strf != NULL);
				jsonstring = strf->baseclass.value;
				g_return_if_fail(discoveryname != NULL);
				DEBUGMSG2("Got DISCJSON frame: %s %d %s" , discoveryname, interval, jsonstring);
				nano_schedule_discovery(discoveryname, interval, jsonstring
				,			parent->baseclass.config
				,			parent->baseclass.transport
				,			fromaddr);
			}
			interval = 0;
			discoveryname = NULL;
			break;

		}
	}
}

/**
 * Act on (obey) a @ref FrameSet telling us to stop a repeating discovery action.
 * <b>FRAMETYPE_DISCNAME</b> - Name of this particular discovery action
 */
FSTATIC void
nanoobey_stopdiscover(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,	      FrameSet*	fs		///<[in] @ref FrameSet giving operational details
	,	      NetAddr*	fromaddr)	///<[in/out] Address this message came from
{

	GSList*		slframe;

	(void)parent;
	(void)fromaddr;
	

	// Loop over the frames, looking for the one we know what to do with ;-)
	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		int	frametype = frame->type;

		switch (frametype) {
			case FRAMETYPE_DISCNAME: { // Discovery instance name
				CstringFrame* strf = CASTTOCLASS(CstringFrame, frame);
				const char *	discoveryname;
				g_return_if_fail(strf != NULL);
				discoveryname = strf->baseclass.value;
				g_return_if_fail(discoveryname == NULL);
                                discovery_unregister(discoveryname);
			}
			break;

		}
	}
}


/**
 * Schedule a discovery instance, potentially repetitively.
 */
FSTATIC void	
nano_schedule_discovery(const char *instance,	///<[in] Name of this particular instance
			guint32 interval,	///<[in] How often to run (0 == one-shot)
			const char* json,	///<[in] JSON data specifying the discovery
			ConfigContext* config,	///<[in] Configuration context
			NetGSource* transport,	///<[in/out] Network Transport
			NetAddr* fromaddr)	///<[in/out] Requestor's address
{
	ConfigContext*	jsonroot;
	JsonDiscovery*	discovery;
	const char*	disctype;

	(void)fromaddr;

	DEBUGMSG1("%s(%s,%d,%s)", __FUNCTION__, instance, interval, json);
	jsonroot = configcontext_new_JSON_string(json);
	g_return_if_fail(jsonroot != NULL);
	disctype = jsonroot->getstring(jsonroot, "type");
	g_return_if_fail(disctype != NULL);
	discovery = jsondiscovery_new(disctype, instance, interval, jsonroot
	,			      transport, config, 0);
	UNREF(jsonroot);
	UNREF2(discovery);
}

/// Stuff we need only for passing parameters through our glib infrastructures - to start up nanoprobes.
struct startup_cruft {
	const char *	initdiscover;
	int		discover_interval;
	NetGSource*	iosource;
	ConfigContext*	context;
};

/// Nanoprobe bootstrap routine.
/// We are a g_main_loop idle function which kicks off a discovery action
/// and continues to run as idle until the discovery finishes, then
/// we schedule a request for configuration - which will run periodically
/// until we get our configuration information safely stored away in our
/// ConfigContext.
gboolean
nano_startupidle(gpointer gcruft)
{
	static enum istate {INIT=3, WAIT=5, DONE=7} state = INIT;
	struct startup_cruft* cruft = gcruft;
	const char *	cfgname = cruft->initdiscover;

	if (state == DONE) {
		return FALSE;
	}
	if (state == INIT) {
		const char * jsontext = "{\"parameters\":{}}";
		ConfigContext*	jsondata = configcontext_new_JSON_string(jsontext);
		JsonDiscovery* jd = jsondiscovery_new
		(	cruft->initdiscover
		,	cruft->initdiscover
		,	cruft->discover_interval
		,	jsondata
		,	cruft->iosource, cruft->context, 0);
		UNREF(jsondata);
		UNREF2(jd);
		state = WAIT;
		return TRUE;
	}
	if (cruft->context->getstring(cruft->context, cfgname)) {
		state = DONE;
		// Call it once, and arrange for it to repeat until we hear back.
		g_timeout_add_seconds(5, nano_reqconfig, gcruft);
		nano_reqconfig(gcruft);
		return FALSE;
	}
	return TRUE;
}

/// Function to request our initial configuration data
/// This is typically called from a g_main_loop timeout, and is also called directly - at startup.
gboolean
nano_reqconfig(gpointer gcruft)
{
	struct startup_cruft* cruft = gcruft;
	FrameSet*	fs;
	CstringFrame*	csf;
	CstringFrame*	usf;
	const char *	cfgname = cruft->initdiscover;
	ConfigContext*	context = cruft->context;
	NetAddr*	cmainit = context->getaddr(context, CONFIGNAME_CMAINIT);
	const char *		jsontext;
	struct utsname	un;	// System name, etc.

	// We <i>have</i> to know our initial request address - or all is lost.
	// NOTE THAT THIS ADDRESS MIGHT BE MULTICAST AND MIGHT BE USED ONLY ONCE
	g_return_val_if_fail(cmainit != NULL, FALSE);

	// Our initial configuration message must contain these parameters.
	if (context->getaddr(context, CONFIGNAME_CMAADDR) != NULL
	&&  context->getaddr(context, CONFIGNAME_CMAFAIL) != NULL
	&&  context->getaddr(context, CONFIGNAME_CMADISCOVER) != NULL
	&&  context->getint(context, CONFIGNAME_CMAPORT) > 0) {
		return FALSE;
	}
	fs = frameset_new(FRAMESETTYPE_STARTUP);

	uname(&un);
	// Put in the system name
	usf = cstringframe_new(FRAMETYPE_HOSTNAME, 0);
	usf->baseclass.setvalue(&usf->baseclass, strdup(un.nodename), strlen(un.nodename)+1
	,			frame_default_valuefinalize);
	frameset_append_frame(fs, &usf->baseclass);
	UNREF2(usf);

	// Put in the JSON discovery text
	jsontext = context->getstring(context, cfgname);
	csf = cstringframe_new(FRAMETYPE_JSDISCOVER, 0);
	csf->baseclass.setvalue(&csf->baseclass, strdup(jsontext), strlen(jsontext)+1
	,			frame_default_valuefinalize);

	frameset_append_frame(fs, &csf->baseclass);
	UNREF2(csf);

	// We've constructed the frameset - now send it - unreliably...
	// That's because the reply will likely be from a different address
	// which would confuse the blazes out of the reliable comm code.
	cruft->iosource->sendaframeset(cruft->iosource, cmainit, fs);
	UNREF(fs);
	return TRUE;
}

static PacketDecoder*	decoder = NULL;
static SwitchDiscovery*	swdisc = NULL;
static AuthListener*	obeycollective = NULL;


/// The set of Collective Management Authority FrameTypes we know about,
/// and what to do when we get them.
/// Resistance is futile...
ObeyFrameSetTypeMap collective_obeylist [] = {
	// This is the complete set of commands that nanoprobes know how to obey - so far...
	{FRAMESETTYPE_SENDHB,		nanoobey_sendhb},
	{FRAMESETTYPE_EXPECTHB,		nanoobey_expecthb},
	{FRAMESETTYPE_SENDEXPECTHB,	nanoobey_sendexpecthb},
	{FRAMESETTYPE_STOPSENDHB,	nanoobey_stopsendhb},
	{FRAMESETTYPE_STOPEXPECTHB,	nanoobey_stopexpecthb},
	{FRAMESETTYPE_STOPSENDEXPECTHB, nanoobey_stopsendexpecthb},
	{FRAMESETTYPE_SETCONFIG,	nanoobey_setconfig},
	{FRAMESETTYPE_INCRDEBUG,	nanoobey_incrdebug},
	{FRAMESETTYPE_DECRDEBUG,	nanoobey_decrdebug},
	{FRAMESETTYPE_DODISCOVER,	nanoobey_startdiscover},
	{FRAMESETTYPE_STOPDISCOVER,	nanoobey_stopdiscover},
	{0,				NULL},
};

/// Return our nanoprobe packet decoder map.
/// Kind of like a secret decoder ring, but more useful ;-).
PacketDecoder*
nano_packet_decoder(void)
{
	static FrameTypeToFrame	decodeframes[] = FRAMETYPEMAP;
	// Set up our packet decoder
	decoder = packetdecoder_new(0, decodeframes, DIMOF(decodeframes));
	return decoder;
}


/**
 * Here is how the startup process works:
 *
 * 1.	Submit a network discovery request from an idle task, rescheduling until it completes.
 *	Go to next step when this is done.						nano_startupidle()
 *
 * 2.	Repeatedly send out a "request for configuration" packet once the discovery data
 *	shows up in the config context, until the rest of our config comes in		nano_reqconfig()
 *
 * 3.	When the CMA receives this request it will send outout a FRAMESETTYPE_SETCONFIG @ref FrameSet
 *	and a series of SENDEXPECTHB heartbeat packets.  We'll just keep asking until we receive the
 *	SETCONFIG we're looking for (currently every 5 seconds).
 *
 * 4.	When the FRAMESETTYPE_SETCONFIG packet is received, this enables the sending of
 *	discovery data from all (JSON and switch (LLDP/CDP)) sources.			nanoobey_setconfig()
 *	In the case of the SwitchDiscovery data, we're already trying to collect it.
 *
 * 5.	When we receive FRAMESETTYPE_SENDEXPECTHB packets (or similar), we start sending
 *	heartbeats and timing heartbeats to flag "dead" machines as we were told.
 *					nanoobey_sendhb(), nanoobey_expecthb(), and/or nanoobey_sendexpecthb()
 *
 * 6.	Now everything is running in "normal" mode.  Happy days!
 *	Eventually we may be told to do other things (monitor services, set up discovery, other queries)
 *	but we'll always go through these steps.
 */

void
nano_start_full(const char *initdiscoverpath	///<[in] pathname of initial network discovery agent
	,	guint discover_interval		///<[in] discovery interval for agent above
	,	NetGSource* io			///<[in/out] network connectivity object
	,	ConfigContext* config)		///<[in/out] configuration object
{
	static struct startup_cruft cruftiness;
	struct startup_cruft initcrufty = {
		initdiscoverpath,
		discover_interval,
		io,
		config
	};
	BINDDEBUG(nanoprobe_main);
	
 	hblistener_set_martian_callback(_real_martian_agent);
	cruftiness = initcrufty;
	g_source_ref(CASTTOCLASS(GSource, io));
	nanotransport = io;

	// Get our local switch discovery information.
	// To be really right, we probably ought to wait until we know our local network
	// configuration - and start it up on all interfaces assigned addresses of global scope.
	///@todo - eventually change switch discovery to be sensitive to our local network configuration
	swdisc = switchdiscovery_new("switchdiscovery_eth0", "eth0", ENABLE_LLDP|ENABLE_CDP, G_PRIORITY_LOW
	,			    g_main_context_default(), io, config, 0);
	obeycollective = authlistener_new(0, collective_obeylist, config, TRUE);
	obeycollective->baseclass.associate(&obeycollective->baseclass, io);
	// Initiate the startup process
	g_idle_add(nano_startupidle, &cruftiness);
}
/// Shut down the things started up by nano_start_full() - mainly free storage to make valgrind happy...
void
nano_shutdown(gboolean report)
{
	if (report) {
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of heartbeats:", nano_hbstats.heartbeat_count);
		g_info("%-35s %8d", "Count of deadtimes:", nano_hbstats.dead_count);
		g_info("%-35s %8d", "Count of warntimes:", nano_hbstats.warntime_count);
		g_info("%-35s %8d", "Count of comealives:", nano_hbstats.comealive_count);
		g_info("%-35s %8d", "Count of martians:", nano_hbstats.martian_count);
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of LLDP/CDP pkts sent:", swdisc->baseclass.reportcount);
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of LLDP/CDP pkts received:", swdisc->baseclass.discovercount);
	}
	hbsender_stopallsenders();
	UNREF2(swdisc);
	if (nanofailreportaddr) {
		UNREF(nanofailreportaddr);
	}
	if (nanotransport) {
		// Unlink heartbeat dispatcher - this should NOT be necessary - but it seems to be...
		nanotransport->addListener(nanotransport, FRAMESETTYPE_HEARTBEAT, NULL);
		g_source_unref(CASTTOCLASS(GSource, nanotransport));
	}
	// Free packet decoder
	if (decoder) {
		UNREF(decoder);
	}
	// Unregister all discovery modules.
	discovery_unregister_all();
	obeycollective->baseclass.dissociate(&obeycollective->baseclass);
	UNREF2(obeycollective);
}
