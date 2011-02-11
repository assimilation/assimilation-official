/**
 * @file
 * @brief libpcap Packet capture Gsource interface description
 * This code creates a GSource object for capturing our LLDP or libpcap packets.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 *
 *
 */
#include <glib.h>
#include <pcap_min.h>
#include <frameset.h>
GSource* g_source_pcap_new(const char * dev,
		  	   unsigned listenmask,
        	  	   gboolean (*dispatch)
                           ( pcap_t* capstruct,		///<[in] Pointer to structure capturing for us
                             const u_char * pkt,	///<[in] Pointer to the packet just read in
                             const u_char * pend,	///<[in] Pointer to first byte past 'pkt'
                             const struct pcap_pkthdr* pkthdr, ///<[in] libpcap packet header
                             const char * capturedev,	///<[in] Device being captured
                             gpointer userdata		///<[in] User data given to us in g_source_pcap_new()
			    ),
			   gpointer userdata,
			   GDestroyNotify notify,
			   gint priority,
			   gboolean can_recurse,
			   GMainContext* context
			  );
FrameSet* construct_pcap_frameset(guint16 framesettype, gconstpointer pkt, gconstpointer pktend,
				  const struct pcap_pkthdr* pkthdr, const char * interface);

