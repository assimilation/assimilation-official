/**
 * @file
 * @brief libpcap Packet capture Gsource module.
 * This code is based on (and meets the API expectations of) the the Glib
 * <b><a href="http://library.gnome.org/devel/glib/unstable/glib-The-Main-Event-Loop.html">main event loop</a></b>
 * (g_main_loop) event scheduler/dispatcher concept.
 * We set things up so that when a libpcap packet arrives that we get invoked.
 * It's a little complicated to set up, but really pretty nice, and quite easy to use once set up.
 * The main function defined in this file is g_source_pcap_new().
 * We supply four key functions in order to meet the Glib main event loop API:
 * - g_source_pcap_prepare()- called before the beginning of each poll(2) call by the mainloop code.
 * - g_source_pcap_check() - look to see if any packets have arrived - don't do anything yet...
 * - g_source_pcap_dispatch() - Handle any packets that might have arrived.
 * - g_source_pcap_finalize() - called during object destruction.
 *
 * The main types we use from Glib are:
 * - <a href="http://library.gnome.org/devel/glib/unstable/glib-The-Main-Event-Loop.html#GSource">GSource</a> - event source
 * - <a href="http://library.gnome.org/devel/glib/unstable/glib-The-Main-Event-Loop.html#GPollFD">GPollFD</a> - fd polling source
 * - <a href="http://library.gnome.org/devel/glib/unstable/glib-Datasets.html#GDestroyNotify">GDestroyNotify</a> - destructor
 * - <a href="http://library.gnome.org/devel/glib/unstable/glib-Basic-Types.html#gpointer">gpointer</a> - generic pointer
 * - <a href="http://library.gnome.org/devel/glib/unstable/glib-Basic-Types.html#gint">gint</a> - generic integer
 *
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

#include <memory.h>
#include <projectcommon.h>
#include <proj_classes.h>
#include <pcap_min.h>
#include <pcap_GSource.h>
#include <intframe.h>
#include <addrframe.h>
#include <cstringframe.h>
#include <frametypes.h>
#include <misc.h>

///@defgroup GSource_Pcap GSource_Pcap class
/// Class representing a pcap GSource object - for capturing packets in the g_main_loop paradigm.
/// This is technically a subclass of GSource (which isn't part of this project).
///@{
///@ingroup C_Classes

FSTATIC gboolean g_source_pcap_prepare(GSource* source, gint* timeout);
FSTATIC gboolean g_source_pcap_check(GSource* source);
FSTATIC gboolean g_source_pcap_dispatch(GSource* source, GSourceFunc callback, gpointer user_data);
FSTATIC void     g_source_pcap_finalize(GSource* source);
FSTATIC guint64 proj_timeval_to_g_real_time(const struct timeval * tv);

static GSourceFuncs g_source_pcap_gsourcefuncs = {
	g_source_pcap_prepare,
	g_source_pcap_check,
	g_source_pcap_dispatch,
	g_source_pcap_finalize,
	NULL,
	NULL
};


/**
 * @brief Construct new GSource from a newly constructed pcap capture object.
 * We use create_pcap_listener() to construct the pcap capture object.
 * This code is based on the the Glib
 * <b><a href="http://library.gnome.org/devel/glib/unstable/glib-The-Main-Event-Loop.html">main event loop</a></b>
 * (g_main_loop) event scheduler/dispatcher concept.
 * @todo investigate whether create_pcap_listener() might need more parameters to allow for
 * non-blocking reads... (?)
 */
