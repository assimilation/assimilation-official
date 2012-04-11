/**
 * @file
 * @brief Library of code to support initial creation of a nanoprobe process.
 * @details This includes the code to obey various CMA packets, and some functions to startup and shut down
 * a nanoprobe process.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 *
 */
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
#include <seqnoframe.h>
#include <packetdecoder.h>
#include <netgsource.h>
#include <authlistener.h>
#include <nvpairframe.h>
#include <hblistener.h>
#include <hbsender.h>
#include <configcontext.h>
#include <jsondiscovery.h>

void nano_start_full(const char *initdiscoverpath, guint discover_interval, NetGSource* io, ConfigContext* config);
void nano_shutdown(void);

FSTATIC void		nanoobey_sendexpecthb(AuthListener*, FrameSet* fs, NetAddr*);
FSTATIC void		nanoobey_sendhb(AuthListener*, FrameSet* fs, NetAddr*);
FSTATIC void		nanoobey_expecthb(AuthListener*, FrameSet* fs, NetAddr*);
FSTATIC void		nanoobey_setconfig(AuthListener*, FrameSet* fs, NetAddr*);
FSTATIC gboolean	nano_startupidle(gpointer gcruft);
FSTATIC	gboolean	nano_reqconfig(gpointer gcruft);
FSTATIC void		_real_heartbeat_agent(HbListener* who);
FSTATIC void		_real_deadtime_agent(HbListener* who);
FSTATIC void		_real_warntime_agent(HbListener* who, guint64 howlate);
FSTATIC void		_real_comealive_agent(HbListener* who, guint64 howlate);
FSTATIC HbListener*	_real_hblistener_new(NetAddr*, ConfigContext*);
static int _nano_dead_count = 0;
static int _nano_heartbeat_count = 0;
static int _nano_warntime_count = 0;
static int _nano_comealive_count = 0;

void (*nanoprobe_deadtime_agent)(HbListener*)			= NULL;
void (*nanoprobe_heartbeat_agent)(HbListener*)			= NULL;
void (*nanoprobe_warntime_agent)(HbListener*, guint64 howlate)	= NULL;
void (*nanoprobe_comealive_agent)(HbListener*, guint64 howlate)	= NULL;
HbListener* (*nanoprobe_hblistener_new)(NetAddr*, ConfigContext*) = _real_hblistener_new;

/// Default HbListener constructor.
/// Supply your own in nanoprobe_hblistener_new if you need to construct a subclass object.
FSTATIC HbListener*
_real_hblistener_new(NetAddr* addr, ConfigContext* context)
{
	return hblistener_new(addr, context, 0);
}


/// Standard nanoprobe 'deadtime elapsed' agent.
/// Supply your own in nanoprobe_deadtime_agent if you want us to call it.
FSTATIC void
_real_deadtime_agent(HbListener* who)
{
	++_nano_dead_count;
	if (nanoprobe_deadtime_agent) {
		nanoprobe_deadtime_agent(who);
	}else{
		char *	addrstring;
		addrstring = who->listenaddr->baseclass.toString(who->listenaddr);
		g_warning("Peer at address %s is dead (has timed out).", addrstring);
		g_free(addrstring);
	}
}

/// Standard nanoprobe 'hearbeat received' agent.
/// Supply your own in nanoprobe_heartbeat_agent if you want us to call it.
FSTATIC void
_real_heartbeat_agent(HbListener* who)
{
	++_nano_heartbeat_count;
	if (nanoprobe_heartbeat_agent) {
		nanoprobe_heartbeat_agent(who);
	}
}


