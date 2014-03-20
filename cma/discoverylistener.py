#!/usr/bin/python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2013 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community - http://assimproj.org
# Paid support is available from Assimilation Systems Limited - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#

'''
Discovery Listener infrastructure
This is the base class for code that wants to hear about various
discovery packets as they arrive.

More details are documented in the DiscoveryListener class
'''
import re, sys
from monitoring import MonitoringRule
from droneinfo import Drone
from consts import CMAconsts
from store import Store
from AssimCclasses import pyNetAddr

from graphnodes import NICNode, IPaddrNode, ProcessNode, IPtcpportNode, GraphNode

class DiscoveryListener:
    '''Class for listening to discovery packets
    We support three different categories/priorities of discovery actions
    as documented below:
    '''

    PRI_CORE   = 0              # This discovery plugin is part of the core system
    PRI_OPTION  = 1             # This is an optional capability that comes with the system
    PRI_CONTRIB = 2             # This is a contributed (and optional) capability
    PRI_LIMIT = PRI_CONTRIB+1

    prio = PRI_CONTRIB
    wantedpackets = None

    def __init__(self, packetio, store, log, debug):
        'Init function for DiscoveryListener'
        self.packetio = packetio
        self.store = store
        self.log = log
        self.debug = debug

    @classmethod
    def priority(cls):
        'Return the priority (ordering) that this should be invoked at'
        return cls.prio

    @classmethod
    def desiredpackets(cls):
        'Return the set of packets we want to be called for'
        return cls.wantedpackets

    def processpkt(self, drone, srcaddr, json):
        'A desired packet has been received - process it'
        raise NotImplementedError('Abstract class - processpkt()')
    

@Drone.add_json_processor
class MonitoringAgentDiscoveryListener(DiscoveryListener):
    'Class for updating our agent cache when we get new monitoringagents information'

    prio = DiscoveryListener.PRI_CORE
    wantedpackets = ('monitoringagents',)

    def processpkt(self, drone, unused_srcaddr, unused_jsonobj):
        '''Update the _agentcache when we get a new set of available agents'''
        unused_jsonobj = unused_jsonobj
        unused_srcaddr = unused_srcaddr
        MonitoringRule.compute_available_agents((self,))

# R0912 -- too many branches
# R0914 -- too many local variables
#pylint: disable=R0914,R0912

