/**
 * @file
 * @brief Test code that uses reliable UDP for pinging...
 * @details See brief statement...
 *
 * This file is part of the Assimilation Project.
 *
 * @author &copy; Copyright 2012 - Alan Robertson <alanr@unix.sh>
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
#include <netaddr.h>
#include <frametypes.h>
#include <reliableudp.h>
#include <authlistener.h>

#include <compressframe.h>
#include <cryptframe.h>
#include <intframe.h>
#include <cstringframe.h>
#include <addrframe.h>
#include <ipportframe.h>
#include <seqnoframe.h>
#include <nvpairframe.h>

#include <packetdecoder.h>

#define	PORT	19840

#define RCVLOSS		0.05
#define XMITLOSS	0.05

/*
 *	You can either give us a list of addresses, or none.
 *
 *	If you give us no addresses, we just hang out waiting for someone(s) to ping us
 *	and we pong them back, and ping them too...
 *
 *	If you give us addresses then we ping them and hang out waiting for pongs and then
 *	we ping back - and so it goes...
 *
 */

void		obey_pingpong(AuthListener*, FrameSet* fs, NetAddr*);
gboolean	exit_when_connsdown(gpointer);
ReliableUDP*	transport = NULL;
int		pongcount = 2;
int		maxpingcount = 10;
GMainLoop*	loop = NULL;

ObeyFrameSetTypeMap	doit [] = {
	{FRAMESETTYPE_PING,	obey_pingpong},
	{FRAMESETTYPE_PONG,	obey_pingpong},
	{0,			NULL}
};

GHashTable*	theircounts = NULL;
GHashTable*	ourcounts = NULL;

gboolean
exit_when_connsdown(gpointer unused)
{
	(void)unused;
	if (transport->_protocol->activeconncount(transport->_protocol) == 0) {
		fprintf(stderr, "ALL CONNECTIONS SHUT DOWN! calling g_main_quit()\n");
		g_main_loop_quit(loop);
		return FALSE;
	}
	return TRUE;
}

