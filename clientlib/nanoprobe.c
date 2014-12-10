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
#include <projectcommon.h>
#include <string.h>
#include <frameset.h>
#include <framesettypes.h>
#include <frametypes.h>
#include <compressframe.h>
#include <cryptframe.h>
#include <cryptcurve25519.h>
#include <intframe.h>
#include <cstringframe.h>
#include <addrframe.h>
#include <ipportframe.h>
#include <seqnoframe.h>
#include <packetdecoder.h>
#include <netgsource.h>
#include <reliableudp.h>
#include <authlistener.h>
#include <nvpairframe.h>
#include <hblistener.h>
#include <hbsender.h>
#include <configcontext.h>
#include <pcap_min.h>
#include <jsondiscovery.h>
#include <switchdiscovery.h>
#include <arpdiscovery.h>
#include <fsprotocol.h>
#include <resourcecmd.h>
#include <resourcequeue.h>
#include <misc.h>
#include <nanoprobe.h>


///@defgroup LibNanoProbe Nanoprobe implementation functions
///  A collection of useful functions for implementing nanoprobes - <i>sans</i> main program.
///@{
void (*nanoprobe_deadtime_agent)(HbListener*)			= NULL;
void (*nanoprobe_heartbeat_agent)(HbListener*)			= NULL;
void (*nanoprobe_warntime_agent)(HbListener*, guint64 howlate)	= NULL;
void (*nanoprobe_comealive_agent)(HbListener*, guint64 howlate)	= NULL;
WINEXPORT NanoHbStats	nano_hbstats = {0U, 0U, 0U, 0U, 0U};
gboolean		nano_connected = FALSE;
WINEXPORT int		errcount = 0;
WINEXPORT GMainLoop*	mainloop = NULL;

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
FSTATIC void		nanoobey_dorscoperation(AuthListener*, FrameSet*, NetAddr*);
FSTATIC void		_nano_send_rscexitstatus(ConfigContext* request, gpointer user_data
,				enum HowDied reason, int rc, int signal, gboolean core_dumped
,				const char * stringresult);
FSTATIC void		nanoobey_cancelrscoperation(AuthListener*, FrameSet*, NetAddr*);
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
FSTATIC gboolean	_nano_final_shutdown(gpointer unused);
FSTATIC gboolean	shutdown_when_outdone(gpointer unused);
FSTATIC gboolean	_nano_initconfig_OK(ConfigContext* config);

HbListener* (*nanoprobe_hblistener_new)(NetAddr*, ConfigContext*) = _real_hblistener_new;

CryptFramePublicKey*	preferred_cma_key_id = NULL;
gboolean		nano_shutting_down = FALSE;
GRand*			nano_random = NULL;
const char *		procname = "nanoprobe";
static AuthListener*	obeycollective = NULL;

static NetAddr*		nanofailreportaddr = NULL;
static NetGSource*	nanotransport = NULL;
static guint		idle_shutdown_gsource = 0;
static ResourceQueue*	RscQ = NULL;
static gboolean		is_encryption_enabled = FALSE;

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
,			  const char * systemnm	///< Name of system doing the reporting
,			  guint64 howlate)	///< How late was the heartbeat?
						///< This is optional - zero means ignore this parameter.
{
		FrameSet*	fs;

		if (nano_shutting_down || NULL == nanofailreportaddr) {
			DEBUGMSG("%s.%d: Ignoring request to send fstype=%d message upstream [%s]."
			,	__FUNCTION__, __LINE__, reporttype
			,	(nano_shutting_down ? "shutting down" : "not connected to CMA"));
			return;
		}

		fs		= frameset_new(reporttype);
		// Construct and send a frameset reporting this event...
		if (howlate > 0) {
			IntFrame*	lateframe	= intframe_new(FRAMETYPE_ELAPSEDTIME, 8);
			lateframe->setint(lateframe, howlate);
			frameset_append_frame(fs, &lateframe->baseclass);
			UNREF2(lateframe);
		}
		// Add the address - if any...
		if (who != NULL) {
			IpPortFrame*	peeraddr	= ipportframe_netaddr_new(FRAMETYPE_IPPORT, who);
			frameset_append_frame(fs, &peeraddr->baseclass);
			UNREF2(peeraddr);
		}
		// Add the system name - if any...
		if (systemnm != NULL) {
			CstringFrame* usf = cstringframe_new(FRAMETYPE_HOSTNAME, 0);
			usf->baseclass.setvalue(&usf->baseclass, g_strdup(systemnm), strlen(systemnm)+1
			,			frame_default_valuefinalize);
			frameset_append_frame(fs, &usf->baseclass);
			UNREF2(usf);
		}
		DEBUGMSG3("%s - sending frameset of type %d", __FUNCTION__, reporttype);
		DUMP3("nanoprobe_report_upstream", &nanofailreportaddr->baseclass, NULL);
		nanotransport->_netio->sendareliablefs(nanotransport->_netio, nanofailreportaddr, DEFAULT_FSP_QID, fs);
		UNREF(fs);
}