GSource*
g_source_pcap_new(const char * dev,	///<[in]Capture device name
		  unsigned listenmask,	///<[in] bit mask of @ref pcap_protocols "supported protocols"
					///[in] called when new pcap data has arrived
        	  gboolean (*dispatch)(GSource_pcap_t*	gsource, ///< Gsource object causing dispatch
			     pcap_t* capstruct,		///<[in] Pointer to structure capturing for us
                             gconstpointer pkt,		///<[in] Pointer to the packet just read in
                             gconstpointer pend,	///<[in] Pointer to first byte past 'pkt'
                             const struct pcap_pkthdr* pkthdr, ///<[in] libpcap packet header
                             const char * capturedev,	///<[in] Device being captured
			     gpointer userdata),	///<[in/out] user-object

		  GDestroyNotify notify,///<[in] Called when this object is being destroyed -
					///< can be NULL.
		  gint priority,	///<[in] g_main_loop
					///< <a href="http://library.gnome.org/devel/glib/unstable/glib-The-Main-Event-Loop.html#G-PRIORITY-HIGH:CAPS">dispatch priority</a>
		  gboolean can_recurse,	///<[in] TRUE if dispatch recursion is allowed
                  GMainContext* context, ///<[in] GMainContext or NULL
		  gsize	objectsize,	///<[in] size of pcap_g_source object to create (or zero)
		  gpointer userdata	///<[in/out] pointer to user object for dispatch function
                  )
{
	pcap_t*		captureobj;
	GSource*	src;
	GSource_pcap_t*	ret;

	if (objectsize < sizeof(GSource_pcap_t)) {
		objectsize = sizeof(GSource_pcap_t);
	}

	// Try and create a GSource object for us to eventually return...
	src = g_source_new(&g_source_pcap_gsourcefuncs, objectsize);
	g_return_val_if_fail(src != NULL, NULL);

	proj_class_register_object(src, "GSource");
	proj_class_register_subclassed(src, "GSource_pcap_t");

	ret = CASTTOCLASS(GSource_pcap_t, src);
	// OK, now create the capture object to associate with it
	if (NULL == (captureobj = create_pcap_listener(dev, FALSE, listenmask, &ret->pcprog))) {
		// OOPS! Didn't work...  Give up.
		g_source_unref(src);
		return NULL;
	}
	ret->capture = captureobj;
	ret->capturedev = g_strdup(dev);
	ret->listenmask = listenmask;
	ret->dispatch = dispatch;
#ifdef _MSC_VER
	// Probably depends on the version of the API - not just being on Windows...
	ret->capturefd = pcap_fileno(ret->capture);
#else
	ret->capturefd = pcap_get_selectable_fd(ret->capture);
#endif
	ret->destroynote = notify;
	ret->gfd.fd = ret->capturefd;
	ret->gfd.events =  G_IO_IN|G_IO_ERR|G_IO_HUP;
	ret->gfd.revents =  0;
	ret->userdata = userdata;
	g_source_add_poll(src, &ret->gfd);
	g_source_set_priority(src, priority);
	g_source_set_can_recurse(src, can_recurse);
	ret->gsourceid = g_source_attach(src, context);
	if (ret->gsourceid == 0) {
                g_source_remove_poll(src, &ret->gfd);
                memset(ret, 0, sizeof(*ret));
                g_source_unref(src);
                src = NULL;
                ret = NULL;
        }
	return (GSource*)ret;
}

/// The GMainLoop <i>prepare</i> function for libpcap packet capturing
gboolean
g_source_pcap_prepare(GSource* source, ///<[in] Gsource being prepared for
                      gint* timeout)   ///<[in,out] timeout - neither referenced nor set
{
	// Don't need to do anything prior to a poll(2) call...
	(void)source;
	(void)timeout;
	return FALSE;
}
/// The GMainLoop <i>check</i> function for libpcap packet capturing
gboolean
g_source_pcap_check(GSource* src) ///<[in] source being <i>check</i>ed
{
	GSource_pcap_t*	psrc = CASTTOCLASS(GSource_pcap_t, src);
	
	// revents: received events...
	// @todo: should check for errors in revents
	return 0 != psrc->gfd.revents;
}
/// The GMainLoop <i>dispatch</i> function for libpcap packet capturing
gboolean
g_source_pcap_dispatch(GSource* src, ///<[in] source being <i>dispatch</i>ed
                       GSourceFunc callback, ///<[in] dispatch function (ignored)
                       gpointer user_data)   ///<[in] user data (ignored)
{
	GSource_pcap_t*	psrc = CASTTOCLASS(GSource_pcap_t, src);
	const u_char *		pkt;
	struct pcap_pkthdr*	hdr;
	int			rc; // Meaning of various rc values:
				    // 1 - read a single packet
				    // 0 - no packets to read at the moment
				    // negative - various kinds of errors
	(void)callback;
	(void)user_data;
	// Process all the packets we can find.
	while (1 == (rc = pcap_next_ex(psrc->capture, &hdr, &pkt))) {
		const u_char* pktend = pkt + hdr->caplen;
		if (!psrc->dispatch(psrc, psrc->capture, pkt, pktend, hdr,
                                    psrc->capturedev, psrc->userdata)) {
			g_source_remove_poll(src, &psrc->gfd);
			g_source_unref(src);
			return FALSE;
		}
	}
	if (rc < 0) {
		g_warning("%s.%d: pcap_next_ex() returned %d [%s]. Returning FALSE."
		,	__FUNCTION__, __LINE__, rc, pcap_geterr(psrc->capture));
	}
	return rc >= 0;
}
/// The GMainLoop <i>finalize</i> function for libpcap packet capturing
/// Called when this object is 'finalized' (destroyed)
void
g_source_pcap_finalize(GSource* src)
{
	GSource_pcap_t*	psrc = CASTTOCLASS(GSource_pcap_t, src);
	if (psrc->destroynote) {
		psrc->destroynote(psrc);
	}
	if (psrc->capture) {
		close_pcap_listener(psrc->capture, psrc->capturedev, psrc->listenmask);
		pcap_freecode(&psrc->pcprog);
		psrc->capture = NULL;
		g_free(psrc->capturedev);
		psrc->capturedev = NULL;
	}
	proj_class_dissociate(src);
}

