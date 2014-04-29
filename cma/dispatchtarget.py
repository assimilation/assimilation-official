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
'''
This file is responsible for a variety of dispatch classes - for handling all our
various types of incoming packets.
'''

import sys
sys.path.append("cma")
from cmadb import CMAdb
from frameinfo import FrameSetTypes, FrameTypes
from AssimCclasses import pyNetAddr, pyConfigContext, DEFAULT_FSP_QID, pySwitchDiscovery
from monitoring import MonitorAction
from assimevent import AssimEvent

class DispatchTarget:
    '''Base class for handling incoming FrameSets.
    This base class is designated to handle unhandled FrameSets.
    All it does is print that we received them.
    '''
    dispatchtable = {}
    def __init__(self):
        'Constructor for base class DispatchTarget'
        from droneinfo import Drone
        self.droneinfo = Drone  # Get around Import loops...
        self.io = None
        self.config = None

    def dispatch(self, origaddr, frameset):
        'Dummy dispatcher for base class DispatchTarget - for unhandled pyFrameSets'
        self = self # Make pylint happy...
        fstype = frameset.get_framesettype()
        CMAdb.log.info("Received unhandled FrameSet of type [%s] from [%s]" 
        %     (FrameSetTypes.get(fstype)[0], str(origaddr)))
        print ("Received unhandled FrameSet of type [%s] from [%s]" 
        %     (FrameSetTypes.get(fstype)[0], str(origaddr)))
        for frame in frameset.iter():
            frametype = frame.frametype()
            print "\tframe type [%s]: [%s]" \
            %     (FrameTypes.get(frametype)[1], str(frame))

    def setconfig(self, io, config):
        'Save away our IO object and our configuration'
        self.io = io
        self.config = config

    @staticmethod
    def register(classtoregister):
        '''Register the given class in DispatchTarget.dispatchtable
        This function is intended to be used as a decorator.
        This is requires that the class being registered be named
        Dispatch{name-of-message-being-dispatched}
        '''
        cname = classtoregister.__name__
        if not cname.startswith('Dispatch'):
            raise(ValueError('Dispatch class names must start with "Dispatch"'))
        msgname = cname[8:]
        # This is kinda cool!
        DispatchTarget.dispatchtable[FrameSetTypes.get(msgname)[0]] = classtoregister()
        return classtoregister


        
@DispatchTarget.register
class DispatchHBDEAD(DispatchTarget):
    'DispatchTarget subclass for handling incoming HBDEAD FrameSets.'

    def dispatch(self, origaddr, frameset):
        'Dispatch function for HBDEAD FrameSets'
        fstype = frameset.get_framesettype()
        fromdrone = self.droneinfo.find(origaddr)
        CMAdb.log.warning("DispatchHBDEAD: received [%s] FrameSet from [%s] [%s]"
        %      (FrameSetTypes.get(fstype)[0], str(origaddr), fromdrone.designation))
        for frame in frameset.iter():
            frametype = frame.frametype()
            if frametype == FrameTypes.IPPORT:
                deaddrone = self.droneinfo.find(frame.getnetaddr())
                if CMAdb.debug:
                    CMAdb.log.debug("DispatchHBDEAD: [%s] is the guy who died!" % deaddrone)
                deaddrone.death_report('dead', 'HBDEAD packet received', origaddr, frameset)

@DispatchTarget.register
class DispatchHBSHUTDOWN(DispatchTarget):
    'DispatchTarget subclass for handling incoming HBSHUTDOWN FrameSets.'
    def dispatch(self, origaddr, frameset):
        'Dispatch function for HBSHUTDOWN FrameSets'
        fstype = frameset.get_framesettype()
        fsname = FrameSetTypes.get(fstype)[0]
        for frame in frameset.iter():
            frametype = frame.frametype()
            if frametype == FrameTypes.HOSTNAME:
                hostname = frame.getstr()
                fromdrone = self.droneinfo.find(hostname, port=origaddr.port())
                if fromdrone is not None:
                    CMAdb.log.info("System %s at %s reports graceful shutdown."
                    %   (hostname, str(origaddr)))
                    print >> sys.stderr, ("System %s at %s reports graceful shutdown."
                    %   (hostname, str(origaddr)))
                    fromdrone.death_report('dead', fsname, origaddr, frameset)
                else:
                    CMAdb.log.error(
                    "DispatchHBSHUTDOWN: received %s FrameSet from unknown drone %s at [%s]"
                    %   (fsname, hostname, str(origaddr)))
                return
        CMAdb.log.error("DispatchHBSHUTDOWN: received invalid %s FrameSet from drone at [%s]"
        %      (fsname, str(origaddr)))
        CMAdb.log.error("DispatchHBSHUTDOWN: invalid FrameSet: %s", str(frameset))


