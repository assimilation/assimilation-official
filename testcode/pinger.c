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

/*
 *	You can either give us a list of addresses, or none.
 *
 *	If you give us no addresses, we just hang out waiting for someone(s) to ping us
 *	and we pong them back, and ping them too...
 *
 *	If you give us addresses then we ping them and hang out waiting for pongs and then
 *	we ping back - and so it goes...
 *
 *	Or at least that's what I think it's going to do...
 *
 */


void		obey_pingpong(AuthListener*, FrameSet* fs, NetAddr*);
ReliableUDP*	transport = NULL;
int		pongcount = 1;
int		maxpingcount = 3;
GMainLoop*	loop = NULL;

ObeyFrameSetTypeMap	doit [] = {
	{FRAMESETTYPE_PING,	obey_pingpong},
	{FRAMESETTYPE_PONG,	obey_pingpong},
	{0,			NULL}
};


void
obey_pingpong(AuthListener* unused, FrameSet* fs, NetAddr* fromaddr)
{
	char *	addrstr = fromaddr->baseclass.toString(&fromaddr->baseclass);
	static int	pingcount = 0;

	(void)unused;
	fprintf(stderr, "Received a %s [%d] packet from %s\n"
	,	(fs->fstype == FRAMESETTYPE_PING ? "ping" : "pong")
	,	fs->fstype
	,	addrstr);
	
	
	// Acknowledge that we acted on this message...
	transport->ackmessage(transport, fromaddr, fs);
	if (fs->fstype == FRAMESETTYPE_PING) {
		FrameSet*	ping = frameset_new(FRAMESETTYPE_PING);
		GSList*		flist = NULL;
		GSList*		iter;
		int		j;
		
		++pingcount;
		if (maxpingcount > 0 && pingcount > maxpingcount) {
			g_message("Quitting on ping count.");
			g_main_loop_quit(loop);
		}
		for (j=0; j < pongcount; ++j) {
			FrameSet*	pong = frameset_new(FRAMESETTYPE_PONG);
			flist = g_slist_append(flist, pong);
		}
		
		fprintf(stderr, "Sending a PONG(%d)/PING set to %s\n"
		,	pongcount, addrstr);
		flist = g_slist_prepend(flist, ping);
		transport->sendreliableM(transport, fromaddr, 0, flist);
		for (iter=flist; iter; iter=iter->next) {
			FrameSet*	fs = CASTTOCLASS(FrameSet, iter->data);
			fs->baseclass.unref(&fs->baseclass);
			fs = NULL;
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
	config->setframe(config, CONFIGNAME_OUTSIG, &signature->baseclass);
	transport = reliableudp_new(0, config, decoder, 0);
	transport->baseclass.baseclass.setpktloss(&transport->baseclass.baseclass, .1, .1);
	transport->baseclass.baseclass.enablepktloss(&transport->baseclass.baseclass, FALSE);
	g_return_val_if_fail(transport->baseclass.baseclass.bindaddr(&transport->baseclass.baseclass, anyaddr, FALSE),16);
	// Connect up our network transport into the g_main_loop paradigm
	// so we get dispatched when packets arrive
	netpkt = netgsource_new(&transport->baseclass.baseclass, NULL, G_PRIORITY_HIGH, FALSE, NULL, 0, NULL);
	act_on_packets = authlistener_new(doit, config, 0);
	act_on_packets->baseclass.associate(&act_on_packets->baseclass, netpkt);
	//g_source_ref(&netpkt->baseclass);
	
	loop = g_main_loop_new(g_main_context_default(), TRUE);

	// Kick everything off with a pingy-dingy
	for (j=1; j < argc; ++j) {
		FrameSet*	ping;
		NetAddr*	toaddr = netaddr_string_new(argv[j]);
		NetAddr*	v6addr;
		if (toaddr == NULL) {
			fprintf(stderr, "WARNING: %s is not a legit ipv4/v6 address"
			,	argv[j]);
			continue;
		}
		v6addr = toaddr->toIPv6(toaddr); UNREF(toaddr);
		v6addr->setport(v6addr, PORT);
		{
			char *	addrstr= v6addr->baseclass.toString(&v6addr->baseclass);
			fprintf(stderr, "Sending an initial PING to %s\n", addrstr);
			g_free(addrstr); addrstr = NULL;
		}
		ping = frameset_new(FRAMESETTYPE_PING);
		transport->sendreliable(transport, v6addr, 0, ping);
		UNREF(ping);
		UNREF(v6addr);
	}
	g_main_loop_run(loop);
	g_main_loop_unref(loop);
	// g_main_loop_unref() calls g_source_unref() - so we should not call it directly (?)
	//g_source_unref(&netpkt->baseclass);
	UNREF(decoder);
	UNREF2(signature);
	UNREF(config);
	UNREF(anyaddr);
	act_on_packets->baseclass.dissociate(&act_on_packets->baseclass);
	UNREF2(act_on_packets);
	UNREF3(transport);
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
