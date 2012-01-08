/**
 * @file
 * @brief C-class defining the SwitchDiscovery classj
 * @details it is for discovering switch configuration information via LLDP or CDP.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#ifdef _MSC_VER
#define _W64
#endif

#include <projectcommon.h>
#include <switchdiscovery.h>
#include <lldp.h>
#include <cdp.h>
#include <memory.h>
FSTATIC gboolean _switchdiscovery_discover(Discovery* self);
FSTATIC void _switchdiscovery_finalize(Discovery* self);
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
_switchdiscovery_finalize(Discovery* dself)
{
	SwitchDiscovery * self = CASTTOCLASS(SwitchDiscovery, dself);
	if (self->source) {
		g_source_destroy(CASTTOCLASS(GSource, self->source));
		self->source = NULL;
	}
	// Call base object finalization routine (which we saved away)
	self->finalize(dself);
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
/// encapsulating the captured packet, then sends this encapsulation packet "upstream"
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
	
	FrameSet* fs;
	(void)gsource; (void)capstruct;
	if (!_switchdiscovery_cache_info(self, pkt, pend)) {
		return TRUE;
	}
	/// @todo - do what the description of this function actually says!
	/// That is, send out the filtered packets.
	fs =  construct_pcap_frameset(FRAMESETTYPE_SWDISCOVER, pkt, pend, pkthdr, capturedev);
	(void)fs;
	return TRUE;
}


/// SwitchDiscovery constructor.
/// Good for discovering switch information via pcap-enabled discovery protocols (like LLDP and CDP)
SwitchDiscovery*
switchdiscovery_new(gsize objsize, const char * dev, guint listenmask, gint priority, GMainContext* context)
{
	Discovery * dret = discovery_new(objsize < sizeof(SwitchDiscovery) ? sizeof(SwitchDiscovery) : objsize);
	SwitchDiscovery* ret;
	g_return_val_if_fail(dret != NULL, NULL);
	proj_class_register_subclassed(dret, "SwitchDiscovery");

	ret = CASTTOCLASS(SwitchDiscovery, dret);

	ret->finalize = dret->finalize;
	dret->finalize = _switchdiscovery_finalize;
	dret->discover = _switchdiscovery_discover;
	ret->source = g_source_pcap_new(dev, listenmask, _switchdiscovery_dispatch, NULL, priority, FALSE, context, 0, ret);

	if (objsize == sizeof(SwitchDiscovery)) {
		// We assume we're not a constructor for a subclass...
		// Not a perfect assumption, but workable...
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

		if (!discovery_types[j].isthistype) {
			continue;
		}
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
			return TRUE;
		}
	}
	return FALSE;
}
///@}