static gint	pingcount = 1;
void
obey_pingpong(AuthListener* unused, FrameSet* fs, NetAddr* fromaddr)
{
	char *	addrstr = fromaddr->baseclass.toString(&fromaddr->baseclass);
	FsProtoState	state = transport->_protocol->connstate(transport->_protocol, 0, fromaddr);

	if (fs->fstype == FRAMESETTYPE_PONG) {
		fprintf(stderr, "Received a PONG packet from %s\n", addrstr);
	}
	
	
	(void)unused;
	// Acknowledge that we acted on this message...
	transport->baseclass.baseclass.ackmessage(&transport->baseclass.baseclass, fromaddr, fs);
	if (FSPR_INSHUTDOWN(state)) {
		// Shutting down -- ignore this message...
		// Note that we DO have to ACK the message...
		return;
	}
	if (fs->fstype == FRAMESETTYPE_PING) {
		FrameSet*	ping = frameset_new(FRAMESETTYPE_PING);
		IntFrame*	count = intframe_new(FRAMETYPE_CINTVAL, sizeof(pingcount));
		GSList*		flist = NULL;
		GSList*		iter;
		int		j;
		GSList*		slframe;
		gpointer	theirlastcount_p = g_hash_table_lookup(theircounts, fromaddr);
		gpointer	ourlastcount_p = g_hash_table_lookup(ourcounts, fromaddr);
		gint		ournextcount;
		gboolean	foundcount = FALSE;
		
		++pingcount;
		if (ourlastcount_p == NULL) {
			ournextcount = 1;
			REF(fromaddr);	// For the 'ourcounts' table
		}else{
			ournextcount = GPOINTER_TO_INT(ourlastcount_p)+1;
		}
		g_hash_table_insert(ourcounts, fromaddr, GINT_TO_POINTER(ournextcount));

		count->setint(count, ournextcount);
		frameset_append_frame(ping, &count->baseclass);
		UNREF2(count);
		if (maxpingcount > 0 && pingcount > maxpingcount) {
			g_message("Shutting down on ping count.");
			transport->_protocol->closeall(transport->_protocol);
			g_idle_add(exit_when_connsdown, NULL);
		}
		for (slframe = fs->framelist; slframe != NULL; slframe = g_slist_next(slframe)) {
			Frame* frame = CASTTOCLASS(Frame, slframe->data);
			if (frame->type == FRAMETYPE_CINTVAL) {
				IntFrame*	cntframe = CASTTOCLASS(IntFrame, frame);
				gint		theirnextcount = cntframe->getint(cntframe);
				foundcount = TRUE;
				if (theirlastcount_p != NULL) {
					gint	theirlastcount = GPOINTER_TO_INT(theirlastcount_p);
					if (theirnextcount != theirlastcount +1) {
						char *	fromstr = fromaddr->baseclass.toString(&fromaddr->baseclass);
						g_warning("%s.%d: PING received from %s was %d should have been %d"
						,	__FUNCTION__, __LINE__, fromstr, theirnextcount, theirlastcount+1);
						g_free(fromstr); fromstr = NULL;
					}
				}else if (theirnextcount != 1) {
					char *	fromstr = fromaddr->baseclass.toString(&fromaddr->baseclass);
					g_warning("%s.%d: First PING received from %s was %d should have been 1"
					,	__FUNCTION__, __LINE__, fromstr, theirnextcount);
					g_free(fromstr); fromstr = NULL;
				}
				g_hash_table_insert(theircounts, fromaddr, GINT_TO_POINTER(theirnextcount));
				if (theirlastcount_p == NULL) {
					REF(fromaddr);
				}
				fprintf(stderr, "Received a PING packet (seq %d) from %s ========================\n"
				,	theirnextcount, addrstr);
			}
		}
		if (!foundcount) {
			char *	s = fs->baseclass.toString(&fs->baseclass);
			fprintf(stderr, "Did not find a count in this PING packet");
			fprintf(stderr, "%s", s);
			FREE(s);
		}


		for (j=0; j < pongcount; ++j) {
			FrameSet*	pong = frameset_new(FRAMESETTYPE_PONG);
			flist = g_slist_append(flist, pong);
		}
		
		fprintf(stderr, "Sending a PONG(%d)/PING set to %s\n"
		,	pongcount, addrstr);
		flist = g_slist_prepend(flist, ping);
		transport->baseclass.baseclass.sendreliablefs(&transport->baseclass.baseclass, fromaddr, 0, flist);
		for (iter=flist; iter; iter=iter->next) {
 			FrameSet*	fs2 = CASTTOCLASS(FrameSet, iter->data);
			UNREF(fs2);
		}
		g_slist_free(flist); flist = NULL;
	}
	if (addrstr) {
		g_free(addrstr); addrstr = NULL;
	}
}


