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
from cmaconfig import ConfigFile
from cmadb import CMAdb
from frameinfo import FrameSetTypes, FrameTypes
from AssimCclasses import pyNetAddr, pyConfigContext, pySwitchDiscovery, pyCryptFrame
from AssimCtypes import cryptcurve25519_save_public_key, DEFAULT_FSP_QID
from monitoring import MonitorAction
from assimevent import AssimEvent

class DispatchTarget(object):
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
        print ("Received unhandled FrameSet of type [%d:%s] from [%s]"
        %     (fstype, FrameSetTypes.get(fstype)[0], str(origaddr)))
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
        #fromdrone = self.droneinfo.find(origaddr)
        #fstype = frameset.get_framesettype()
        #CMAdb.log.warning("DispatchHBDEAD: received [%s] FrameSet from [%s] [%s]"
        #%      (FrameSetTypes.get(fstype)[0], str(origaddr), fromdrone.designation))
        for frame in frameset.iter():
            frametype = frame.frametype()
            if frametype == FrameTypes.IPPORT:
                deaddrone = self.droneinfo.find(frame.getnetaddr())
                if deaddrone.status == 'up':
                    CMAdb.log.warning("DispatchHBDEAD: Drone@%s is dead(%s)"
                    %   (frame.getnetaddr(), deaddrone))
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


