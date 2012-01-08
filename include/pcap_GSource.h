/**
 * @file
 * @brief libpcap Packet capture Gsource interface description
 * @details
 * This code creates a GSource object for capturing our LLDP or libpcap packets.
 * @todo recode the g_source_pcap stuff to be classes in our C-Class system.
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
/// @todo make this fit better into the @ref ProjectClass system.
struct _GSource_pcap {
	GSource		gs;		///< Parent GSource Object
	GPollFD		gfd;		///< Poll/select object for gmainloop
	pcap_t*		capture;	///< Pcap capture object
	int		capturefd;	///< Underlying file descriptor
	const char*	capturedev;	///< Capture device name
	unsigned	listenmask;	///< Protocols selected from @ref pcap_protocols
	gint		gsourceid;	///< Source ID from g_source_attach()
	gpointer	userdata;	///< Saved user data	
        ///[in] user dispatch function - we call it when a packet is read
        gboolean (*dispatch)(GSource_pcap_t* gsource,	///<[in] object causing the dispatch
			     pcap_t* capstruct,		///<[in] Pointer to structure doing the capturing for us
                             gconstpointer pkt,	///<[in] Pointer to the packet just read in
                             gconstpointer pend,	///<[in] Pointer to first byte past 'pkt'
                             const struct pcap_pkthdr* pkthdr, ///<[in] libpcap packet header
                             const char * capturedev,	///<[in] capture device name
			     gpointer userdata);	///<[in] Device being captured
					///<[in] called when new pcap data has arrived
	GDestroyNotify	destroynote;	///<[in] function to call when we're destroyed...
};

#ifdef _MSC_VER
#define EXP_FUNC __declspec( dllexport )
#endif
EXP_FUNC GSource* g_source_pcap_new(const char * dev,
		  	   unsigned listenmask,
        	  	   gboolean (*dispatch)
                            (GSource_pcap_t*	gsource, ///< Gsource object causing dispatch
                             pcap_t* capstruct,		///<[in] Pointer to structure capturing for us
                             gconstpointer pkt,	///<[in] Pointer to the packet just read in
                             gconstpointer pend,	///<[in] Pointer to first byte past 'pkt'
                             const struct pcap_pkthdr* pkthdr, ///<[in] libpcap packet header
                             const char * capturedev,	///<[in] Device being captured
			     gpointer userdata		///<[in/out] user object pointer
			    ),
			   GDestroyNotify notify,
			   gint priority,
			   gboolean can_recurse,
			   GMainContext* context,
			   gsize objectsize,
			   gpointer userdata
			  );
EXP_FUNC void g_source_pcap_finalize(GSource* src); // Here to work around some Glib bugs/misunderstandings...
//rhm changed interface to interfacep as interface is reserved word in vc6
EXP_FUNC FrameSet* construct_pcap_frameset(guint16 framesettype, gconstpointer pkt, gconstpointer pktend,
				  const struct pcap_pkthdr* pkthdr, const char * interfacep);
