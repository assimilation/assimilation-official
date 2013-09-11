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
import time
import sys
#import os, traceback
from py2neo import neo4j
from cmadb import CMAdb
from consts import CMAconsts
from store import Store
from graphnodes import nodeconstructor
from graphnodes import NICNode, IPaddrNode, SystemNode, ProcessNode, IPtcpportNode
from frameinfo import FrameSetTypes, FrameTypes
from AssimCclasses import pyNetAddr, pyConfigContext, DEFAULT_FSP_QID

class Drone(SystemNode):
    '''Everything about Drones - endpoints that run our nanoprobes.

    There are two Cypher queries that get initialized later:
    Drone.IPownerquery_1: Given an IP address, return what SystemNode (probably Drone) that 'owns' it.
    Drone.OwnedIPsQuery:  Given a Drone object, return all the IPaddrNodes that it 'owns'
    '''
    _JSONprocessors = {}
    IPownerquery_1 = None
    OwnedIPsQuery = None
    IPownerquery_1_txt = '''START n=node:IPaddrNode({ipaddr})
                            MATCH n<-[:%s]-()<-[:%s]-drone
                            return drone LIMIT 1'''
    OwnedIPsQuery_txt = '''START d=node({droneid}) 
                           MATCH d-[:%s]->()-[:%s]->ip
                           return ip'''


    # R0913: Too many arguments to __init__()
    # pylint: disable=R0913
    def __init__(self, designation, port=None, startaddr=None
    ,       primary_ip_addr=None, domain=CMAconsts.globaldomain
    ,       status= '(unknown)', reason='(initialization)', roles=None):
        '''Initialization function for the Drone class.
        We mainly initialize a few attributes from parameters as noted above...

        The first time around we also initialize a couple of class-wide CypherQuery
        objects for a couple of queries we know we'll need later.
        '''
        SystemNode.__init__(self, domain=domain, designation=designation)
        if roles is None:
            roles = ['host', 'drone']
        self.addrole(roles)
        self._io = CMAdb.io
        self.status = status
        self.reason = reason
        self.startaddr = str(startaddr)
        self.primary_ip_addr = str(primary_ip_addr)
        self.time_status_ms = int(round(time.time() * 1000))
        self.time_status_iso8601 = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        if port is not None:
            self.port = int(port)
        else:
            self.port = None

        if Drone.IPownerquery_1 is None:
            Drone.IPownerquery_1 =  neo4j.CypherQuery(CMAdb.cdb.db, Drone.IPownerquery_1_txt
            % (CMAconsts.REL_ipowner, CMAconsts.REL_nicowner))
            Drone.OwnedIPsQuery_subtxt = Drone.OwnedIPsQuery_txt    \
            %       (CMAconsts.REL_nicowner, CMAconsts.REL_ipowner)
            Drone.OwnedIPsQuery =  neo4j.CypherQuery(CMAdb.cdb.db, Drone.OwnedIPsQuery_subtxt)


    def get_owned_ips(self):
        '''Return a list of all the IP addresses that this Drone owns'''
        params = {'droneid':Store.id(self)}
        if False and CMAdb.debug:
            print >> sys.stderr, ('IP owner query:\n%s\nparams %s'
            %   (Drone.OwnedIPsQuery_subtxt, params))

        return [node for node in CMAdb.store.load_cypher_nodes(Drone.OwnedIPsQuery, IPaddrNode
        ,       params=params)]

        
   
    def logjson(self, jsontext):
        'Process and save away JSON discovery data'
        assert CMAdb.store.has_node(self)
        jsonobj = pyConfigContext(jsontext)
        if not 'discovertype' in jsonobj or not 'data' in jsonobj:
            CMAdb.log.warning('Invalid JSON discovery packet: %s' % jsontext)
            return
        dtype = jsonobj['discovertype']
        designation = self.designation
        jsonname = 'JSON_' + dtype
        if not hasattr(self, jsonname) or str(getattr(self, jsonname)) != jsontext:
            if CMAdb.debug:
                CMAdb.log.debug("Saved discovery type %s for endpoint %s."
                %       (dtype, self.designation))
            setattr(self, jsonname, jsontext)
        else:
            if CMAdb.debug:
                CMAdb.log.debug('Discovery type %s for endpoint %s is unchanged. ignoring' 
                %       (dtype, self.designation))
            return

        if dtype in Drone._JSONprocessors:
            Drone._JSONprocessors[dtype](self, jsonobj)
            if CMAdb.debug:
                CMAdb.log.debug('Processed %s JSON data from %s into graph.'
                %   (dtype, designation))
        else:
            CMAdb.log.info('Stored %s JSON data from %s without processing.'
            %   (dtype, designation))

    # R0912 -- too many branches
    # R0914 -- too many local variables
    #pylint: disable=R0914,R0912
    def _add_netconfig_addresses(self, jsonobj, **kw):
        '''Save away the network configuration data we got from netconfig JSON discovery.
        This includes all our NICs, their MAC addresses, all our IP addresses and so on
        for any (non-loopback) interface.  Whee!

        This code is more complicated than I'd like but it's not obvious how to simplify it...
        '''

        assert CMAdb.store.has_node(self)
        data = jsonobj['data'] # The data portion of the JSON message
        kw = kw # Don't currently need this argument...

        currmacs = {}
        # Get our current list of NICs 
        iflist = CMAdb.store.load_related(self, CMAconsts.REL_nicowner, NICNode)
        for nic in iflist:
            currmacs[nic.macaddr] = nic

        primaryifname = None
        newmacs = {}
        for ifname in data.keys(): # List of interfaces just below the data section
            ifinfo = data[ifname]
            if not 'address' in ifinfo:
                continue
            macaddr = str(ifinfo['address'])
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
                CMAdb.store.separate(self, CMAconsts.REL_ipowner, currmac)
                #CMAdb.store.separate(self, CMAconsts.REL_causes,  currmac)
                # @TODO Needs to be a 'careful, complete' reference count deletion...
                CMAdb.store.delete(currmac)
                del currmacs[macaddr]
        currmacs = None

        # Create REL_nicowner relationships for the newly created NIC nodes
        for macaddr in newmacs.keys():
            nic = newmacs[macaddr]
            if Store.is_abstract(nic):
                CMAdb.store.relate(self, CMAconsts.REL_nicowner, nic, {'causes': True})
                #CMAdb.store.relate(self, CMAconsts.REL_causes,   nic)

        # Now newmacs contains all the current info about our NICs - old and new...
        # Let's figure out what's happening with our IP addresses...

        primaryip = None

        for macaddr in newmacs.keys():
            mac = newmacs[macaddr]
            ifname = mac.ifname
            iptable = data[str(ifname)]['ipaddrs']
            currips = {}
            iplist = CMAdb.store.load_related(mac, CMAconsts.REL_ipowner, IPaddrNode)
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
                iponly, cidrmask = ip.split('/')
                netaddr = pyNetAddr(iponly).toIPv6()
                if netaddr.islocal():
                    continue
                ipnode = CMAdb.store.load_or_create(IPaddrNode
                ,   domain=self.domain, ipaddr=str(netaddr), cidrmask=cidrmask)
                ## FIXME: Not an ideal way to determine primary (preferred) IP address...
                ## it's a bit idiosyncratic to Linux...
                if ifname == primaryifname  and primaryip is None and ipname == ifname:
                    primaryip = ipnode
                    self.primary_ip_addr = str(primaryip.ipaddr)
                newips[str(netaddr)] = ipnode

            # compare the two sets of IP addresses (old and new)
            for ipaddr in currips.keys():
                currip = currips[ipaddr]
                if ipaddr in newips:
                    newips[ipaddr] = currip.update_attributes(newips[ipaddr])
                else:
                    del currips[ipaddr]
                    CMAdb.store.separate(mac, currip, CMAconsts.REL_ipowner)
                    # @TODO Needs to be a 'careful, complete' reference count deletion...
                    CMAdb.store.delete(currip)

            # Create REL_ipowner relationships for all the newly created IP nodes
            for ipaddr in newips.keys():
                ip = newips[ipaddr]
                if Store.is_abstract(ip):
                    CMAdb.store.relate(mac, CMAconsts.REL_ipowner, ip, {'causes': True})
                    #CMAdb.store.relate(mac, CMAconsts.REL_causes,  ip)

    def _add_tcplisteners(self, jsonobj, **keywords):
        '''Add TCP listeners and/or clients.  Same or separate messages - we don't care.'''
        data = jsonobj['data'] # The data portion of the JSON message
        keywords = keywords # Don't really need this argument...
        if CMAdb.debug:
            CMAdb.log.debug('_add_tcplisteners(data=%s)' % data)

        assert(not Store.is_abstract(self))
        allourips = self.get_owned_ips()
        if CMAdb.debug:
            CMAdb.log.debug('Processing keys(%s)' % data.keys())
        newprocs = {}
        newprocmap = {}
        discoveryroles = {}
        for procname in data.keys(): # List of names of processes...
            procinfo = data[procname]
            if 'listenaddrs' in procinfo:
                if not CMAconsts.ROLE_server in discoveryroles:
                    discoveryroles[CMAconsts.ROLE_server] = True
                    self.addrole(CMAconsts.ROLE_server)
            if 'clientaddrs' in procinfo:
                if not CMAconsts.ROLE_client in discoveryroles:
                    discoveryroles[CMAconsts.ROLE_client] = True
                    self.addrole(CMAconsts.ROLE_client)
            processproc = CMAdb.store.load_or_create(ProcessNode, domain=self.domain
            ,   host=self.designation
            ,   pathname=procinfo.get('exe', 'unknown'), arglist=procinfo.get('cmdline', 'unknown')
            ,   uid=procinfo.get('uid','unknown'), gid=procinfo.get('gid', 'unknown')
            ,   cwd=procinfo.get('cwd', '/'))
            assert hasattr(processproc, '_Store__store_node')

            newprocs[processproc.processname] = processproc
            newprocmap[procname] = processproc
            if CMAdb.store.is_abstract(processproc):
                CMAdb.store.relate(self, CMAconsts.REL_hosting, processproc, {'causes':True})
            if CMAdb.debug:
                CMAdb.log.debug('procinfo(%s) - processproc created=> %s' % (procinfo, processproc))

        oldprocs = {}
        for proc in CMAdb.store.load_related(self, CMAconsts.REL_hosting, ProcessNode):
            assert hasattr(proc, '_Store__store_node')
            procname = proc.processname
            oldprocs[procname] = proc
            if not procname in newprocs:
                if len(proc.delrole(discoveryroles.keys())) == 0:
                    assert not Store.is_abstract(proc)
                    CMAdb.store.separate(self, CMAconsts.REL_hosting, proc)
                    # @TODO Needs to be a 'careful, complete' reference count deletion...
                    CMAdb.store.delete(proc)

        for procname in data.keys(): # List of names of processes...
            processnode = newprocmap[procname]
            procinfo = data[procname]
            if CMAdb.debug:
                CMAdb.log.debug('Processing key(%s): proc: %s' % (procname, processnode))
            if not CMAdb.store.is_abstract(processnode):
                if CMAdb.debug:
                    CMAdb.log.debug('Process key(%s) already in database' % procname)
                continue
            if 'listenaddrs' in procinfo:
                srvportinfo = procinfo['listenaddrs']
                processnode.addrole(CMAconsts.ROLE_server)
                for srvkey in srvportinfo.keys():
                    self._add_serveripportnodes(srvportinfo[srvkey], processnode, allourips)
            if 'clientaddrs' in procinfo:
                clientinfo = procinfo['clientaddrs']
                processnode.addrole(CMAconsts.ROLE_client)
                for clientkey in clientinfo.keys():
                    self._add_clientipportnode(clientinfo[clientkey], processnode)

    def _add_clientipportnode(self, ipportinfo, processnode):
        '''Add the information for a single client IPtcpportNode to the database.'''
        servip_name = str(pyNetAddr(ipportinfo['addr']).toIPv6())
        servip = CMAdb.store.load_or_create(IPaddrNode, domain=self.domain, ipaddr=servip_name)
        servport = int(ipportinfo['port'])
        ip_port = CMAdb.store.load_or_create(IPtcpportNode, domain=self.domain
        ,       ipaddr=servip_name, port=servport)
        CMAdb.store.relate_new(ip_port, CMAconsts.REL_baseip, servip, {'causes': True})
        CMAdb.store.relate_new(processnode, CMAconsts.REL_tcpclient, ip_port, {'causes': True})

    def _add_serveripportnodes(self, jsonobj, processnode, allourips):
        '''We create tcpipports objects that correspond to the given json object in
        the context of the set of IP addresses that we support - including support
        for the ANY ipv4 and ipv6 addresses'''
        netaddr = pyNetAddr(str(jsonobj['addr'])).toIPv6()
        if netaddr.islocal():
            CMAdb.log.warning('add_serveripportnodes("%s"): address is local' % netaddr)
            return
        addr = str(netaddr)
        port = jsonobj['port']
        # Were we given the ANY address?
        anyaddr = netaddr.isanyaddr()
        for ipaddr in allourips:
            if not anyaddr and str(ipaddr.ipaddr) != addr:
                continue
            ip_port = CMAdb.store.load_or_create(IPtcpportNode, domain=self.domain
            ,   ipaddr=ipaddr.ipaddr, port=port)
            assert hasattr(ip_port, '_Store__store_node')
            CMAdb.store.relate_new(processnode, CMAconsts.REL_tcpservice, ip_port)
            assert hasattr(ipaddr, '_Store__store_node')
            CMAdb.store.relate_new(ip_port, CMAconsts.REL_baseip, ipaddr)
            if not anyaddr:
                return
        if not anyaddr:
            print >> sys.stderr, ('LOOKING FOR %s in: %s'
            %       (netaddr, [str(ip.ipaddr) for ip in allourips]))
            raise ValueError('IP Address mismatch for Drone %s - could not find address %s'
            %       (self, addr))

    def _add_linkdiscovery(self, jsonobj, **keywords):
        'Add Low Level (Link Level) discovery data to the database'
        #
        #   This code doesn't yet deal with moving network connections around
        #   it is certain that it won't delete the old information and replace it
        #   There are two possibilities:
        #       We are connecting to a switch port which is previously connected:
        #           Drop any wiredto connection that already exists to that port
        #       We are connecting to somewhere different
        #           Drop any wiredto relationship between the switch port and us
        #
        keywords = keywords # don't need these
        data = jsonobj['data']
        #print >> sys.stderr, 'SWITCH JSON:', str(data)
        if 'ChassisId' not in data:
            CMAdb.log.warning('Chassis ID missing from discovery data from switch [%s]'
            %   (str(data)))
            return
        chassisid = data['ChassisId']
        attrs = {}
        for key in data.keys():
            if key == 'ports' or key == 'SystemCapabilities':
                continue
            value = data[key]
            if not isinstance(value, int) and not isinstance(value, float):
                value = str(value)
            attrs[key] = value
        attrs['name'] =  chassisid
        #### FIXME What should the domain of a switch default to?
        attrs['domain'] =  self.domain
        switch = CMAdb.store.load_or_create(SystemNode, **attrs)

        if not 'SystemCapabilities' in data:
            switch.addrole(CMAconsts.ROLE_bridge)
        else:
            caps = data['SystemCapabilities']
            for role in caps.keys():
                if caps[role]:
                    switch.addrole(role)
            #switch.addrole([role for role in caps.keys() if caps[role]])
            

        if 'ManagementAddress' in attrs:
            # FIXME - not sure if I know how I should do this now - no MAC address for mgmtaddr?
            mgmtaddr = attrs['ManagementAddress']
            adminnic = CMAdb.store.load_or_create(NICNode, domain=switch.domain, macaddr=chassisid
            ,           ifname='(adminNIC)')
            mgmtip = CMAdb.store.load_or_create(IPaddrNode, domain=switch.domain
            ,           cidrmask='unknown', ipaddr=mgmtaddr)
            if Store.is_abstract(adminnic) or Store.is_abstract(switch):
                CMAdb.store.relate(switch, CMAconsts.REL_nicowner, adminnic, {'causes': True})
            if Store.is_abstract(mgmtip) or Store.is_abstract(adminnic):
                CMAdb.store.relate(adminnic, CMAconsts.REL_ipowner, mgmtip, {'causes': True})
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
            nicnode = CMAdb.store.load_or_create(NICNode, domain=self.domain
            ,   macaddr=nicmac, **attrs)
            CMAdb.store.relate(switch, CMAconsts.REL_nicowner, nicnode, {'causes': True})
            try:
                assert thisport['ConnectsToHost'] == self.designation
                matchif = thisport['ConnectsToInterface']
                niclist = CMAdb.store.load_related(self, CMAconsts.REL_nicowner, NICNode)
                for dronenic in niclist:
                    if dronenic.ifname == matchif:
                        CMAdb.store.relate_new(nicnode, CMAconsts.REL_wiredto, dronenic)
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
    def _send_hbmsg(self, dest, fstype, addrlist):
        '''Send a message with an attached pyNetAddr list - each including port numbers'
           This is intended primarily for start or stop heartbeating messages.'''
        CMAdb.transaction.add_packet(dest, fstype, addrlist, frametype=FrameTypes.IPPORT)

    def death_report(self, status, reason, fromaddr, frameset):
        'Process a death/shutdown report for us.  RIP us.'
        from hbring import HbRing
        frameset = frameset # We don't use the frameset at this point in time
        if CMAdb.debug:
            print >> sys.stderr, 'DRONE %s died! (reason=%s)' % (self, reason)
        if reason != 'HBSHUTDOWN':
            CMAdb.log.info('Node %s has been reported as %s by address %s. Reason: %s'
            %   (self.designation, status, str(fromaddr), reason))
        self.status = status
        self.reason = reason
        self.time_status_ms = int(round(time.time() * 1000))
        self.time_status_iso8601 = time.strftime('%Y-%m-%d %H:%M:%S')
        # There is a need for us to be a little more sophisticated
        # in terms of the number of peers this particular drone had
        # It's here in this place that we will eventually add the ability
        # to distinguish death of a switch or subnet or site from death of a single drone
        for mightbering in CMAdb.store.load_in_related(self, None, nodeconstructor):
            if isinstance(mightbering, HbRing):
                mightbering.leave(self)
        deadip = pyNetAddr(self.primary_ip(), port=self.port)
        if CMAdb.debug:
            CMAdb.log.debug('Closing connection to %s/%d' % (deadip, DEFAULT_FSP_QID))
        self._io.closeconn(DEFAULT_FSP_QID, deadip)

    def start_heartbeat(self, ring, partner1, partner2=None):
        '''Start heartbeating to the given partners.
        We insert ourselves between partner1 and partner2.
        We only use forward links - because we can follow them in both directions in Neo4J.
        So, we need to create a forward link from partner1 to us and from us to partner2 (if any)
        '''
        ouraddr = pyNetAddr(self.primary_ip(), port=self.port)
        partner1addr = pyNetAddr(partner1.select_ip(ring), port=partner1.port)
        if partner2 is not None:
            partner2addr = pyNetAddr(partner2.select_ip(ring), port=partner2.port)
        else:
            partner2addr = None
        if CMAdb.debug:
            CMAdb.log.debug('STARTING heartbeat(s) from %s [%s] to %s [%s] and %s [%s]' %
                (self, ouraddr, partner1, partner1addr, partner2, partner2addr))
        self._send_hbmsg(ouraddr, FrameSetTypes.SENDEXPECTHB, (partner1addr, partner2addr))

    def stop_heartbeat(self, ring, partner1, partner2=None):
        '''Stop heartbeating to the given partners.'
        We don't know which node is our forward link and which our back link,
        but we need to remove them either way ;-).
        '''
        ouraddr = pyNetAddr(self.primary_ip(), port=self.port)
        partner1addr = pyNetAddr(partner1.select_ip(ring), port=partner1.port)
        if partner2 is not None:
            partner2addr = pyNetAddr(partner2.select_ip(ring), port=partner2.port)
        else:
            partner2addr = None
        # Stop sending the heartbeat messages between these (former) peers
        if CMAdb.debug:
            CMAdb.log.debug('STOPPING heartbeat(s) from %s [%s] to %s [%s] and %s [%s]' % 
                (self, ouraddr, partner1, partner1addr, partner2, partner2addr))
        self._send_hbmsg(ouraddr, FrameSetTypes.STOPSENDEXPECTHB, (partner1addr, partner2addr))

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
            if interval is not None and interval > 0:
                frames.append({'frametype': FrameTypes.DISCINTERVAL, 'framevalue': int(interval)})
            if isinstance(json, pyConfigContext):
                json = str(json)
            elif json is None:
                json = instance
            if not json.startswith('{'):
                json = '{"type":"%s", "parameters":{}}' % json
            frames.append({'frametype': FrameTypes.DISCJSON, 'framevalue': json})
        # This doesn't work if the client has bound to a VIP
        ourip = self.primary_ip()    # meaning select our primary IP
        ourip = pyNetAddr(ourip)
        ourip.setport(self.port)
        #self.io.sendreliablefs(ourip, (fs,))
        CMAdb.transaction.add_packet(ourip,  FrameSetTypes.DODISCOVER, frames)
        if CMAdb.debug:
            CMAdb.log.debug('Sent Discovery request(%s, %s) to %s Frames: %s'
            %	(instance, str(interval), str(ourip), str(frames)))


    def __str__(self):
        'Give out our designation'
        return 'Drone(%s)' % self.designation

    @staticmethod
    def find(designation, port=None, domain=None):
        'Find a drone with the given designation or IP address, or Neo4J node.'
        desigstr = str(designation)
        if isinstance(designation, Drone):
            return designation
        elif isinstance(designation, str):
            if domain is None:
                domain = CMAconsts.globaldomain
            drone = CMAdb.store.load_or_create(Drone, port=port, domain=domain
            ,       designation=designation)
            assert drone.designation == designation
            assert CMAdb.store.has_node(drone)
            return drone
        elif isinstance(designation, pyNetAddr):
            desig = designation.toIPv6()
            desig.setport(0)
            desigstr = str(desig)
            if domain is None:
                dstr = '*'
            else:
                dstr = domain
            query = '%s:%s' % (str(Store.lucene_escape(desigstr)), dstr)
            #We now do everything by IPv6 addresses...
            drone = CMAdb.store.load_cypher_node(Drone.IPownerquery_1, Drone, {'ipaddr':query})
            if drone is not None:
                assert CMAdb.store.has_node(drone)
                return drone
            if CMAdb.debug:
                CMAdb.log.warn('Could not find IP NetAddr address in Drone.find... %s [%s] [%s]'
                %   (designation, desigstr, type(designation)))
           
        if True or CMAdb.debug:
            CMAdb.log.debug("DESIGNATION2 (%s) = %s" % (designation, desigstr))
            CMAdb.log.debug("QUERY (%s) = %s" % (designation, query))
            print >> sys.stderr, ("DESIGNATION2 (%s) = %s" % (designation, desigstr))
            print >> sys.stderr, ("QUERY (%s) = %s" % (designation, query))
        if CMAdb.debug:
            raise RuntimeError('drone.find(%s) (%s) (%s) => returning None' % (
                str(designation), desigstr, type(designation)))
                #str(designation), desigstr, type(designation)))
            #tblist = traceback.extract_stack()
            ##tblist = traceback.extract_tb(trace, 20)
            #CMAdb.log.info('======== Begin missing IP Traceback ========')
            #for tbelem in tblist:
                #(filename, line, funcname, text) = tbelem
                #filename = os.path.basename(filename)
                #CMAdb.log.info('%s.%s:%s: %s'% (filename, line, funcname, text))
            #CMAdb.log.info('======== End missing IP Traceback ========')
            #CMAdb.log.warn('drone.find(%s) (%s) (%s) => returning None' % (
        return None

    @staticmethod
    def add(designation, reason, status='up', port=None, domain=CMAconsts.globaldomain
    ,       primary_ip_addr=None):
        'Add a drone to our set unless it is already there.'
        drone = CMAdb.store.load_or_create(Drone, domain=domain, designation=designation
        ,   primary_ip_addr=primary_ip_addr, port=port, status=status, reason=reason)
        assert CMAdb.store.has_node(drone)
        drone.reason = reason
        drone.status = status
        drone.statustime = int(round(time.time() * 1000))
        drone.iso8601 = time.strftime('%Y-%m-%d %H:%M:%S')
        if port is not None:
            drone.port = port
        return drone

    @staticmethod
    def add_json_processors(*args):
        "Register (add) all the json processors we've been given as arguments"
        for ourtuple in args:
            Drone._JSONprocessors[ourtuple[0]] = ourtuple[1]

# W0202 Access to a protected member _add_netconfig_addresses of a client class
# W0212 Access to a protected member _add_tcplisteners of a client class
# W0212 Access to a protected member _add_tcplisteners of a client class
# W0212 Access to a protected member _add_linkdiscovery of a client class

# pylint: disable=W0212
Drone.add_json_processors(('netconfig', Drone._add_netconfig_addresses),)
Drone.add_json_processors(('tcplisteners', Drone._add_tcplisteners),)
Drone.add_json_processors(('tcpclients', Drone._add_tcplisteners),)
Drone.add_json_processors(('__LinkDiscovery', Drone._add_linkdiscovery),)
