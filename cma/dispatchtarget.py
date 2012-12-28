#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab
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

from cmadb import CMAdb
from frameinfo import *
from AssimCclasses import *

class DispatchTarget:
    '''Base class for handling incoming FrameSets.
    This base class is designated to handle unhandled FrameSets.
    All it does is print that we received them.
    '''
    def __init__(self):
        from droneinfo import DroneInfo
        self.DroneInfo = DroneInfo  # Get around Import loops...
    def dispatch(self, origaddr, frameset):
        fstype = frameset.get_framesettype()
        CMAdb.log.info("Received unhandled FrameSet of type [%s] from [%s]" 
        %     (FrameSetTypes.get(fstype)[0], str(origaddr)))
        for frame in frameset.iter():
            frametype=frame.frametype()
            print "\tframe type [%s]: [%s]" \
            %     (FrameTypes.get(frametype)[1], str(frame))

    def setconfig(self, io, config):
        self.io = io
        self.config = config
        
class DispatchHBDEAD(DispatchTarget):
    'DispatchTarget subclass for handling incoming HBDEAD FrameSets.'
    def dispatch(self, origaddr, frameset):
        'Dispatch function for HBDEAD FrameSets'
        json = None
        fstype = frameset.get_framesettype()
        fromdrone = self.DroneInfo.find(origaddr)
        #print>>sys.stderr, "DispatchHBDEAD: received [%s] FrameSet from [%s]" \
    #%      (FrameSetTypes.get(fstype)[0], str(origaddr))
        for frame in frameset.iter():
            frametype=frame.frametype()
            if frametype == FrameTypes.IPADDR:
                deaddrone = self.DroneInfo.find(frame.getnetaddr())
                deaddrone.death_report('dead', 'HBDEAD packet', origaddr, frameset)

class DispatchHBSHUTDOWN(DispatchTarget):
    'DispatchTarget subclass for handling incoming HBHBDEAD FrameSets.'
    def dispatch(self, origaddr, frameset):
        'Dispatch function for HBDEAD FrameSets'
        json = None
        fstype = frameset.get_framesettype()
        CMAdb.log.warning("DispatchHBSHUTDOWN: received [%s] FrameSet from [%s]" 
        %      (FrameSetTypes.get(fstype)[0], str(origaddr)))
        for frame in frameset.iter():
            frametype=frame.frametype()
            if frametype == FrameTypes.HOSTNAME:
                fromdrone = self.DroneInfo.find(frame.getstr(), port=origaddr.port())
                if fromdrone is not None:
                    fromdrone.death_report('dead', 'HBSHUTDOWN packet', origaddr, frameset)
                else:
                    CMAdb.log.error("DispatchHBSHUTDOWN: received FrameSet from unknown drone at [%s]"
                    %   str(origaddr))
                return
        CMAdb.log.error("DispatchHBSHUTDOWN: received invalid FrameSet from drone at [%s] [%s]"
        %   str(origaddr, str(frameset)))


class DispatchSTARTUP(DispatchTarget):
    'DispatchTarget subclass for handling incoming STARTUP FrameSets.'
    def dispatch(self, origaddr, frameset):
        json = None
        addrstr = repr(origaddr)
        fstype = frameset.get_framesettype()
        if CMAdb.debug:
            CMAdb.log.debug("DispatchSTARTUP: received [%s] FrameSet from [%s]"
        %       (FrameSetTypes.get(fstype)[0], addrstr))
        for frame in frameset.iter():
            frametype=frame.frametype()
            if frametype == FrameTypes.HOSTNAME:
                sysname = frame.getstr()
            if frametype == FrameTypes.JSDISCOVER:
                json = frame.getstr()
        fs = CMAlib.create_setconfig(self.config)
        #print 'Telling them to heartbeat themselves.'
        #fs2 = CMAlib.create_sendexpecthb(self.config, FrameSetTypes.SENDEXPECTHB
        #,      origaddr)
        #print 'Sending SetConfig frameset to %s' % origaddr
        #self.io.sendreliablefs(origaddr, (fs,fs2))
        self.io.sendreliablefs(origaddr, fs)
        CMAdb.log.info('Drone %s registered from address %s (%s)' % (sysname, origaddr, addrstr))
        self.DroneInfo.add(sysname, 'STARTUP packet')
        drone = self.DroneInfo.find(sysname)
        drone.setport(origaddr.port())
        #print >>sys.stderr, 'DRONE from find: ', drone, type(drone), drone.port
        drone.startaddr=origaddr
        if json is not None:
            drone.logjson(json)
        CMAdb.cdb.TheOneRing.join(drone)
        drone.request_discovery(('tcplisteners',    3555),
                                ('tcpclients',      3333),
                                ('cpu',             36000),
                                ('os',              0),
                                ('arpcache',        45))

class DispatchJSDISCOVERY(DispatchTarget):
    'DispatchTarget subclass for handling incoming JSDISCOVERY FrameSets.'
    def dispatch(self, origaddr, frameset):
        fstype = frameset.get_framesettype()
        if CMAdb.debug:
            CMAdb.log.debug("DispatchJSDISCOVERY: received [%s] FrameSet from [%s]" 
            %       (FrameSetTypes.get(fstype)[0], repr(origaddr)))
        sysname = None
        for frame in frameset.iter():
            frametype=frame.frametype()
            if frametype == FrameTypes.HOSTNAME:
                sysname = frame.getstr()
            if frametype == FrameTypes.JSDISCOVER:
                json = frame.getstr()
                #print 'JSON received: ', json
                if sysname is None:
                    jsonconfig = pyConfigContext(init=json)
                    if not jsonconfig:
                        CMAdb.log.warning('BAD JSON [%s]' % json)
                        return
                    sysname = jsonconfig.getstring('host')
                drone = self.DroneInfo.find(sysname)
                drone.logjson(json)
                sysname = None

class DispatchSWDISCOVER(DispatchTarget):
    'DispatchTarget subclass for handling incoming SWDISCOVER FrameSets.'

    def dispatch(self, origaddr, frameset):
        fstype = frameset.get_framesettype()
        if CMAdb.debug:
            CMAdb.log.debug("DispatchSWDISCOVER: received [%s] FrameSet from [%s]"
            %       (FrameSetTypes.get(fstype)[0], str(origaddr)))
        wallclock = None
        interface = None
        designation = None
        for frame in frameset.iter():
            frametype=frame.frametype()
            if frametype == FrameTypes.HOSTNAME:
                designation = frame.getstr()
            elif frametype == FrameTypes.INTERFACE:
                interface = frame.getstr()
            elif frametype == FrameTypes.WALLCLOCK:
                wallclock = frame.getint()
            elif frametype == FrameTypes.PKTDATA:
                if wallclock is None or interface is None or designation is None:
                    raise ValueError('Incomplete Switch Discovery Packet')
                pktstart = frame.framevalue()
                pktend = frame.frameend()
                switchjson = SwitchDiscovery.decode_discovery(designation, interface
                ,               wallclock, pktstart, pktend)
                if CMAdb.debug:
                    CMAdb.log.debug('GOT Link Discovery INFO from %s: %s' % (interface, str(switchjson)))
                drone = self.DroneInfo.find(designation)
                drone.logjson(str(switchjson))
                break

