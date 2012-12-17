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

ObeyFrameSetTypeMap	doit [] = {
	{FRAMESETTYPE_PING,	obey_pingpong},
	{FRAMESETTYPE_PONG,	obey_pingpong},
	{0,			NULL}
};


void
obey_pingpong(AuthListener* unused, FrameSet* fs, NetAddr* fromaddr)
{
	char *	addrstr = fromaddr->baseclass.toString(&fromaddr->baseclass);

	(void)unused;
	fprintf(stderr, "Received a %s [%d] packet from %s\n"
	,	(fs->fstype == FRAMESETTYPE_PING ? "ping" : "pong")
	,	fs->fstype
	,	addrstr);
	
	
	// Acknowledge that we acted on this message...
	transport->ackmessage(transport, fromaddr, fs);
	if (fs->fstype == FRAMESETTYPE_PING) {
		FrameSet*	pong = frameset_new(FRAMESETTYPE_PONG);
		FrameSet*	ping = frameset_new(FRAMESETTYPE_PING);
		GSList*		flist;
		flist = g_slist_prepend(NULL, ping);
		flist = g_slist_prepend(flist, pong);
		
		fprintf(stderr, "Sending a PONG/PING pair to %s\n"
		,	addrstr);
		transport->sendreliableM(transport, fromaddr, 0, flist);
		g_slist_free(flist); flist = NULL;
		ping->baseclass.unref(&ping->baseclass);
		pong->baseclass.unref(&pong->baseclass);
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
	GMainLoop*	loop;

	g_log_set_fatal_mask(NULL, G_LOG_LEVEL_ERROR|G_LOG_LEVEL_CRITICAL);
	proj_class_incr_debug(NULL);
	proj_class_incr_debug(NULL);
	config->setframe(config, CONFIGNAME_OUTSIG, &signature->baseclass);
	transport = reliableudp_new(0, config, decoder);
	g_return_val_if_fail(transport->baseclass.baseclass.bindaddr(&transport->baseclass.baseclass, anyaddr, FALSE),16);
	// Connect up our network transport into the g_main_loop paradigm
	// so we get dispatched when packets arrive
	netpkt = netgsource_new(CASTTOCLASS(NetIO, transport), NULL, G_PRIORITY_HIGH, FALSE, NULL, 0, NULL);
	act_on_packets = authlistener_new(doit, config, 0);
	act_on_packets->baseclass.associate(&act_on_packets->baseclass, netpkt);
	g_source_ref(CASTTOCLASS(GSource, netpkt));
	
	// Kick everything off with a pingy-dingy
	for (j=1; j < argc; ++j) {
		FrameSet*	ping;
		NetAddr*	toaddr = netaddr_string_new(argv[j]);
		if (toaddr == NULL) {
			fprintf(stderr, "WARNING: %s is not a legit ipv4/v6 address"
			,	argv[j]);
			continue;
		}
		toaddr->setport(toaddr, PORT);
		{
			char *	addrstr= toaddr->baseclass.toString(&toaddr->baseclass);
			fprintf(stderr, "Sending an initial PING to %s\n", addrstr);
			g_free(addrstr); addrstr = NULL;
		}
		ping = frameset_new(FRAMESETTYPE_PING);
		transport->sendreliable(transport, toaddr, 0, ping);
		ping->baseclass.unref(&ping->baseclass);
		toaddr->baseclass.unref(&toaddr->baseclass); toaddr = NULL;
	}
	loop = g_main_loop_new(g_main_context_default(), TRUE);
	g_main_loop_run(loop);
	return 0;
}
