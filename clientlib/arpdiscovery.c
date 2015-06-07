/**
 * @file
 * @brief functions for handling standard client incoming ARP packet dispatch.
 * @details It passes off incoming ARP packet info to the appropriate functions.
 *
 * This file is part of the Assimilation Project.
 *
 * @author Carrie Oswald (carrie_oswald@yahoo.com)
 * Copyright (c) 2014 - Assimilation Systems Limited
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

#include <stdio.h>
#include <projectcommon.h>
#include <memory.h>
#include <arpdiscovery.h>
#include <configcontext.h>
#include <netaddr.h>
#include <misc.h>
#include <tlvhelper.h>
#include <nanoprobe.h>
/**
 * @defgroup arp_format Layout of ARP Packets
 * @ingroup WireDataFormats
 * ARP is the Address Resolution Protocol - which we receive and then map IP to MAC addresses.
 * ARP packets consist of a 8-byte initial header, followed by sender and target Hardware and IP 
 * Addresses.  An ARP packet should never exceed ??? bytes.
 * The ARP Packet (after ethernet and SNAP headers) is laid out as shown below:
 * <PRE>
 * +----------------------------------+----------------------------------+
 * |        Hardware Type (HRD)       |        Protocol Type (PRO)       |
 * |              2 bytes             |              2 bytes             |    
 * |-----------------+----------------+----------------------------------|
 * |  Hardware       |  Protocol      |                                  |
 * |  Address        |  Address       |            Opcode (OP)           |
 * |  Length (HLN)   |  Length (PLN)  |              2 bytes             |
 * |     1 byte      |     1 byte     |                                  |
 * |-----------------+----------------+----------------------------------|
 * |                     Sender Hardware Address (SHA)                   |
 * |                              HLN bytes                              |
 * |                                  +----------------------------------|
 * |                                  |   Sender Protocol Address (SPA)  |
 * |                                  |        4 bytes (bytes 1-2)       |
 * |----------------------------------+----------------------------------|
 * |      Sender Protocol Address     |                                  |
 * |            (bytes 3-4)           |                                  |
 * |----------------------------------+                                  |
 * |                                      Target Hardware Address (THA)  |
 * |                                                HLN bytes            |
 * |---------------------------------------------------------------------|
 * |                    Target Protocol Address (TPA)                    |
 * |                              4 bytes                                |
 * +---------------------------------------------------------------------+
 * </PRE>
 */
/** @defgroup  arp_packet_offsets ARP: Offsets of initial items in an ARP packet.
 *  The initial items are the hardware and protocol types, address lengths, and the operation code.
 *  These all come before the IP/MAC address portion of the ARP packet.
 *
 *  @{ 
 *  @ingroup arp_format
 */
#define		ARP_PKT_OFFSET 	14	///< Number of bytes before the ARP packet itself starts
#define		ARP_HRD_LEN 	2	///< Number of bytes for the Hardware Type field
#define		ARP_PRO_LEN 	2	///< Number of bytes for the Protocol Type field
#define		ARP_HLN_LEN 	1	///< Number of bytes for the Hardware Address Length field
#define		ARP_PLN_LEN 	1	///< Number of bytes for the Protocol Address Length field
#define		ARP_OP_LEN 	2	///< Number of bytes for the Opcode field
/// Number of bytes for the ARP Packet header info (before addresses start)
#define 	ARP_HDR_LEN 	(ARP_HRD_LEN + ARP_PRO_LEN + ARP_HLN_LEN + ARP_PLN_LEN + ARP_OP_LEN)
/// @}


FSTATIC gboolean _arpdiscovery_discover(Discovery* self);
FSTATIC void _arpdiscovery_finalize(AssimObj* self);
FSTATIC gboolean _arpdiscovery_dispatch(GSource_pcap_t* gsource, pcap_t*, gconstpointer, gconstpointer,
                          const struct pcap_pkthdr*, const char *, gpointer selfptr);
