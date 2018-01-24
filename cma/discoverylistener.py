#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100 fileencoding=utf-8
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2013,2014 - Assimilation Systems Limited
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
Discovery Listener infrastructure
This is the base class for code that wants to hear about various
discovery packets as they arrive.

More details are documented in the DiscoveryListener class
"""
from __future__ import print_function
import re
from sys import stderr
import os
from droneinfo import Drone
from consts import CMAconsts
from AssimCtypes import CONFIGNAME_TYPE, CONFIGNAME_INSTANCE, ADDR_FAMILY_IPV4
from AssimCclasses import pyNetAddr, pyConfigContext
from systemnode import ChildSystem

from graphnodes import NICNode, IPaddrNode, ProcessNode, IPtcpportNode, NetworkSegment, Subnet


class DiscoveryListener(object):
    """Class for listening to discovery packets
    We support three different categories/priorities of discovery actions
    as documented below:
    """

    PRI_CORE = 0              # This discovery plugin is part of the core system
    PRI_OPTION = 1             # This is an optional capability that comes with the system
    PRI_CONTRIB = 2             # This is a contributed (and optional) capability
    PRI_LIMIT = PRI_CONTRIB+1

    prio = PRI_CONTRIB
    wantedpackets = None

    def __init__(self, config, packetio, store, log, debug):
        """Init function for DiscoveryListener"""
        self.packetio = packetio
        self.store = store
        self.log = log
        self.debug = debug
        self.config = config

    @classmethod
    def priority(cls):
        """Return the priority (ordering) that this should be invoked at"""
        return cls.prio

    @classmethod
    def desiredpackets(cls):
        """Return the set of packets we want to be called for"""
        return cls.wantedpackets

    def processpkt(self, drone, srcaddr, json, discoverychanged):
        """A desired packet has been received - process it"""
        raise NotImplementedError('Abstract class - processpkt()')


@Drone.add_json_processor
class MonitoringAgentDiscoveryListener(DiscoveryListener):
    """Class for updating our agent cache when we get new monitoringagents information"""

    prio = DiscoveryListener.PRI_CORE
    wantedpackets = ('monitoringagents',)

    def processpkt(self, drone, srcaddr, jsonobj, discoverychanged):
        """Update the _agentcache when we get a new set of available agents"""
        if not discoverychanged:
            return
        # print ('SETTING MONITORING AGENTS: %s' %  jsonobj['data'], file=stderr)
        setattr(drone, '_agentcache', jsonobj['data'])


@Drone.add_json_processor
class AuditdConfDiscoveryListener(DiscoveryListener):
    """Class for discovering audit permissions"""

    prio = DiscoveryListener.PRI_CORE
    wantedpackets = ('auditd_conf',)

    def processpkt(self, drone, srcaddr, jsonobj, discoverychanged):
        """Request discovery of auditd (log) files and directories.
        They will be evaluated by some auditd best practice rules"""
        if not discoverychanged:
            return
        data = jsonobj['data']  # The data portion of the JSON message
        params = pyConfigContext()
        params['parameters'] = pyConfigContext()
        params[CONFIGNAME_TYPE] = 'fileattrs'
        params[CONFIGNAME_INSTANCE] = 'auditd_fileattrs'
        if 'log_file' in data:
            filelist = os.path.dirname(data['log_file']) + '/'
        else:
            filelist = '/var/log/audit/'
        params['parameters']['filelist'] = filelist
        params['parameters']['ASSIM_filelist'] = filelist
        # print('DISCOVERING %s' % str(params), file=stderr)
        # repeat, warn, and interval are automatically added
        drone.request_discovery((params,))


# R0912 -- too many branches
# R0914 -- too many local variables
# pylint: disable=R0914,R0912
@Drone.add_json_processor
class NetconfigDiscoveryListener(DiscoveryListener):
    """Class for the (initial) netconfig discovery packet"""

    prio = DiscoveryListener.PRI_CORE
    wantedpackets = ('netconfig',)

    @staticmethod
    def determine_scope_from_ifinfo(drone, ifinfo):
        """
        Determine the value for 'scope' from the interface information for this interface
        :param drone: SystemNode: System that this info is from
        :param ifinfo: dict-like: Interface information
        :return: str: scope value
        """
        if ifinfo['virtual']:
            return drone.designation
        return '_GLOBAL_'

    def guess_net_segment(self, system, if_info):
        """
        :param system: SystemNode: System Node that this inteface goes with...
        :param if_info: dict-like: single interface information from discovery
        :return: str
        """
        macaddr = str(if_info['address'])
        pairs = []
        for ip in if_info['ipaddrs']:
            iponly, _ = ip.split('/')
            addr = pyNetAddr(iponly)
            if addr.addrtype() != ADDR_FAMILY_IPV4:
                continue
            addr = str(addr.toIPv6())
            pairs.append((macaddr, addr))
        return NetworkSegment.guess_net_segment(self.store, system.domain, pairs)

    def processpkt(self, drone, _, jsonobj, discoverychanged):
        """Save away the network configuration data we got from netconfig JSON discovery.
        This includes all our NICs, their MAC addresses, all our IP addresses and so on
        for any (non-loopback) interface.  Whee!

        This code is more complicated than I'd like but it's not obvious how to simplify it...
        """
        assert drone.association.node_id is not None
        store = drone.association.store
        if not discoverychanged:
            return
        data = jsonobj['data']  # The data portion of the JSON message

        currmacs = {}   # Currmacs is a list of current NICNode objects belonging to this host
        #                 indexed by MAC address
        # Get our current list of NICs
        iflist = self.store.load_related(drone, CMAconsts.REL_nicowner)
        for nic in iflist:
            currmacs[nic.macaddr] = nic

        primaryifname = None
        net_segments = {}
        newmacs = {}    # Newmacs is a list of NICNode objects found/created by this discovery
        #                 indexed by MAC address
        for ifname in data.keys():  # List of interfaces just below the data section
            ifinfo = data[ifname]
            if 'address' not in ifinfo:
                continue
            macaddr = str(ifinfo['address'])
            net_segment = self.guess_net_segment(drone, ifinfo)
            net_segments[macaddr] = net_segment
            # A slightly more generous/forgiving find operation than load_or_create()
            newnic = NICNode.find_this_macaddr(store, drone.domain,  macaddr, system=drone,
                                               net_segment=net_segment)
            if newnic is None:
                scope = self.determine_scope_from_ifinfo(drone, ifinfo)
                newnic = self.store.load_or_create(NICNode,
                                                   domain=drone.domain,
                                                   scope=scope,
                                                   macaddr=macaddr,
                                                   ifname=ifname,
                                                   json=str(ifinfo),
                                                   net_segment=net_segment)
            newmacs[macaddr] = newnic
            if 'default_gw' in ifinfo and primaryifname is None:
                primaryifname = ifname

        # Now compare the two sets of MAC addresses (old and new) and update the "old" MAC
        # address with info from the new discovery and deleting any MAC addresses that
        # we don't have any more...
        for macaddr in currmacs.keys():
            currmac = currmacs[macaddr]
            if macaddr in newmacs:
                # This MAC may need updating
                newmacs[macaddr] = currmac.update_attributes(newmacs[macaddr])
            else:
                # This MAC has disappeared
                self.store.separate(drone, CMAconsts.REL_ipowner, currmac)
                # @TODO Needs to be a 'careful, complete' reference count deletion...
                # On the other hand, garbage collection is a good thought...
                self.store.delete(currmac)
                del currmacs[macaddr]
        del currmacs

        # Create REL_nicowner relationships for any newly created NIC nodes
        for macaddr in newmacs.keys():
            nic = newmacs[macaddr]
            self.store.relate_new(drone, CMAconsts.REL_nicowner, nic)

        # Now newmacs contains all the updated info about our current NICs
        # Let's figure out what's happening with our IP addresses...

        primaryip = None

        for macaddr in newmacs.keys():
            mac = newmacs[macaddr]
            ifname = mac.ifname
            # print ('MAC IS', str(mac), file=stderr)
            # print ('DATA IS:', str(data), file=stderr)
            # print ('IFNAME IS', str(ifname), file=stderr)
            iptable = data[str(ifname)]['ipaddrs']
            currips = {}
            iplist = self.store.load_related(mac, CMAconsts.REL_ipowner)
            for ip in iplist:
                currips[ip.ipaddr] = ip

            newips = {}
            for ip in iptable.keys():   # keys are 'ip/mask' in CIDR format
                ipinfo = iptable[ip]
                ipname = ipinfo.get('name', ':::INVALID:::')
                # if ipinfo['scope'] != 'global':
                #     continue
                print('PROCESSING IP %s' % ip, file=stderr)
                iponly, cidrmask = ip.split('/')
                netaddr = pyNetAddr(iponly).toIPv6()
                subnet_context = drone.designation if mac.virtual else '__GLOBAL__'
                #   This is a more forgiving/generous subnet finding algorithm than load_or_create
                subnet = Subnet.find_subnet(self.store,
                                            domain=drone.domain,
                                            ipaddr=iponly,
                                            cidrmask=int(cidrmask),
                                            context=subnet_context,
                                            net_segment=net_segments[macaddr])
                print('Creating/Finding IP %s' % str(netaddr), file=stderr)
                if subnet is None:
                    subnet = self.store.load_or_create(Subnet,
                                                       domain=drone.domain,
                                                       ipaddr=iponly,
                                                       cidrmask=int(cidrmask),
                                                       context=subnet_context,
                                                       net_segment=net_segments[macaddr])
                print('Creating/Finding IP %s on subnet [%s]' % (str(netaddr), str(subnet)),
                      file=stderr)
                ipnode = self.store.load_or_create(IPaddrNode,
                                                   ipaddr=str(netaddr),
                                                   domain=drone.domain,
                                                   subnet=subnet)

                # FIXME: Not an ideal way to determine primary (preferred) IP address...
                # it's a bit idiosyncratic to Linux...
                # A better way would be to use their 'startaddr' (w/o the port)
                # This uses the IP address they used to talk to us.
                if ifname == primaryifname and primaryip is None and ipname == ifname:
                    primaryip = ipnode
                    drone.primary_ip_addr = str(primaryip.ipaddr)
                newips[str(netaddr)] = ipnode

            # compare the two sets of IP addresses (old and new)
            for ipaddr in currips.keys():
                currip = currips[ipaddr]
                if ipaddr in newips:
                    newips[ipaddr] = currip.update_attributes(newips[ipaddr])
                else:
                    # print ('Deleting address %s from MAC %s' %  (currip, macaddr), file=stderr)
                    # print ('currip:%s, currips:%s' %  (str(currip), str(currips)), file=stderr)
                    self.log.debug('Deleting address %s from MAC %s' % (currip, macaddr))
                    self.log.debug('currip:%s, currips:%s' % (str(currip), str(currips)))
                    self.store.separate(mac, rel_type=CMAconsts.REL_ipowner, obj=currip)
                    # @TODO Needs to be a 'careful, complete' reference count deletion...
                    # @TODO May also need to delete a subnet if no other references...
                    # On the other hand, garbage collection is a good thought...
                    self.store.delete(currip)
                    del currips[ipaddr]

            # Create REL_ipowner relationships for all the newly created IP nodes
            for ipaddr in newips.keys():
                ip = newips[ipaddr]
                self.store.relate_new(mac, CMAconsts.REL_ipowner, ip)


@Drone.add_json_processor
class TCPDiscoveryListener(DiscoveryListener):
    """Class for TCP discovery handling"""

    prio = DiscoveryListener.PRI_CORE
    wantedpackets = ('tcpdiscovery',)
    netstatipportpat = re.compile('(.*):([^:]*)$')

    # disable=R0914 means too many local variables...
    # disable=R0912 means too many branches
    # pylint: disable=R0914,R0912
    def processpkt(self, drone, _, jsonobj, discoverychanged):
        """Add TCP listeners and clients."""
        if not discoverychanged:
            return
        data = jsonobj['data']   # The data portion of the JSON message
        if self.debug:
            self.log.debug('_add_tcplisteners(data=%s)' % data)

        allourips = drone.get_owned_ips()
        if self.debug:
            self.log.debug('Processing keys(%s)' % data.keys())
        newprocs = {}
        newprocmap = {}
        discoveryroles = {}
        for procname in data.keys():    # List of nanoprobe-assigned names of processes...
            procinfo = data[procname]
            if 'listenaddrs' in procinfo:
                if CMAconsts.ROLE_server not in discoveryroles:
                    discoveryroles[CMAconsts.ROLE_server] = True
                    drone.addrole(CMAconsts.ROLE_server)
            if 'clientaddrs' in procinfo:
                if CMAconsts.ROLE_client not in discoveryroles:
                    discoveryroles[CMAconsts.ROLE_client] = True
                    drone.addrole(CMAconsts.ROLE_client)
            # print ('CREATING PROCESS %s!!' % procname, file=stderr)
            processproc = self.store.load_or_create(ProcessNode, domain=drone.domain,
                                                    processname=procname,
                                                    host=drone.designation,
                                                    pathname=procinfo.get('exe', 'unknown'),
                                                    argv=procinfo.get('cmdline', 'unknown'),
                                                    uid=procinfo.get('uid', 'unknown'),
                                                    gid=procinfo.get('gid', 'unknown'),
                                                    cwd=procinfo.get('cwd', '/'))
            processproc.procinfo = str(procinfo)

            newprocs[processproc.processname] = processproc
            newprocmap[procname] = processproc
            self.store.relate_new(drone, CMAconsts.REL_hosting, processproc)
            if self.debug:
                self.log.debug('procinfo(%s) - processproc created=> %s' % (procinfo, processproc))

        oldprocs = {}
        # Several kinds of nodes have the same relationship to the host...
        for proc in self.store.load_related(drone, CMAconsts.REL_hosting):
            if not isinstance(proc, ProcessNode):
                continue
            procname = proc.processname
            oldprocs[procname] = proc
            if procname not in newprocs:
                if len(proc.delrole(discoveryroles.keys())) == 0:
                    self.store.separate(drone, CMAconsts.REL_hosting, proc)
                    # @TODO Needs to be a 'careful, complete' reference count deletion...
                    # On the other hand, garbage collection is a good thought...
                    print('TRYING TO DELETE node %s' % procname, file=stderr)
                    for newprocname in newprocs:
                        print('*** new procs: proc.procname %s' % str(newprocname), file=stderr)
                    print('*** DELETING proc: proc.procname %s: proc=%s'
                          % (str(procname), str(proc)), file=stderr)
                    self.store.delete(proc)

        for procname in data.keys():  # List of names of processes...
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
        """Add the information for a single client IPtcpportNode to the database."""
        servip_name = str(pyNetAddr(ipaddr).toIPv6())
        servip = self.store.load_or_create(IPaddrNode, domain=drone.domain, ipaddr=servip_name,
                                           subnet=None)
        ip_port = self.store.load_or_create(IPtcpportNode,
                                            domain=drone.domain,
                                            ipaddr=servip_name,
                                            port=servport)
        self.store.relate_new(ip_port, CMAconsts.REL_baseip, servip)
        self.store.relate_new(ip_port, CMAconsts.REL_tcpclient, processnode)

    def _add_serveripportnodes(self, drone, ip, port, processnode, allourips):
        """We create tcpipports objects that correspond to the given json object in
        the context of the set of IP addresses that we support - including support
        for the ANY ipv4 and ipv6 addresses"""
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
            ip_port = self.store.load_or_create(IPtcpportNode, domain=drone.domain,
                                                ipaddr=ipaddr.ipaddr, port=port)
            self.store.relate_new(processnode, CMAconsts.REL_tcpservice, ip_port)
            self.store.relate_new(ip_port, CMAconsts.REL_baseip, ipaddr)
            if not anyaddr:
                return
        if not anyaddr:
            print('LOOKING FOR %s (%s, %s) in: %s'
                  % (netaddr, type(ip), type(netaddr),
                     [str(ip.ipaddr) for ip in allourips]),
                  file=stderr)
            # raise ValueError('IP Address mismatch for Drone %s - could not find address %s'
            # %       (drone, addr))
            # Must not have been discovered yet. Hopefully discovery will come along and
            # fill in the cidrmask, and create the NIC relationship ;-)
            ipnode = self.store.load_or_create(IPaddrNode, domain=drone.domain, ipaddr=addr,
                                               subnet=None)
            allourips.append(ipnode)
            self._add_serveripportnodes(drone, addr, port, processnode, allourips)


@Drone.add_json_processor
class SystemSubclassDiscoveryListener(DiscoveryListener):
    """Listening for subsystem discovery results"""

    prio = DiscoveryListener.PRI_CORE
    wantedpackets = ('vagrant', 'docker')

    def processpkt(self, drone, _, jsonobj, discoverychanged):
        """ Kick off discovery for a Docker or vagrant instance - as though it were a
            real boy -- I mean a real Drone
        """
        if not discoverychanged:
            return

        data = jsonobj['data']
        if 'containers' not in data:
            return
        childtype = jsonobj['discovertype']
        systems = data['containers']
        # print('=====================GOT %s packet' % (childtype), file=stderr)
        discovery_types = self.config['containers'][childtype]['initial_discovery']
        for sysid in systems:
            system = ChildSystem.childfactory(drone, childtype, sysid, systems[sysid])
            # Connect it to its parent system
            self.store.relate_new(system, CMAconsts.REL_parentsys, drone)

            runspec = (' "runas_user": "%s",' % system.runas_user
                       if system.runas_user is not None else '')
            if system.runas_group is not None:
                runspec += ' "runas_group": "%s",' % system.runas_group

            allparams = []
            for dtype in discovery_types:
                # kick off discovery...
                instance = '_init_%s_%s' % (dtype, system.childpath)
                allparams.append(pyConfigContext(
                                        '{"%s": "%s", "%s": "%s",%s "parameters":{"%s": "%s"}}'
                                        % (CONFIGNAME_TYPE, dtype,
                                           CONFIGNAME_INSTANCE, instance,
                                           runspec,
                                           'ASSIM_PROXY_PATH', system.childpath)))
            # kick off discovery...
            # print('=====================REQUESTING DISCOVERY: %s' % (str(allparams)), file=stderr)
            system.request_discovery(allparams)