/// Convert <b>struct timeval</b> to g_get_real_time() style value
FSTATIC guint64
proj_timeval_to_g_real_time(const struct timeval * tv)
{
	guint64		ret;
	ret = (guint64)tv->tv_sec * (guint64)1000000UL;
	ret += (guint64)tv->tv_usec;
	return ret;
}

/// Construct a PCAP capture FrameSet from a PCAP packet
FrameSet*
construct_pcap_frameset(guint16 framesettype,		  ///<[in] type to create FrameSet with
			gconstpointer pkt,		  ///<[in] captured packet
			gconstpointer pktend,		  ///<[in] one byte past end of pkt
			const struct pcap_pkthdr* pkthdr, ///<[in] libpcap packet header
			const char * interfacep)	  ///<[in] interface it was captured on
{
	IntFrame*	timeframe = intframe_new(FRAMETYPE_WALLCLOCK, sizeof(proj_timeval_to_g_real_time(NULL)));
	Frame* 		pktframe = frame_new(FRAMETYPE_PKTDATA, 0);
	CstringFrame*	intfname = cstringframe_new(FRAMETYPE_INTERFACE, 0);
	CstringFrame*	fsysname = cstringframe_new(FRAMETYPE_HOSTNAME, 0);
	FrameSet*	fs = frameset_new(framesettype);
	const guint8*	bpkt = (const guint8*) pkt;
	gsize		pktlen = ((const guint8*)pktend-bpkt);
	guint8*		cppkt = MALLOC0(pktlen);
	gchar*		sysname;

	sysname = proj_get_sysname();
	g_return_val_if_fail(NULL != sysname, NULL);
	g_return_val_if_fail(fsysname != NULL, NULL);
	g_return_val_if_fail(timeframe != NULL, NULL);
	g_return_val_if_fail(pktframe != NULL, NULL);
	g_return_val_if_fail(intfname != NULL, NULL);
	g_return_val_if_fail(cppkt != NULL, NULL);

	// System name
	fsysname->baseclass.setvalue(&fsysname->baseclass, sysname, strlen(sysname)+1, g_free);
	frameset_append_frame(fs, &fsysname->baseclass);
	UNREF2(fsysname);

	// Interface name
	intfname->baseclass.setvalue(&intfname->baseclass, g_strdup(interfacep), strlen(interfacep)+1, g_free);
	frameset_append_frame(fs, &intfname->baseclass);
	UNREF2(intfname);

	// Local time stamp
	timeframe->setint(timeframe, proj_timeval_to_g_real_time(&(pkthdr->ts)));
	frameset_append_frame(fs, &timeframe->baseclass);
	UNREF2(timeframe);

	// Packet data
	memcpy(cppkt, pkt, pktlen);
	pktframe->setvalue(pktframe, cppkt, pktlen, g_free);
	frameset_append_frame(fs, pktframe);
	UNREF(pktframe);

	return fs;
}
///@}
