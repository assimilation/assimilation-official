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
'''
   Design outline:

   All incoming network messages come in and get sent to a client who is a dispatcher.

   The dispatcher looks at the message type and computes which queue to send the
   message to based on the message type and contents.

       For death notices, the dispatcher forwards the message to the worker
       assigned to the switch the system is on - if known, or the worker
       assigned to the subnet.

   Each worker handles one or more rings - probably handling the per-switch rings
   for a subnet and the subnet ring as well.  It is important to ensure that a ring
   is handled by only one worker.  This eliminates locking concerns.  When a given
   worker receives a death notice for a drone that is also in higher-level rings,
   it does its at its level and also forwards the request to the worker handling
   the higher level ring as well.  The first subnet worker will also handle the work
   for the top-level (global) ring.

   Packets are ACKed by workers after all work has been completed.  In the case of
   a drone on multiple rings, it is only ACKed after both rings have been fully
   repaired.

   The reason for this is that until it is fully repaired, the system might crash
   before completing its work.  Retransmission timeouts will need to be set
   accordingly...

   Although congestion is normally very unlikely, this is not true for full
   datacenter powerons - where it is reasonably likely - depending on how
   quickly one can power on the servers and not pop circuit breakers or
   damage UPSes
       (it would be good to know how fast hosts can come up worst case).


   Misc Workers with well-known-names
   Request-To-Create-Ring


   Mappings:

   Drone-related information-------------------------
   NetAddr-to-drone-name
   drone-name to NetAddr
   (drone-name,ifname) to interface-info (including switch info)
   drone-neighbor-info:
       drone-name-to-neighbor-info (drone-name, NetAddr, ring-name)

   Ring-related information--------------------------
   drone-name to ring-name(s)
   ring-names to ring-information (level, #members, etc)
   ring-links-info ??
   Subnet-to-ring-name
   Switch-to-ring-name
   Global-ring-name [TheOneRing]

   Discovery-related information---------------------
   (drone-name, Interface-name) to LLDP/CDP packet
   (drone-name, discovery-type) to JSON info


   Misc Info-----------------------------------------
   NetAddr(MAC)-to-NetAddr(IP)


   Dispatcher logic:
   For now sends all requests to TheOneRing because we need to write more code ;-)


################################################################################
#
# It is readily observable that the code is headed that way, but is a long
# way from that structure...
#
################################################################################
'''


import optparse, time
import os, sys, signal
import cmainit
from frameinfo import FrameSetTypes
#import atexit
#
#   "Main" program starts below...
#   It is a the real CMA intended to run with some real nanoprobes running
#   somewhere out there...
#
#pylint: disable=R0914
def main():
    'Main program for the CMA (Collective Management Authority)'
    DefaultPort = 1984
    # VERY Linux-specific - but useful and apparently correct ;-)
    PrimaryIPcmd =   \
    "ip address show primary scope global | grep '^ *inet' | sed -e 's%^ *inet *%%' -e 's%/.*%%'"
    ipfd = os.popen(PrimaryIPcmd, 'r')
    OurAddrStr = ('%s:%d' % (ipfd.readline().rstrip(), DefaultPort))
    ipfd.close()

    OurPort = None

    parser = optparse.OptionParser(prog='CMA', version='0.0.1',
        description='Collective Management Authority for the Assimilation System',
        usage='cma.py [--bind address:port]')

    parser.add_option('-b', '--bind', action='store', default=None, dest='bind'
    ,   metavar='address:port-to-bind-to'
    ,   help='Address:port to listen to - for nanoprobes to connect to')

    parser.add_option('-d', '--debug', action='count', default=0, dest='debug'
    ,   help='enable debug for CMA and libraries - multiple occurances increase debug value')

    parser.add_option('-s', '--status', action='store_true', default=False, dest='status'
    ,   help='Return status of running CMA')

    parser.add_option('-k', '--kill', action='store_true', default=False, dest='kill'
    ,   help='Shut down running CMA.')

    parser.add_option('-e', '--erasedb', action='store_true', default=False, dest='erasedb'
    ,   help='Erase Neo4J before starting')

    parser.add_option('-f', '--foreground', action='store_true', default=False, dest='foreground'
    ,   help='keep the CMA from going into the background')

    parser.add_option('-p', '--pidfile', action='store', default='/var/run/cma', dest='pidfile'
    ,   metavar='pidfile-pathname'
    ,   help='full pathname of where to locate our pid file')

    parser.add_option('-T', '--trace', action='store_true', default=False, dest='doTrace'
    ,   help='Trace CMA execution')


    opt = parser.parse_args()[0]

    from AssimCtypes import daemonize_me, assimilation_openlog, are_we_already_running, \
        kill_pid_service, pidrunningstat_to_status, remove_pid_file, rmpid_and_exit_on_signal
        

    if opt.status:
        rc = pidrunningstat_to_status(are_we_already_running(opt.pidfile, None))
        return rc

    if opt.kill:
        if kill_pid_service(opt.pidfile, 15) < 0:
            print >> sys.stderr, "Unable to stop CMA."
            return 1
        return 0
        

    # This doesn't seem to work no matter where I invoke it...
    # But if we don't fork in daemonize_me() ('C' code), it works great...
