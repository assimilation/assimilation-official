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
typedef struct _GSource_pcap	GSource_pcap_t;

/// g_main_loop GSource object for creating events from libpcap (pcap_t) objects
/// We manage this with our @ref ProjectClass system to help catch errors.
struct _GSource_pcap {
	GSource		gs;		///< Parent GSource Object
	GPollFD		gfd;		///< Poll/select object for gmainloop
	pcap_t*		capture;	///< Pcap capture object
	int		capturefd;	///< Underlying file descriptor
	const char*	capturedev;	///< Capture device name
	unsigned	listenmask;	///< Protocols selected from @ref pcap_protocols
	gint		gsourceid;	///< Source ID from g_source_attach()
        ///[in] user dispatch function - we call it when a packet is read
        gboolean (*dispatch)(GSource_pcap_t* gsource,	///<[in] object causing the dispatch
			     pcap_t* capstruct,		///<[in] Pointer to structure doing the capturing for us
                             const u_char * pkt,	///<[in] Pointer to the packet just read in
                             const u_char * pend,	///<[in] Pointer to first byte past 'pkt'
                             const struct pcap_pkthdr* pkthdr, ///<[in] libpcap packet header
                             const char * capturedev);	///<[in] Device being captured
					///<[in] called when new pcap data has arrived
	GDestroyNotify	destroynote;	///<[in] function to call when we're destroyed...
};

GSource* g_source_pcap_new(const char * dev,
		  	   unsigned listenmask,
        	  	   gboolean (*dispatch)
                            (GSource_pcap_t*	gsource, ///< Gsource object causing dispatch
                             pcap_t* capstruct,		///<[in] Pointer to structure capturing for us
                             const u_char * pkt,	///<[in] Pointer to the packet just read in
                             const u_char * pend,	///<[in] Pointer to first byte past 'pkt'
                             const struct pcap_pkthdr* pkthdr, ///<[in] libpcap packet header
                             const char * capturedev	///<[in] Device being captured
			    ),
			   GDestroyNotify notify,
			   gint priority,
			   gboolean can_recurse,
			   GMainContext* context,
			   gsize objectsize
			  );
FrameSet* construct_pcap_frameset(guint16 framesettype, gconstpointer pkt, gconstpointer pktend,
				  const struct pcap_pkthdr* pkthdr, const char * interface);