/// Standard nanoprobe 'warntime elapsed' agent - called when a heartbeat arrives after 'warntime' but before 'deadtime'.
/// Supply your own in nanoprobe_warntime_agent if you want us to call it.
FSTATIC void
_real_warntime_agent(HbListener* who, guint64 howlate)
{
	++_nano_warntime_count;
	if (nanoprobe_warntime_agent) {
		nanoprobe_warntime_agent(who, howlate);
	}else{
		char *	addrstring;
		guint64 mslate = howlate / 1000;
		addrstring = who->listenaddr->baseclass.toString(who->listenaddr);
		g_warning("Heartbeat from peer at address %s was "FMT_64BIT"d ms late.", addrstring, mslate);
		g_free(addrstring);
	}
}
/// Standard nanoprobe 'warntime elapsed' agent - called when a heartbeats arrive after 'deadtime'.
/// Supply your own in nanoprobe_comealive_agent if you want us to call it.
FSTATIC void
_real_comealive_agent(HbListener* who, guint64 howlate)
{
	++_nano_comealive_count;
	if (nanoprobe_comealive_agent) {
		nanoprobe_comealive_agent(who, howlate);
	}else{
		char *	addrstring;
		double secsdead = ((double)((howlate+50000) / 100000))/10.0; // Round to nearest tenth of a second
		addrstring = who->listenaddr->baseclass.toString(who->listenaddr);
		g_warning("Peer at address %s came alive after being dead for %g seconds.", addrstring, secsdead);
		g_free(addrstring);
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
				hblisten->baseclass.baseclass.unref(hblisten); hblisten = NULL;
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

	nanoobey_sendhb  (parent, fs, fromaddr);
	nanoobey_expecthb(parent, fs, fromaddr);
}

/*
 * Act on (obey) a FRAMESETTYPE_SETCONFIG @ref FrameSet.
 * This frameset is sent during the initial configuration phase.
 * It contains name value pairs to save into our configuration (ConfigContext).
 * These might be {string,string} pairs or {string,ipaddr} pairs, or
 * {string, integer} pairs.  We process them all.
 * The frame types that we receive for these are:
 * FRAMETYPE_PARAMNAME - parameter name to set
 * FRAMETYPE_CSTRINGVAL - string value to associate with name
 * FRAMETYPE_CINTVAL - integer value to associate with naem
 * FRAMETYPE_PORTNUM - port number for subsequent IP address
 * FRAMETYPE_IPADDR - IP address to associate with name
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
	g_debug("In %s", __FUNCTION__);

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
}//nanoobey_setconfig

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
	const char *	cfgname = strrchr(cruft->initdiscover, '/');

	g_warning("In nano_startupidle(state:%d) - looking for %s in config"
	,	  state, cfgname);
	if (state == DONE) {
		return FALSE;
	}
	if (cfgname == NULL) {
		cfgname = cruft->initdiscover;
	}
	if (state == INIT) {
		JsonDiscovery* jd = jsondiscovery_new(cruft->initdiscover
		,	cruft->discover_interval
		,	cruft->iosource, cruft->context, 0);
		g_warning("In nano_startupidle - starting discovery code");
		jd->baseclass.baseclass.unref(jd);
		state = WAIT;
		return TRUE;
	}
	if (cruft->context->getstring(cruft->context, cfgname)) {
		state = DONE;
		// Call it once, and arrange for it to repeat until we hear back.
		nano_reqconfig(gcruft);
		g_timeout_add_seconds(5, nano_reqconfig, gcruft);
		return FALSE;
	}
	return TRUE;
}

/// Function to request our configuration data
/// This is called from a g_main_loop timeout, and directly (once).
gboolean
nano_reqconfig(gpointer gcruft)
{
	struct startup_cruft* cruft = gcruft;
	FrameSet*	fs;
	CstringFrame*	csf;
	const char *	cfgname = strrchr(cruft->initdiscover, '/');
	ConfigContext*	context = cruft->context;
	NetAddr *	cmainit = context->getaddr(context, CONFIGNAME_CMAINIT);

	// We <i>have</i> to know our initial request address
	g_return_val_if_fail(cmainit != NULL, FALSE);

	// Our configuration response should contain these parameters.
	if (context->getaddr(context, CONFIGNAME_CMAADDR) != NULL
	&&  context->getaddr(context, CONFIGNAME_CMAFAIL) != NULL
	&&  context->getaddr(context, CONFIGNAME_CMADISCOVER) != NULL
	&&  context->getint(context, CONFIGNAME_CMAPORT) > 0) {
		return FALSE;
	}
	fs = frameset_new(FRAMESETTYPE_STARTUP);
	csf = cstringframe_new(FRAMETYPE_JSDISCOVER, 0);
	csf->baseclass.setvalue(&csf->baseclass, strdup(cfgname), strlen(cfgname)+1
	,			frame_default_valuefinalize);
	
	frameset_append_frame(fs, &csf->baseclass);
	cruft->iosource->sendaframeset(cruft->iosource, cmainit, fs);
	fs->unref(fs);
	csf->baseclass.baseclass.unref(csf);
	return TRUE;
}

FrameTypeToFrame	decodeframes[] = FRAMETYPEMAP;

/**
 * Here is how the startup process works:
 *
 * 1.	Submit a network discovery request from an idle task, rescheduling until it completes.
 *	(or this could be done every 10ms or so via a timer) {nano_startupidle()}
 *
 * 2.	Send out a "request for configuration" packet (role: nanoprobe) once the discovery
 *	shows up in the config context. {nano_reqconfig()}
 *
 * 3.	When the CMA receives this request (role: CMA) it sends out a SETCONFIG packet
 *	and a series of SENDEXPECTHB heartbeat packets {fakecma_startup()}
 *
 * 4.	When the SETCONFIG packet is received (role: nanoprobe), it enables the sending of
 *	discovery data from all (JSON and switch (LLDP/CDP)) sources.  {nanoobey_setconfig()}
 *
 * 5.	When the SENDEXPECTHB packet is received (role: nanoprobe), it starts sending
 *	heartbeats and timing heartbeats to flag "dead" machines.
 *
 * 6.	Now everything is running in "normal" mode.
 */

static PacketDecoder*	decoder;
void
nano_start_full(const char *initdiscoverpath, guint discover_interval, NetGSource* io, ConfigContext* config)
{
	static struct startup_cruft the_real_cruft;
	struct startup_cruft cruft = {
		initdiscoverpath,
		discover_interval,
		io,
		config
	};
	the_real_cruft = cruft;

	g_idle_add(nano_startupidle, &the_real_cruft);
	decoder = packetdecoder_new(0, decodeframes, DIMOF(decodeframes));
}
void
nano_shutdown(void)
{
	// Free packet decoder
	decoder->baseclass.unref(decoder);
}
