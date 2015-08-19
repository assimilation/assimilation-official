#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2014 - Assimilation Systems Limited
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
ARP Discovery Listener code.
This is the class for handling ARP discovery packets as they arrive.
These packets include data from all nanoprobe-observed ARP packets - broadcast and unicast.
It is a subclass of the DiscoveryListener class.

More details are documented in the ArpDiscoveryListener class
'''

from consts import CMAconsts
from store import Store
from AssimCclasses import pyNetAddr
from AssimCclasses import pyConfigContext
from AssimCtypes import ADDR_FAMILY_IPV4, ADDR_FAMILY_IPV6
from AssimCtypes import CONFIGNAME_INSTANCE, CONFIGNAME_DEVNAME
from discoverylistener import DiscoveryListener
from droneinfo import Drone
from graphnodes import NICNode, IPaddrNode, GraphNode
from cmaconfig import ConfigFile
import netaddr
import sys

@Drone.add_json_processor   # Register ourselves to process discovery packets
class ArpDiscoveryListener(DiscoveryListener):
    '''Class for processing ARP cache discovery entries.
    The data section contains (IPaddress, MACaddress) pairs as a hash table (JSON object)
    Nanoprobes currently send their entire cache each time anything shows up

    For interest, here are some default ARP cache timeouts as of this writing:
        Linux         300 seconds
        Solaris       300 seconds
        Windows       600 seconds
        AIX          1200 seconds
        FreeBSD      1200 seconds
        NetBSD       1200 seconds
        OpenBSD      1200 seconds
        VMWare       1200 seconds
        Cisco       14400 seconds

    For large subnets, it would be much more efficient to send only changes --
    additions and deletions -- but that's not what we currently do :-D

    @TODO: Change ARP updates to give deltas

    If we changed the nanoprobes to send delta updates, then you wouldn't particularly
    want a 20 minute timeout - you'd want something more like a few minutes
    so that they came a few at a time to the CMA.  This would keep the CMA from
    being bottlenecked by massive updates if you have a subnet with a lot of IP
    addresses on it.  It also means that we would not get 1024 entries just because
    one came online...

    Of course, a lot of what causes this code to be really slow is the fact that we
    hit the database with a transaction for each IP and each MAC that we find in the
    message.
    '''

    prio = DiscoveryListener.PRI_OPTION     # This is an optional feature
    # We are interested in two kinds of packets:
    # netconfig:    Packets from network configuration discovery
    #               When we hear these we send requests to listen to ARPs
    #               This is what eventually causes ARP discovery packets to be sent
    # ARP:          Packets resulting from ARP discovery - triggered by
    #               the requests we send above...
    wantedpackets = ('ARP', 'netconfig')

    ip_map = {}
    mac_map = {}

    def processpkt(self, drone, srcaddr, jsonobj):
        '''Trigger ARP discovery or add ARP data to the database.
        '''
        if jsonobj['discovertype'] == 'ARP':
            self.processpkt_arp(drone, srcaddr, jsonobj)
        elif jsonobj['discovertype'] == 'netconfig':
            self.processpkt_netconfig(drone, srcaddr, jsonobj)
        else:
            print >> sys.stderr, 'OOPS! bad packet type [%s]', jsonobj['discovertype']

    def processpkt_netconfig(self, drone, unused_srcaddr, jsonobj):
        '''We want to trigger ARP discovery when we hear a 'netconfig' packet

        Build up the parameters for the discovery
        action, then send it to drone.request_discovery(...)
        To build up the parameters, you use ConfigFile.agent_params()
        which will pull values from the system configuration.
        '''

        unused_srcaddr = unused_srcaddr # make pylint happy
        init_params = ConfigFile.agent_params(self.config, 'discovery', '#ARP', drone.designation)
        netconfiginfo = pyConfigContext(jsonobj)
        

        data = jsonobj['data'] # the data portion of the JSON message
        discovery_args = []
        for devname in data.keys():
            #print >> sys.stderr, "*** devname:", devname
            devinfo = data[devname]
            if (str(devinfo['operstate']) == 'up' and str(devinfo['carrier']) == 'True'
                                          and str(devinfo['address']) != '00-00-00-00-00-00'
                                          and str(devinfo['address']) != ''):
                params = dict(init_params)
                params[CONFIGNAME_INSTANCE] = '#ARP_' + devname
                params[CONFIGNAME_DEVNAME] = devname
                #print >> sys.stderr, '#ARP parameters:', params
                discovery_args.append(params)
        if discovery_args:
            drone.request_discovery(discovery_args)

    def processpkt_arp(self, drone, unused_srcaddr, jsonobj):
        '''We want to update the database when we hear a 'ARP' discovery packet
        These discovery entries are the result of listening to ARP packets
        in the nanoprobes.  Some may already be in our database, and some may not be.

        As we process the packets we create any IPaddrNode and NICNode objects
        that correspond to the things we've discovered.  Since IP addresses
        can move around, we potentially need to clean up relationships to 
        NICNodes - so that any given IP address is only associated with a single
        MAC address.

        As noted in the class docs, the data we get is organized by IP address.
        This means that a single MAC address (NIC) may appear multiple times in the
        discovery data.

        One interesting question is what we should default the domain to for MACs and IPs
        that we create.  My thinking is that defaulting them to the domain of the Drone
        that did the discovery is a reasonable choice.
        '''

        data = jsonobj['data']
        maciptable = {}
        # Group the IP addresses by MAC address - reversing the map
        for ip in data.keys():
            mac = str(data[ip])
            if mac not in maciptable:
                maciptable[mac] = []
            maciptable[mac].append(ip)

        for mac in maciptable:
            self.filtered_add_mac_ip(drone, mac, maciptable[mac])

    def filtered_add_mac_ip(self, drone, macaddr, IPlist):
        '''We process all the IP addresses that go with a given MAC address (NICNode)
        The parameters are expected to be canonical address strings like str(pyNetAddr(...)).

        Lots of the information we're given is typically repeats of information we
        were given before.  This is why we keep these two in-memory maps
        - to help speed that up by a huge factor.
        '''
        for ip in IPlist:
            if ArpDiscoveryListener.ip_map.get(ip) != macaddr:
                self.add_mac_ip(drone, macaddr, IPlist)
                for ip in IPlist:
                    ArpDiscoveryListener.ip_map[ip] = macaddr
                    if macaddr not in ArpDiscoveryListener.mac_map:
                        ArpDiscoveryListener.mac_map[macaddr] = []
                    if ip not in ArpDiscoveryListener.mac_map[macaddr]:
                        ArpDiscoveryListener.mac_map[macaddr].append(ip)
                return

    def add_mac_ip(self, drone, macaddr, IPlist):
        '''We process all the IP addresses that go with a given MAC address (NICNode)
        The parameters are expected to be canonical address strings like str(pyNetAddr(...)).
        '''
        nicnode = self.store.load_or_create(NICNode, domain=drone.domain, macaddr=macaddr)
        macprefix = str(nicnode.macaddr)[0:8]
        try:
            org = str(netaddr.EUI(nicnode.macaddr).oui.registration().org)
        except netaddr.NotRegisteredError:
            local_OUI_map = self.config['OUI']
            if macprefix in local_OUI_map:
                org = local_OUI_map[macprefix]
            else:
                org = macprefix
        if not Store.is_abstract(nicnode):
            # This NIC already existed - let's see what IPs it already owned
            currips = {}
            oldiplist = self.store.load_related(nicnode, CMAconsts.REL_ipowner, IPaddrNode)
            for ipnode in oldiplist:
                currips[ipnode.ipaddr] = ipnode
                #print >> sys.stderr, ('IP %s already related to NIC %s'
                #%       (str(ipnode.ipaddr), str(nicnode.macaddr)))
            # See what IPs still need to be added
            ips_to_add = []
            for ip in IPlist:
                if ip not in currips:
                    ips_to_add.append(ip)
            # Replace the original list of IPs with those not already there...
            IPlist = ips_to_add

        # Now we have a NIC and IPs which aren't already related to it
        for ip in IPlist:
            ipnode = self.store.load_or_create(IPaddrNode, domain=drone.domain
            ,       ipaddr=ip)
            #print >> sys.stderr, ('CREATING IP %s for NIC %s'
            #%       (str(ipnode.ipaddr), str(nicnode.macaddr)))
            if not Store.is_abstract(ipnode):
                # Then this IP address already existed,
                # but it wasn't related to our NIC...
                # Make sure it isn't related to a different NIC
                for oldnicnode in self.store.load_in_related(ipnode, CMAconsts.REL_ipowner
                    , GraphNode.factory):
                    self.store.separate(oldnicnode, CMAconsts.REL_ipowner, ipnode)
            print >> sys.stderr, ('RELATING (%s)-[:ipowner]->(%s)	[%s]'
            %       (str(nicnode.macaddr), str(ipnode.ipaddr), org))
            self.store.relate(nicnode, CMAconsts.REL_ipowner, ipnode)
            if org != macprefix and not hasattr(nicnode, 'OUI'):
                nicnode.OUI = org

