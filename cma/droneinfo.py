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
#
'''
We implement the DroneInfo class - which implements all the properties of
drones as a Python class.
'''
import weakref, traceback, time, os
from .cmadb import CMAdb

from .frameinfo import FrameSetTypes, FrameTypes
from .AssimCclasses import pyNetAddr, pyFrameSet, pyCstringFrame, pyConfigContext, \
        pyIntFrame, pyIpPortFrame, DEFAULT_FSP_QID
from py2neo import neo4j, rest
from .hbring import HbRing

class DroneInfo:
    'Everything about Drones - endpoints that run our nanoprobes'
    _droneweakrefs = {}
    _JSONprocessors = {}
    def __init__(self, designation, port=None, **kw):
        self.io = CMAdb.io
        self.status = '(unknown)'
        self.reason = '(initialization)'
        if isinstance(designation, neo4j.Node):
            self.node = designation
        else:
            #print >>sys.stderr, 'New DroneInfo(designation = %s", kw=%s)' \
            #%   (designation, str(**kw))
            self.node = CMAdb.cdb.new_drone(designation, **kw)
        DroneInfo._droneweakrefs[designation] = weakref.ref(self)
        if port is not None:
            self.setport(port)
        elif 'port' in self.node:
            self.port = self.node['port']

    def __getitem__(self, key):
        return self.node[key]

    def __delitem__(self, key):
        del self.node[key]

    def __setitem__(self, key, value):
        self.node[key] = value

    def __len__(self, key, value):
        return len(self.node)


    def getport(self):
        '''Return the port we talk to this drone on'''
        if not hasattr(self, 'port'):
            self.port = self.node['port']
        return self.port

    def setport(self, port):
        '''Set the port we talk to this drone on'''
        self.port = port
        self.node['port'] = port
        
   
    def logjson(self, jsontext):
        'Process and save away JSON discovery data'
        jsonobj = pyConfigContext(jsontext)
        if not jsonobj.has_key('discovertype') or not jsonobj.has_key('data'):
            CMAdb.log.warning('Invalid JSON discovery packet: %s' % jsontext)
            return
        dtype = jsonobj['discovertype']
        #print "Saved discovery type %s for endpoint %s." % \
        #   (dtype, self.designation)
        designation = self.node['name']
        jsonname = 'JSON_' + dtype
        if jsonname in self.node:
            if self.node[jsonname] == jsontext:
                # A really cheap optimization for reboots, etc.
                if CMAdb.debug:
                    CMAdb.log.debug(
                    'DroneInfo.logjson: JSON text for %s/%s already processed - ignoring.'
                    %       (designation, dtype))
                return
        self.node[jsonname] = jsontext
        if dtype in DroneInfo._JSONprocessors:
            if CMAdb.debug:
                CMAdb.log.debug('Processing %s JSON data from %s into graph.'
                %       (dtype, designation))
            DroneInfo._JSONprocessors[dtype](self, jsonobj)
            if CMAdb.debug:
                CMAdb.log.debug('Processed %s JSON data from %s into graph.'
                %   (dtype, designation))
        else:
            CMAdb.log.info('Stored %s JSON data from %s without processing.'
            %   (dtype, designation))

    def add_netconfig_addresses(self, jsonobj, **kw):
        '''Save away the network configuration data we got from JSON discovery.
        This includes all our NICs, their MAC addresses, all our IP addresses and so on
        for any non-loopback interface.  Whee!
        In theory we could make a giant 'create' for everything and do all the db creation
        in one swell foop - or at most two...
        '''
        # Ought to protect this code by try blocks...
        data = jsonobj['data'] # The data portion of the JSON message
        primaryip = None
        for ifname in data.keys(): # List of interfaces just below the data section
            ifinfo = data[ifname]
            isprimaryif = ifinfo.has_key('default_gw')
            #print 'IFINFO: [%s]' % str(ifinfo)
            if not ifinfo.has_key('address'):
                continue
            ifaddr = ifinfo['address']
            #print 'ADDRESS: [%s]' % str(ifaddr)
            if ifaddr.startswith('00:00:00:'):
                continue
            nicnode = CMAdb.cdb.new_nic(ifname, ifaddr, self, isprimaryif=isprimaryif, **kw)
            iptable = ifinfo['ipaddrs'] # look in the 'ipaddrs' section
            for ip in iptable.keys():   # keys are 'ip/mask' in CIDR format
                ipinfo = iptable[ip]
                ipname = ':::INVALID:::'
                if ipinfo.has_key('name'):
                    ipname = ipinfo['name']
                if ipinfo['scope'] != 'global':
                    continue
                iponly = ip.split('/')[0] # other part is mask
                netaddr = pyNetAddr(iponly).toIPv6()
                if netaddr.islocal():
                    continue
                iponly = str(netaddr)
                isprimaryip = False
                ## FIXME: May want to consider looking at 'brd' for broadcast as well...
                ## otherwise this can be a little fragile...
                if isprimaryif and primaryip == None and ipname == ifname:
                    isprimaryip = True
                    primaryip = iponly
                    #print >>sys.stderr, 'PRIMARY IP is %s' % iponly
                ipnode = CMAdb.cdb.new_ipaddr(nicnode, iponly, ifname=ifname
                ,       hostname = self.node['name'])
                # Save away whichever IP address is our primary IP address...
                if isprimaryip:
                    rel = self.node.get_single_relationship(neo4j.Direction.OUTGOING
                    ,   'primaryip')
                    if rel is not None and rel.end_node.id != ipnode.id:
                        rel.delete()
                        rel = None
                    if rel is None:
                        CMAdb.cdb.db.get_or_create_relationships((self.node, 'primaryip', ipnode),)

    def add_tcplisteners(self, jsonobj, **keywords):
        '''Add TCP listeners and/or clients.  Same or separate messages - we don't care.'''
        data = jsonobj['data'] # The data portion of the JSON message
        keywords = keywords # Don't really need this argument...
        if CMAdb.debug:
            CMAdb.log.debug('add_tcplisteners(data=%s)' % data)
            CMAdb.log.debug('Calling get_related_nodes(%d, %s)'
            %       (neo4j.Direction.INCOMING, CMAdb.REL_iphost))
        allourips = self.node.get_related_nodes(neo4j.Direction.INCOMING, CMAdb.REL_iphost)
        if CMAdb.debug:
            CMAdb.log.debug('Processing keys(%s)' % data.keys())
        for procname in data.keys(): # List of names of processes...
            if CMAdb.debug:
                CMAdb.log.debug('Processing key(%s)' % procname)
            procinfo = data[procname]
            if CMAdb.debug:
                CMAdb.log.debug('Processing procinfo(%s)' % procinfo)
            ipproc = CMAdb.cdb.new_ipproc(procname, procinfo, self.node)
            if CMAdb.debug:
                CMAdb.log.debug('procinfo(%s) - ipproc created=> %s'
            %   (procinfo, ipproc))
            if 'listenaddrs' in procinfo:
                if CMAdb.debug:
                    CMAdb.log.debug('listenaddrs is in (%s)' % procinfo)
                tcpipportinfo = procinfo['listenaddrs']
                for tcpipport in tcpipportinfo.keys():
                    if CMAdb.debug:
                        CMAdb.log.debug('Processing tcpipport(listenaddrs)(%s)' % tcpipport)
                    self.add_tcpipports(True, tcpipportinfo[tcpipport], ipproc, allourips)
            if 'clientaddrs' in procinfo:
                if CMAdb.debug:
                    CMAdb.log.debug('clientaddrs is in (%s)' % procinfo)
                tcpipportinfo = procinfo['clientaddrs']
                for tcpipport in tcpipportinfo.keys():
                    if CMAdb.debug:
                        CMAdb.log.debug('Processing tcpipport(clientaddrs)(%s)' % tcpipport)
                    self.add_tcpipports(False, tcpipportinfo[tcpipport], ipproc, None)

    def add_tcpipports(self, isserver, jsonobj, ipproc, allourips):
        '''We create tcpipports objects that correspond to the given json object in
        the context of the set of IP addresses that we support - including support
        for the ANY ipv4 and ipv6 addresses'''
        netaddr = pyNetAddr(str(jsonobj['addr'])).toIPv6()
        if netaddr.islocal():
            CMAdb.log.warning('add_tcpipports("%s"): address is local' % netaddr)
            return
        addr = str(netaddr)
        port = jsonobj['port']
        netaddrandport = pyNetAddr(str(netaddr))
        netaddrandport.setport(port)
        name = str(netaddrandport)
        # Were we given the ANY address?
        if isserver and (addr == '::' or addr == '::ffff:0.0.0.0'):
            for ipaddr in allourips:
                ipnetaddr = (pyNetAddr(ipaddr['name']).toIPv6())
                ipnetaddr.setport(port)
                name = str(ipnetaddr)
                CMAdb.cdb.new_tcpipport(name, isserver
                ,   jsonobj, self.node, ipproc, ipaddr)
        elif isserver:
            for ipaddr in allourips:
                ipaddrname = ipaddr['name']
                ipnetaddr = (pyNetAddr(str(ipaddrname)).toIPv6())
                if ipnetaddr == netaddr:
                    CMAdb.cdb.new_tcpipport(name, isserver, jsonobj, self.node, ipproc, ipaddr)
                    return
            raise ValueError('IP Address mismatch for Drone %s - could not find address %s'
                            % (self.node['name'], addr))
        else:
            netaddr.setport(port)
            ipaddr = CMAdb.cdb.new_ipaddr(None, addr)
            CMAdb.cdb.new_tcpipport(str(netaddr), isserver, jsonobj, None, ipproc, ipaddr)

    def add_linkdiscovery(self, jsonobj, **keywords):
        'Add Low Level (Link Level) discovery data to the database'
        keywords = keywords # don't need these
        data = jsonobj['data']
        if 'ChassisId' not in data:
            CMAdb.log.warning('Chassis ID missing from discovery data from switch [%s]'
            %   (str(data)))
            return
        chassisid = data['ChassisId']
        attrs = {}
        for key in data.keys():
            if key == 'ports':
                continue
            value = data[key]
            if isinstance(value, pyNetAddr):
                value = str(value)
            attrs[key] = value
        switch = CMAdb.cdb.new_switch(chassisid, **attrs)
        if ('ManagementAddress' in attrs):
            mgmtaddr = attrs['ManagementAddress']
            adminnic = CMAdb.cdb.new_nic('(adminNIC)', chassisid, switch)
            CMAdb.cdb.new_ipaddr(adminnic, mgmtaddr)
        ports = data['ports']
        for portname in ports.keys():
            attrs = {}
            thisport = ports[portname]
            for key in thisport.keys():
                value = thisport[key]
                if isinstance(value, pyNetAddr):
                    value = str(value)
                attrs[key] = value
            if 'sourceMAC' in thisport:
                nicmac = thisport['sourceMAC']
            else:
                nicmac = chassisid # Hope that works ;-)
            nicnode = CMAdb.cdb.new_nic(portname, nicmac, switch, **attrs)
            try:
                assert thisport['ConnectsToHost'] == self.node['name']
                matchnic = thisport['ConnectsToInterface']
                niclist = self.node.get_related_nodes(neo4j.Direction.INCOMING, CMAdb.REL_nicowner)
                for dronenic in niclist:
                    if dronenic['nicname'] == matchnic:
                        nicnode.create_relationship_from(dronenic, CMAdb.REL_wiredto)
                        break
            except KeyError:
                CMAdb.log.error('OOPS! got an exception...')


    def primary_ip(self, ring=None):
        '''Return the "primary" IP for this host'''
        ring = ring # should eventually use the ring if it's supplied
        # Should this come from our initial contact with the node?
        primaryip = self.node.get_single_related_node(neo4j.Direction.OUTGOING, 'primaryip')
        return str(primaryip['name'])

    def select_ip(self, ring=None):
        '''Select an appropriate IP address for talking to a partner on this ring
        or our primary IP if ring is None'''
        ring = ring # should eventually use the ring if it's supplied
        # Current code is not really good enough for the long term,
        # but is good enough for now...
        # In particular, when talking on a particular switch ring, or
        # subnet ring, we want to choose an IP that's on that subnet,
        # and preferably on that particular switch for a switch-level ring.
        # For TheOneRing, we want their primary IP address.
        return self.primary_ip()
    
    def send_hbmsg(self, dest, fstype, addrlist):
        '''Send a message with an attached pyNetAddr list - each including port numbers'
           This is intended primarily for start or stop heartbeating messages.'''
        fs = pyFrameSet(fstype)
        for addr in addrlist:
            if addr is None:
                continue
            aframe = pyIpPortFrame(FrameTypes.IPPORT, addrstring=addr)
            fs.append(aframe)
        self.io.sendreliablefs(dest, (fs,))

    def death_report(self, status, reason, fromaddr, frameset):
        'Process a death/shutdown report for us.  RIP us.'
        frameset = frameset # We don't use the frameset at this point in time
        if reason != 'HBSHUTDOWN':
            CMAdb.log.info('Node %s has been reported as %s by address %s. Reason: %s'
            %   (self.node['name'], status, str(fromaddr), reason))
        self.status = status
        self.reason = reason
        self.node['status'] = status
        self.node['reason'] = reason
        self.node['statustime'] = int(round(time.time() * 1000))
        self.node['iso8601'] = time.strftime('%Y-%m-%d %H:%M:%S')
        # There is a need for us to be a little more sophisticated
        # in terms of the number of peers this particular drone had
        # It's here in this place that we will eventually add the ability
        # to distinguish death of a switch or subnet or site from death of a single drone
        rellist = self.node.get_relationships(direction=neo4j.Direction.OUTGOING)
        for rel in rellist:
            try:
                if rel.type.startswith(HbRing.memberprefix):
                    ringname = rel.end_node['name']
                    if CMAdb.debug:
                        CMAdb.log.debug('%s was a member of ring %s' % (self, ringname))
                    HbRing.ringnames[ringname].leave(self)
                    # We can't just break out - we might belong to more than one ring
            except rest.ResourceNotFound:
                # OOPS! The leave(self) call above must have deleted it...
                pass
            
        deadip = pyNetAddr(self.primary_ip(), port=self.getport())
        if CMAdb.debug:
            CMAdb.log.debug('Closing connection to %s/%d' % (deadip, DEFAULT_FSP_QID))
        self.io.closeconn(DEFAULT_FSP_QID, deadip)



    def start_heartbeat(self, ring, partner1, partner2=None):
        '''Start heartbeating to the given partners.
        We insert ourselves between partner1 and partner2.
        We only use forward links - because we can follow them in both directions in Neo4J.
        So, we need to create a forward link from partner1 to us and from us to partner2 (if any)
        '''
        ouraddr = pyNetAddr(self.primary_ip(), port=self.getport())
        partner1addr = pyNetAddr(partner1.select_ip(ring), port=partner1.getport())
        if partner2 is not None:
            partner2addr = pyNetAddr(partner2.select_ip(ring), port=partner2.getport())
        else:
            partner2addr = None
        if CMAdb.debug:
            CMAdb.log.debug('STARTING heartbeat(s) from %s [%s] to %s [%s] and %s [%s]' %
                (self, ouraddr, partner1, partner1addr, partner2, partner2addr))
        self.send_hbmsg(ouraddr, FrameSetTypes.SENDEXPECTHB, (partner1addr, partner2addr))

    def stop_heartbeat(self, ring, partner1, partner2=None):
        '''Stop heartbeating to the given partners.'
        We don't know which node is our forward link and which our back link,
        but we need to remove them either way ;-).
        '''
        ouraddr = pyNetAddr(self.primary_ip(), port=self.getport())
        partner1addr = pyNetAddr(partner1.select_ip(ring), port=partner1.getport())
        if partner2 is not None:
            partner2addr = pyNetAddr(partner2.select_ip(ring), port=partner2.getport())
        else:
            partner2addr = None
        # Stop sending the heartbeat messages between these (former) peers
        if CMAdb.debug:
            CMAdb.log.debug('STOPPING heartbeat(s) from %s [%s] to %s [%s] and %s [%s]' % 
                (self, ouraddr, partner1, partner1addr, partner2, partner2addr))
        self.send_hbmsg(ouraddr, FrameSetTypes.STOPSENDEXPECTHB, (partner1addr, partner2addr))

    def request_discovery(self, *args): ##< A vector of arguments formed like this:
        ##< instance       Which (unique) discovery instance is this?
        ##< interval = 0     How often to perform it?
        ##< json = None):    JSON string (or ConfigContext) describing discovery
        ##<                If json is None, then instance is used for JSON type
        '''Send our drone a request to perform discovery
        We send a           DISCNAME frame with the instance name
        then an optional    DISCINTERVAL frame with the repeat interval
        then a              DISCJSON frame with the JSON data for the discovery operation.
        '''
        fs = pyFrameSet(FrameSetTypes.DODISCOVER)
        if type(args[0]) is str:
            if len(args) == 1:
                args = ((args[0], 0, None),)
            elif len(args) == 2:
                args = ((args[0], args[1], None),)
            elif len(args) == 3:
                args = ((args[0], args[1], args[2]),)
            else:
                raise ValueError('Incorrect argument length: %d vs 1, 2 or 3' % len(args))

        for ourtuple in args:
            if len(ourtuple) != 2 and len(ourtuple) != 3:
                raise ValueError('Incorrect argument tuple length: %d vs 2 or 3 [%s]'
                %        (len(ourtuple), args))
            instance = ourtuple[0]
            interval = ourtuple[1]
            json = None
            if len(ourtuple) == 3:
                json = ourtuple[2]
            discname = pyCstringFrame(FrameTypes.DISCNAME)
            #print >>sys.stderr, 'SETTING VALUE TO: (%s)' % instance
            discname.setvalue(instance)
            fs.append(discname)
            if interval is not None and interval > 0:
                discint = pyIntFrame(FrameTypes.DISCINTERVAL, intbytes=4, initval=int(interval))
                fs.append(discint)
            if isinstance(json, pyConfigContext):
                json = str(json)
            elif json is None:
                json = instance
            if not json.startswith('{'):
                json = '{"type":"%s", "parameters":{}}' % json
            jsonframe = pyCstringFrame(FrameTypes.DISCJSON)
            jsonframe.setvalue(json)
            fs.append(jsonframe)
        # This doesn't work if the client has bound to a VIP
        ourip = self.primary_ip()    # meaning select our primary IP
        ourip = pyNetAddr(ourip)
        ourip.setport(self.getport())
        self.io.sendreliablefs(ourip, (fs,))
        if CMAdb.debug:
            CMAdb.log.debug('Sent Discovery request(%s, %s) to %s Framesets: %s'
            %	(instance, str(interval), str(ourip), str(fs)))


    def __str__(self):
        'Give out our designation'
        return 'Drone(%s)' % self.node['name']

    @staticmethod
    def find(designation, port=None):
        'Find a drone with the given designation or IP address, or Neo4J node.'
        ret = None
        desigstr = str(designation)
        if isinstance(designation, str):
            drone = None
            if designation in DroneInfo._droneweakrefs:
                drone = DroneInfo._droneweakrefs[designation]()
            if drone is None:
                drone = DroneInfo(designation, port=port)
            assert drone.node['name'] == designation
            return drone
        if isinstance(designation, pyNetAddr):
            dport = None
            desigport = designation.port()
            if desigport is not None and desigport > 0:
                dport = desigport
            desig = designation.toIPv6(port=0)
            #desig=designation
            desigstr = str(desig)
            #Note that we now do everything by IPv6 addresses...
            ipaddrs = CMAdb.cdb.ipindex.get(CMAdb.NODE_ipaddr, desigstr)
            for ip in ipaddrs:
                # Shouldn't have duplicates, but they happen...
                # FIXME: Think about how to manage duplicate IP addresses...
                # Do we really want to be looking up just by IP addresses here?
                node = ip.get_single_related_node(neo4j.Direction.OUTGOING, CMAdb.REL_iphost)
                return DroneInfo.find(node, port=dport)
            if CMAdb.debug:
                CMAdb.log.warn('Could not find IP NetAddr address in Drone.find... %s [%s] [%s]' % (
                    str(designation), desigstr, type(designation)))
        elif isinstance(designation, neo4j.Node):
            nodedesig = designation['name']
            if nodedesig in DroneInfo._droneweakrefs:
                ret = DroneInfo._droneweakrefs[nodedesig]()
                if ret is not None:
                    return ret
            return DroneInfo(designation)
           
        if CMAdb.debug:
            CMAdb.log.debug("DESIGNATION (%s) = %s" % (designation, desigstr))
        if desigstr in DroneInfo._droneweakrefs:
            ret = DroneInfo._droneweakrefs[designation]()
        if ret is None:
            if CMAdb.debug:
                CMAdb.log.warn('drone.find(%s) (%s) (%s) => returning None' % (
                    str(designation), desigstr, type(designation)))
                if isinstance(designation, str):
                    CMAdb.log.warn('drone.find(%s) (%s) (string) => returning None' % (
                        str(designation), desigstr))
                if isinstance(designation, pyNetAddr):
                    CMAdb.log.warn('drone.find(%s) (%s) (pyNetAddr) => returning None' % (
                        str(designation), desigstr))
                tblist = traceback.extract_stack()
                #tblist = traceback.extract_tb(trace, 20)
                CMAdb.log.info('======== Begin missing IP Traceback ========')
                for tbelem in tblist:
                    (filename, line, funcname, text) = tbelem
                    filename = os.path.basename(filename)
                    CMAdb.log.info('%s.%s:%s: %s'% (filename, line, funcname, text))
                CMAdb.log.info('======== End missing IP Traceback ========')
        return ret

    @staticmethod
    def add(designation, reason, status='up', port=None):
        'Add a drone to our set unless it is already there.'
        ret = None
        if designation in DroneInfo._droneweakrefs:
            ret = DroneInfo._droneweakrefs[designation]()
        if ret is None:
            ret = DroneInfo.find(designation, port=port)
        if ret is None:
            ret = DroneInfo(designation, port=port)
        ret.node['reason'] = reason
        ret.node['status'] = status
        ret.node['statustime'] = int(round(time.time() * 1000))
        ret.node['iso8601'] = time.strftime('%Y-%m-%d %H:%M:%S')
        if port is not None:
            ret.setport(port)
        return ret

    @staticmethod
    def add_json_processors(*args):
        "Register (add) all the json processors we've been given as arguments"
        for ourtuple in args:
            DroneInfo._JSONprocessors[ourtuple[0]] = ourtuple[1]

DroneInfo.add_json_processors(('netconfig', DroneInfo.add_netconfig_addresses),)
DroneInfo.add_json_processors(('tcplisteners', DroneInfo.add_tcplisteners),)
DroneInfo.add_json_processors(('tcpclients', DroneInfo.add_tcplisteners),)
DroneInfo.add_json_processors(('#LinkDiscovery', DroneInfo.add_linkdiscovery),)
