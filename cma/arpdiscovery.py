#!/usr/bin/python
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
from AssimCtypes import ADDR_FAMILY_IPV4, ADDR_FAMILY_IPV6
from discoverylistener import DiscoveryListener
from droneinfo import Drone
from graphnodes import NICNode, IPaddrNode, GraphNode
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
    '''

    prio = DiscoveryListener.PRI_OPTION     # This is an optional feature
    wantedpackets = ('ARP',)                # We are only interested in hearing 'ARP' packets

    def processpkt(self, drone, unused_srcaddr, jsonobj):
        '''Add ARP discovery data to the database.
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
            self.add_mac_ip(drone, mac, maciptable[mac])


    def add_mac_ip(self, drone, macaddr, IPlist):
        '''We process all the IP addresses that go with a given MAC address (NICNode)
        The parameters are expected to be canonical address strings like str(pyNetAddr(...)).
        '''
        nicnode = self.store.load_or_create(NICNode, domain=drone.domain, macaddr=macaddr)
        if not Store.is_abstract(nicnode):
            # This NIC already existed - let's see what IPs it already owned
            currips = {}
            oldiplist = self.store.load_related(nicnode, CMAconsts.REL_ipowner, IPaddrNode)
            for ipnode in oldiplist:
                currips[ipnode.ipaddr] = ipnode
                print >> sys.stderr, ('IP %s already related to NIC %s' 
                %       (str(ipnode.ipaddr), str(nicnode.macaddr)))
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
            print >> sys.stderr, ('CREATING IP %s for NIC %s' 
            %       (str(ipnode.ipaddr), str(nicnode.macaddr)))
            if not Store.is_abstract(ipnode):
                # Then this IP address already existed,
                # but it wasn't related to our NIC...
                ## @TODO We should make sure it isn't related to a different NIC
                for oldnicnode in self.store.load_in_related(ipnode, CMAconsts.REL_ipowner
                    , GraphNode.factory):
                    self.store.separate(oldnicnode, CMAconsts.REL_ipowner, oldnicnode)
            print >> sys.stderr, ('RELATING NIC %s-[:ipowner]->IP %s' 
            %       (str(nicnode.macaddr), str(ipnode.ipaddr)))
            self.store.relate(nicnode, CMAconsts.REL_ipowner, ipnode)

