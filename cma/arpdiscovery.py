#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100 fileencoding=utf-8
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

"""
ARP Discovery Listener code.
This is the class for handling ARP discovery packets as they arrive.
These packets include data from all nanoprobe-observed ARP packets - broadcast and unicast.
It is a subclass of the DiscoveryListener class.

More details are documented in the ArpDiscoveryListener class
"""

from __future__ import print_function
from sys import stderr
from consts import CMAconsts
from AssimCclasses import pyConfigContext
from AssimCtypes import CONFIGNAME_INSTANCE, CONFIGNAME_DEVNAME
from discoverylistener import DiscoveryListener
from graphnodes import NICNode, IPaddrNode, NetworkSegment, Subnet
from systemnode import SystemNode
from cmaconfig import ConfigFile
from linkdiscovery import discovery_indicates_link_is_up


@SystemNode.add_json_processor   # Register ourselves to process discovery packets
class ArpDiscoveryListener(DiscoveryListener):
    """
    Class for processing ARP cache discovery entries.
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
    """

    prio = DiscoveryListener.PRI_OPTION     # This is an optional feature
    # We are interested in two kinds of packets:
    # netconfig:    Packets from network configuration discovery
    #               When we hear these we send requests to listen to ARPs
    #               This is what eventually causes ARP discovery packets to be sent
    # ARP:          Packets resulting from ARP discovery - triggered by
    #               the requests we send above...
    wantedpackets = ('ARP', 'netconfig')

    def processpkt(self, drone, srcaddr, jsonobj, discoverychanged):
        """
        Trigger ARP discovery or add ARP data to the database.

        :param drone: SystemNode: who discovered this?
        :param srcaddr: pyNetAddr: address this came from
        :param jsonobj: dict: discovery JSON as object
        :param discoverychanged: bool: TRUE if this discovery has changed
        :return: None
        """
        if not discoverychanged:
            return
        if jsonobj['discovertype'] == 'ARP':
            self.processpkt_arp(drone, srcaddr, jsonobj)
        elif jsonobj['discovertype'] == 'netconfig':
            self.processpkt_netconfig(drone, srcaddr, jsonobj)
        else:
            self.log.warning('Unexpected ArpDiscovery packet type [%s]' % jsonobj['discovertype'])
            print('OOPS! unexpected ArpDiscovery packet type [%s]'
                  % jsonobj['discovertype'], file=stderr)

    def processpkt_netconfig(self, drone, _unused_srcaddr, jsonobj):
        """
        We want to trigger ARP discovery when we hear a 'netconfig' packet

        Build up the parameters for the discovery
        action, then send it to drone.request_discovery(...)
        To build up the parameters, you use ConfigFile.agent_params()
        which will pull values from the system configuration.

        :param drone: SystemNode: who discovered this?
        :param _unused_srcaddr: pyNetAddr: address this came from
        :param jsonobj: dict: discovery JSON as object
        :return: None
        """
        init_params = ConfigFile.agent_params(self.config, 'discovery', '#ARP', drone.designation)

        data = jsonobj['data']  # the data portion of the JSON message
        discovery_args = []
        for devname in data.keys():
            # print ("*** devname:", devname, file=stderr)
            devinfo = data[devname]
            if discovery_indicates_link_is_up(devinfo):
                params = pyConfigContext(init_params)
                params[CONFIGNAME_INSTANCE] = '_ARP_' + devname
                params[CONFIGNAME_DEVNAME] = devname
                # print('#ARP parameters:', params, file=stderr)
                discovery_args.append(params)
        if discovery_args:
            drone.request_discovery(discovery_args)

    def processpkt_arp(self, drone, _unused_srcaddr, jsonobj):
        """
        Process ARP (cache) packets when they come in

        We want to update the database when we hear a 'ARP' discovery packet
        These discovery entries are the result of listening to ARP packets
        in the nanoprobes.  Some may already be in our database, and some may not be.

        As we process the packets we create any IPaddrNode and NICNode objects
        that correspond to the things we've discovered.

        Since IP addresses can move around, we potentially need to clean up relationships to
        NICNodes - so that any given IP address is only associated with a single
        MAC address.

        We also create a NetworkSegment object for this network segment, and associate it with
        all the MAC addresses we deal with. We also try and update Subnets for any IP addresses
        we find on this subnet. If this network segment only has one Subnet associated with it,
        and this NIC has an IP address associated with it, then we get them all set up correctly.

        As noted in the class docs, the data we get is organized by IP address.
        This means that a single MAC address (NIC) may appear multiple times in the
        discovery data.

        As it stands now, not sure what to do about removed (MAC,IP) pairs...
        @FIXME: Nanoprobe code needs to time out MAC/IP entries, and we need to deal with
        having the IP address removed. MAC addresses in some sense never go away...
        We also need to deal with the fact that a given MAC address might show up on different
        subnets at different times - WiFi, VPN, etc

        :param drone: SystemNode: system node (Drone) that heard this packet
        :param _unused_srcaddr: IPaddrNode: unused - address that this packet came from
        :param jsonobj: dict-like: the JSON from the discovery - rendered into a dict-like thing
        :return:
        """

        data = jsonobj['data']
        device_name = jsonobj['device']
        device = drone.find_nic(device_name)
        if drone is None:
            raise(ValueError("Cannot find NIC %s for drone %s" % (device_name, str(drone))))
        mac_ip_table = {}
        # Group the IP addresses by MAC address - inverting the map
        for ip, mac in data.viewitems():
            macstr = str(mac)
            if macstr not in mac_ip_table:
                mac_ip_table[macstr] = []
            mac_ip_table[macstr].append(ip)

        net_segment = self.find_net_segment(drone, device, mac_ip_table)
        device.net_segment = net_segment.name
        self.fix_net_segment(domain=drone.domain, device=device, net_segment=net_segment,
                             mac_ip_table=mac_ip_table)

    def find_net_segment(self, _drone, device, mac_ip_table):
        """
        Figure out which network segment this device belongs to or create one if its new...

        :param _drone: Drone:  this NIC segment is attached to
        :param device: NICNode: device these ARPs were heard on
        :param mac_ip_table: Table of IPs associated with NICs
        :return: NetworkSegment
        """
        if device.net_segment is not None:
            return self.store.load(NetworkSegment, domain=device.domain, name=device.net_segment)
        mac_ip_pairs = []
        for mac, ip_list in mac_ip_table.viewitems():
            for ip in ip_list:
                mac_ip_pairs.append((mac, ip))
        segment = NetworkSegment.guess_net_segment(self.store, device.domain, mac_ip_pairs)
        self.store.log.debug("Guess_net_segment() returned %s" % segment)
        if segment is None:
            result = self.store.load_or_create(NetworkSegment, domain=device.domain)
        else:
            result = self.store.load(NetworkSegment, domain=device.domain, name=segment.name)
        return result

    # pylint - too many local variables
    # pylint: disable=R0914
    def fix_net_segment(self, domain, device, net_segment, mac_ip_table):
        """
        Fix up the network segment for the MAC/IP pairs on this network segment
        :param domain: str: Domain for created IP/MAC addresses
        :param device: NICNode: device that heard the ARP packets
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
        #   Something I haven't completely thought through yet...
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
        found_subnets = set()
        subnet_names = set()

        for mac, ip in self.store.load_cypher_query(mac_ip_query, parameters):
            if (mac.macaddr, ip.ipaddr) not in missing_pairs:
                # Could be a mismatched pair or a new/old IP for this same MAC
                continue
            missing_pairs.remove((mac.macaddr, ip.ipaddr))
            found_pairs.add((mac, ip))
            mac.net_segment = net_segment
            if ip.subnet is not None and ip.subnet not in subnet_names:
                found_subnets.add(Subnet.find_subnet_by_name(self.store, ip.subnet))
                subnet_names.add(ip.subnet)
        Subnet.normalize_subnet_set(found_subnets)  # This removes duplicate/overlapping subnets
        # Now we have a list of all the missing (MAC, IP) pairs - create them
        self.create_missing_mac_ip_pairs(domain, device.scope, net_segment,
                                         missing_pairs, found_subnets)
        self.fix_ip_subnets(found_subnets, [pair[1] for pair in found_pairs])

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
            # find_this_macaddr is a more "generous" find operation than load_or_create()...
            nic = NICNode.find_this_macaddr(self.store, domain=domain,  macaddr=mac,
                                            net_segment=net_segment)
            if nic is None:
                nic = self.store.load_or_create(NICNode, domain=domain, macaddr=mac,
                                                scope=scope, net_segment=net_segment)
            subnet = Subnet.find_matching_subnet(ip, found_subnets)
            other_ip = None
            for other_ip in self.store.load_related(nic, CMAconsts.REL_ipowner):
                if other_ip.ipaddr == ip:
                    other_ip.subnet = subnet
                    break  # Strange... It already exists...
            if other_ip is None or other_ip.ipaddr != ip:
                ipnode = self.store.load_or_create(IPaddrNode, ipaddr=ip,
                                                   domain=domain, subnet=subnet)
                self.store.relate(nic, CMAconsts.REL_ipowner, ipnode)

    @staticmethod
    def fix_ip_subnets(found_subnets, ip_list):
        """
        Fix up the subnets of everything we can on this Network Segment.
        "We can" means we _know_ which subnet a particular IP address goes with.

        :param found_subnets: Iterable(Subnet): Candidate subnets
        :param ip_list: Iterable(IPaddrNode): IP addresses to fix up with their subnets
        :return:
        """
        for ip in ip_list:
            subnet = Subnet.find_matching_subnet(ip, found_subnets)
            if subnet is not None:
                ip.subnet = subnet.name
