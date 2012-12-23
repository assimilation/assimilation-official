#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2011, 2012 - Alan Robertson <alanr@unix.sh>
#
#  The Assimilation software is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  The Assimilation software is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
#
#
#   Design outline:
#
#   All incoming network messages come in and get sent to a client who is a dispatcher.
#
#   The dispatcher looks at the message type and computes which queue to send the
#   message to based on the message type and contents.
#
#       For death notices, the dispatcher forwards the message to the worker
#       assigned to the switch the system is on - if known, or the worker
#       assigned to the subnet.
#
#   Each worker handles one or more rings - probably handling the per-switch rings
#   for a subnet and the subnet ring as well.  It is important to ensure that a ring
#   is handled by only one worker.  This eliminates locking concerns.  When a given
#   worker receives a death notice for a drone that is also in higher-level rings,
#   it does its at its level and also forwards the request to the worker handling
#   the higher level ring as well.  The first subnet worker will also handle the work
#   for the top-level (global) ring.
#
#   Packets are ACKed by workers after all work has been completed.  In the case of
#   a drone on multiple rings, it is only ACKed after both rings have been fully
#   repaired.
#
#   The reason for this is that until it is fully repaired, the system might crash
#   before completing its work.  Retransmission timeouts will need to be set
#   accordingly...
#
#   Although congestion is normally very unlikely, this is not true for full
#   datacenter powerons - where it is reasonably likely - depending on how
#   quickly one can power on the servers and not pop circuit breakers or
#   damage UPSes
#       (it would be good to know how fast hosts can come up worst case).
#
#
#   Misc Workers with well-known-names
#   Request-To-Create-Ring
#
#
#   Mappings:
#
#   Drone-related information-------------------------
#   NetAddr-to-drone-name
#   drone-name to NetAddr
#   (drone-name,ifname) to interface-info (including switch info)
#   drone-neighbor-info:
#       drone-name-to-neighbor-info (drone-name, NetAddr, ring-name)
#
#   Ring-related information--------------------------
#   drone-name to ring-name(s)
#   ring-names to ring-information (level, #members, etc)
#   ring-links-info ??
#   Subnet-to-ring-name
#   Switch-to-ring-name
#   Global-ring-name [TheOneRing]
#
#   Discovery-related information---------------------
#   (drone-name, Interface-name) to LLDP/CDP packet
#   (drone-name, discovery-type) to JSON info
#
#
#   Misc Info-----------------------------------------
#   NetAddr(MAC)-to-NetAddr(IP)
#
#
#   Dispatcher logic:
#   For now sends all requests to TheOneRing because we need to write more code ;-)
#
#
################################################################################
#
# It is readily observable that the code is headed that way, but is a long
# way from that structure...
#
################################################################################

if __name__ == '__main__':
    import optparse
    #
    #   "Main" program starts below...
    #   It is a test program intended to run with some real nanoprobes running
    #   somewhere out there...
    #
    OurAddr = None
    DefaultPort = 1984
    OurPort = None

    parser = optparse.OptionParser(prog='CMA', version='0.0.1',
        description='Collective Management Authority for the Assimilation System',
        usage='cma.py [--bind address:port]')

    parser.add_option('-b', '--bind', action='store', default='0.0.0.0:1984', dest='bind'
    ,   metavar='address:port-to-bind-to'
    ,   help='Address:port to listen to - for nanoprobes to connect to')

    parser.add_option('-f', '--foreground', action='store_true', default=False, dest='foreground'
    ,   help='keep the CMA from going into the background')


    opt, args = parser.parse_args()


    from AssimCtypes import daemonize_me
    daemonize_me(opt.foreground, '/')
    from packetlistener import PacketListener
    from messagedispatcher import MessageDispatcher
    from dispatchtarget import DispatchSTARTUP, DispatchHBDEAD, DispatchJSDISCOVERY, DispatchSWDISCOVER, DispatchHBSHUTDOWN
    from cmadb import CMAdb
    from AssimCclasses import pyNetAddr, pySignFrame, pyConfigContext, pyReliableUDP, pyPacketDecoder
    from AssimCtypes import CONFIGNAME_CMAINIT, CONFIGNAME_CMAADDR, CONFIGNAME_CMADISCOVER, CONFIGNAME_CMAFAIL, CONFIGNAME_CMAPORT, CONFIGNAME_HBPORT, CONFIGNAME_OUTSIG, CONFIGNAME_DEADTIME, CONFIGNAME_WARNTIME, CONFIGNAME_HBTIME, CONFIGNAME_OUTSIG
    from frameinfo import FrameTypes, FrameSetTypes
    OurAddr = pyNetAddr(opt.bind)
    if OurAddr.port() > 0:
        OurPort = OurAddr.port()
    else:
        OurAddr.setport(1984)


    configinit = {
    	CONFIGNAME_CMAINIT:	OurAddr,    # Initial 'hello' address
    	CONFIGNAME_CMAADDR:	OurAddr,    # not sure what this one does...
    	CONFIGNAME_CMADISCOVER:	OurAddr,    # Discovery packets sent here
    	CONFIGNAME_CMAFAIL:	OurAddr,    # Failure packets sent here
    	CONFIGNAME_CMAPORT:	OurPort,
    	CONFIGNAME_HBPORT:	OurPort,
    	CONFIGNAME_OUTSIG:	pySignFrame(1),
    	CONFIGNAME_DEADTIME:	10*1000000,
    	CONFIGNAME_WARNTIME:	3*1000000,
    	CONFIGNAME_HBTIME:	1*1000000,
        CONFIGNAME_OUTSIG:	pySignFrame(1),
    }
    config = pyConfigContext(init=configinit)
    io = pyReliableUDP(config, pyPacketDecoder(0))
    CMAdb.initglobal(io, True)
    CMAdb.log.info('Listening on Address: %s' % str(OurAddr))
    CMAdb.log.info('TheOneRing created - id = %d' % CMAdb.TheOneRing.node.id)

    print FrameTypes.get(1)[2]
    disp = MessageDispatcher(
    {   FrameSetTypes.STARTUP: DispatchSTARTUP(),
        FrameSetTypes.HBDEAD: DispatchHBDEAD(),
        FrameSetTypes.JSDISCOVERY: DispatchJSDISCOVERY(),
        FrameSetTypes.SWDISCOVER: DispatchSWDISCOVER(),
        FrameSetTypes.HBSHUTDOWN: DispatchHBSHUTDOWN()
    })
    listener = PacketListener(config, disp)
    listener.listen()