/// Standard nanoprobe 'martian heartbeat received' agent.
FSTATIC void
_real_martian_agent(NetAddr* who)
{
	static gint64		last_martian_time = 0;		// microseconds
	static guint		recent_martian_count = 0;
	gint64			now = g_get_monotonic_time();	// microseconds
	const gint64		uS = 1000000;

	++nano_hbstats.martian_count;

	// If it's been more than MARTIAN_TIMEOUT seconds since the last
	// martian, then reset the count of recent martians
	if (now > (last_martian_time + (MARTIAN_TIMEOUT*uS))) {
		recent_martian_count = 0;	
	}

	last_martian_time = now;
	++recent_martian_count;

	// This means if we only get one martian then none, we say nothing
	// This can happen as a result of timing - and it's OK.
	// But if we get more than one, we complain then and once every 10 afterwards
	if ((recent_martian_count % 10) == 2) {
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
 * The send interval can come from the FrameSet or from the
 * @ref ConfigContext parameter we're given - with the FrameSet taking priority.
 *
 * If these parameters are in the FrameSet, they have to precede the FRAMETYPE_IPPORT
 * @ref IpPortFrame in the FrameSet.
 */
void
nanoobey_sendhb(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,   FrameSet*	fs		///<[in] @ref FrameSet indicating who to send HBs to
	,   NetAddr*	fromaddr)	///<[in/out] Address this message came from
{

	GSList*		slframe;
	guint		addrcount = 0;
	ConfigContext*	config = parent->baseclass.config;
	guint16		sendinterval;
	gint64		intvalue;

	if (nano_shutting_down) {
		return;
	}

	g_return_if_fail(fs != NULL);
	(void)fromaddr;
	
	intvalue = config->getint(config, CONFIGNAME_INTERVAL);
	sendinterval = (intvalue > 0 ? intvalue : CONFIG_DEFAULT_HBTIME);

	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		int	frametype = frame->type;
		switch(frametype) {
			IntFrame*	iframe;
			IpPortFrame*	aframe;
			HbSender*	hb;

			case FRAMETYPE_HBINTERVAL:
				iframe = CASTTOCLASS(IntFrame, frame);
				sendinterval = (guint16) iframe->getint(iframe);
				break;
			case FRAMETYPE_RSCJSON:{
				CstringFrame*	csf = CASTTOCLASS(CstringFrame, frame);
				ConfigContext*	cfg;
				const char *	json;
				json = csf->baseclass.value;
				DEBUGMSG3("%s.%d: Got RSCJSON frame: %s", __FUNCTION__
				,	__LINE__, json);
				cfg = configcontext_new_JSON_string(json);
				g_return_if_fail(cfg != NULL);
				intvalue = cfg->getint(cfg, CONFIGNAME_INTERVAL);
				sendinterval = (intvalue > 0 ? intvalue : sendinterval);
				UNREF(cfg);
				break;
			}
			case FRAMETYPE_IPPORT:
				if (0 == sendinterval) {
					g_warning("Send interval is zero in %s", __FUNCTION__);
					continue;
				}
				aframe = CASTTOCLASS(IpPortFrame, frame);
				addrcount++;
				hb = hbsender_new(aframe->getnetaddr(aframe)
				,	parent->baseclass.transport, sendinterval, 0);
				(void)hb;
				break;
		}
	}
}
/**
 * Act on (obey) a @ref FrameSet telling us to expect heartbeats.
 * Such framesets are sent when the Collective Authority wants us to expect
 * Heartbeats from various addresses.  This might be from a FRAMESETTYPE_EXPECTHB
 * FrameSet or a FRAMESETTYPE_SENDEXPECTHB FrameSet.
 * The deadtime, warntime can come from the FrameSet or the
 * @ref ConfigContext parameter we're given - with the FrameSet taking priority.
 *
 * If these parameters are in the FrameSet, they have to precede the FRAMETYPE_IPPORT
 * @ref IpPortFrame in the FrameSet.
 */
void
nanoobey_expecthb(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,   FrameSet*	fs		///<[in] @ref FrameSet indicating who to send HBs to
	,   NetAddr*	fromaddr)	///<[in/out] Address this message came from
{

	GSList*		slframe;
	ConfigContext*	config = parent->baseclass.config;
	guint		addrcount = 0;

	guint64		deadtime;
	guint64		warntime;
	gint64		intvalue;

	(void)fromaddr;

	if (nano_shutting_down) {
		return;
	}

	g_return_if_fail(fs != NULL);
	intvalue = config->getint(config, CONFIGNAME_TIMEOUT);
	deadtime = (intvalue > 0 ? intvalue : CONFIG_DEFAULT_DEADTIME);
	intvalue = config->getint(config, CONFIGNAME_WARNTIME);
	warntime = (intvalue > 0 ? intvalue : CONFIG_DEFAULT_WARNTIME);

	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		int	frametype = frame->type;
		switch(frametype) {
			IntFrame*	iframe;

			case FRAMETYPE_HBDEADTIME:
				iframe = CASTTOCLASS(IntFrame, frame);
				deadtime = iframe->getint(iframe);
				break;

			case FRAMETYPE_HBWARNTIME:
				iframe = CASTTOCLASS(IntFrame, frame);
				intvalue = iframe->getint(iframe);
				warntime = (intvalue > 0 ? (guint64)intvalue : warntime);
				break;

			case FRAMETYPE_RSCJSON: {
				CstringFrame*	csf = CASTTOCLASS(CstringFrame, frame);
				ConfigContext*	cfg;
				const char *	json;
				json = csf->baseclass.value;
				DEBUGMSG3("%s.%d: Got RSCJSON frame: %s", __FUNCTION__
				,	__LINE__, json);
				cfg = configcontext_new_JSON_string(json);
				g_return_if_fail(cfg != NULL);
				intvalue = cfg->getint(cfg, CONFIGNAME_TIMEOUT);
				deadtime = (intvalue > 0 ? (guint64)intvalue : deadtime);
				intvalue = cfg->getint(cfg, CONFIGNAME_WARNTIME);
				warntime = (intvalue > 0 ? (guint64)intvalue : warntime);
				UNREF(cfg);
			}
			break;

			case FRAMETYPE_IPPORT: {
				HbListener*	hblisten;
				IpPortFrame*	aframe;
				NetGSource*	transport = parent->baseclass.transport;
				aframe = CASTTOCLASS(IpPortFrame, frame);
				addrcount++;
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
				,		    &hblisten->baseclass);
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
 * If these parameters are in the FrameSet, they have to precede the FRAMETYPE_IPPORT
 * @ref IpPortFrame in the FrameSet.
 */
void
nanoobey_sendexpecthb(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,   FrameSet*	fs		///<[in] @ref FrameSet indicating who to send HBs to
	,   NetAddr*	fromaddr)	///<[in/out] Address this message came from
{
	g_return_if_fail(fs != NULL && fs->fstype == FRAMESETTYPE_SENDEXPECTHB);

	if (nano_shutting_down) {
		return;
	}
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
			case FRAMETYPE_IPPORT: {
				// This is _so_ much simpler than the code to send them ;-)
				IpPortFrame*	aframe = CASTTOCLASS(IpPortFrame, frame);
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
			case FRAMETYPE_IPPORT: {
				// This is _so_ much simpler than the code to listen for heartbeats...
				IpPortFrame*	aframe = CASTTOCLASS(IpPortFrame, frame);
				NetAddr*	destaddr = aframe->getnetaddr(aframe);
				NetIO*		transport = parent->baseclass.transport->_netio;
				hblistener_unlisten(destaddr);
				transport->closeconn(transport, DEFAULT_FSP_QID, destaddr);
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
 * Nowadays we only want one frame type:
 * <b>FRAMETYPE_CONFIGJSON</b> - A JSON ConfigContext with everything in it.
 */
void
nanoobey_setconfig(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,      FrameSet*	fs	///<[in] @ref FrameSet to process
	,      NetAddr*	fromaddr)	///<[in/out] Address this message came from
{
	GSList*		slframe;
	ConfigContext*	newconfig = NULL;
	ConfigContext*	config = parent->baseclass.config;

	(void)fromaddr;
	DUMP2("nanoobey_setconfig config is from: ", &fromaddr->baseclass, NULL);


	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		switch (frame->type) {
			case FRAMETYPE_CONFIGJSON: { // Configuration JSON string (parameters)
				CstringFrame*	strf = CASTTOCLASS(CstringFrame, frame);
				const char *	jsonstring;
				int		cprs_thresh;
				g_return_if_fail(strf != NULL);
				jsonstring = strf->baseclass.value;
				DEBUGMSG3("%s.%d: Got CONFIGJSON frame: %s", __FUNCTION__, __LINE__
				,	jsonstring);
				newconfig = configcontext_new_JSON_string(jsonstring);
				// This is a good place to check for a compression threshold
				// And possibly other parameters
				if (newconfig) {
					cprs_thresh = 
					newconfig->getint(newconfig, CONFIGNAME_CPRS_THRESH);
					if (cprs_thresh > 0) {
						Frame*	f;
						f = config->getframe(config, CONFIGNAME_COMPRESS);
						if (f) {
							CompressFrame*	cf 
							=	CASTTOCLASS(CompressFrame, f);
							cf->compression_threshold = cprs_thresh;
						}
					}
				}
				goto endloop;
			}
		}
	}
endloop:
	if (NULL == newconfig) {
		g_warning("%s.%d: SETCONFIG message without valid JSON configuration"
		,	__FUNCTION__, __LINE__);
		return;
	}

	if (config) {
		GSList*	keylist = newconfig->keys(newconfig);
		GSList* thiskey;
		GSList*	nextkey;

		// Merge the new configuration into the old configuration data...
		for (thiskey = keylist; thiskey; thiskey=nextkey) {
			const char *		key = thiskey->data;
			enum ConfigValType	valtype = newconfig->gettype(newconfig, key);

			nextkey=thiskey->next;

			switch(valtype) {
				case CFG_NETADDR:
					config->setaddr(config, key, newconfig->getaddr(newconfig, key));
					break;

				case CFG_CFGCTX: 
					config->setconfig(config, key, newconfig->getconfig(newconfig, key));
					break;

				case CFG_STRING:
					config->setstring(config, key, newconfig->getstring(newconfig, key));
					break;

				case CFG_BOOL:
					config->setbool(config, key, newconfig->getbool(newconfig, key));
					break;

				case CFG_INT64:
					config->setint(config, key, newconfig->getint(newconfig, key));
					break;

				case CFG_FLOAT:
					config->setdouble(config, key, newconfig->getdouble(newconfig, key));
					break;
				default:
					break;
			}
			g_slist_free1(thiskey);
		}
		if (DEBUG >= 2) {
			DEBUGMSG("%s.%d: Validating the config we processed...", __FUNCTION__, __LINE__);
			if (!_nano_initconfig_OK(config)) {
				DEBUGMSG("%s.%d: config we read is good", __FUNCTION__, __LINE__);
			}else{
				DEBUGMSG("%s.%d: config we read is BAD", __FUNCTION__, __LINE__);
			}
		}
	}
	UNREF(newconfig);

	DUMP3("nanoobey_setconfig: cfg is", &config->baseclass, NULL);

	if (config && config->getaddr(config, CONFIGNAME_CMAFAIL) != NULL) {
		if (nanofailreportaddr == NULL) {
			nanofailreportaddr = config->getaddr(config, CONFIGNAME_CMAFAIL);
		}else if (config->getaddr(config, CONFIGNAME_CMAFAIL) != nanofailreportaddr) {
			UNREF(nanofailreportaddr);
			nanofailreportaddr = config->getaddr(config, CONFIGNAME_CMAFAIL);
		}
		DUMP3("nanoobey_setconfig: nanofailreportaddr", &nanofailreportaddr->baseclass, NULL);
		{
			// Alias localhost to the CMA nanofailreportaddr (at least for now...)
			///@todo If we split the CMA into multiple machines this will need to change.
			///@todo do we even need this alias code at all?

			NetAddr* localhost = netaddr_string_new("127.0.0.1");
			NetIO* io = parent->baseclass.transport->_netio;
			io->addalias(io, localhost, nanofailreportaddr);
			UNREF(localhost);
		}
		REF(nanofailreportaddr);
	}
	g_message("Connected to CMA.  Happiness :-D");
	nano_connected = TRUE;
}//nanoobey_setconfig

/**
 * Act on (obey) a @ref FrameSet telling us to increment or decrement debug levels
 * either on a specific set of classes, or on all classes.
 */
FSTATIC void
nanoobey_change_debug(gint plusminus		///<[in] +1 or -1 - for incrementing/decrementing
	,	      AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,	      FrameSet*	fs		///<[in] @ref FrameSet giving the details
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
	
	if (nano_shutting_down) {
		return;
	}

	DEBUGMSG3("%s - got frameset", __FUNCTION__);
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
				DEBUGMSG3("%s - got DISCOVERYNAME %s", __FUNCTION__, discoveryname);
			}
			break;

			case FRAMETYPE_DISCINTERVAL: { // Discovery interval
				IntFrame* intf = CASTTOCLASS(IntFrame, frame);
				interval = (guint)intf->getint(intf);
				DEBUGMSG3("%s - got DISCOVERYINTERVAL %d", __FUNCTION__, interval);
			}
			break;

			case FRAMETYPE_DISCJSON: { // Discovery JSON string (parameters)
				CstringFrame* strf = CASTTOCLASS(CstringFrame, frame);
				const char *  jsonstring;
				g_return_if_fail(strf != NULL);
				jsonstring = strf->baseclass.value;
				g_return_if_fail(discoveryname != NULL);
				DEBUGMSG3("Got DISCJSON frame: %s %d %s" , discoveryname, interval, jsonstring);
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

/// Callback that gets called when a resource operation sends back status
FSTATIC void
_nano_send_rscexitstatus(ConfigContext* request, gpointer user_data
,			enum HowDied reason, int rc, int signal, gboolean core_dumped
,			const char * stringresult)
{
	NetGSource*	transport = CASTTOCLASS(NetGSource, user_data);
	ConfigContext*	response = configcontext_new(0);
	FrameSet*	fs = frameset_new(FRAMESETTYPE_RSCOPREPLY);
	CstringFrame*	sf = cstringframe_new(FRAMETYPE_RSCJSONREPLY, 0);
	char*		rsp_json;

	struct {
		const char*	framename;
		int		framevalue;
	} pktframes[] = {
		{REQREASONENUMNAMEFIELD,	reason},
		{REQRCNAMEFIELD,		rc},
		{REQSIGNALNAMEFIELD,		signal},
	};
	unsigned	j;

	for (j=0; j < DIMOF(pktframes); ++j) {
		response->setint(response, pktframes[j].framename, pktframes[j].framevalue);
	}
	response->setbool(response, REQCOREDUMPNAMEFIELD, core_dumped);
	if (stringresult) {
		response->setstring(response, REQSTRINGRETNAMEFIELD, stringresult);
	}
	// Copy the request ID over from the original request
	response->setint(response, REQIDENTIFIERNAMEFIELD
	,	request->getint(request, REQIDENTIFIERNAMEFIELD));
	// Copy the resource name (instance) over from the original request
	response->setstring(response, CONFIGNAME_INSTANCE
	,	request->getstring(request, CONFIGNAME_INSTANCE));
	// Package it up as a JSON string to send to the CMA
	rsp_json = response->baseclass.toString(&response->baseclass);
	UNREF(response);
	DEBUGMSG1("Reporting resource state change: %s", rsp_json);
	sf->baseclass.setvalue(&sf->baseclass, rsp_json, strlen(rsp_json)+1, g_free);
	frameset_append_frame(fs, &sf->baseclass);
	UNREF2(sf);
	transport->_netio->sendareliablefs(transport->_netio, nanofailreportaddr, DEFAULT_FSP_QID, fs);
	UNREF(fs);
}
FSTATIC void
nanoobey_dorscoperation(AuthListener* parent, FrameSet* fs, NetAddr*fromaddr)
{
	GSList*		slframe;

	(void)parent;
	(void)fromaddr;
	if (nano_shutting_down) {
		return;
	}
	if (NULL == RscQ) {
		RscQ = resourcequeue_new(0);
	}
	// Loop over the frames, looking for those we know what to do with ;-)
	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		CstringFrame* csframe;
		ConfigContext*	cfg;
		if (frame->type != FRAMETYPE_RSCJSON) {
			continue;
		}
		csframe = CASTTOCLASS(CstringFrame, frame);
		cfg = configcontext_new_JSON_string(csframe->baseclass.value);
		if (NULL == cfg) {
			g_warning("%s.%d: Received malformed JSON string [%*s]"
			,	__FUNCTION__, __LINE__
			,	csframe->baseclass.length-1
			,	(char*)csframe->baseclass.value);
			continue;
		}
		RscQ->Qcmd(RscQ, cfg, _nano_send_rscexitstatus, nanotransport);
		UNREF(cfg);
	}
}

FSTATIC void
nanoobey_cancelrscoperation(AuthListener* parent, FrameSet* fs, NetAddr* fromaddr)
{
	GSList*		slframe;

	(void)parent;
	(void)fromaddr;
	if (NULL == RscQ) {
		RscQ = resourcequeue_new(0);
	}

	for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
		Frame* frame = CASTTOCLASS(Frame, slframe->data);
		CstringFrame* csframe;
		ConfigContext*	cfg;
		if (frame->type != FRAMETYPE_RSCJSON) {
			continue;
		}
		csframe = CASTTOCLASS(CstringFrame, frame);
		cfg = configcontext_new_JSON_string(csframe->baseclass.value);
		if (NULL == cfg) {
			g_warning("%s.%d: Received malformed JSON string [%*s]"
			,	__FUNCTION__, __LINE__
			,	csframe->baseclass.length-1
			,	(char*)csframe->baseclass.value);
			continue;
		}
		RscQ->cancel(RscQ, cfg);
		UNREF(cfg);
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

	DEBUGMSG3("%s(%s,%d,%s)", __FUNCTION__, instance, interval, json);
	jsonroot = configcontext_new_JSON_string(json);
	g_return_if_fail(jsonroot != NULL);
	disctype = jsonroot->getstring(jsonroot, CONFIGNAME_TYPE);
	g_return_if_fail(disctype != NULL);

        if (strcmp(disctype, "#SWITCH") == 0) {
            //printf("*** jsonroot = %s: \n", jsonroot->baseclass.toString(&jsonroot->baseclass));
	    DEBUGMSG3("%s.%d: jsonroot = %s", __FUNCTION__, __LINE__, jsonroot->baseclass.toString(&jsonroot->baseclass));
	    switchdiscovery_new(jsonroot, G_PRIORITY_LOW, g_main_context_default()
	    ,	transport, config, 0);
        } else if (strcmp(disctype, "#ARP") == 0) {
            //printf("*** jsonroot = %s: \n", jsonroot->baseclass.toString(&jsonroot->baseclass));
	    DEBUGMSG3("%s.%d: jsonroot = %s", __FUNCTION__, __LINE__, jsonroot->baseclass.toString(&jsonroot->baseclass));
	    arpdiscovery_new(jsonroot, G_PRIORITY_LOW, g_main_context_default()
	    ,	transport, config, 0);
        } else {
	    discovery = jsondiscovery_new(disctype, instance, interval, jsonroot
	    ,			      transport, config, 0);
	    if (discovery) {
		UNREF2(discovery);
	    }
        }

	UNREF(jsonroot);
}

/// Stuff we need only for passing parameters through our glib infrastructures - to start up nanoprobes.
struct startup_cruft {
	const char *	initdiscover;
	int		discover_interval;
	NetGSource*	iosource;
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

	if (state == DONE || nano_shutting_down) {
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
		,	cruft->iosource, obeycollective->baseclass.config, 0);
		UNREF(jsondata);
		UNREF2(jd);
		state = WAIT;
		return TRUE;
	}
	if (obeycollective->baseclass.config->getstring(obeycollective->baseclass.config, cfgname)) {
		state = DONE;
		// Call it once, and arrange for it to repeat until we hear back.
		g_timeout_add_seconds(5, nano_reqconfig, gcruft);
		nano_reqconfig(gcruft);
		return FALSE;
	}
	return TRUE;
}

// Check to see if the parameters we really need are present in our config
FSTATIC gboolean
_nano_initconfig_OK(ConfigContext* config)
{
	if (config->getaddr(config, CONFIGNAME_CMAFAIL)		!= NULL
	&&  config->getaddr(config, CONFIGNAME_CMADISCOVER)	!= NULL) {
		DEBUGMSG2("%s.%d: FOUND '%s and '%s' in config.", __FUNCTION__, __LINE__
		,	CONFIGNAME_CMAFAIL, CONFIGNAME_CMADISCOVER)
		return TRUE;
	}
	DUMP2("_nano_initconfig_OK: Could not find both of " CONFIGNAME_CMAFAIL
	" and " CONFIGNAME_CMADISCOVER "  in " , &config->baseclass, "");
	return FALSE;
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
	IpPortFrame*	ippf;
	const char *	cfgname = cruft->initdiscover;
	ConfigContext*	context = obeycollective->baseclass.config;
	NetAddr*	cmainit = context->getaddr(context, CONFIGNAME_CMAINIT);
	const char *	jsontext;
	char *		sysname = NULL;
	NetAddr*	boundaddr;
 	IntFrame*       timeframe;
	static guint64	starttime = 0L;

	if (nano_shutting_down) {
		return FALSE;
	}

	// We <i>have</i> to know our initial request address - or all is lost.
	// NOTE THAT THIS ADDRESS MIGHT BE MULTICAST AND MIGHT BE USED ONLY ONCE
	g_return_val_if_fail(cmainit != NULL, FALSE);

	// Our initial configuration message must contain these parameters.
	if (_nano_initconfig_OK(context)) {
		// We're good
		return FALSE;
	}
	fs = frameset_new(FRAMESETTYPE_STARTUP);

	// Put in the system name
	usf = cstringframe_new(FRAMETYPE_HOSTNAME, 0);
	sysname = proj_get_sysname();
	usf->baseclass.setvalue(&usf->baseclass, g_strdup(sysname), strlen(sysname)+1
	,			frame_default_valuefinalize);
	frameset_append_frame(fs, &usf->baseclass);
	UNREF2(usf);

	// Put in our listening address - useful if we're NATted
	boundaddr = cruft->iosource->_netio->boundaddr(cruft->iosource->_netio);
	ippf = ipportframe_netaddr_new(FRAMETYPE_IPPORT, boundaddr);
	UNREF(boundaddr);
	frameset_append_frame(fs, &ippf->baseclass);
	UNREF2(ippf);

	// Put in our startup time - helps the CMA eliminate dups (w/o protocol)
	// If it gets busy, we might send it another request before it finishes the first
	// one. If it's busy that's the worst time to give it unnecessary work.
	if (starttime == 0) {
		starttime = g_get_real_time();
	}
	timeframe = intframe_new(FRAMETYPE_WALLCLOCK, sizeof(starttime));
	timeframe->setint(timeframe, starttime);
	frameset_append_frame(fs, &timeframe->baseclass);
	UNREF2(timeframe);

	// Put in the JSON configuration text
	jsontext = context->getstring(context, cfgname);
	csf = cstringframe_new(FRAMETYPE_JSDISCOVER, 0);
	csf->baseclass.setvalue(&csf->baseclass, g_strdup(jsontext), strlen(jsontext)+1
	,			frame_default_valuefinalize);

	frameset_append_frame(fs, &csf->baseclass);
	UNREF2(csf);

	// We've constructed the frameset - now send it - unreliably...
	// That's because the reply is typically from a different address
	// which would confuse the blazes out of the reliable comm code.
	cruft->iosource->sendaframeset(cruft->iosource, cmainit, fs);
	DEBUGMSG("%s.%d: Sent initial STARTUP frameset for %s."
	,	__FUNCTION__, __LINE__, sysname);
	g_free(sysname); sysname = NULL; 
	UNREF(fs);
	return TRUE;
}

static PacketDecoder*	decoder = NULL;


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
	{FRAMESETTYPE_DORSCOP,		nanoobey_dorscoperation},
	{FRAMESETTYPE_STOPRSCOP,	nanoobey_cancelrscoperation},
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
 *	Eventually we are likely to be told to do other things (monitor services, set up discovery,
 *	respond to other queries) but we'll always go through these steps.
 */

WINEXPORT void
nano_start_full(const char *initdiscoverpath	///<[in] pathname of initial network discovery agent
	,	guint		discover_interval///<[in] discovery interval for agent above
	,	NetGSource*	io		///<[in/out] network connectivity object
	,	ConfigContext* config)		///<[in/out] configuration object
{
	static struct startup_cruft cruftiness;
	struct startup_cruft initcrufty = {
		initdiscoverpath,
		discover_interval,
		io,
	};
	
	BINDDEBUG(nanoprobe_main);
	nano_shutting_down = FALSE;
	if (NULL == nano_random) {
		nano_random = g_rand_new();
	}
 	hblistener_set_martian_callback(_real_martian_agent);
	cruftiness = initcrufty;
	g_source_ref(CASTTOCLASS(GSource, io));
	nanotransport = io;

	obeycollective = authlistener_new(0, collective_obeylist, config, TRUE);
	obeycollective->baseclass.associate(&obeycollective->baseclass, io);
	nanoprobe_initialize_keys();
	// Initiate the startup process
	g_idle_add(nano_startupidle, &cruftiness);
}

/// Shut down the things started up by nano_start_full() - mainly free storage to make valgrind happy...
WINEXPORT void
nano_shutdown(gboolean report)
{
	if (report) {
		NetIOstats*	ts = &nanotransport->_netio->stats;
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of heartbeats:", nano_hbstats.heartbeat_count);
		g_info("%-35s %8d", "Count of deadtimes:", nano_hbstats.dead_count);
		g_info("%-35s %8d", "Count of warntimes:", nano_hbstats.warntime_count);
		g_info("%-35s %8d", "Count of comealives:", nano_hbstats.comealive_count);
		g_info("%-35s %8d", "Count of martians:", nano_hbstats.martian_count);
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of recvfrom calls:", ts->recvcalls);
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of pkts read:", ts->pktsread);
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of framesets read:", ts->fsreads);
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of sendto calls:", ts->sendcalls);
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of pkts written:", ts->pktswritten);
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of framesets written:", ts->fswritten);
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of reliable framesets sent:", ts->reliablesends);
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of reliable framesets recvd:", ts->reliablereads);
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of ACKs sent:", ts->ackssent);
		g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of ACKs recvd:", ts->acksrecvd);
	}
	hbsender_stopallsenders();
	hblistener_shutdown();


	if (nanofailreportaddr) {
		UNREF(nanofailreportaddr);
	}
	if (nanotransport) {
		g_source_destroy(CASTTOCLASS(GSource, nanotransport));
		g_source_unref(CASTTOCLASS(GSource, nanotransport));
		nanotransport = NULL;
	}
	// Free packet decoder
	if (decoder) {
		UNREF(decoder);
	}
	obeycollective->baseclass.dissociate(&obeycollective->baseclass);
	UNREF2(obeycollective);
}

/// Initiate shutdown - return TRUE if we have shut down immediately...
WINEXPORT gboolean
nano_initiate_shutdown(void)
{

	if (nano_connected) {
		FsProtocol*	proto = CASTTOCLASS(ReliableUDP, nanotransport->_netio)->_protocol;
		char *	sysname;
		DEBUGMSG("Sending HBSHUTDOWN to CMA");
		sysname = proj_get_sysname();
		nanoprobe_report_upstream(FRAMESETTYPE_HBSHUTDOWN, NULL, sysname, 0);
		g_free(sysname); sysname = NULL;
		// Initiate connection shutdown.
		// This process will wait for all our output to be ACKed.
		// It also has an ACK timer, so it won't wait forever...
		proto->closeall(proto);
		idle_shutdown_gsource = g_timeout_add_full(G_PRIORITY_LOW, 100 // .1 Secs
		,		shutdown_when_outdone, NULL, NULL);
		nano_shutting_down = TRUE;
		// Unregister all discovery modules.  Keep us from starting any new ones...
		discovery_unregister_all();
		// Let's not start any more resource operations either...
		if (RscQ) {
			RscQ->cancelall(RscQ);
			UNREF(RscQ);
		}
		// @TODO We need to ignore additional requests during shutdown as well...
	}else{
		nano_shutting_down = TRUE;
		g_warning("%s: Never connected to CMA - cannot send shutdown message.", procname);
		++errcount;  // Trigger non-zero exit code...
		_nano_final_shutdown(NULL);
		return TRUE;
	}
	return FALSE;
}

/// Shut down everything when output is all ACKed - this is idle loop code
FSTATIC gboolean
shutdown_when_outdone(gpointer unused)
{
	ReliableUDP*	t = CASTTOCLASS(ReliableUDP, nanotransport->_netio);
	FsProtocol*	proto = CASTTOCLASS(FsProtocol, t->_protocol);
	static		gint64		giveuptime = 0;
	(void)unused;
	if (giveuptime == 0) {
		giveuptime = g_get_monotonic_time() + ((gint64)(FSPROTO_ACKTIMEOUTINT+1)*(gint64)1000000L);
	}
	if (g_get_monotonic_time() > giveuptime) {
		g_critical("Immediate shutdown. Connections still active after %d seconds."
		,	(int)FSPROTO_ACKTIMEOUTINT);
		g_main_quit(mainloop);
		return FALSE;
	}
	// Wait for all our connections to be shut down
	if (proto->activeconncount(proto) == 0){
		g_info("%s.%d: Shutting down - all connections closed."
		,	__FUNCTION__, __LINE__);
		g_main_quit(mainloop);
		return FALSE;
	}
	return TRUE;
}
// Final Shutdown -- a contingency timer to make sure we eventually shut down
FSTATIC gboolean
_nano_final_shutdown(gpointer unused)
{
	(void)unused;
	g_info("%s.%d: Initiating final shutdown", __FUNCTION__, __LINE__);
	if (nano_connected && nanotransport->_netio->outputpending(nanotransport->_netio)){
		g_warning("Shutting down with unACKed output.");
		DUMP("Transport info", &nanotransport->_netio->baseclass, NULL);
	}
	if (idle_shutdown_gsource) {
		g_source_remove(idle_shutdown_gsource);
		idle_shutdown_gsource = 0;
	}
	if (nano_random) {
		g_rand_free(nano_random);
		nano_random = NULL;
	}
	g_main_quit(mainloop);
	return FALSE;
}

// Initialize our encryption setup...
WINEXPORT void
nanoprobe_initialize_keys(void)
{
	GList*		key_id_list;
	GList*		thiselem;
	char *		sysname = proj_get_sysname();
	int		sysname_len = strlen(sysname);
	// Read in and cache all our key pairs
	cryptcurve25519_cache_all_keypairs();

	key_id_list = cryptframe_get_key_ids();
	// We're looking for our own signing key, and all the CMA's signing keys
	for (thiselem = key_id_list; NULL != thiselem; thiselem=g_list_next(thiselem)) {
		const char *	key_id = (char*)thiselem->data;
		// Format of our key ids: "system-name@@our-key-hash-value"
		if (strncmp(key_id, sysname, sysname_len) == 0 && key_id[sysname_len] == '@') {
			if (NULL != cryptframe_public_key_by_id(key_id)) {
				cryptframe_set_signing_key_id(key_id);
			}
		}else if (strncmp(key_id, CMA_KEY_PREFIX, sizeof(CMA_KEY_PREFIX)-1) == 0) {
			cryptframe_associate_identity(CMA_IDENTITY_NAME, key_id);
		}
	}
	if (cryptframe_key_ids_for(CMA_IDENTITY_NAME) == NULL) {
		g_warning("%s.%d: Encryption not enabled (no CMA public key available)."
		,	__FUNCTION__, __LINE__);
	}else{
		// Generate a key pair if we don't already have one
		if (cryptframe_get_signing_key() == NULL) {
			char *	key_id = (char*)thiselem->data;
			key_id = cryptcurve25519_gen_persistent_keypair(NULL);
			if (NULL != key_id) {
				cryptframe_set_signing_key_id(key_id);
				g_free(key_id);
			}else{
				g_warning("%s.%d: Encryption not enabled"
				": cannot generate public key pair.", __FUNCTION__, __LINE__);
			}
		}
		if (cryptframe_get_signing_key() != NULL) {
			cryptframe_set_encryption_method(cryptcurve25519_new_generic);
			is_encryption_enabled = TRUE;
		}
	}
	g_list_free(key_id_list); key_id_list = NULL;
	g_free(sysname); sysname = NULL;
}

/// Associate the given encryption key for all CMA addresses in the config we're given.
/// We assume any address in the config whose name starts with "cma" is a CMA address.
/// The purpose of this function is to make sure we use that key when talking to the CMA.
WINEXPORT void
nanoprobe_associate_cma_key(const char *key_id, ConfigContext *cfg)
{
	GSList*	keys = cfg->keys(cfg);
	GSList*	thiskey;
	static const char	cmaprefix[] = "cma";

	for (thiskey = keys; NULL != thiskey; thiskey=g_slist_next(thiskey)) {
		const char *	keyname = (const char *)thiskey->data;

		// Is this entry a NetAddr whose name starts with "cma"?
		if (	cfg->gettype(cfg, keyname) == CFG_NETADDR
		&&	strncmp(keyname, cmaprefix, sizeof(cmaprefix)-1) == 0) {
			NetAddr*	destaddr = cfg->getaddr(cfg, keyname);
			cryptframe_set_dest_public_key_id(destaddr, key_id);
		}
	}
	g_slist_free(keys); keys=NULL;
}

#define	SECOND	1000000
#define	COMPLAINT_INTERVAL (60*SECOND)

/// Return TRUE if this FrameSet came
WINEXPORT gboolean
nanoprobe_is_cma_frameset(const FrameSet * fs)
{
	gpointer		maybecrypt;
	CryptFrame*		cryptframe;
	const char*		identity;
	
	if (!is_encryption_enabled) {
		static	gint64	last_complaint = 0L;
		gint64		now = g_get_monotonic_time();
		if (now >= (last_complaint+COMPLAINT_INTERVAL)) {
			g_critical("%s.%d: Encryption is NOT enabled.  Encryption REQUIRED for production."
			,	__FUNCTION__, __LINE__);
			g_info("See Assimilation documentation for how to distribute the CMA's public key.");
			last_complaint = now;
		}
		// Without encryption, we have to accept every frameset as authenticated...
		return TRUE;
	}

	// If we have an encryption frame it must be the second frame
	maybecrypt = g_slist_nth_data(fs->framelist, 2);
	if (!OBJ_IS_A(maybecrypt, maybecrypt)) {
		return FALSE;
	}
	cryptframe = CASTTOCLASS(CryptFrame, maybecrypt);
	identity = cryptframe_whois_key_id(cryptframe->sender_key_id);
	return (strcmp(identity, CMA_IDENTITY_NAME) == 0);
}
///@}