FSTATIC void _arpdiscovery_notify_function(gpointer data);
FSTATIC void _arpdiscovery_sendarpcache(ArpDiscovery* self);
FSTATIC gboolean _arpdiscovery_gsourcefunc(gpointer);
FSTATIC gboolean _arpdiscovery_first_discovery(gpointer);

DEBUGDECLARATIONS

///@defgroup ArpDiscoveryClass ArpDiscovery class
/// Class providing an ARP Discovery class for discovering IP/MAC address resolution - subclass of @ref DiscoveryClass.
/// We deal with the ARP protocol in order to "hear" our IP/MAC address configuration.
/// @{
/// @ingroup DiscoveryClass

/// finalize a ArpDiscovery object
FSTATIC void
_arpdiscovery_finalize(AssimObj* dself)
{
	ArpDiscovery * self = CASTTOCLASS(ArpDiscovery, dself);
	g_info("%-35s %8"G_GINT64_MODIFIER"d", "Count of ARP pkts received:"
	,	self->baseclass.discovercount);
	if (self->source) {
		g_source_unref(self->source);
		g_source_destroy(self->source);
		self->source = NULL;
	}
        if (self->timeout_source != 0) {
                g_source_remove(self->timeout_source);
		self->timeout_source = 0;
        }
	if (self->arpconfig) {
		UNREF(self->arpconfig);
	}

	UNREF(self->ArpMap);
	self->ArpMapData = NULL;	// Child object of ArpMap
	
	// Call base object finalization routine (which we saved away)
	self->finalize(&self->baseclass.baseclass);
}

/// Discover member function for timed discovery -- not applicable -- return FALSE
FSTATIC gboolean
_arpdiscovery_discover(Discovery* self)  ///<[in/out] 
{
	(void)self;
	return FALSE;
}


/// A GSourceFunc to be called for the first (random) discovery *only*
FSTATIC gboolean
_arpdiscovery_first_discovery(gpointer gself) ///<[in/out] Pointer to 'self'
{
        ArpDiscovery*	self = CASTTOCLASS(ArpDiscovery, gself);
	int		interval = self->arpconfig->getint(self->arpconfig, CONFIGNAME_INTERVAL);
	if (self->timeout_source > 0) {
		g_source_remove(self->timeout_source);
		self->timeout_source = 0;
	}
	self->timeout_source
	=	g_timeout_add_seconds_full
        	(G_PRIORITY_HIGH, interval, _arpdiscovery_gsourcefunc
        	,	self, _arpdiscovery_notify_function);
	DEBUGMSG3("Sender %p subsequent timeout source is: %d, interval is %d", self
   	,         self->timeout_source, interval);
        _arpdiscovery_sendarpcache(self);
        return FALSE;
}


/// Function which periodically sends our ARP cache upstream
FSTATIC gboolean
_arpdiscovery_gsourcefunc(gpointer gself) ///<[in/out] Pointer to 'self'
{
        ArpDiscovery* self = CASTTOCLASS(ArpDiscovery, gself);
        _arpdiscovery_sendarpcache(self);
        return TRUE;
}


/// Callback function from the GSource world - notifying us when we're getting shut down
/// from their end
FSTATIC void
_arpdiscovery_notify_function(gpointer data)
{
        ArpDiscovery* self = CASTTOCLASS(ArpDiscovery, data);
        self->timeout_source = 0;
}

