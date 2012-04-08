/**
 * @file
 * @brief Simple pcap testing code using 'mainloop'.
 * Listens for CDP or LLDP packets on the network - all using the mainloop dispatch code.
 * Probably a short-lived piece of test code.  Well... Maybe not so short-lived, but definitely
 * basic testing.
 *
 * Here's what it does at the moment:
 *	+ listen for LLDP or CDP packets and:
 *		demarshall them and remarshall them to see if they're the same
 *	+ listen for heartbeats - and there won't be any at first
 *		When we have declared ourself dead, we begin to send ourselves heartbeats.
 *		The first one will be declared late, but the remaining ones should be on time.
 *	The software is built to expect this behavior from itself and print info messages when
 *	things go as they should, and warning messages when things deviate from expectations.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 *
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <projectcommon.h>
#include <frameset.h>
#include <ctype.h>
#include <cdp.h>
#include <lldp.h>
#include <server_dump.h>
#include <pcap_GSource.h>
#include <packetdecoder.h>
#include <netgsource.h>
#include <netioudp.h>
#include <netaddr.h>
#include <hblistener.h>
#include <authlistener.h>
#include <hbsender.h>
#include <signframe.h>
#include <cryptframe.h>
#include <compressframe.h>
#include <intframe.h>
#include <addrframe.h>
#include <cstringframe.h>
#include <nvpairframe.h>
#include <seqnoframe.h>
#include <frametypes.h>
#include <jsondiscovery.h>



#define		TESTPORT	1984

int		expected_dead_count = 1;
gint64		maxpkts  = G_MAXINT64;
gint64		pktcount = 0;
GMainLoop*	loop = NULL;
NetIO*		nettransport;
NetGSource*	netpkt;
NetAddr*	destaddr;
NetAddr*	otheraddr;
NetAddr*	otheraddr2;
NetAddr*	anyaddr;
HbSender*	sender = NULL;
int		wirepktcount = 0;
int		heartbeatcount = 0;
int		errcount = 0;
int		pcapcount = 0;
void send_encapsulated_packet(gconstpointer, gconstpointer, const struct pcap_pkthdr *, const char *);
gboolean gotapcappacket(GSource_pcap_t*, pcap_t *, gconstpointer, gconstpointer, const struct pcap_pkthdr *
,			const char *, gpointer);
gboolean gotnetpkt(Listener*, FrameSet* fs, NetAddr* srcaddr);
void real_deadtime_agent(HbListener* who);
void initial_deadtime_agent(HbListener* who);
void got_heartbeat(HbListener* who);
void got_heartbeat2(HbListener* who);

void obey_sendexpecthb(AuthListener*, FrameSet* fs, NetAddr*);
void obey_sendhb(AuthListener*, FrameSet* fs, NetAddr*);
void obey_expecthb(AuthListener*, FrameSet* fs, NetAddr*);

ObeyFrameSetTypeMap obeylist [] = {
	{FRAMESETTYPE_SENDHB,		obey_sendhb},
	{FRAMESETTYPE_EXPECTHB,		obey_expecthb},
	{FRAMESETTYPE_SENDEXPECTHB,	obey_sendexpecthb},
	{0,				NULL},
};
	

FrameSet* create_sendexpecthb(ConfigContext*, NetAddr* addrs, int addrcount);

/// Test routine for sending an encapsulated Pcap packet.
void
send_encapsulated_packet(gconstpointer packet,		///<[in] pcap packet data
		   gconstpointer pktend,		///<[in] one byte past end of pkt
           	   const struct pcap_pkthdr *hdr,	///<[in] pcap header
		   const char * dev)			///<[in] capture device
{
	FrameSet *	fs = construct_pcap_frameset(FRAMESETTYPE_SWDISCOVER, packet, pktend, hdr, dev);
	//g_message("Sending a frameset containing an encapsulated capture packet.");
	nettransport->sendaframeset(nettransport, destaddr, fs);
	fs->unref(fs); fs = NULL;
}

/// Routine called when a packet is received from the g_main_loop() mechanisms.
gboolean
gotapcappacket(GSource_pcap_t* srcobj,		///<[in]GSource object causing this call
	   pcap_t *capfd,			///<[in]pcap capture object
           gconstpointer pkt,			///<[in]captured packet
           gconstpointer pend,			///<[in]end of captured packet
           const struct pcap_pkthdr *hdr,	///<[in]pcap header
           const char *dev,			///<[in]name of capture device
	   gpointer vdecoder)			///<[in]PacketDecoder object
{
	FrameSet *	fs;
	SignFrame*	signature;
	PacketDecoder*	decoder = CASTTOCLASS(PacketDecoder, vdecoder);
	(void)srcobj; (void)capfd;
	
	++pcapcount;
	if (is_valid_lldp_packet(pkt, pend)) {
		g_message("Found a %d/%d byte LLDP packet!", hdr->caplen, hdr->len);
		//dump_lldp_packet(pkt, pend);
	}else if (is_valid_cdp_packet(pkt, pend)) {
		g_message("Found a %d/%d byte CDP packet!", hdr->caplen, hdr->len);
		//dump_cdp_packet(pkt, pend);
	}else{
		g_warning("Found a %d/%d byte INVALID packet!", hdr->caplen, hdr->len);
		++errcount;
	}
	signature = signframe_new(G_CHECKSUM_SHA256, 0);
	//g_message("Constructing a frameset for this %d byte captured packet.", hdr->caplen);
	fs = construct_pcap_frameset(0xfeed, pkt, pend, hdr, dev);
	//g_message("Constructing a capture packet packet from the constructed frameset.");
	frameset_construct_packet(fs, signature, NULL, NULL);
	signature->baseclass.baseclass.unref(signature); signature = NULL;
	if (!fs->packet) {
		g_critical("fs is NULL!");
		++errcount;
	}else{
		GSList*		fslist;
		int	size = (guint8*)fs->pktend - (guint8*) fs->packet;
		g_message("Constructed packet is %d bytes", size);
		fslist = decoder->pktdata_to_framesetlist(decoder, fs->packet, fs->pktend);
		if (fslist == NULL) {
			g_warning("fslist is NULL!");
			++errcount;
		}else{
			FrameSet*	copyfs = CASTTOCLASS(FrameSet, fslist->data);
			SignFrame*	newsig = signframe_new(G_CHECKSUM_SHA256, 0);
			frameset_construct_packet(copyfs, newsig, NULL, NULL);
			newsig->baseclass.baseclass.unref(newsig);
			newsig = NULL;
			if (!copyfs->packet) {
				g_warning("copyfs->packet is NULL!");
				++errcount;
			}else{
				int	cpsize = (guint8*)copyfs->pktend - (guint8*) copyfs->packet;
				//g_message("Second Constructed packet is %d bytes", cpsize);
				//frameset_dump(fs);
				//frameset_dump(copyfs);
				if (size == cpsize) {
					if (memcmp(fs->packet, copyfs->packet, size) == 0) {
						g_message("Packets are identical!");
					}else{
						g_warning("Packets are different :-(");
						++errcount;
					}
				}else{
					g_warning("Packets are different sizes:-(");
					++errcount;
				}
			}
			//g_message("FrameSet for copy packet - freed!");
			copyfs->unref(copyfs);
			copyfs = NULL;
			g_slist_free(fslist);
		}
	}
	fs->unref(fs);
	fs = NULL;
	//g_message("FrameSet for constructed packet - freed!");
	send_encapsulated_packet(pkt, pend, hdr, dev);
	++pktcount;
	return TRUE;
}

/// Test routine called when a NetIO packet is received.
gboolean
gotnetpkt(Listener* l,		///<[in/out] Input GSource
	  FrameSet* fs,		///<[in/out] @ref FrameSet "FrameSet"s received
	  NetAddr* srcaddr	///<[in] Source address of this packet
	  )
{
	(void)l; (void)srcaddr;
	++wirepktcount;
	g_message("Received a packet over the 'wire'!");
	//g_message("DUMPING packet received over 'wire':");
	//frameset_dump(fs);
	//g_message("END of packet received over 'wire':");
	fs->unref(fs);
	if (wirepktcount >= maxpkts) {
		g_message("QUITTING NOW!");
		g_main_loop_quit(loop);
		return FALSE;
	}
	return TRUE;
}

void
real_deadtime_agent(HbListener* who)
{
	char *	addrstring;
	static int deadcount = 0;
	addrstring = who->listenaddr->baseclass.toString(who->listenaddr);
	++deadcount;
	if (deadcount > expected_dead_count) {
		g_warning("Subsequent (unexpected) deadtime event occurred for address %s."
		,	addrstring);
		++errcount;
	}else{
		g_message("Subsequent (expected) deadtime event occurred for address %s."
		,	addrstring);
	}
	g_free(addrstring);
}
void
got_heartbeat(HbListener* who)
{
	(void)who;
	++heartbeatcount;
	//g_debug("Got heartbeat()");
}

void
got_heartbeat2(HbListener* who)
{
	(void)who;
	++heartbeatcount;
	//g_debug("Got heartbeat2()");
}

void
initial_deadtime_agent(HbListener* who)
{
	FrameSet * pkt;
	JsonDiscovery*	discover_netconfig;
	(void)who;
	g_message("Expected deadtime event occurred (once)");
	// Send ourselves a message so that we send heartbeats to ourselves
	// and also expect to hear them from ourselves.
	// This will set up the proper callbacks for "normal" operation
	pkt = create_sendexpecthb(who->baseclass.config, destaddr, 1);
	netpkt->sendaframeset(netpkt, destaddr, pkt);
	pkt->unref(pkt); pkt = NULL;
	pkt = create_sendexpecthb(who->baseclass.config, otheraddr, 1);
	netpkt->sendaframeset(netpkt, destaddr, pkt);
	pkt->unref(pkt); pkt = NULL;
	pkt = create_sendexpecthb(who->baseclass.config, otheraddr2, 1);
	netpkt->sendaframeset(netpkt, destaddr, pkt);
	pkt->unref(pkt); pkt = NULL;

	discover_netconfig = jsondiscovery_new(
		"/home/alanr/monitor/src/discovery_agents/netconfig"
		,			       2, netpkt, who->baseclass.config, 0);
	discover_netconfig->baseclass.discover(CASTTOCLASS(Discovery, discover_netconfig));
	discover_netconfig->baseclass.baseclass.unref(discover_netconfig);
}

/**
 * Create a @ref FrameSet to send and expect heartbeats from the same sets of addresses.
 * Keep in mind the entire packet needs to fit in a UDP packet (< 64K).
 * The port, hbtime, deadtime, and warntime parameters apply to all given addresses.
 */
