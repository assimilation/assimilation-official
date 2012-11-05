/**
 * @file
 * @brief functions for handling standard client incoming packet dispatch.
 * @details It passes off incoming packets to the appropriate functions.
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
#include <switchdiscovery.h>
#include <lldp.h>
#include <cdp.h>
#include <memory.h>
FSTATIC gboolean _switchdiscovery_discover(Discovery* self);
FSTATIC void _switchdiscovery_finalize(AssimObj* self);
FSTATIC gboolean _switchdiscovery_cache_info(SwitchDiscovery* self, gconstpointer pkt, gconstpointer pend);
FSTATIC gboolean _switchdiscovery_dispatch(GSource_pcap_t* gsource, pcap_t*, gconstpointer, gconstpointer,
                          const struct pcap_pkthdr*, const char *, gpointer selfptr);
///@defgroup SwitchDiscoveryClass SwitchDiscovery class
/// Class providing a switch discovery class for discovering network switch properties - subclass of @ref DiscoveryClass.
/// We deal with things like CDP, LDP and so on in order to "hear" our switch/port configuration.
/// @{
/// @ingroup DiscoveryClass

/// finalize a SwitchDiscovery object
FSTATIC void
_switchdiscovery_finalize(AssimObj* dself)
{
	SwitchDiscovery * self = CASTTOCLASS(SwitchDiscovery, dself);
	if (self->source) {
		g_source_unref(self->source);
		self->source = NULL;
	}
	if (self->switchid) {
		g_free(self->switchid);
		self->switchid = NULL;
	}
	if (self->portid) {
		g_free(self->portid);
		self->portid = NULL;
	}
	
	// Call base object finalization routine (which we saved away)
	self->finalize(&self->baseclass.baseclass);
}

/// Discover member function for timed discovery -- not applicable -- return FALSE
FSTATIC gboolean
_switchdiscovery_discover(Discovery* self)  ///<[in/out] 
{
	(void)self;
	return FALSE;
}


/// Internal pcap gsource dispatch routine - called when we get a packet.
/// It examines the packet and sees if it is the same switch id and port ID as previously.
/// If there is no previous packet, or something has changed, it constructs a packet
/// encapsulating the captured packet, then sends this encapsulated packet "upstream"
/// to the CMA.
/// All we care about about are those two fields - the rest we leave to the CMA.
FSTATIC gboolean
_switchdiscovery_dispatch(GSource_pcap_t* gsource, ///<[in] Gsource object causing dispatch
                          pcap_t* capstruct,	   ///<[in] Pointer to structure capturing for us
                          gconstpointer pkt,	   ///<[in] Pointer to the packet just read in
                          gconstpointer pend,	   ///<[in] Pointer to first byte past 'pkt'
                          const struct pcap_pkthdr* pkthdr, ///<[in] libpcap packet header
                          const char * capturedev,  ///<[in] Device being captured
			  gpointer selfptr	   ///<[in/out] pointer to our Discover object
			  )
{
	SwitchDiscovery*	self = CASTTOCLASS(SwitchDiscovery, selfptr);
	Discovery*		dself = &(self->baseclass);
	NetGSource*		transport = dself->_iosource;
	NetAddr*		dest = dself->_config->getaddr(dself->_config, CONFIGNAME_CMADISCOVER);
	FrameSet*		fs;
	
	(void)gsource; (void)capstruct;
	//g_debug("Got an incoming LLDP/CDP packet");
	/// Don't cache if we can't send - and don't send if we have sent this info previously.
	++ self->baseclass.discovercount;
	if (!dest || !_switchdiscovery_cache_info(self, pkt, pend)) {
		return TRUE;
	}
	++ self->baseclass.reportcount;
	//g_debug("Sending out LLDP/CDP packet - hurray!");
	fs = construct_pcap_frameset(FRAMESETTYPE_SWDISCOVER, pkt, pend, pkthdr, capturedev);
	transport->sendaframeset(transport, dest, fs);
	fs->baseclass.unref(&fs->baseclass);
	return TRUE;
}

/// SwitchDiscovery constructor.
/// Good for discovering switch information via pcap-enabled discovery protocols (like LLDP and CDP)
SwitchDiscovery*
switchdiscovery_new(const char *	instance///<[in] instance name
,		    const char *	dev	///<[in] device to listen on
,		    guint listenmask		///<[in] what protocols to listen to
,		    gint priority		///<[in] source priority
,		    GMainContext* 	mcontext///<[in/out] mainloop context
,	            NetGSource*		iosrc	///<[in/out] I/O object
,	            ConfigContext*	config	///<[in/out] configuration context
,	            gsize objsize)		///<[in] object size
{
	Discovery * dret = discovery_new(instance, iosrc, config
	,		                 objsize < sizeof(SwitchDiscovery) ? sizeof(SwitchDiscovery) : objsize);
	SwitchDiscovery* ret;
	g_return_val_if_fail(dret != NULL, NULL);
	proj_class_register_subclassed(dret, "SwitchDiscovery");

	ret = CASTTOCLASS(SwitchDiscovery, dret);

	ret->finalize = dret->baseclass._finalize;
	dret->baseclass._finalize = _switchdiscovery_finalize;
	dret->discover = _switchdiscovery_discover;
	ret->source = g_source_pcap_new(dev, listenmask, _switchdiscovery_dispatch, NULL, priority, FALSE, mcontext, 0, ret);

	if (objsize == sizeof(SwitchDiscovery)) {
		// Subclass constructors need to register themselves, but we'll register
		// ourselves.
		discovery_register(dret);
	}
	ret->switchid = NULL;	ret->switchidlen = -1;
	ret->portid = NULL;	ret->portidlen = -1;
	return ret;
}

typedef struct _SwitchDiscoveryType SwitchDiscoveryType;
static struct _SwitchDiscoveryType {
	const char *	discoverytype;
	gboolean (*isthistype)(gconstpointer tlv_vp, gconstpointer pktend);
	gconstpointer (*get_switch_id)(gconstpointer tlv_vp, gssize* idlength, gconstpointer pktend);
	gconstpointer (*get_port_id)(gconstpointer tlv_vp, gssize* idlength, gconstpointer pktend);
} discovery_types[] = {
	{"lldp", is_valid_lldp_packet, get_lldp_chassis_id, get_lldp_port_id},
	{"cdp", is_valid_cdp_packet, get_cdp_chassis_id, get_cdp_port_id}
};

///
///@return TRUE if this data is new or has changed from our previously cached version.
FSTATIC gboolean
_switchdiscovery_cache_info(SwitchDiscovery* self,  ///<[in/out] Our SwitchDiscovery object
			   gconstpointer pkt,	   ///<[in] Pointer to the packet just read in
                           gconstpointer pktend)   ///<[in] Pointer to first byte past 'pkt'
{
	gsize	j;
	///@todo deal with switches that send both LLDP and CDP packets

	for (j=0; j < DIMOF(discovery_types); ++j) {
		gconstpointer	curswitchid;
		gssize		curswitchidlen = -1;
		gconstpointer	curportid;
		gssize		curportidlen = -1;

		if (!discovery_types[j].isthistype(pkt, pktend)) {
			continue;
		}
		//g_debug("Got packet of type %s", discovery_types[j].discoverytype);
		curswitchid = discovery_types[j].get_switch_id(pkt, &curswitchidlen, pktend);
		curportid = discovery_types[j].get_port_id(pkt, &curportidlen, pktend);
		g_return_val_if_fail(curswitchid != NULL, FALSE);
		g_return_val_if_fail(curportid != NULL, FALSE);

		if (self->switchid == NULL || self->portid == NULL
                    || curportidlen != self->portidlen || curswitchidlen != self->switchidlen
		    || memcmp(curswitchid, self->switchid, curswitchidlen) != 0
		    || memcmp(curportid, self->portid, curportidlen) != 0) {

			if (self->switchid != NULL) {
				FREE(self->switchid); self->switchid = NULL;
			}
			if (self->portid != NULL) {
				FREE(self->portid); self->portid = NULL;
			}
			self->switchid = g_memdup(curswitchid, curswitchidlen);
			self->portid = g_memdup(curportid, curportidlen);
			self->switchidlen = curswitchidlen;
			self->portidlen = curportidlen;
			return TRUE;
		}
		break;
	}
	return FALSE;
}
///@}