/// Internal pcap gsource dispatch routine - called when we get an ARP packet.
/// It examines the ARP packet and sees if it is the same IP address and MAC address as previously discovered.
/// A hash table is built of IP/MAC addresses.  If the IP address is new, it adds it to the hash table.
/// If not new, then it checks to see if the corresponding MAC address has changed.  
/// If so, then it adds it to the hash table.
/// All we really care about are those two fields (Sender IP & MAC addresses)--the rest we leave to the CMA.
FSTATIC gboolean
_arpdiscovery_dispatch(GSource_pcap_t* gsource, ///<[in] Gsource object causing dispatch
                          pcap_t* capstruct,	   ///<[in] Pointer to structure capturing for us
                          gconstpointer pkt,	   ///<[in] Pointer to the packet just read in
                          gconstpointer pend,	   ///<[in] Pointer to first byte past 'pkt'
                          const struct pcap_pkthdr* pkthdr, ///<[in] libpcap packet header
                          const char * capturedev,  ///<[in] Device being captured
			  gpointer selfptr	   ///<[in/out] pointer to our Discover object
			  )
{
	ArpDiscovery*		self = CASTTOCLASS(ArpDiscovery, selfptr);
	Discovery*		dself = &(self->baseclass);
	NetAddr*		dest = dself->_config->getaddr(dself->_config, CONFIGNAME_CMADISCOVER);

        struct arppacket {
                guint16 arp_hrd_type;		///< Hardware type (network byte order)
                guint16 arp_protocol;		///< Protocol type (network byte order)
                guint8  arp_hln;		///< Hardware address length (should be 6 or 8)
                guint8  arp_pln;		///< Protocol address lenght (should be 4 for IPV4 addresses)
                guint16 arp_op;			///< opcode (net byte order - we care about 1 and 2)
        };
	struct arppacket	arppkt;
	const guint8*		pktstart = ((const guint8*)pkt) + ARP_PKT_OFFSET;
	const guint8*		arp_sha;	// sender hardware address
	const guint8*		arp_spa;	// sender protocol address
	NetAddr*		sha_netaddr;	// sender hardware address
	NetAddr*		spa_netaddr;	// sender protocol address
	NetAddr*		arp_spaIPv6;	// sender protocol address in IPv6 format
	const guint8*		arp_tha;	// target hardware address
	const guint8*		arp_tpa;	// target protocol address
	const guint8*		lastbyte;	// last byte of packet according to ARP
	NetAddr*		tha_netaddr;	// target hardware address
	NetAddr*		tpa_netaddr;	// target protocol address
	NetAddr*		theMAC;
	char *			v6string;
	static const guint8	zeroes[4] = {0, 0, 0, 0};

	(void)gsource; (void)capstruct; (void)pkthdr; (void)capturedev;
	DEBUGMSG3("** Got an incoming ARP packet! - dest is %p", dest);

	arppkt.arp_hrd_type =	tlv_get_guint16(pktstart, pend);
	arppkt.arp_protocol =	tlv_get_guint16(pktstart+ARP_HRD_LEN, pend);
	arppkt.arp_hln = 	tlv_get_guint8(pktstart+ARP_HRD_LEN+ARP_PRO_LEN, pend);
	arppkt.arp_pln =	tlv_get_guint8(pktstart+ARP_HRD_LEN+ARP_PRO_LEN+ARP_HLN_LEN, pend);
	arppkt.arp_op =		tlv_get_guint16(pktstart+ARP_HRD_LEN+ARP_PRO_LEN+ARP_HLN_LEN+ARP_PLN_LEN
	,			pend);

	/*
	fprintf(stderr, "ARP Hardware Type: %u\n", arppkt.arp_hrd_type);
	fprintf(stderr, "ARP Protocol Type: %u\n", arppkt.arp_protocol);
	fprintf(stderr, "ARP Hardware Address Length: %u\n", arppkt.arp_hln);
	fprintf(stderr, "ARP Protocol Address Length: %u\n", arppkt.arp_pln);
	fprintf(stderr, "ARP Protocol Opcode: %u\n", arppkt.arp_op);
	*/

	arp_sha = pktstart + ARP_HDR_LEN;
	arp_spa = arp_sha + arppkt.arp_hln;
	lastbyte = arp_sha + (2*arppkt.arp_pln) + (2*arppkt.arp_hln);
	g_return_val_if_fail(lastbyte <= (const guint8*)pend, TRUE);
	g_return_val_if_fail(arppkt.arp_hln == 6 || arppkt.arp_hln == 8, TRUE);
	g_return_val_if_fail(arppkt.arp_pln == 4, TRUE);
	if (memcmp(arp_spa, zeroes, arppkt.arp_pln) == 0) {
		// Some glitchy device gave us a funky IP address...
		return TRUE;
	}
	sha_netaddr = netaddr_macaddr_new(arp_sha, arppkt.arp_hln);
	spa_netaddr = netaddr_ipv4_new(arp_spa, 0);
	arp_spaIPv6 = spa_netaddr->toIPv6(spa_netaddr);		// convert sender protocol address to IPv6 format
	arp_tha = arp_spa + arppkt.arp_pln;
	arp_tpa = arp_tha + arppkt.arp_hln;
	tha_netaddr = netaddr_macaddr_new(arp_tha, arppkt.arp_hln);
	tpa_netaddr = netaddr_ipv4_new(arp_tpa, 0);

	/*
	fprintf(stderr, "ARP Sender Hardware Address: %s  %p\n", arp_sha->baseclass.toString(&arp_sha->baseclass), arp_sha);
	fprintf(stderr, "ARP Sender Protocol Address: %s  %p\n", arp_spa->baseclass.toString(&arp_spa->baseclass), arp_spa);
	fprintf(stderr, "ARP Sender Protocol Address as IPV6: %s  %p\n", arp_spaIPv6->baseclass.toString(&arp_spaIPv6->baseclass), arp_spaIPv6);
	fprintf(stderr, "ARP Target Hardware Address: %s  %p\n", arp_tha->baseclass.toString(&arp_tha->baseclass), arp_tha);
	fprintf(stderr, "ARP Target Protocol Address: %s  %p\n", arp_tpa->baseclass.toString(&arp_tpa->baseclass), arp_tpa);
	*/

	++ self->baseclass.discovercount;

	v6string = arp_spaIPv6->baseclass.toString(&arp_spaIPv6->baseclass);
	theMAC = self->ArpMapData->getaddr(self->ArpMapData, v6string);
	if (NULL == theMAC) {
		// The IP address is not already there, so add it to the ConfigContext hash table.
		DEBUGMSG3("IP Address NOT in ConfigContext table: %s", v6string);
		self->ArpMapData->setaddr(self->ArpMapData, v6string, sha_netaddr);
	} else {
		// If the IP address is already there, see if the MAC address is the same.  
		// If so, then we do not need to add it again.
		DEBUGMSG3("IP Address FOUND in ConfigContext table: %s", v6string);
		if ( ! theMAC->equal(theMAC, sha_netaddr) ) {
			DEBUGMSG3(" ... but MAC address is different: %s", v6string);
			self->ArpMapData->setaddr(self->ArpMapData, v6string, sha_netaddr);
		}
	}
	g_free(v6string);
	UNREF(sha_netaddr);
	UNREF(spa_netaddr);
	UNREF(tha_netaddr);
	UNREF(tpa_netaddr);
	UNREF(arp_spaIPv6);

	return TRUE;
}