#    def cleanup():
#        remove_pid_file(opt.pidfile)
#    atexit.register(cleanup)
#    signal.signal(signal.SIGTERM, lambda sig, stack: sys.exit(0))
#    signal.signal(signal.SIGINT, lambda sig, stack: sys.exit(0))

    daemonize_me(opt.foreground, '/', opt.pidfile)
        
    rmpid_and_exit_on_signal(opt.pidfile, signal.SIGTERM)

    # Next statement can't appear before daemonize_me() or bind() fails -- not quite sure why...
    assimilation_openlog("cma")
    from packetlistener import PacketListener
    from messagedispatcher import MessageDispatcher
    from dispatchtarget import DispatchSTARTUP, DispatchHBDEAD, DispatchJSDISCOVERY, \
         DispatchSWDISCOVER, DispatchHBSHUTDOWN
    from cmadb import CMAdb
    from AssimCclasses import pyNetAddr, pySignFrame, pyConfigContext, pyReliableUDP, \
         pyPacketDecoder
    from AssimCtypes import CONFIGNAME_CMAINIT, CONFIGNAME_CMAADDR, CONFIGNAME_CMADISCOVER, \
        CONFIGNAME_CMAFAIL, CONFIGNAME_CMAPORT, CONFIGNAME_HBPORT, CONFIGNAME_OUTSIG, \
        CONFIGNAME_DEADTIME, CONFIGNAME_WARNTIME, CONFIGNAME_HBTIME, CONFIGNAME_OUTSIG,\
        proj_class_incr_debug, VERSION_STRING, LONG_LICENSE_STRING
    for debug in range(opt.debug):
        debug = debug
        proj_class_incr_debug(None)

    if opt.bind is None:
        BindAddrStr = ('0.0.0.0:%d' % DefaultPort)
    else:
        BindAddrStr = opt.bind
        OurAddrStr = opt.bind

    OurAddr = pyNetAddr(OurAddrStr)
    BindAddr = pyNetAddr(BindAddrStr)
    if OurAddr.port() == 0:
        OurAddr.setport(DefaultPort)
    OurPort = OurAddr.port()


    configinit = {
    	CONFIGNAME_CMAINIT:	BindAddr,   # Initial listening (bind) address
    	CONFIGNAME_CMAADDR:	OurAddr,    # not sure what this one does...
    	CONFIGNAME_CMADISCOVER:	OurAddr,# Discovery packets sent here
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
    io = pyReliableUDP(config, pyPacketDecoder())
    trycount = 0
    while True:
        try:
            cmainit.CMAinit(io, cleanoutdb=opt.erasedb, debug=(opt.debug > 0))
        except RuntimeError:
            print >> sys.stderr, 'TRYING AGAIN...'
            trycount += 1
            if trycount > 300:
                remove_pid_file(opt.pidfile)
                print >> sys.stderr, ('Neo4j still not started - giving up.')
                CMAdb.log.critical('Neo4j still not started - giving up.')
                raise SystemExit(1)
            if (trycount % 60) == 1:
                print >> sys.stderr, ('Waiting for Neo4j to start.')
                CMAdb.log.warning('Waiting for Neo4j to start.')
            # Let's try again in a second...
            time.sleep(1)
            continue
        # Neo4j started.  All is well with the world.
        break

    CMAdb.log.info('Listening on: %s' % str(config[CONFIGNAME_CMAINIT]))
    CMAdb.log.info('Requesting return packets sent to: %s' % str(OurAddr))
    if CMAdb.debug:
        CMAdb.log.info('TheOneRing created - id = %s' % CMAdb.TheOneRing)
        CMAdb.log.info('Config Object sent to nanoprobes: %s' % config)

    disp = MessageDispatcher(
    {   FrameSetTypes.STARTUP: DispatchSTARTUP(),
        FrameSetTypes.HBDEAD: DispatchHBDEAD(),
        FrameSetTypes.JSDISCOVERY: DispatchJSDISCOVERY(),
        FrameSetTypes.SWDISCOVER: DispatchSWDISCOVER(),
        FrameSetTypes.HBSHUTDOWN: DispatchHBSHUTDOWN()
    })
    CMAdb.log.info('Starting CMA version %s - licensed under %s'
    %   (VERSION_STRING, LONG_LICENSE_STRING))
    if opt.foreground:
        print >> sys.stderr, ('Starting CMA version %s - licensed under %s'
        %   (VERSION_STRING, LONG_LICENSE_STRING))
    # Important to note that we don't want PacketListener to create its own 'io' object
    # or it will screw up the ReliableUDP protocol...
    listener = PacketListener(config, disp, io=io)
    if opt.doTrace:
        import trace
        tracer = trace.Trace(count=False, trace=True)
        if CMAdb.debug:
            CMAdb.log.debug(
            'Starting up traced listener.listen(); debug=%d' % opt.debug)
        if opt.foreground:
            print >> sys.stderr, (
            'cma: Starting up traced listener.listen() in foreground; debug=%d' % opt.debug)
        tracer.run('listener.listen()')
    else:
        if CMAdb.debug:
            CMAdb.log.debug(
            'Starting up untraced listener.listen(); debug=%d' % opt.debug)
        if opt.foreground:
            print >> sys.stderr, (
            'cma: Starting up untraced listener.listen() in foreground; debug=%d' % opt.debug)
        listener.listen()
    return 0

if __name__ == '__main__':
    sys.exit(main())
