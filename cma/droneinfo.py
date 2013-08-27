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
'''
We implement the Drone class - which implements all the properties of
drones as a Python class.
'''
import weakref, time
import sys
#import os, traceback
from cmadb import CMAdb
from store import Store
from graphnodes import NICNode, IPaddrNode, SystemNode, nodeconstructor
from py2neo import neo4j


from frameinfo import FrameSetTypes, FrameTypes
from AssimCclasses import pyNetAddr, pyConfigContext, DEFAULT_FSP_QID
from py2neo import neo4j
import hbring
from graphnodes import GraphNode, nodeconstructor

class Drone(SystemNode):
    'Everything about Drones - endpoints that run our nanoprobes'
    _droneweakrefs = {}
    _JSONprocessors = {}
    IPownerquery_1 = None
    OwnedIPsQuery = None


    def __init__(self, designation, port=None, startaddr=None
    ,       primary_ip_addr=None, domain=CMAdb.globaldomain):
        super(Drone, self).__init__(domain=domain, systemtype='drone')
        self._io = CMAdb.io
        self.status = '(unknown)'
        self.reason = '(initialization)'
        self.startaddr = str(startaddr)
        self.primary_ip_addr = str(primary_ip_addr)
        self.port = port
        self.designation = designation
        if Drone.IPownerquery_1 is None:
            Drone.IPownerquery_1 =  neo4j.CypherQuery(CMAdb.cdb.db,
            '''START n=node:IPaddrNode({ipquery})\
               MATCH n<-[:%s]-()<-[:%s]-drone
               return drone LIMIT 1
            ''' % (CMAdb.REL_ipowner, CMAdb.REL_nicowner))
            Drone.OwnedIPsQuery =  neo4j.CypherQuery(CMAdb.cdb.db,
            '''START d=node:Drone({droneid})\
               MATCH drone-[:%s]->()-[:%s]->ip
               return ip
            ''' % (CMAdb.REL_nicowner, CMAdb.REL_ipowner))


    def getport(self):
        '''Return the port we talk to this drone on'''
        return self.port

    def setport(self, port):
        '''Set the port we talk to this drone on'''
        self.port = port
        
   
    def logjson(self, jsontext):
        'Process and save away JSON discovery data'
        assert CMAdb.store.has_node(self)
        jsonobj = pyConfigContext(jsontext)
        if not jsonobj.has_key('discovertype') or not jsonobj.has_key('data'):
            CMAdb.log.warning('Invalid JSON discovery packet: %s' % jsontext)
            return
        dtype = jsonobj['discovertype']
        print "Saved discovery type %s for endpoint %s." % \
           (dtype, self.designation)
        designation = self.designation
        jsonname = 'JSON_' + dtype
        setattr(self, jsonname, jsontext)
        if dtype in Drone._JSONprocessors:
            if CMAdb.debug:
                CMAdb.log.debug('Processing %s JSON data from %s into graph.'
                %       (dtype, designation))
            assert CMAdb.store.has_node(self)
            Drone._JSONprocessors[dtype](self, jsonobj)
            if CMAdb.debug:
                CMAdb.log.debug('Processed %s JSON data from %s into graph.'
                %   (dtype, designation))
        else:
            CMAdb.log.info('Stored %s JSON data from %s without processing.'
            %   (dtype, designation))

    #pylint: disable=R0914
    def add_netconfig_addresses(self, jsonobj, **kw):
        '''Save away the network configuration data we got from netconfig JSON discovery.
        This includes all our NICs, their MAC addresses, all our IP addresses and so on
        for any (non-loopback) interface.  Whee!
        '''

        assert CMAdb.store.has_node(self)
        data = jsonobj['data'] # The data portion of the JSON message

        currmacs = {}
        # Get our current list of NICs 
        iflist = CMAdb.store.load_related(self, CMAdb.REL_nicowner, NICNode)
        for nic in iflist:
            currmacs[nic.macaddr] = nic

        primaryifname=None
        newmacs = {}
        for ifname in data.keys(): # List of interfaces just below the data section
            ifinfo = data[ifname]
            #if not ifinfo.has_key('address'):
            if not 'address' in ifinfo:
                continue
            macaddr = ifinfo['address']
            #print 'ADDRESS: [%s]' % str(macaddr)
            if macaddr.startswith('00:00:00:'):
                continue
            newnic = CMAdb.store.load_or_create(NICNode, domain=self.domain
            ,       macaddr=macaddr, ifname=ifname)
            newmacs[macaddr] = newnic
            if 'default_gw' in ifinfo and primaryifname == None:
                primaryifname = ifname

        # Now compare the two sets of MAC addresses (old and new)
        for macaddr in currmacs.keys():
            currmac = currmacs[macaddr]
            if macaddr in newmacs:
                newmacs[macaddr] = currmac.update_attributes(newmacs[macaddr])
            else:
                CMAdb.store.separate(self, CMAdb.REL_ipowner, currmac)
                CMAdb.store.separate(self, CMAdb.REL_causes,  currmac)
                # This needs to be a "reference count" deletion...
                CMAdb.store.delete(currmac)
                del currmacs[macaddr]
        currmacs = None

        # Create REL_nicowner relationships for the newly created NIC nodes
        for macaddr in newmacs.keys():
            nic = newmacs[macaddr]
            if Store.is_abstract(nic):
                CMAdb.store.relate(self, CMAdb.REL_nicowner, nic, {'causes': True})
                CMAdb.store.relate(self, CMAdb.REL_causes,   nic)

        # Now newmacs contains all the current info about our NICs - old and new...
        # Let's figure out what's happening with our IP addresses...

        primaryip = None

        for macaddr in newmacs.keys():
            mac = newmacs[macaddr]
            ifname = mac.ifname
            iptable = data[str(ifname)]['ipaddrs']
            currips = {}
            iplist = CMAdb.store.load_related(mac, CMAdb.REL_ipowner, IPaddrNode)
            for ip in iplist:
                currips[ip.ipaddr] = ip

            newips = {}
            for ip in iptable.keys():   # keys are 'ip/mask' in CIDR format
                ipname = ':::INVALID:::'
                ipinfo = iptable[ip]
                if 'name' in ipinfo:
                    ipname = ipinfo['name']
                if ipinfo['scope'] != 'global':
                    continue
                iponly,cidrmask = ip.split('/')
                netaddr = pyNetAddr(iponly).toIPv6()
                if netaddr.islocal():
                    continue
                ipnode = CMAdb.store.load_or_create(IPaddrNode, domain=self.domain, ipaddr=str(netaddr)
                ,   cidrmask=cidrmask)
                ## FIXME: Not an ideal way to determine primary (preferred) IP address...
                ## it's a bit idiosyncratic to Linux...
                if ifname == primaryifname  and primaryip is None and ipname == ifname:
                    primaryip = ipnode
                    self.primary_ip_addr = str(primaryip.ipaddr)
                    print >>sys.stderr, 'PRIMARY IP is %s' % iponly
                newips[str(netaddr)] = ipnode
            # compare the two sets of IP addresses (old and new)
            for ipaddr in currips.keys():
                currip = currips[ipaddr]
                if ipaddr in newips:
                    newips[ipaddr] = currip.update_attributes(newips[ipaddr])
                else:
                    del currips[ipaddr]
                    # This needs to be a "reference count" deletion...
                    CMAdb.store.separate(mac, currip, CMAdb.REL_ipowner)
                    CMAdb.store.delete(currip)

            # Create REL_ipowner relationships for all the newly created IP nodes
            for ipaddr in newips.keys():
                ip = newips[ipaddr]
                if Store.is_abstract(ip):
                    CMAdb.store.relate(mac, CMAdb.REL_ipowner, ip, {'causes': True})
                    CMAdb.store.relate(mac, CMAdb.REL_causes,  ip)



    def add_tcplisteners(self, jsonobj, **keywords):
        '''Add TCP listeners and/or clients.  Same or separate messages - we don't care.'''
        data = jsonobj['data'] # The data portion of the JSON message
        keywords = keywords # Don't really need this argument...
        if CMAdb.debug:
            CMAdb.log.debug('add_tcplisteners(data=%s)' % data)
        print 'STORE contains:', CMAdb.store
        allourips = CMAdb.store.load_cypher_nodes(Drone.OwnedIPsQuery, Drone
        ,       {'droneid':Store.id(self)})
        print 'ALL OUR IPs:', allourips
        if CMAdb.debug:
            CMAdb.log.debug('Processing keys(%s)' % data.keys())
        for procname in data.keys(): # List of names of processes...
            if CMAdb.debug:
                CMAdb.log.debug('Processing key(%s)' % procname)
            procinfo = data[procname]
            if CMAdb.debug:
                CMAdb.log.debug('Processing procinfo(%s)' % procinfo)
            ipproc = CMAdb.cdb.new_ipproc(procname, procinfo, self)
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
                ipnetaddr = (pyNetAddr(ipaddr.ipaddr).toIPv6())
                ipnetaddr.setport(port)
                name = str(ipnetaddr)
                CMAdb.cdb.new_tcpipport(name, isserver
                ,   jsonobj, self, ipproc, ipaddr)
        elif isserver:
            for ipaddr in allourips:
                ipaddrname = ipaddr['name']
                ipnetaddr = (pyNetAddr(str(ipaddrname)).toIPv6())
                if ipnetaddr == netaddr:
                    CMAdb.cdb.new_tcpipport(name, isserver, jsonobj, self, ipproc, ipaddr)
                    return
            raise ValueError('IP Address mismatch for Drone %s - could not find address %s'
                            % (self.designation, addr))
        else:
            netaddr.setport(port)
            ipaddr = CMAdb.cdb.new_ipaddr(None, addr)
            CMAdb.cdb.new_tcpipport(str(netaddr), isserver, jsonobj, None, ipproc, ipaddr)

    #pylint: disable=R0914
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
        #### FIXME What should the domain of a switch default to?
        switch = CMAdb.store.load_or_create(SystemNode, domain=self.domain
        ,       systemtype='switch', **attrs)
        if 'ManagementAddress' in attrs:
            # FIXME - not sure if I know how I should do this now - no MAC address for mgmtaddr?
            mgmtaddr = attrs['ManagementAddress']
            adminnic = CMAdb.store.load_or_create(NICnode, domain=switch.domain, macaddr=chassisid
            ,           ifname='(adminNIC)')
            mgmtip = CMAdb.store.load_or_create(IPaddrNode, domain=switch.domain, cidrmask='unknown')
            if Store.is_abstract(adminnic) or Store.is_abstract(switch):
                CMAdb.store.relate(switch, REL_nicowner, adminnic, {'causes': True})
            if Store.is_abstract(mgmtip) or Store.is_abstract(adminnic):
                CMAdb.store.relate(adminnic, REL_ipowner, mgmtip, {'causes': True})
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
            nicnode = CMAdb.store.load_or_create(NICnode, domain=self.domain, macaddr=nicmac, **attrs)
            try:
                assert thisport['ConnectsToHost'] == self.designation
                matchnic = thisport['ConnectsToInterface']
                niclist = self.node.get_related_nodes(neo4j.Direction.INCOMING, CMAdb.REL_nicowner)
                for dronenic in niclist:
                    if dronenic['nicname'] == matchnic:
                        CMAdb.store.relate(nicnode, CMAdb._REL_wiredto, dronenic)
                        break
            except KeyError:
                CMAdb.log.error('OOPS! got an exception...')


    def primary_ip(self, ring=None):
        '''Return the "primary" IP for this host'''
        ring = ring # should eventually use the ring if it's supplied
        return self.primary_ip_addr

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
    

    #Current implementation does not use 'self'
    #pylint: disable=R0201
    def send_hbmsg(self, dest, fstype, addrlist):
        '''Send a message with an attached pyNetAddr list - each including port numbers'
           This is intended primarily for start or stop heartbeating messages.'''
        CMAdb.transaction.add_packet(dest, fstype, addrlist, frametype=FrameTypes.IPPORT)

    def death_report(self, status, reason, fromaddr, frameset):
        'Process a death/shutdown report for us.  RIP us.'
        from hbring import HbRing
        frameset = frameset # We don't use the frameset at this point in time
        print >> sys.stderr, 'DRONE %s died!' % self
        if reason != 'HBSHUTDOWN':
            CMAdb.log.info('Node %s has been reported as %s by address %s. Reason: %s'
            %   (self.designation, status, str(fromaddr), reason))
        self.status = status
        self.reason = reason
        self.status = status
        self.reason = reason
        self.statustime = int(round(time.time() * 1000))
        self.iso8601 = time.strftime('%Y-%m-%d %H:%M:%S')
        # There is a need for us to be a little more sophisticated
        # in terms of the number of peers this particular drone had
        # It's here in this place that we will eventually add the ability
        # to distinguish death of a switch or subnet or site from death of a single drone
        for mightbering in CMAdb.store.load_related(self, None, nodeconstructor):
            if isinstance(mightbering, HbRing):
                mightbering.leave(self)
        deadip = pyNetAddr(self.primary_ip(), port=self.getport())
        if CMAdb.debug:
            CMAdb.log.debug('Closing connection to %s/%d' % (deadip, DEFAULT_FSP_QID))
        self._io.closeconn(DEFAULT_FSP_QID, deadip)



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
        #fs = pyFrameSet(FrameSetTypes.DODISCOVER)
        if type(args[0]) is str:
            if len(args) == 1:
                args = ((args[0], 0, None),)
            elif len(args) == 2:
                args = ((args[0], args[1], None),)
            elif len(args) == 3:
                args = ((args[0], args[1], args[2]),)
            else:
                raise ValueError('Incorrect argument length: %d vs 1, 2 or 3' % len(args))

        frames = []
        for ourtuple in args:
            if len(ourtuple) != 2 and len(ourtuple) != 3:
                raise ValueError('Incorrect argument tuple length: %d vs 2 or 3 [%s]'
                %        (len(ourtuple), args))
            instance = ourtuple[0]
            interval = ourtuple[1]
            json = None
            if len(ourtuple) == 3:
                json = ourtuple[2]
            frames.append({'frametype': FrameTypes.DISCNAME, 'framevalue': instance})
            #discname = pyCstringFrame(FrameTypes.DISCNAME)
            #print >>sys.stderr, 'SETTING VALUE TO: (%s)' % instance
            #discname.setvalue(instance)
            #fs.append(discname)
            if interval is not None and interval > 0:
                frames.append({'frametype': FrameTypes.DISCINTERVAL, 'framevalue': int(interval)})
                #discint = pyIntFrame(FrameTypes.DISCINTERVAL, intbytes=4, initval=int(interval))
                #fs.append(discint)
            if isinstance(json, pyConfigContext):
                json = str(json)
            elif json is None:
                json = instance
            if not json.startswith('{'):
                json = '{"type":"%s", "parameters":{}}' % json
            frames.append({'frametype': FrameTypes.DISCJSON, 'framevalue': json})
            #jsonframe = pyCstringFrame(FrameTypes.DISCJSON)
            #jsonframe.setvalue(json)
            #fs.append(jsonframe)
        # This doesn't work if the client has bound to a VIP
        ourip = self.primary_ip()    # meaning select our primary IP
        ourip = pyNetAddr(ourip)
        ourip.setport(self.getport())
        #self.io.sendreliablefs(ourip, (fs,))
        CMAdb.transaction.add_packet(ourip,  FrameSetTypes.DODISCOVER, frames)
        if CMAdb.debug:
            CMAdb.log.debug('Sent Discovery request(%s, %s) to %s Frames: %s'
            %	(instance, str(interval), str(ourip), str(frames)))


    def __str__(self):
        'Give out our designation'
        return 'Drone(%s)' % self.designation

    @staticmethod
    def find(designation, port=None, domain=CMAdb.globaldomain):
        'Find a drone with the given designation or IP address, or Neo4J node.'
        desigstr = str(designation)
        if isinstance(designation, Drone):
            return designation
        elif isinstance(designation, str):
            drone = CMAdb.store.load_or_create(Drone, port=port, domain=domain
            ,       designation=designation)
            print >> sys.stderr, 'DESIGNATION1: %s' % designation
            assert drone.designation == designation
            assert CMAdb.store.has_node(drone)
            return drone
        elif isinstance(designation, pyNetAddr):
            dport = None
            desigport = designation.port()
            if desigport is not None and desigport > 0:
                dport = desigport
            desig = designation.toIPv6(port=0)
            #desig=designation
            desigstr = str(desig)
            query = '%s:%s' % (self.domain, desigstr)
            #Note that we now do everything by IPv6 addresses...
            drone = CMAdb.store.load_cypher_node(Drone.IPownerquery_1, Drone, {'ipquery':query})
            if drone is not None:
                assert CMAdb.store.has_node(drone)
                return drone
            if CMAdb.debug:
                CMAdb.log.warn('Could not find IP NetAddr address in Drone.find... %s [%s] [%s]'
                %   (designation, desigstr, type(designation)))
           
        if CMAdb.debug:
            CMAdb.log.debug("DESIGNATION2 (%s) = %s" % (designation, desigstr))
        if CMAdb.debug:
            raise RuntimeError('drone.find(%s) (%s) (%s) => returning None' % (
                str(designation), desigstr, type(designation)))
            #CMAdb.log.warn('drone.find(%s) (%s) (%s) => returning None' % (
                #str(designation), desigstr, type(designation)))
            #tblist = traceback.extract_stack()
            ##tblist = traceback.extract_tb(trace, 20)
            #CMAdb.log.info('======== Begin missing IP Traceback ========')
            #for tbelem in tblist:
                #(filename, line, funcname, text) = tbelem
                #filename = os.path.basename(filename)
                #CMAdb.log.info('%s.%s:%s: %s'% (filename, line, funcname, text))
            #CMAdb.log.info('======== End missing IP Traceback ========')
        return ret

    @staticmethod
    def add(designation, reason, status='up', port=None, domain=CMAdb.globaldomain
    ,       primary_ip_addr=None):
        'Add a drone to our set unless it is already there.'
        drone = CMAdb.store.load_or_create(Drone, domain=domain, designation=designation
        ,   primary_ip_addr=primary_ip_addr)
        assert CMAdb.store.has_node(drone)
        drone.reason=reason
        drone.status=status
        drone.statustime=int(round(time.time() * 1000))
        drone.iso8601=time.strftime('%Y-%m-%d %H:%M:%S')
        if port is not None:
            drone.setport(port)
        print >> sys.stderr, 'ADD returning %s' % drone
        return drone

    @staticmethod
    def add_json_processors(*args):
        "Register (add) all the json processors we've been given as arguments"
        for ourtuple in args:
            Drone._JSONprocessors[ourtuple[0]] = ourtuple[1]

Drone.add_json_processors(('netconfig', Drone.add_netconfig_addresses),)
Drone.add_json_processors(('tcplisteners', Drone.add_tcplisteners),)
Drone.add_json_processors(('tcpclients', Drone.add_tcplisteners),)
Drone.add_json_processors(('#LinkDiscovery', Drone.add_linkdiscovery),)