FrameSet*
create_sendexpecthb(ConfigContext* config	///<[in] Provides deadtime, port, etc.
		,   NetAddr* addrs		///<[in/out] Addresses to include
		,   int addrcount)		///<[in] Count of 'addrs' provided
{
	FrameSet* ret = frameset_new(FRAMESETTYPE_SENDEXPECTHB);
	int	count = 0;

	// Put the port in the message (if asked)
	if (config->getint(config, CONFIGNAME_HBPORT) > 0) {
		gint	port = config->getint(config, CONFIGNAME_HBPORT);
		IntFrame * intf = intframe_new(FRAMETYPE_PORTNUM, 2);
		intf->setint(intf, port);
		frameset_append_frame(ret, CASTTOCLASS(Frame, intf));
		intf->baseclass.baseclass.unref(intf); intf = NULL;
	}
	// Put the heartbeat interval in the message (if asked)
	if (config->getint(config, CONFIGNAME_HBTIME) > 0) {
		gint	hbtime = config->getint(config, CONFIGNAME_HBTIME);
		IntFrame * intf = intframe_new(FRAMETYPE_HBINTERVAL, 4);
		intf->setint(intf, hbtime);
		frameset_append_frame(ret, CASTTOCLASS(Frame, intf));
		intf->baseclass.baseclass.unref(intf); intf = NULL;
	}
	// Put the heartbeat deadtime in the message (if asked)
	if (config->getint(config, CONFIGNAME_DEADTIME) > 0) {
		gint deadtime = config->getint(config, CONFIGNAME_DEADTIME);
		IntFrame * intf = intframe_new(FRAMETYPE_HBDEADTIME, 4);
		intf->setint(intf, deadtime);
		frameset_append_frame(ret, CASTTOCLASS(Frame, intf));
		intf->baseclass.baseclass.unref(intf); intf = NULL;
	}
	// Put the heartbeat warntime in the message (if asked)
	if (config->getint(config, CONFIGNAME_WARNTIME) > 0) {
		gint warntime = config->getint(config, CONFIGNAME_WARNTIME);
		IntFrame * intf = intframe_new(FRAMETYPE_HBWARNTIME, 4);
		intf->setint(intf, warntime);
		frameset_append_frame(ret, CASTTOCLASS(Frame, intf));
		intf->baseclass.baseclass.unref(intf); intf = NULL;
	}

	// Put all the addresses we were given in the message.
	for (count=0; count < addrcount; ++count) {
		AddrFrame* hbaddr = addrframe_new(FRAMETYPE_IPADDR, 0);
		hbaddr->setnetaddr(hbaddr, &addrs[count]);
		frameset_append_frame(ret, CASTTOCLASS(Frame, hbaddr));
		hbaddr->baseclass.baseclass.unref(hbaddr); hbaddr = NULL;
	}
	return  ret;
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
obey_sendhb(AuthListener* parent	///<[in] @ref AuthListener object invoking us
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
				hb = hbsender_new(aframe->getnetaddr(aframe), parent->transport
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
obey_expecthb(AuthListener* parent	///<[in] @ref AuthListener object invoking us
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
				hblisten->set_deadtime_callback(hblisten, real_deadtime_agent);
				hblisten->set_heartbeat_callback(hblisten, got_heartbeat2);
				// Intercept incoming heartbeat packets
				netpkt->addListener(netpkt, FRAMESETTYPE_HEARTBEAT
				,		    CASTTOCLASS(Listener, hblisten));
				// Unref this heartbeat listener, and forget our reference.
				hblisten->baseclass.baseclass.unref(hblisten); hblisten = NULL;
				// That still leaves two references to 'hblisten':
				//   - in the netpkt dispatch table
				//   - in the global heartbeat listener table
				// And one reference to the previous 'hblisten' object:
				//   - in the global heartbeat listener table
				// Also note that we become the 'proxy' for all incoming heartbeats
				// but we dispatch them to the right HbListener object.
				// Since we've become the proxy for all incoming heartbeats, if
				// we displace and free the old proxy, this all still works nicely,
				// because the netpkt object gets rid of its old reference to the
				// old 'proxy' object.
				/// @todo These comments are too valuable to reside only in a piece of
				/// test code.
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
obey_sendexpecthb(AuthListener* parent	///<[in] @ref AuthListener object invoking us
	,   FrameSet*	fs		///<[in] @ref FrameSet indicating who to send HBs to
	,   NetAddr*	fromaddr)	///<[in/out] Address this message came from
{
	g_return_if_fail(fs != NULL && fs->fstype == FRAMESETTYPE_SENDEXPECTHB);

	obey_sendhb  (parent, fs, fromaddr);
	obey_expecthb(parent, fs, fromaddr);
}


FrameTypeToFrame	decodeframes[] = FRAMETYPEMAP;

/// Test program looping and reading LLDP/CDP packets.
int
main(int argc, char **argv)
{
	char *		dev;					// Device to listen on
	GSource*	pcapsource;				// GSource for packets
	unsigned	protocols = ENABLE_LLDP|ENABLE_CDP;	// Protocols to watch for...
	char		errbuf[PCAP_ERRBUF_SIZE];		// Error buffer...
	const guint8	loopback[] = CONST_IPV6_LOOPBACK;
	const guint8	otheradstring[] = {10,10,10,5};
	const guint8	otheradstring2[] = {10,10,10,4};
	const guint8	anyadstring[] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
	guint16		testport = TESTPORT;
	SignFrame*	signature = signframe_new(G_CHECKSUM_SHA256, 0);
	HbListener*	hblisten;
	Listener*	otherlistener;
	ConfigContext*	config = configcontext_new(0);
	PacketDecoder*	decoder = packetdecoder_new(0, decodeframes, DIMOF(decodeframes));
	AuthListener*	obeycollective;


	g_log_set_fatal_mask (NULL, G_LOG_LEVEL_ERROR|G_LOG_LEVEL_CRITICAL);
	if (argc > 1) {
		maxpkts = atol(argv[1]);
                g_debug("Max LLDP/CDP packet count is %lld", maxpkts);
	}

	if (netio_is_dual_ipv4v6_stack()) {
		g_message("Our OS supports dual ipv4/v6 sockets. Hurray!");
	}else{
		g_warning("Our OS DOES NOT support dual ipv4/v6 sockets - this may not work!!");
	}
	
	dev = pcap_lookupdev(errbuf);	// Find name of default network device...
	if (dev == NULL) {
		g_critical("Couldn't find default device: %s", errbuf);
		++errcount;
		return(2);
	}
	g_message("PCAP capture device is: %s", dev);


	// Create a pcap packet Gsource for the g_main_loop environment,
	// and connect it up to run in the default context

	pcapsource = g_source_pcap_new(dev, protocols, gotapcappacket, NULL,
                                      G_PRIORITY_DEFAULT, FALSE, NULL, 0, decoder);
	g_return_val_if_fail(NULL != pcapsource, 1);

	config->setframe(config, CONFIGNAME_OUTSIG, CASTTOCLASS(Frame, signature));
	config->setint(config, CONFIGNAME_HBPORT, testport);
	config->setint(config, CONFIGNAME_HBTIME, 1000000);
	config->setint(config, CONFIGNAME_DEADTIME, 3*1000000);

	// Create a network transport object (UDP packets)
	nettransport = CASTTOCLASS(NetIO, netioudp_new(0, config, decoder));
	g_return_val_if_fail(NULL != nettransport, 2);

	// Construct the NetAddr we'll talk to (i.e., ourselves) and listen from
	destaddr =  netaddr_ipv6_new(loopback, testport);
	g_return_val_if_fail(NULL != destaddr, 3);

	// Construct another couple of NetAddrs to talk to and listen from
	otheraddr =  netaddr_ipv4_new(otheradstring, testport);
	g_return_val_if_fail(NULL != otheraddr, 4);
	otheraddr2 =  netaddr_ipv4_new(otheradstring2, testport);
	g_return_val_if_fail(NULL != otheraddr2, 4);

	// Construct another NetAddr to bind to (anything)
	anyaddr =  netaddr_ipv6_new(anyadstring, testport);
	g_return_val_if_fail(NULL != destaddr, 5);

	// Listen for our own packets...
	g_return_val_if_fail(nettransport->bindaddr(nettransport, anyaddr),16);
	//g_return_val_if_fail(nettransport->bindaddr(nettransport, destaddr),16);

	// Connect up our network transport into the g_main_loop paradigm
	// so we get dispatched when packets arrive
	netpkt = netgsource_new(nettransport, NULL, G_PRIORITY_HIGH, FALSE, NULL, 0, NULL);
	otherlistener = listener_new(config, 0);
	otherlistener->got_frameset = gotnetpkt;
	netpkt->addListener(netpkt, 0, otherlistener);	// Get all unclaimed packets...
	// Unref the "other" listener
	otherlistener->baseclass.unref(otherlistener); otherlistener = NULL;

	// Create a heartbeat listener
	hblisten = hblistener_new(destaddr, config, 0);
	hblisten->set_deadtime(hblisten, 10*1000000);
	hblisten->set_heartbeat_callback(hblisten, got_heartbeat);
	hblisten->set_deadtime_callback(hblisten, initial_deadtime_agent);

	// Intercept incoming heartbeat packets - direct them to heartbeat listener
	netpkt->addListener(netpkt, FRAMESETTYPE_HEARTBEAT, CASTTOCLASS(Listener, hblisten));
	// Unref the heartbeat listener - the listener table holds a reference to it
	hblisten->baseclass.baseclass.unref(CASTTOCLASS(Listener, hblisten)); hblisten = NULL;
	// Listen for packets from the Collective Management Authority
	obeycollective = authlistener_new(obeylist, config, 0);
	obeycollective->associate(obeycollective, netpkt);

	loop = g_main_loop_new(g_main_context_default(), TRUE);

	// Start up the main loop - run the program...
	g_main_loop_run(loop);

	nettransport->finalize(nettransport); nettransport = NULL;
	if (sender) {
		sender->unref(sender); sender = NULL;
	}
	g_source_pcap_finalize((GSource*)pcapsource);

	// g_main_loop_unref() calls g_source_unref() - so we should not call it directly.
	g_main_context_unref(g_main_context_default());

	// Main loop is over - shut everything down, free everything...
	g_main_loop_unref(loop); loop=NULL; pcapsource=NULL;

	// Unlink heartbeat dispatcher - this should NOT be necessary...
	netpkt->addListener(netpkt, FRAMESETTYPE_HEARTBEAT, NULL);

	// Unlink misc dispatcher - this should NOT be necessary...
	netpkt->addListener(netpkt, 0, NULL);

	// Dissociate packet actions from the packet source.
	obeycollective->dissociate(obeycollective);

	// Stop all our discovery activities.
	discovery_unregister_all();

	// Unref the AuthListener object
	obeycollective->baseclass.baseclass.unref(obeycollective);
	obeycollective = NULL;

	// Free signature frame
	signature->baseclass.baseclass.unref(signature); signature = NULL;

	// Free misc addresses
        destaddr-> baseclass.unref(destaddr);
        otheraddr->baseclass.unref(otheraddr);
        otheraddr2->baseclass.unref(otheraddr2);
        anyaddr->  baseclass.unref(anyaddr);

	// Free packet decoder
	decoder->baseclass.unref(decoder);

	// Free config object
	config->baseclass.unref(config);

	// At this point - nothing should show up - we should have freed everything
	proj_class_dump_live_objects();
	if (proj_class_live_object_count() > 2) {
		g_warning("Too many objects (%d) alive at end of test.", 
			proj_class_live_object_count());
		++errcount;
	}
	g_message("Count of pcap packets received:\t%d", pcapcount);
	g_message("Count of pkts received over wire:\t%d", wirepktcount);
	g_message("Count of heartbeats received:\t%d", heartbeatcount);
	g_message("Count of errors:\t\t\t%d", errcount);
        proj_class_finalize_sys(); /// Shut down object system to make valgrind happy :-D
	return(errcount <= 127 ? errcount : 127);
}
