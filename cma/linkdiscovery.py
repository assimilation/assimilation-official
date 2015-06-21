#!/usr/bin/env python
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
Link (LLDP or CDP) Discovery Listener code.
This is the class for handling link discovery packets as they arrive.
It is a subclass of the DiscoveryListener class.

More details are documented in the LinkDiscoveryListener class
'''

from consts import CMAconsts
from store import Store
from AssimCclasses import pyNetAddr
from AssimCtypes import ADDR_FAMILY_IPV4, ADDR_FAMILY_IPV6, ADDR_FAMILY_802
from AssimCtypes import CONFIGNAME_INSTANCE
from AssimCtypes import CONFIGNAME_DEVNAME, CONFIGNAME_SWPROTOS
from discoverylistener import DiscoveryListener
from droneinfo import Drone
from graphnodes import NICNode, IPaddrNode, SystemNode
from cmaconfig import ConfigFile
import sys

@Drone.add_json_processor
class LinkDiscoveryListener(DiscoveryListener):
    '''Class for processing Link Discovery JSON messages
    We create the System nodes for switches we discover and
    any NIC nodes for the port we're connected to and any other
    NICs that the switch tells us about.
    We also create 'wiredto' relationships between host NICs and switch NICs.

    Note that all the CDP and LLDP packets are sent intact (in binary) from the
    nanoprobes then post-processed by the CMA to create the JSON which we
    receive here just as though the nanoprobe had sent us JSON in the first place.
    '''

    prio = DiscoveryListener.PRI_OPTION
    wantedpackets = ('__LinkDiscovery', 'netconfig')

    #R0914:684,4:LinkDiscoveryListener.processpkt: Too many local variables (25/15)
    # pylint: disable=R0914

    def processpkt(self, drone, unused_srcaddr, jsonobj):
        '''Trigger Switch discovery or add Low Level (Link Level) discovery data to the database.
        '''
        if jsonobj['discovertype'] == '__LinkDiscovery':
            self.processpkt_linkdiscovery(drone, unused_srcaddr, jsonobj)
        elif jsonobj['discovertype'] == 'netconfig':
            self.processpkt_netconfig(drone, unused_srcaddr, jsonobj)
        else:
            print >> sys.stderr, 'OOPS! bad packet type [%s]', jsonobj['discovertype']

    def processpkt_netconfig(self, drone, unused_srcaddr, jsonobj):
        '''We want to trigger Switch discovery when we hear a 'netconfig' packet

        Build up the parameters for the discovery
        action, then send it to drone.request_discovery(...)
        To build up the parameters, you use ConfigFile.agent_params()
        which will pull values from the system configuration.
        '''

        unused_srcaddr = unused_srcaddr # make pylint happy
        init_params = ConfigFile.agent_params(self.config, 'discovery', '#SWITCH'
        ,   drone.designation)

        data = jsonobj['data'] # the data portion of the JSON message
        print >> sys.stderr, "*** SWITCH DISCOVERY on:", str(data)
        discovery_args = []
        for devname in data.keys():
            print >> sys.stderr, "*** SWITCH DISCOVERY devname:", devname
            devinfo = data[devname]
            if (str(devinfo['operstate']) == 'up' and str(devinfo['carrier']) == 'True'
                                          and str(devinfo['address']) != '00-00-00-00-00-00'
                                          and str(devinfo['address']) != ''):
                params = dict(init_params)
                params[CONFIGNAME_INSTANCE] = '#SWITCH_' + devname
                params[CONFIGNAME_DEVNAME] = devname
                params[CONFIGNAME_SWPROTOS] = ["lldp", "cdp"]
                #print >> sys.stderr, '***#SWITCH parameters:', params
                discovery_args.append(params)
        if discovery_args:
            drone.request_discovery(discovery_args)

    def processpkt_linkdiscovery(self, drone, unused_srcaddr, jsonobj):
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
        unused_srcaddr = unused_srcaddr
        data = jsonobj['data']
        #print >> sys.stderr, 'SWITCH JSON:', str(data)
        if 'ChassisId' not in data:
            self.log.warning('Chassis ID missing from discovery data from switch [%s]'
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
        attrs['designation'] =  chassisid
        #### FIXME What should the domain of a switch default to?
        attrs['domain'] =  drone.domain
        switch = self.store.load_or_create(SystemNode, **attrs)

        if not 'SystemCapabilities' in data:
            switch.addrole(CMAconsts.ROLE_bridge)
        else:
            caps = data['SystemCapabilities']
            for role in caps.keys():
                if caps[role]:
                    switch.addrole(role)
            #switch.addrole([role for role in caps.keys() if caps[role]])


        if 'ManagementAddress' in attrs:
            self._process_mgmt_addr(switch, chassisid, attrs)
        self._process_ports(drone, switch, chassisid, data['ports'])

    def _process_mgmt_addr(self, switch, chassisid, attrs):
        'Process the ManagementAddress field in the LLDP packet'
        # FIXME - not sure if I know how I should do this now - no MAC address for mgmtaddr?
        mgmtaddr = attrs['ManagementAddress']
        mgmtnetaddr = pyNetAddr(mgmtaddr)
        atype = mgmtnetaddr.addrtype()
        if atype == ADDR_FAMILY_IPV4 or atype == ADDR_FAMILY_IPV6:
            # MAC addresses are permitted, but IP addresses are preferred
            chassisaddr = pyNetAddr(chassisid)
            chassistype = chassisaddr.addrtype()
            if chassistype == ADDR_FAMILY_802: # It might be an IP address instead
                adminnic = self.store.load_or_create(NICNode, domain=switch.domain
                ,       macaddr=chassisid, ifname='(adminNIC)')
                mgmtip = self.store.load_or_create(IPaddrNode, domain=switch.domain
                ,           cidrmask='unknown', ipaddr=mgmtaddr)
                if Store.is_abstract(adminnic) or Store.is_abstract(switch):
                    self.store.relate(switch, CMAconsts.REL_nicowner, adminnic)
                if Store.is_abstract(mgmtip) or Store.is_abstract(adminnic):
                    self.store.relate(adminnic, CMAconsts.REL_ipowner, mgmtip)
            else:
                self.log.info('LLDP ATTRS: %s' % str(attrs))
                if mgmtnetaddr != chassisaddr:
                    # Not really sure what I should be doing in this case...
                    self.log.warning(
                    'Chassis ID [%s] not a MAC addr and not the same as mgmt addr [%s]'
                    %   (chassisid, mgmtaddr))
                    self.log.warning('Chassis ID [%s] != mgmt addr [%s]'
                    %   (str(mgmtnetaddr), str(chassisaddr)))
        elif atype == ADDR_FAMILY_802:
            mgmtnic = self.store.load_or_create(NICNode, domain=switch.domain
            ,       macaddr=mgmtaddr, ifname='(ManagementAddress)')
            if Store.is_abstract(mgmtnic) or Store.is_abstract(switch):
                self.store.relate(switch, CMAconsts.REL_nicowner, mgmtnic)
    def _process_ports(self, drone, switch, chassisid, ports):
        'Process the ports listed in JSON data from switch discovery'

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
            nicnode = self.store.load_or_create(NICNode, domain=drone.domain
            ,   macaddr=nicmac, **attrs)
            self.store.relate(switch, CMAconsts.REL_nicowner, nicnode, {'causes': True})
            try:
                assert thisport['ConnectsToHost'] == drone.designation
                matchif = thisport['ConnectsToInterface']
                niclist = self.store.load_related(drone, CMAconsts.REL_nicowner, NICNode)
                for dronenic in niclist:
                    if dronenic.ifname == matchif:
                        self.store.relate_new(nicnode, CMAconsts.REL_wiredto, dronenic)
                        break
            except KeyError:
                self.log.error('OOPS! got an exception...')