# pylint: disable=R0914,R0912
@DispatchTarget.register
class DispatchSTARTUP(DispatchTarget):
    'DispatchTarget subclass for handling incoming STARTUP FrameSets.'
    def dispatch(self, origaddr, frameset):
        json = None
        addrstr = repr(origaddr)
        fstype = frameset.get_framesettype()
        localtime = None
        listenaddr = None
        keyid = None
        pubkey = None
        keysize = None

        #print >> sys.stderr, ("DispatchSTARTUP: received [%s] FrameSet from [%s]"
        #%       (FrameSetTypes.get(fstype)[0], addrstr))
        if CMAdb.debug:
            CMAdb.log.debug("DispatchSTARTUP: received [%s] FrameSet from [%s]"
            %       (FrameSetTypes.get(fstype)[0], addrstr))
        if not self.io.connactive(origaddr):
            self.io.closeconn(DEFAULT_FSP_QID, origaddr)
        for frame in frameset.iter():
            frametype = frame.frametype()
            if frametype == FrameTypes.WALLCLOCK:
                localtime = str(frame.getint())
            elif frametype == FrameTypes.IPPORT:
                listenaddr = frame.getnetaddr()
            elif frametype == FrameTypes.HOSTNAME:
                sysname = frame.getstr()
                if sysname == CMAdb.nodename:
                    if origaddr.islocal():
                        CMAdb.log.info("Received STARTUP from local system (%s)" % addrstr)
                    else:
                        addresses = ['127.0.0.1', '::ffff:127.0.0.1', '::1' ]
                        for address in addresses:
                            localhost = pyNetAddr(address)
                            self.io.addalias(localhost, origaddr)
                            CMAdb.log.info("Aliasing %s to %s" % (localhost, origaddr))
            elif frametype == FrameTypes.JSDISCOVER:
                json = frame.getstr()
                #print >> sys.stderr,  'GOT JSDISCOVER JSON: [%s] (strlen:%s,framelen:%s)' \
                #% (json, len(json), frame.framelen())
            elif frametype == FrameTypes.KEYID:
                keyid = frame.getstr()
            elif frametype == FrameTypes.PUBKEYCURVE25519:
                pubkey = frame.framevalue()
                keysize = frame.framelen()

        joininfo = pyConfigContext(init=json)
        origaddr, isNAT = self.validate_source_ip(sysname, origaddr, joininfo, listenaddr)


        CMAdb.log.info('Drone %s registered from address %s (%s) port %s, key_id %s'
        %       (sysname, origaddr, addrstr, origaddr.port(), keyid))
        drone = self.droneinfo.add(sysname, 'STARTUP packet', port=origaddr.port()
        ,   primary_ip_addr=str(origaddr))
        drone.listenaddr = str(listenaddr)  # Seems good to hang onto this...
        drone.isNAT = isNAT                 # ditto...
        # Did they give us the crypto info we need?
        if keyid is None or pubkey is None:
            if CMAdb.debug:
                CMAdb.log.debug('Drone %s registered with keyid %s and pubkey provided: %s'
                %   (self, keyid, pubkey is not None))
        else:
            if drone.key_id == '':
                if not keyid.startswith(sysname + "@@"):
                    CMAdb.log.warning("Drone %s wants to register with key_id %s -- permitted."
                    ,   sysname, keyid)
                if not cryptcurve25519_save_public_key(keyid, pubkey, keysize):
                    raise ValueError("Drone %s public key (key_id %s, %d bytes) is invalid."
                    %   (sysname, keyid, keysize))
            elif drone.key_id != keyid:
                raise ValueError("Drone %s tried to register with key_id %s instead of %s."
                %   (sysname, keyid, drone.key_id))
            drone.set_crypto_identity(keyid=keyid)
            pyCryptFrame.dest_set_key_id(origaddr, keyid)
        #
        # THIS IS HERE BECAUSE OF A PROTOCOL BUG...
        # @FIXME Protocol bug when starting up a connection if our first (this) packet gets lost,
        # then the protocol doesn't retransmit it.
        # More specifically, it seems to clear it out of the queue.
        # This might be CMA bug or a protocol bug.  It's not clear...
        # The packet goes into the queue, but if that packet is lost in transmission, then when
        # we come back around here, it's not in the queue any more, even though it
        # definitely wasn't ACKed.
        # Once this is fixed, this "add_packet" call needs to go *after* the 'if' statement below.
        #
        CMAdb.transaction.add_packet(origaddr, FrameSetTypes.SETCONFIG, (str(self.config), )
        ,   FrameTypes.CONFIGJSON)

        if (localtime is not None):
            if (drone.lastjoin == localtime):
                CMAdb.log.warning('Drone %s [%s] sent duplicate STARTUP' % (sysname, origaddr))
                if CMAdb.debug:
                    self.io.log_conn(origaddr)
                return
            drone.lastjoin = localtime
        #print >> sys.stderr, 'DRONE from find: ', drone, type(drone), drone.port

        drone.startaddr = str(origaddr)
        if json is not None:
            drone.logjson(origaddr, json)
        if CMAdb.debug:
            CMAdb.log.debug('Joining TheOneRing: %s / %s / %s' % (drone, type(drone), drone.port))
        CMAdb.cdb.TheOneRing.join(drone)
        if CMAdb.debug:
            CMAdb.log.debug('Requesting Discovery from  %s' % str(drone))
        discovery_params = []
        for agent in self.config['initial_discovery']:
            params = ConfigFile.agent_params(self.config, 'discovery', agent, sysname)
            params['agent'] = agent
            params['instance'] = '_init_%s' % agent
            discovery_params.append(params)
        if CMAdb.debug:
            CMAdb.log.debug('Discovery details:  %s' % str(discovery_params))
        drone.request_discovery(discovery_params)
        AssimEvent(drone, AssimEvent.OBJUP)

    @staticmethod
    def validate_source_ip(sysname, origaddr, jsobj, listenaddr):
        '''
        This chunk of code is kinda stupid...
        There is a docker/NAT bug where it screws up the source address of multicast packets
        This code detects that that has happened and works around it...
        '''
        # Local addresses aren't NATted, but the code below will think so...
        if origaddr.islocal():
            return origaddr, False
        match = False
        isNAT = False
        jsdata = jsobj['data']
        canonorig = str(pyNetAddr(origaddr).toIPv6())
        primaryip = None
        for ifname in jsdata:
            for ip_netmask in jsdata[ifname]['ipaddrs']:
                ip = ip_netmask.split('/')[0]
                canonip = pyNetAddr(ip, origaddr.port()).toIPv6()
                if str(canonip) == canonorig:
                    match = True
                    break
                ipinfo = jsdata[ifname]['ipaddrs'][ip_netmask]
                if 'default_gw' in jsdata[ifname] and ipinfo.get('name') == ifname:
                    primaryip = canonip
        # FIXME: This currently is set up to work around gratuitous NATting in Docker (bug!)
        # It should evolve to do the right things for real NAT configurations...
        if not match:
            CMAdb.log.warning('Drone %s sent STARTUP packet with NATted source address (%s)'
            %       (sysname, origaddr))
            isNAT = True
            if primaryip is not None:
                if CMAdb.running_under_docker():
                    CMAdb.log.warning('Drone %s STARTUP orig address assumed to be (%s)'
                    %       (sysname, primaryip))
                    CMAdb.log.warning('Presumed to be due to a known Docker bug.')
                    origaddr = primaryip
                    if listenaddr is not None and primaryip.port() != listenaddr.port():
                        CMAdb.log.warning('Drone %s STARTUP port is NATted: Assumed to be (%s)'
                        %       (sysname, listenaddr.port()))
                        origaddr = pyNetAddr(origaddr, port=listenaddr.port())
        return origaddr, isNAT