int
main(int argc, char **argv)
{
	int		j;
	FrameTypeToFrame	decodeframes[] = FRAMETYPEMAP;
	PacketDecoder*	decoder = packetdecoder_new(0, decodeframes, DIMOF(decodeframes));
	SignFrame*      signature = signframe_new(G_CHECKSUM_SHA256, 0);
	ConfigContext*	config = configcontext_new(0);
	const guint8	anyadstring[] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
	NetAddr* anyaddr = netaddr_ipv6_new(anyadstring, PORT);
	NetGSource*	netpkt;
	AuthListener*	act_on_packets;
	int		liveobjcount;

	g_log_set_fatal_mask(NULL, G_LOG_LEVEL_ERROR|G_LOG_LEVEL_CRITICAL);
	proj_class_incr_debug(NULL);
	proj_class_incr_debug(NULL);
	proj_class_incr_debug(NULL);
	theircounts = g_hash_table_new(netaddr_g_hash_hash, netaddr_g_hash_equal);
	ourcounts = g_hash_table_new(netaddr_g_hash_hash, netaddr_g_hash_equal);
	config->setframe(config, CONFIGNAME_OUTSIG, &signature->baseclass);
	transport = reliableudp_new(0, config, decoder, 0);
	transport->baseclass.baseclass.setpktloss(&transport->baseclass.baseclass, RCVLOSS, XMITLOSS);
	transport->baseclass.baseclass.enablepktloss(&transport->baseclass.baseclass, TRUE);
	g_return_val_if_fail(transport->baseclass.baseclass.bindaddr(&transport->baseclass.baseclass, anyaddr, FALSE),16);
	// Connect up our network transport into the g_main_loop paradigm
	// so we get dispatched when packets arrive
	netpkt = netgsource_new(&transport->baseclass.baseclass, NULL, G_PRIORITY_HIGH, FALSE, NULL, 0, NULL);
	act_on_packets = authlistener_new(0, doit, config, FALSE);
	act_on_packets->baseclass.associate(&act_on_packets->baseclass, netpkt);
	//g_source_ref(&netpkt->baseclass);

	fprintf(stderr, "Expecting %d packets\n", maxpingcount);
	fprintf(stderr, "Sending   %d PONG packets per PING packet\n", pongcount);
	fprintf(stderr, "Transmit packet loss: %g\n", XMITLOSS*100);
	fprintf(stderr, "Receive packet loss:  %g\n", RCVLOSS*100);
	
	
	loop = g_main_loop_new(g_main_context_default(), TRUE);

	// Kick everything off with a pingy-dingy
	for (j=1; j < argc; ++j) {
		FrameSet*	ping;
		NetAddr*	toaddr = netaddr_string_new(argv[j]);
		NetAddr*	v6addr;
		IntFrame*	iframe  = intframe_new(FRAMETYPE_CINTVAL, 1);
		if (toaddr == NULL) {
			fprintf(stderr, "WARNING: %s is not a valid ipv4/v6 address"
			,	argv[j]);
			continue;
		}
		v6addr = toaddr->toIPv6(toaddr); UNREF(toaddr);
		v6addr->setport(v6addr, PORT);
		g_hash_table_insert(ourcounts, v6addr, GINT_TO_POINTER(1));
		REF(v6addr);	// For the 'ourcounts' table
		{
			char *	addrstr= v6addr->baseclass.toString(&v6addr->baseclass);
			fprintf(stderr, "Sending an initial PING to %s\n", addrstr);
			g_free(addrstr); addrstr = NULL;
		}
		ping = frameset_new(FRAMESETTYPE_PING);
		iframe->setint(iframe, 1);
		frameset_append_frame(ping, &iframe->baseclass);
		UNREF2(iframe);
		transport->baseclass.baseclass.sendareliablefs(&transport->baseclass.baseclass, v6addr, 0, ping);
		UNREF(ping);
		UNREF(v6addr);
	}
	UNREF(decoder);
	UNREF2(signature);
	UNREF(config);
	UNREF(anyaddr);
	g_main_loop_run(loop);
	act_on_packets->baseclass.dissociate(&act_on_packets->baseclass);
	UNREF2(act_on_packets);

	UNREF3(transport);	// 'transport' global variable is referenced while the loop is running

	// Free up our hash tables and they NetAddrs we've held onto
	{
		GHashTableIter	iter;
		gpointer	key;
		gpointer	value;
		g_hash_table_iter_init(&iter, theircounts);
		while (g_hash_table_iter_next(&iter, &key, &value)) {
			NetAddr*	addr = CASTTOCLASS(NetAddr, key);
			g_hash_table_iter_remove(&iter);
			UNREF(addr);
		}
		g_hash_table_destroy(theircounts); theircounts = NULL;
		g_hash_table_iter_init(&iter, ourcounts);
		while (g_hash_table_iter_next(&iter, &key, &value)) {
			NetAddr*	addr = CASTTOCLASS(NetAddr, key);
			g_hash_table_iter_remove(&iter);
			UNREF(addr);
		}
		g_hash_table_destroy(ourcounts); ourcounts = NULL;
	}
	g_main_loop_unref(loop);
	g_source_unref(&netpkt->baseclass);
	g_main_context_unref(g_main_context_default());
	// At this point - nothing should show up - we should have freed everything
	liveobjcount = proj_class_live_object_count();
	if (liveobjcount > 0) {
		g_warning("============ OOPS %d objects still alive ==============================="
		,	liveobjcount);
		proj_class_dump_live_objects();
		g_warning("Too many objects (%d) alive at end of test.", liveobjcount);
	}else{
		g_message("No objects left alive.  Awesome!");
	}
        proj_class_finalize_sys(); // Shut down object system to make valgrind happy :-D
	return 0;
}
