#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
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

import sys
from consts import CMAconsts
from store import Store
from AssimCclasses import pyConfigContext
from AssimCtypes import CONFIGNAME_INSTANCE, CONFIGNAME_DEVNAME
from discoverylistener import DiscoveryListener
from graphnodes import NICNode, IPaddrNode, NetworkSegment, Subnet
from systemnode import SystemNode
from cmaconfig import ConfigFile
from linkdiscovery import discovery_indicates_link_is_up

@SystemNode.add_json_processor   # Register ourselves to process discovery packets
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

    def processpkt(self, drone, srcaddr, jsonobj, discoverychanged):
        '''Trigger ARP discovery or add ARP data to the database.
        '''
        if not discoverychanged:
            return
        if jsonobj['discovertype'] == 'ARP':
            self.processpkt_arp(drone, srcaddr, jsonobj)
        elif jsonobj['discovertype'] == 'netconfig':
            self.processpkt_netconfig(drone, srcaddr, jsonobj)
        else:
            print >> sys.stderr, 'OOPS! unexpected packet type [%s]', jsonobj['discovertype']

    def processpkt_netconfig(self, drone, _unused_srcaddr, jsonobj):
        '''We want to trigger ARP discovery when we hear a 'netconfig' packet

        Build up the parameters for the discovery
        action, then send it to drone.request_discovery(...)
        To build up the parameters, you use ConfigFile.agent_params()
        which will pull values from the system configuration.
        '''

        init_params = ConfigFile.agent_params(self.config, 'discovery', '#ARP', drone.designation)

        data = jsonobj['data'] # the data portion of the JSON message
        discovery_args = []
        for devname in data.keys():
            #print >> sys.stderr, "*** devname:", devname
            devinfo = data[devname]
            if discovery_indicates_link_is_up(devinfo):
                params = pyConfigContext(init_params)
                params[CONFIGNAME_INSTANCE] = '_ARP_' + devname
                params[CONFIGNAME_DEVNAME] = devname
                #print >> sys.stderr, '#ARP parameters:', params
                discovery_args.append(params)
        if discovery_args:
            drone.request_discovery(discovery_args)

    def processpkt_arp(self, drone, _unused_srcaddr, jsonobj):
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
        device_name = jsonobj['device']
        device = self.find_nic(device_name)
        mac_ip_table = {}
        # Group the IP addresses by MAC address - reversing the map
        for ip, mac in data.viewitems():
            macstr = str(mac)
            if macstr not in mac_ip_table:
                mac_ip_table[macstr] = []
            mac_ip_table[macstr].append(ip)

        net_segment = self.find_net_segment(drone, device, mac_ip_table)
        device.net_segment = net_segment.name

        for mac, ip in mac_ip_table.viewitems():
            self.filtered_add_mac_ip(drone, device, net_segment, mac, ip)
        self.fix_net_segment(net_segment, mac_ip_table)

    def find_net_segment(self, drone, device, mac_ip_table):
        """
        Figure out which network segment this Drone belongs to...

        :param drone: Drone:  this NIC segment is attached to
        :param device: NICNode: device these ARPs were heard on
        :param mac_ip_table: Table of IPs associated with NICs
        :return: NetworkSegment
        """
        if device.net_segment is not None:
            return drone.store.load(domain=device.domain, name=device.net_segment)
        mac_ip_pairs = []
        for mac, ip_list in mac_ip_table.viewitems():
            for ip in ip_list:
                mac_ip_pairs.append((mac, ip))
        segment = NetworkSegment.guess_net_segment(device.domain, mac_ip_pairs)
        if segment is not None:
            return self.store.load(NetworkSegment, domain=device.domain, name=segment)
        return self.store.load_or_create(NetworkSegment, domain=device.domain)

    def fix_net_segment(self, domain, device, net_segment, mac_ip_table):
        """
        Fix up the network segment for the MAC/IP pairs on this network segment
        :param domain: str: Domain for created IP/MAC addresses
        :param device: NICNode: device where this was discovered
        :param net_segment: NetworkSegment: our network segment
        :param mac_ip_table: MAC/IP map - organized by MAC address
        :return: None
        """
        mac_ip_query = """
        MATCH(nic:Class_NICNode)-[:ipowner]->(ip:Class_IPaddrNode)
        WHERE ip.ipaddr in $ipaddrs AND nic.macaddr in $macaddrs
        AND (nic.net_segment = $net_segment OR nic.net_segment IS NULL)
        RETURN nic, ip
        """
        # Our algorithm is as follows:
        # - Find all the IP,MAC pairs that are either in our network segment, or could be part of
        #   our network segment, and update the network segment of those that aren't yet in any
        #   network segment.
        # - along the way, collect the set of subnets that the IP addresses belong to, and the
        #   IP addresses that don't belong to any subnet yet
        # - All those pairs that don't yet exist, create them, and link them together and
        #   make them part of our network segment
        # - Walk through the IP addresses we've collected, and make them part of one of these
        #   subnets if we can.
        #
        #   Something I haven't throught through yet...
        #   What happens when a MAC address gets a new IP address?
        #
        mac_ip_pairs = set()
        mac_list = []
        ip_list = []
        for mac, ip_list in mac_ip_table.viewitems():
            mac_list.append(mac)
            for ip in ip_list:
                mac_ip_pairs.add((mac, ip))
                ip_list.append(ip)
        parameters = {
            'ipaddrs': ip_list,
            'macaddrs': mac_list,
            'net_segment': net_segment
        }
        missing_pairs = mac_ip_pairs
        found_pairs = set()
        found_subnets = {}

        for mac, ip in self.store.load_cypher_query(mac_ip_query, parameters):
            if (mac.macaddr, ip.ipaddr) not in missing_pairs:
                # Could be a mismatched pair...
                continue
            missing_pairs.remove((mac.macaddr, ip.ipaddr))
            found_pairs.add((mac, ip))
            if mac.net_segment is None:
                mac.net_segment = net_segment
            if ip.subnet is not None and ip.subnet not in found_subnets:
                found_subnets[ip.subnet] = Subnet.find_subnet_by_name(self.store, ip.subnet)
        # Now we have a list of all the (MAC, IP) pairs that are missing...
        scope = '_GLOBAL_'
        self.create_missing_mac_ip_pairs(domain, device.scope, net_segment,
                                         missing_pairs, found_subnets)
        self.fix_ip_subnets(found_subnets, ip_list)

    def create_missing_mac_ip_pairs(self, domain, scope, net_segment, missing_pairs, found_subnets):
        """
        Create all the missing (mac, IP) pairs
        :param domain: str: domain for IP and MAC addresses
        :param scope: str: scope for created MAC addresses
        :param net_segment: str: the network segment to associate them with
        :param missing_pairs: set((str,str)) - set of (mac, IP) addresses in canonical form
        :param found_subnets: set(Subnet) - list of subnets found on this network segment
        :return: None
        """
        for mac, ip in missing_pairs:
            # find_this_macaddr is a more generous find operation than load_or_create()...
            nic = NICNode.find_this_macaddr(self.store, domain=domain,  macaddr=mac,
                                            net_segment=net_segment)
            if nic is None:
                nic = self.store.load_or_create(NICNode, domain=domain, macaddr=mac,
                                                scope=scope, net_segment=net_segment)
            subnet = Subnet.find_matching_subnet(ip, found_subnets)
            # FIXME: THIS IS BROKEN!!!
            other_ip = self.store.load_related(nic, CMAconsts.REL_ipowner)
            if other_ip is not None:
                if other_ip.ipaddr == ip:
                    other_ip.subnet = subnet
                    return
                else:
                    self.store.separate(nic, CMAconsts.REL_ipowner, other_ip)
                    other_ip = None
            ipnode = self.store.load_or_create(IPaddrNode, ipaddr=ip, domain=domain, subnet=subnet)
            self.store.relate(nic, CMAconsts.REL_ipowner, ipnode)

    def fix_ip_subnets(self, found_subnets, ip_list):
        """
        Fix up the subnets of everything we can on this Network Segment

        :param found_subnets:
        :param ip_list:
        :return:
        """
        for ip in ip_list:
            subnet = Subnet.find_matching_subnet(ip, found_subnets)
            if subnet is not None:
                ip.subnet = subnet.name

    def filtered_add_mac_ip(self, drone, device, net_segment, macaddr, ip_list):
        '''We process all the IP addresses that go with a given MAC address (NICNode)
        The parameters are expected to be canonical address strings like str(pyNetAddr(...)).

        Lots of the information we're given is typically repeats of information we
        were given before.  This is why we keep these two in-memory maps
        - to help speed that up by a huge factor.
        '''
        for ip in ip_list:
            if ArpDiscoveryListener.ip_map.get(ip) != macaddr:
                self.add_mac_ip(drone, device, net_segment, macaddr, ip_list)
                # FIXME: I'm not sure what this 2nd loop is doing... This looks broken...
                for ip2 in ip_list:
                    ArpDiscoveryListener.ip_map[ip2] = macaddr
                    if macaddr not in ArpDiscoveryListener.mac_map:
                        ArpDiscoveryListener.mac_map[macaddr] = []
                    if ip not in ArpDiscoveryListener.mac_map[macaddr]:
                        ArpDiscoveryListener.mac_map[macaddr].append(ip2)
                return

    def add_mac_ip(self, drone, device, net_segment, macaddr, ip_list):
        '''We process all the IP addresses that go with a given MAC address (NICNode)
        The parameters are expected to be canonical address strings like str(pyNetAddr(...)).
        '''
        nicnode = self.store.load_or_create(NICNode, domain=drone.domain, macaddr=macaddr)
        currips = {}
        oldiplist = self.store.load_related(nicnode, CMAconsts.REL_ipowner)
        for ipnode in oldiplist:
            currips[ipnode.ipaddr] = ipnode
            # print >> sys.stderr, ('IP %s already related to NIC %s'
            # %       (str(ipnode.ipaddr), str(nicnode.macaddr)))
        # See what IPs still need to be added
        ips_to_add = []
        for ip in ip_list:
            if ip not in currips:
                ips_to_add.append(ip)
        # Replace the original list of IPs with those not already there...
        ip_list = ips_to_add

        # Now we have a NIC and IPs which aren't already related to it
        for ip in ip_list:
            ipnode = self.store.load_or_create(IPaddrNode, domain=drone.domain, ipaddr=ip)
            # print >> sys.stderr, ('CREATING IP %s for NIC %s'
            # %       (str(ipnode.ipaddr), str(nicnode.macaddr)))
        # Make sure it isn't related to a different NIC
            for oldnicnode in self.store.load_in_related(ipnode, CMAconsts.REL_ipowner):
                self.store.separate(oldnicnode, CMAconsts.REL_ipowner, ipnode)
            self.store.relate(nicnode, CMAconsts.REL_ipowner, ipnode)