@DispatchTarget.register
class DispatchSTARTUP(DispatchTarget):
    'DispatchTarget subclass for handling incoming STARTUP FrameSets.'
    def dispatch(self, origaddr, frameset):
        json = None
        addrstr = repr(origaddr)
        fstype = frameset.get_framesettype()
        #print >> sys.stderr, ("DispatchSTARTUP: received [%s] FrameSet from [%s]"
        #%       (FrameSetTypes.get(fstype)[0], addrstr))
        if CMAdb.debug:
            CMAdb.log.debug("DispatchSTARTUP: received [%s] FrameSet from [%s]"
            %       (FrameSetTypes.get(fstype)[0], addrstr))
            #CMAdb.log.debug('Resetting communications to %s/%d' % (origaddr, DEFAULT_FSP_QID))
        self.io.closeconn(DEFAULT_FSP_QID, origaddr)
        for frame in frameset.iter():
            frametype = frame.frametype()
            if frametype == FrameTypes.HOSTNAME:
                sysname = frame.getstr()
                if sysname == CMAdb.nodename:
                    if origaddr.islocal():
                        CMAdb.log.warning("Received STARTUP from local system (%s)" % addrstr)
                    else:
                        addresses = ['127.0.0.1', '::ffff:127.0.0.1', '::1' ]
                        for address in addresses:
                            localhost = pyNetAddr(address)
                            self.io.addalias(localhost, origaddr)
                            CMAdb.log.info("Aliasing %s to %s" % (localhost, origaddr))
            if frametype == FrameTypes.JSDISCOVER:
                json = frame.getstr()
                #print >> sys.stderr,  'GOT JSDISCOVER JSON: [%s] (strlen:%s,framelen:%s)' \
                #% (json, len(json), frame.framelen())
        CMAdb.transaction.add_packet(origaddr, FrameSetTypes.SETCONFIG, (str(self.config), )
        ,   FrameTypes.CONFIGJSON)
        CMAdb.log.info('Drone %s registered from address %s (%s) port %s' 
        %       (sysname, origaddr, addrstr, origaddr.port()))
        drone = self.droneinfo.add(sysname, 'STARTUP packet', port=origaddr.port()
        ,   primary_ip_addr=str(origaddr))
        #print >> sys.stderr, 'DRONE from find: ', drone, type(drone), drone.port

        drone.startaddr = str(origaddr)
        if json is not None:
            drone.logjson(origaddr, json)
        #print >> sys.stderr, 'Joining TheOneRing: ', drone, type(drone), drone.port
        CMAdb.cdb.TheOneRing.join(drone)
        #print >> sys.stderr, 'Requesting Discovery from ', drone
        drone.request_discovery(
                                ('packages',            1603),
                                ('monitoringagents',    3300),
                                ('os',                  0),
                                ('ulimit',              0),
                                ('cpu',                 36000),
                                ('arpcache',            45),
                                ('tcpdiscovery',        3700)
                               )
        #print >> sys.stderr, 'Creating OBJUP event for ', drone
        AssimEvent(drone, AssimEvent.OBJUP)

@DispatchTarget.register
class DispatchJSDISCOVERY(DispatchTarget):
    'DispatchTarget subclass for handling incoming JSDISCOVERY FrameSets.'
    def dispatch(self, origaddr, frameset):
        fstype = frameset.get_framesettype()
        if CMAdb.debug:
            CMAdb.log.debug("DispatchJSDISCOVERY: received [%s] FrameSet from [%s]" 
            %       (FrameSetTypes.get(fstype)[0], repr(origaddr)))
        sysname = None
        for frame in frameset.iter():
            frametype = frame.frametype()
            if frametype == FrameTypes.HOSTNAME:
                sysname = frame.getstr()
            if frametype == FrameTypes.JSDISCOVER:
                json = frame.getstr()
                #print 'JSON received: ', json
                if sysname is None:
                    jsonconfig = pyConfigContext(init=json)
                    sysname = jsonconfig.getstring('host')
                drone = self.droneinfo.find(sysname)
                #print >> sys.stderr, 'FOUND DRONE for %s IS: %s' % (sysname, drone)
                #print >> sys.stderr, 'LOGGING JSON FOR DRONE for %s IS: %s' % (drone, json)
                drone.logjson(origaddr, json)
                sysname = None

@DispatchTarget.register
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
            frametype = frame.frametype()
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
                switchjson = pySwitchDiscovery.decode_discovery(designation, interface
                ,               wallclock, pktstart, pktend)
                if CMAdb.debug:
                    CMAdb.log.debug('Got Link discovery info from %s: %s' \
                    %   (interface, str(switchjson)))
                drone = self.droneinfo.find(designation)
                drone.logjson(origaddr, str(switchjson))
                break

@DispatchTarget.register
class DispatchRSCOPREPLY(DispatchTarget):
    'DispatchTarget subclass for handling incoming RSCOPREPLY FrameSets.'
    GOODTOBAD = 1
    BADTOGOOD = 2
    def dispatch(self, origaddr, frameset):
        fstype = frameset.get_framesettype()
        if CMAdb.debug:
            CMAdb.log.debug("DispatchRSCOPREPLY: received [%s] FrameSet from [%s]"
            %       (FrameSetTypes.get(fstype)[0], str(origaddr)))

        for frame in frameset.iter():
            frametype = frame.frametype()
            if frametype == FrameTypes.RSCJSONREPLY:
                obj = pyConfigContext(frame.getstr())
                MonitorAction.logchange(origaddr, obj)
                return
        CMAdb.log.critical('RSCOPREPLY message from %s did not have a RSCJSONREPLY field'
        %   (str(origaddr)))
