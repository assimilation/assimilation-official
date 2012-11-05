/**
 * @file
 * @brief libpcap Packet capture Gsource interface description
 * @details
 * This code creates a GSource object for capturing our LLDP or libpcap packets.
 * @todo recode the g_source_pcap stuff to be classes in our C-Class system.
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
 *
 */
#ifndef _PCAP_GSOURCE_H
#define _PCAP_GSOURCE_H
#include <projectcommon.h>
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
	struct bpf_program pcprog;	///< Pcap program
	int		capturefd;	///< Underlying file descriptor
	char*		capturedev;	///< Capture device name
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

WINEXPORT GSource* g_source_pcap_new(const char * dev,
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
WINEXPORT void g_source_pcap_finalize(GSource* src); // Here to work around some Glib bugs/misunderstandings...
WINEXPORT FrameSet* construct_pcap_frameset(guint16 framesettype, gconstpointer pkt, gconstpointer pktend,
				  const struct pcap_pkthdr* pkthdr, const char * interfacep);
#endif /* _PCAP_GSOURCE_H */