@Drone.add_json_processor
class NetconfigDiscoveryListener(DiscoveryListener):
    'Class for the (initial) netconfig discovery packet'

    prio = DiscoveryListener.PRI_CORE
    wantedpackets = ('netconfig',)

    def processpkt(self, drone, unused_srcaddr, jsonobj):
        '''Save away the network configuration data we got from netconfig JSON discovery.
        This includes all our NICs, their MAC addresses, all our IP addresses and so on
        for any (non-loopback) interface.  Whee!

        This code is more complicated than I'd like but it's not obvious how to simplify it...
        '''

        unused_srcaddr = unused_srcaddr
        assert self.store.has_node(drone)
        data = jsonobj['data'] # The data portion of the JSON message

        currmacs = {}
        # Get our current list of NICs 
        iflist = self.store.load_related(drone, CMAconsts.REL_nicowner, NICNode)
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
            newnic = self.store.load_or_create(NICNode, domain=drone.domain
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
                self.store.separate(drone, CMAconsts.REL_ipowner, currmac)
                #self.store.separate(drone, CMAconsts.REL_causes,  currmac)
                # @TODO Needs to be a 'careful, complete' reference count deletion...
                self.store.delete(currmac)
                del currmacs[macaddr]
        currmacs = None

        # Create REL_nicowner relationships for the newly created NIC nodes
        for macaddr in newmacs.keys():
            nic = newmacs[macaddr]
            if Store.is_abstract(nic):
                self.store.relate(drone, CMAconsts.REL_nicowner, nic, {'causes': True})
                #self.store.relate(drone, CMAconsts.REL_causes,   nic)

        # Now newmacs contains all the current info about our NICs - old and new...
        # Let's figure out what's happening with our IP addresses...

        primaryip = None

        for macaddr in newmacs.keys():
            mac = newmacs[macaddr]
            ifname = mac.ifname
            iptable = data[str(ifname)]['ipaddrs']
            currips = {}
            iplist = self.store.load_related(mac, CMAconsts.REL_ipowner, IPaddrNode)
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
                if netaddr.islocal():       # We ignore loopback addresses - might be wrong...
                    continue
                ipnode = self.store.load_or_create(IPaddrNode
                ,   domain=drone.domain, ipaddr=str(netaddr), cidrmask=cidrmask)
                ## FIXME: Not an ideal way to determine primary (preferred) IP address...
                ## it's a bit idiosyncratic to Linux...
                ## A better way would be to use their 'startaddr' (w/o the port)
                ## This uses the IP address they used to talk to us.
                if ifname == primaryifname  and primaryip is None and ipname == ifname:
                    primaryip = ipnode
                    drone.primary_ip_addr = str(primaryip.ipaddr)
                newips[str(netaddr)] = ipnode

            # compare the two sets of IP addresses (old and new)
            for ipaddr in currips.keys():
                currip = currips[ipaddr]
                if ipaddr in newips:
                    newips[ipaddr] = currip.update_attributes(newips[ipaddr])
                else:
                    del currips[ipaddr]
                    # @FIXME - this is a bug -- 'currip' is a string... - or _something_ is...
                    self.store.separate(mac, currip, CMAconsts.REL_ipowner)
                    # @TODO Needs to be a 'careful, complete' reference count deletion...
                    self.store.delete(currip)

            # Create REL_ipowner relationships for all the newly created IP nodes
            for ipaddr in newips.keys():
                ip = newips[ipaddr]
                self.store.relate_new(mac, CMAconsts.REL_ipowner, ip, {'causes': True})
                #self.store.relate(mac, CMAconsts.REL_causes,  ip)

@Drone.add_json_processor
class TCPDiscoveryListener(DiscoveryListener):
    'Class for TCP discovery handling'

    prio = DiscoveryListener.PRI_CORE
    wantedpackets = ('tcpdiscovery',)
    netstatipportpat = re.compile('(.*):([^:]*)$')

    # disable=R0914 means too many local variables...
    # disable=R0912 means too many branches
    # pylint: disable=R0914,R0912
    def processpkt(self, drone, unused_srcaddr, jsonobj):
        '''Add TCP listeners and clients.'''
        unused_srcaddr = unused_srcaddr # Make pylint happy
        data = jsonobj['data'] # The data portion of the JSON message
        if self.debug:
            self.log.debug('_add_tcplisteners(data=%s)' % data)

        assert(not Store.is_abstract(drone))
        allourips = drone.get_owned_ips()
        if self.debug:
            self.log.debug('Processing keys(%s)' % data.keys())
        newprocs = {}
        newprocmap = {}
        discoveryroles = {}
        for procname in data.keys():    # List of nanoprobe-assigned names of processes...
            procinfo = data[procname]
            if 'listenaddrs' in procinfo:
                if not CMAconsts.ROLE_server in discoveryroles:
                    discoveryroles[CMAconsts.ROLE_server] = True
                    drone.addrole(CMAconsts.ROLE_server)
            if 'clientaddrs' in procinfo:
                if not CMAconsts.ROLE_client in discoveryroles:
                    discoveryroles[CMAconsts.ROLE_client] = True
                    drone.addrole(CMAconsts.ROLE_client)
            #print >> sys.stderr, 'CREATING PROCESS %s!!' % procname
            processproc = self.store.load_or_create(ProcessNode, domain=drone.domain
            ,   processname=procname
            ,   host=drone.designation
            ,   pathname=procinfo.get('exe', 'unknown'), argv=procinfo.get('cmdline', 'unknown')
            ,   uid=procinfo.get('uid','unknown'), gid=procinfo.get('gid', 'unknown')
            ,   cwd=procinfo.get('cwd', '/'))
            assert hasattr(processproc, '_Store__store_node')
            processproc.JSON_procinfo = str(procinfo)

            newprocs[processproc.processname] = processproc
            newprocmap[procname] = processproc
            if self.store.is_abstract(processproc):
                self.store.relate(drone, CMAconsts.REL_hosting, processproc, {'causes':True})
            if self.debug:
                self.log.debug('procinfo(%s) - processproc created=> %s' % (procinfo, processproc))

        oldprocs = {}
        # Several kinds of nodes have the same relationship to the host...
        for proc in self.store.load_related(drone, CMAconsts.REL_hosting, GraphNode.factory):
            if not isinstance(proc, ProcessNode):
                continue
            assert hasattr(proc, '_Store__store_node')
            procname = proc.processname
            oldprocs[procname] = proc
            if not procname in newprocs:
                if len(proc.delrole(discoveryroles.keys())) == 0:
                    assert not Store.is_abstract(proc)
                    self.store.separate(drone, CMAconsts.REL_hosting, proc)
                    # @TODO Needs to be a 'careful, complete' reference count deletion...
                    print >> sys.stderr, ('TRYING TO DELETE node %s'
                    %   (procname))
                    for newprocname in newprocs:
                        print >> sys.stderr, ('*** new procs: proc.procname %s' 
                        %   (str(newprocname)))
                    print >> sys.stderr, ('*** DELETING proc: proc.procname %s: proc=%s' 
                    %   (str(procname), str(proc)))
                    self.store.delete(proc)

        for procname in data.keys(): # List of names of processes...
            processnode = newprocmap[procname]
            procinfo = data[procname]
            if self.debug:
                self.log.debug('Processing key(%s): proc: %s' % (procname, processnode))
            if 'listenaddrs' in procinfo:
                srvportinfo = procinfo['listenaddrs']
                processnode.addrole(CMAconsts.ROLE_server)
                for srvkey in srvportinfo.keys():
                    match = TCPDiscoveryListener.netstatipportpat.match(srvkey)
                    (ip, port) = match.groups()
                    self._add_serveripportnodes(drone, ip, int(port), processnode, allourips)
            if 'clientaddrs' in procinfo:
                clientinfo = procinfo['clientaddrs']
                processnode.addrole(CMAconsts.ROLE_client)
                for clientkey in clientinfo.keys():
                    match = TCPDiscoveryListener.netstatipportpat.match(clientkey)
                    (ip, port) = match.groups()
                    self._add_clientipportnode(drone, ip, int(port), processnode)

    def _add_clientipportnode(self, drone, ipaddr, servport, processnode):
        '''Add the information for a single client IPtcpportNode to the database.'''
        servip_name = str(pyNetAddr(ipaddr).toIPv6())
        servip = self.store.load_or_create(IPaddrNode, domain=drone.domain, ipaddr=servip_name)
        ip_port = self.store.load_or_create(IPtcpportNode, domain=drone.domain
        ,       ipaddr=servip_name, port=servport)
        self.store.relate_new(ip_port, CMAconsts.REL_baseip, servip, {'causes': True})
        self.store.relate_new(processnode, CMAconsts.REL_tcpclient, ip_port, {'causes': True})

    def _add_serveripportnodes(self, drone, ip, port, processnode, allourips):
        '''We create tcpipports objects that correspond to the given json object in
        the context of the set of IP addresses that we support - including support
        for the ANY ipv4 and ipv6 addresses'''
        netaddr = pyNetAddr(str(ip)).toIPv6()
        if netaddr.islocal():
            self.log.warning('add_serveripportnodes("%s"): address is local' % netaddr)
            return
        addr = str(netaddr)
        # Were we given the ANY address?
        anyaddr = netaddr.isanyaddr()
        for ipaddr in allourips:
            if not anyaddr and str(ipaddr.ipaddr) != addr:
                continue
            ip_port = self.store.load_or_create(IPtcpportNode, domain=drone.domain
            ,   ipaddr=ipaddr.ipaddr, port=port)
            assert hasattr(ip_port, '_Store__store_node')
            self.store.relate_new(processnode, CMAconsts.REL_tcpservice, ip_port)
            assert hasattr(ipaddr, '_Store__store_node')
            self.store.relate_new(ip_port, CMAconsts.REL_baseip, ipaddr)
            if not anyaddr:
                return
        if not anyaddr:
            print >> sys.stderr, ('LOOKING FOR %s in: %s'
            %       (netaddr, [str(ip.ipaddr) for ip in allourips]))
            raise ValueError('IP Address mismatch for Drone %s - could not find address %s'
            %       (drone, addr))