/// ArpDiscovery constructor - good for listening to ARP packets via pcap
ArpDiscovery*
arpdiscovery_new(ConfigContext*	arpconfig	///<[in] ARP configuration info
,		 gint		priority	///<[in] source priority
,		 GMainContext* 	mcontext	///<[in/out] mainloop context
,	         NetGSource*	iosrc		///<[in/out] I/O object
,	         ConfigContext*	config		///<[in/out] Global configuration
,	         gsize		objsize)	///<[in] object size
{
	Discovery *	dret;
	ArpDiscovery*	ret;
	const char*	dev;
	const char*	instance;
	int		firstinterval;
	int		interval;
	char*		sysname;

	BINDDEBUG(ArpDiscovery);
	g_return_val_if_fail(arpconfig != NULL, NULL);
	dev = arpconfig->getstring(arpconfig, CONFIGNAME_DEVNAME);
	g_return_val_if_fail(dev != NULL, NULL);
	instance = arpconfig->getstring(arpconfig, CONFIGNAME_INSTANCE);
	g_return_val_if_fail(instance != NULL, NULL);
	if (objsize < sizeof(ArpDiscovery)) {
		objsize = sizeof(ArpDiscovery);
	}
	dret = discovery_new(instance, iosrc, config, objsize);
	g_return_val_if_fail(dret != NULL, NULL);
	interval = arpconfig->getint(arpconfig, CONFIGNAME_INTERVAL);
	if (interval <= 0) {
		interval = DEFAULT_ARP_SENDINTERVAL;
		arpconfig->setint(arpconfig, CONFIGNAME_INTERVAL, interval);
	}
	ret = NEWSUBCLASS(ArpDiscovery, dret);

	ret->arpconfig = arpconfig;
	REF(arpconfig);
	ret->finalize = dret->baseclass._finalize;
	dret->baseclass._finalize = _arpdiscovery_finalize;
	dret->discover = _arpdiscovery_discover;
	ret->source = g_source_pcap_new(dev, ENABLE_ARP, _arpdiscovery_dispatch, NULL, priority, FALSE, mcontext, 0, ret);

	ret->ArpMap = configcontext_new_JSON_string("{\"discovertype\": \"ARP\", \"description\": \"ARP map\", \"source\": \"arpcache\", \"data\":{}}");
	// Need to set host, and discoveryname
	sysname = proj_get_sysname();
	ret->ArpMap->setstring(ret->ArpMap, "host", sysname);
	g_free(sysname); sysname = NULL;
	ret->ArpMap->setstring(ret->ArpMap, CONFIGNAME_INSTANCE, instance);
	ret->ArpMap->setstring(ret->ArpMap, CONFIGNAME_DEVNAME, dev);

	ret->ArpMapData = ret->ArpMap->getconfig(ret->ArpMap, "data");

	// Set the timer for initially when to send to the CMA
	// We do start this randomly to keep multiple reporters from flooding the CMA
	// It's not a bad idea in general, but until we select who is reporting ARPs
	// it's a really wonderful idea.
	firstinterval = g_rand_int_range(nano_random, interval, 2*interval);
	ret->timeout_source
	=	g_timeout_add_seconds_full
        	(G_PRIORITY_HIGH, firstinterval, _arpdiscovery_first_discovery
        	,	ret, _arpdiscovery_notify_function);
	DEBUGMSG3("Sender %p initial timeout source is: %d, interval is %d", ret
   	,         ret->timeout_source, interval);

	if (objsize == sizeof(ArpDiscovery)) {
		// Subclass constructors need to register themselves, but we'll register ourselves.
		discovery_register(dret);
	}
	return ret;
}


/// Function for sending the ARP info in JSON to the CMA.
FSTATIC void
_arpdiscovery_sendarpcache(ArpDiscovery* self)
{
	gchar* jsonout = NULL;
	gsize jsonlen = 0;
	jsonout = self->ArpMap->baseclass.toString(&self->ArpMap->baseclass);
        jsonlen = strlen(jsonout);
        if (jsonlen == 0) {
               	g_warning("JSON arp discovery produced no output.");
		return;
        }
        DEBUGMSG3("Got %zd bytes of JSON TEXT: [%s]", jsonlen, jsonout);
        if (DEBUG) {
               	ConfigContext* jsobj = configcontext_new_JSON_string(jsonout);
               	if (jsobj == NULL) {
                       	g_warning("JSON arp discovery [%zd bytes] produced bad JSON.", jsonlen);
                       	FREE(jsonout); jsonout = NULL;
			return;
               	}else{
                       	// Good output!
                       	UNREF(jsobj);
               	}
        }
	DEBUGMSG3("Passing off ARP packet to sendjson() - hurray!");
	self->baseclass.sendjson(&self->baseclass, jsonout, jsonlen);
}

///@}
