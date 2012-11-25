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
import weakref
from cmadb import CMAdb
from frameinfo import *
from AssimCclasses import *
from py2neo import neo4j
from hbring import HbRing
class DroneInfo:
    'Everything about Drones - endpoints that run our nanoprobes'
    _droneweakrefs = {}
    _JSONprocessors = {}
    def __init__(self, designation, node=None, **kw):
        self.io = CMAdb.io
        if isinstance(designation, neo4j.Node):
            self.node = designation
        else:
            #print >>sys.stderr, 'New DroneInfo(designation = %s", kw=%s)' % (designation, str(**kw))
            self.node = CMAdb.cdb.new_drone(designation, **kw)
        DroneInfo._droneweakrefs[designation] = weakref.ref(self)
        

    def __getitem__(self, key):
       return self.node[key]

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
        self.node['JSON_' + dtype] = jsontext
        if dtype in DroneInfo._JSONprocessors:
            if CMAdb.debug: CMAdb.log.debug('Processed %s JSON data from %s into graph.' % (dtype, designation))
            DroneInfo._JSONprocessors[dtype](self, jsonobj)
        else:
            CMAdb.log.info('Stored %s JSON data from %s without processing.' % (dtype, designation))

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
            isprimaryif= ifinfo.has_key('default_gw')
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
                (iponly,mask) = ip.split('/')
                isprimaryip = False
                ## FIXME: May want to consider looking at 'brd' for broadcast as well...
                ## otherwise this can be a little fragile...
                if isprimaryif and primaryip == None and ipname == ifname:
                    isprimaryip = True
                    primaryip = iponly
                    #print >>sys.stderr, 'PRIMARY IP is %s' % iponly
                ipnode = CMAdb.cdb.new_IPaddr(nicnode, iponly, ifname=ifname, hostname=self.node['name'])
                # Save away whichever IP address is our primary IP address...
                if isprimaryip:
                    rel = self.node.get_single_relationship(neo4j.Direction.OUTGOING, 'primaryip')
                    if rel is not None and rel.end_node.id != ipnode.id:
                        rel.delete()
                        rel = None
                    if rel is None:
                      CMAdb.cdb.db.relate((self.node, 'primaryip', ipnode),)

    def add_tcplisteners(self, jsonobj, **kw):
        '''Add TCP listeners and/or clients.  Same or separate messages - we don't care.'''
        data = jsonobj['data'] # The data portion of the JSON message
        primaryip = None
        allourips = self.node.get_related_nodes(neo4j.Direction.INCOMING, CMAdb.REL_iphost)
        for procname in data.keys(): # List of names of processes...
            procinfo = data[procname]
            ipproc = CMAdb.cdb.new_ipproc(procname, procinfo, self.node)
            if 'listenaddrs' in procinfo:
                tcpipportinfo = procinfo['listenaddrs']
                for tcpipport in tcpipportinfo.keys():
                    self.add_tcpipports(True, tcpipportinfo[tcpipport], ipproc, allourips)
            if 'clientaddrs' in procinfo:
                tcpipportinfo = procinfo['clientaddrs']
                for tcpipport in tcpipportinfo.keys():
                    self.add_tcpipports(False, tcpipportinfo[tcpipport], ipproc, None)

    def add_tcpipports(self, isserver, jsonobj, ipproc, allourips):
        '''We create tcpipports objects that correspond to the given json object in
        the context of the set of IP addresses that we support - including support
        for the ANY ipv4 and ipv6 addresses'''
        addr = str(jsonobj['addr'])
        port = jsonobj['port']
        name = addr + ':' + str(port)
        # Were we given the ANY address?
        if isserver and (addr == '0.0.0.0' or addr == '::'):
            for ipaddr in allourips:
                name = ipaddr['name'] + ':' + str(port)
                tcpipport = CMAdb.cdb.new_tcpipport(name, isserver, jsonobj, self.node, ipproc, ipaddr)
        elif isserver:
            for ipaddr in allourips:
                if ipaddr['name'] == addr:
                    CMAdb.cdb.new_tcpipport(name, isserver, jsonobj, self.node, ipproc, ipaddr)
                    return
            raise ValueError('IP Address mismatch for Drone %s - could not find address %s'
                            % (self.node['name'], addr))
        else:
            name = addr + ':' + str(port)
            ipaddr = CMAdb.cdb.new_IPaddr(None, addr)
            CMAdb.cdb.new_tcpipport(name, isserver, jsonobj, None, ipproc, ipaddr)

    def add_linkdiscovery(self, jsonobj, **kw):
        data = jsonobj['data']
        if 'ChassisId' not in data:
            CMAdb.log.warning('Chassis ID missing from discovery data from switch [%s]' % (str(data)))
            return
        ChassisId = data['ChassisId']
        attrs = {}
        for key in data.keys():
            if key == 'ports':  continue
            value = data[key]
            if isinstance(value, pyNetAddr):
                value = str(value)
            attrs[key] = value
        switch = CMAdb.cdb.new_switch(ChassisId, **attrs)
        if ('ManagementAddress' in attrs):
            mgmtaddr = attrs['ManagementAddress']
            adminnic = CMAdb.cdb.new_nic('(adminNIC)', ChassisId, switch)
            CMAdb.cdb.new_IPaddr(adminnic, mgmtaddr)
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
                nicmac = ChassisId # Hope that works ;-)
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
                pass




    def primary_ip(self, ring=None):
        '''Return the "primary" IP for this host'''
        # Should this come from our initial contact with the node?
        primaryIP = self.node.get_single_related_node(neo4j.Direction.OUTGOING, 'primaryip')
        return str(primaryIP['name'])

    def select_ip(self, ring=None):
        '''Select an appropriate IP address for talking to a partner on this ring
        or our primary IP if ring is None'''
        # Current code is not really good enough for the long term,
        # but is good enough for now...
        # In particular, when talking on a particular switch ring, or
        # subnet ring, we want to choose an IP that's on that subnet,
        # and preferably on that particular switch for a switch-level ring.
        # For TheOneRing, we want their primary IP address.
        return self.primary_ip()
    
    def send_hbmsg(self, dest, fstype, port, addrlist):
        '''Send a message with an attached address list and optional port.
           This is intended primarily for start or stop heartbeating messages.'''
        fs = pyFrameSet(fstype)
        pframe = None
        if port is not None and port > 0 and port < 65536:
           pframe = pyIntFrame(FrameTypes.PORTNUM, intbytes=2, initval=int(port))
        for addr in addrlist:
            if addr is None: continue
            if pframe is not None:
                fs.append(pframe)
            aframe = pyAddrFrame(FrameTypes.IPADDR, addrstring=addr)
            fs.append(aframe)
        if type(dest) is str or type(dest) is unicode:
            dest = pyNetAddr(dest)
            dest.setport(self.port)
        self.io.sendframesets(dest, (fs,))

    def death_report(self, status, reason, fromaddr, frameset):
        'Process a death/shutdown report for us.  RIP us.'
        CMAdb.log.warning('Node %s has been reported as %s by address %s. Reason: %s'
        %   (self.node['name'], status, str(fromaddr), reason))
        self.status = status
        self.reason = reason
        self.node['status'] = status
        self.node['reason'] = reason
        # There is a need for us to be a little more sophisticated
        # in terms of the number of peers this particular drone had
        # It's here in this place that we will eventually add the ability
        # to distinguish death of a switch or subnet or site from death of a single drone
        rellist = self.node.get_relationships(direction=neo4j.Direction.OUTGOING)
        for rel in rellist:
            if rel.type.startswith(HbRing.memberprefix):
                ringname = rel.end_node['name']
                if True or CMAdb.debug:
                    CMAdb.log.debug('Drone %s is (was) a member of ring %s' % (self, ringname))
                HbRing.ringnames[ringname].leave(self)


    def start_heartbeat(self, ring, partner1, partner2=None):
        '''Start heartbeating to the given partners.
        We insert ourselves between partner1 and partner2.
        We only use forward links - because we can follow them in both directions in Neo4J.
        So, we need to create a forward link from partner1 to us and from us to partner2 (if any)
        '''
        ourip = self.select_ip(ring)
        partner1ip = partner1.select_ip(ring)
        if partner2 is not None:
            partner2ip = partner2.select_ip(ring)
            partner2port = partner2.port
        else:
            partner2ip = None
            partner2port = None
        if True or CMAdb.debug:
            CMAdb.log.debug('STARTING heartbeat(s) from %s [%s:%s] to %s [%s:%s] and %s [%s:%s]' %
                (self, ourip, self.port, partner1, partner1ip, partner1.port, partner2, partner2ip, partner2port))
	if partner2 is None or partner2.port == partner1.port:
        	self.send_hbmsg(ourip, FrameSetTypes.SENDEXPECTHB, partner1.port, (partner1ip, partner2ip))
	else:
        	self.send_hbmsg(ourip, FrameSetTypes.SENDEXPECTHB, partner1.port, (partner1ip, None))
        	self.send_hbmsg(ourip, FrameSetTypes.SENDEXPECTHB, partner2port, (partner2ip, None))

    def stop_heartbeat(self, ring, partner1, partner2=None):
        '''Stop heartbeating to the given partners.'
        We don't know which node is our forward link and which our back link,
        but we need to remove them either way ;-).
        '''
        ourip = self.select_ip(ring)
        partner1ip = partner1.select_ip(ring)
        if partner2 is not None:
            partner2ip = partner2.select_ip(ring)
        else:
            partner2ip = None
        # Stop sending the heartbeat messages between these (former) peers
        if True or CMAdb.debug:
            CMAdb.log.debug('STOPPING heartbeat(s) from %s [%s] to %s [%s] and %s [%s]' % 
                (self, ourip, partner1, partner1ip, partner2, partner2ip))
        #self.send_hbmsg(ourip, FrameSetTypes.SENDEXPECTHB, 0, (partner1ip, partner2ip))
        self.send_hbmsg(ourip, FrameSetTypes.STOPSENDEXPECTHB, None, (partner1ip, partner2ip))

    def request_discovery(self, *args): ##< A vector of arguments formed like this:
        ##< instance       Which (unique) discovery instance is this?
        ##< interval=0     How often to perform it?
        ##< json=None):    JSON string (or ConfigContext) describing discovery
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
               raise ValueError('Incorrect argument length: %d vs 1,2 or 3' % len(args))

        for tuple in args:
            if len(tuple) != 2 and len(tuple) != 3:
               raise ValueError('Incorrect argument tuple length: %d vs 2 or 3 [%s]' % (len(tuple), args))
            instance = tuple[0]
            interval = tuple[1]
            json = None
            if len(tuple) == 3: json = tuple[2]

            discname = pyCstringFrame(FrameTypes.DISCNAME)
            #print >>sys.stderr, 'SETTING VALUE TO: (%s)' % instance
            discname.setvalue(instance)
            fs.append(discname)
            if interval is not None and interval > 0:
                discint = pyIntFrame(FrameTypes.DISCINTERVAL, intbytes=4, initval=int(interval))
                fs.append(discint)
            instframe = pyCstringFrame(FrameTypes.DISCNAME)
            if isinstance(json, pyConfigContext):
                json = str(json)
            elif json is None:
                json = instance
            if not json.startswith('{'):
                json = '{"type":"%s","parameters":{}}' % json
            jsonframe = pyCstringFrame(FrameTypes.DISCJSON)
            jsonframe.setvalue(json)
            fs.append(jsonframe)
        # This doesn't work if the client has bound to a VIP
        ourip = self.primary_ip()    # meaning select our primary IP
        ourip = pyNetAddr(ourip)
        ourip.setport(self.getport())
        self.io.sendframesets(ourip, (fs,))
        if CMAdb.debug:
            CMAdb.log.debug('Sent Discovery request(%s,%s) to %s Framesets: %s'
            %	(instance, str(interval), str(ourip), str(fs)))


    def __str__(self):
        'Give out our designation'
        return 'Drone(%s)' % self.node['name']

    @staticmethod
    def find(designation):
        'Find a drone with the given designation or IP address, or Neo4J node.'
        if isinstance(designation, str):
            drone = None
            if designation in DroneInfo._droneweakrefs:
                drone = DroneInfo._droneweakrefs[designation]()
            if drone is None:
                drone = DroneInfo(designation)
            assert drone.node['name'] == designation
            return drone
        if isinstance(designation, pyNetAddr):
            #Is there a concern about non-canonical IP address formats?
            ipaddrs = CMAdb.cdb.ipindex.get(CMAdb.NODE_ipaddr, repr(designation))
            for ip in ipaddrs:
                # Shouldn't have duplicates, but they happen...
                # FIXME: Think about how to manage duplicate IP addresses...
                # Do we really want to be looking up just by IP addresses here?
                node = ip.get_single_related_node(neo4j.Direction.OUTGOING, CMAdb.REL_iphost)
                return DroneInfo.find(node)
            if CMAdb.debug:
                CMAdb.log.debug('COULD NOT FIND IP ADDRESS in Drone.find... %s' % repr(designation))
        elif isinstance(designation, neo4j.Node):
            nodedesig = designation['name']
            if nodedesig in DroneInfo._droneweakrefs:
                ret = DroneInfo._droneweakrefs[nodedesig]()
                if ret is not None:  return ret
            return DroneInfo(designation)
           
        if CMAdb.debug:
            CMAdb.log.debug("DESIGNATION repr(%s) = %s" % (designation, repr(designation)))
        if repr(designation) in DroneInfo._droneweakrefs:
            ret = DroneInfo._droneweakrefs[designation]()
        return None

    @staticmethod
    def add(designation, reason, status='up'):
        'Add a drone to our set unless it is already there.'
        ret = None
        if designation in DroneInfo._droneweakrefs:
            ret = DroneInfo._droneweakrefs[designation]()
        if ret is None:
            ret = DroneInfo.find(designation)
        if ret is None:
            ret = DroneInfo(designation)
        ret.node['reason'] = reason
        ret.node['status'] = status
        return ret

    @staticmethod
    def add_json_processors(*args):
        for tuple in args:
            DroneInfo._JSONprocessors[tuple[0]] = tuple[1]

DroneInfo.add_json_processors(('netconfig', DroneInfo.add_netconfig_addresses),)
DroneInfo.add_json_processors(('tcplisteners', DroneInfo.add_tcplisteners),)
DroneInfo.add_json_processors(('tcpclients', DroneInfo.add_tcplisteners),)
DroneInfo.add_json_processors(('#LinkDiscovery', DroneInfo.add_linkdiscovery),)