@DispatchTarget.register
class DispatchHBMARTIAN(DispatchTarget):
    '''DispatchTarget subclass for handling incoming HBMARTIAN FrameSets.
    HBMARTIAN packets occur when a system is receiving unexpected heartbeats from another system.

    There are a few known causes for them:
        - The reporting system was slow to act on a request to expect these heartbeats
        - The MARTIAN source had been erroneously declared dead (network split) with 2 subcases:
            - It is currently marked as dead - we should resurrect it and add to the ring
              mark it as alive, and tell it to stop sending
              UNLESS it's from an HBSHUTDOWN - then it's likely bad timing...
            - It is currently marked as alive - two subcases:
                - the reporting system is one of its partners peers - just ignore this
                - the reporting system is not one of its partners - tell source to stop
                    this can be caused by the system being slower to update
    '''
    def dispatch(self, origaddr, frameset):
        fstype = frameset.get_framesettype()
        if CMAdb.debug:
            CMAdb.log.debug("DispatchHBMARTIAN: received [%s] FrameSet from address %s "
                %       (FrameSetTypes.get(fstype)[0], origaddr))
        reporter = self.droneinfo.find(origaddr) # System receiving the MARTIAN FrameSet
        martiansrcaddr = None
        for frame in frameset.iter():
            frametype = frame.frametype()
            if frametype == FrameTypes.IPPORT:
                martiansrcaddr = frame.getnetaddr()
        martiansrc = self.droneinfo.find(martiansrcaddr) # Source of MARTIAN event
        if CMAdb.debug:
            CMAdb.log.debug("DispatchHBMARTIAN: received [%s] FrameSet from %s/%s about %s/%s"
            %       (FrameSetTypes.get(fstype)[0], reporter, origaddr, martiansrc, martiansrcaddr))
        if martiansrc.status != 'up':
            if martiansrc.reason == 'HBSHUTDOWN':
                # Just bad timing.  All is well...
                return
            CMAdb.log.info('DispatchHBMARTIAN: %s had been erroneously marked %s; reason %s'
            %   (martiansrc, martiansrc.status, martiansrc.reason))
            if CMAdb.debug:
                CMAdb.log.info('DispatchHBMARTIAN: telling %s/%s to stop sending to %s/%s (%s case)'
                %       (martiansrc, martiansrcaddr, reporter, origaddr, martiansrc.status))
            martiansrc.status='up'
            martiansrc.reason='HBMARTIAN'
            martiansrc.send_hbmsg(martiansrcaddr, FrameSetTypes.STOPSENDEXPECTHB, (origaddr,))
            CMAdb.cdb.TheOneRing.join(martiansrc)
            AssimEvent(martiansrc, AssimEvent.OBJUP)
            return
        # OK, it's alive...
        if CMAdb.cdb.TheOneRing.are_partners(reporter, martiansrc):
            if CMAdb.debug:
                CMAdb.log.debug('DispatchHBMARTIAN: Ignoring msg from %s about %s'
                %   (reporter, martiansrc))
        else:
            if CMAdb.debug:
                CMAdb.log.info('DispatchHBMARTIAN: telling %s/%s to stop sending to %s/%s (%s case)'
                %       (martiansrc, martiansrcaddr, reporter, origaddr, martiansrc.status))
            # This probably isn't necessary in most cases, but it doesn't hurt anything
            # if the offender is just slow to update, he'll catch up...
            martiansrc.send_hbmsg(martiansrcaddr, FrameSetTypes.STOPSENDEXPECTHB, (origaddr,))

class DispatchHBBACKALIVE(DispatchTarget):
    '''DispatchTarget subclass for handling incoming HBHBBACKALIVE FrameSets.
    HBBACKALIVE packets occur when a system hears a heartbeat from a system it thought was dead.
    '''
    def dispatch(self, origaddr, frameset):
        fstype = frameset.get_framesettype()
        if CMAdb.debug:
            CMAdb.log.debug("DispatchHBBACKALIVE: received [%s] FrameSet from address %s"
                %       (FrameSetTypes.get(fstype)[0], origaddr))
        reporter = self.droneinfo.find(origaddr) # System receiving the MARTIAN FrameSet
        alivesrcaddr = None
        for frame in frameset.iter():
            frametype = frame.frametype()
            if frametype == FrameTypes.IPPORT:
                alivesrcaddr = frame.getnetaddr()
        alivesrc = self.droneinfo.find(alivesrcaddr) # Source of HBBACKALIVE event
        if CMAdb.debug:
            CMAdb.log.debug("DispatchHBBACKALIVE: received [%s] FrameSet from %s/%s about %s/%s"
            %       (FrameSetTypes.get(fstype)[0], reporter, origaddr, alivesrc, alivesrcaddr))
        if alivesrc.status != 'up':
            if alivesrc.reason == 'HBSHUTDOWN':
                # Just bad timing.  All is well...
                return
            CMAdb.log.info('DispatchHBBACKALIVE: %s had been erroneously marked %s; reason %s'
            %   (alivesrc, alivesrc.status, alivesrc.reason))
            alivesrc.status='up'
            alivesrc.reason='HBBACKALIVE'
            CMAdb.cdb.TheOneRing.join(alivesrc)
            AssimEvent(alivesrc, AssimEvent.OBJUP)

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

@DispatchTarget.register
class DispatchCONNSHUT(DispatchTarget):
    'Class for handling (ignoring) CONNSHUT packets'
    def dispatch(self, origaddr, frameset):
        origaddr = origaddr
        frameset = frameset
