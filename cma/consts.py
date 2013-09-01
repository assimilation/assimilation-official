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
'''
This module defines various constants used by the Assimilation CMA
'''

class CMAconsts(object):
    globaldomain = 'global'

#########################################################################
#       Indexes:
#       ringindex - index of all Ring objects [nodetype=ring]
#       droneindex - index of all Drone objects [nodetype=drone]
#       ipindex - index of all IP address objects [nodetype=ipaddr]
#       macindex - index of all interfaces by MAC address [nodetype=nic]
#########################################################################
#
#       Node types [nodetype enumeration values]:
#
    NODE_nodetype   = 'CMAclass'      # A type node - for all nodes of that type
    NODE_ring       = 'HbRing'        # A ring of Drones
    NODE_drone      = 'Drone'         # A server running our nanoprobes
    NODE_system     = 'SystemNode'    # A system without a nanoprobe - switches so far...
    NODE_NIC        = 'NICNode'       # A network interface card (connection)
    NODE_ipaddr     = 'IPaddrNode'    # IP address
    NODE_ipproc     = 'ProcessNode'   # A client and/or server process
    NODE_tcpipport  = 'IPtcpportNode' # (ip, port) tuple for a TCP service
#
#       Relationship types [reltype enumeration values]
# ---------------------------------------------------------------
#   Constant name    reltype        fromnodetype       tonodetype
# ---------------    --------       ------------       ----------
    REL_isa         = 'IS_A'        # Any node          ->  NODE_nodetype
    REL_nicowner    = 'nicowner'    # NODE_NIC          ->  NODE_system - or subclass
    REL_ipowner     = 'ipowner'     # NODE_ipaddr       ->  NODE_NIC
    REL_parentring  = 'parentring'  # NODE_ring         ->  NODE_ring
    REL_baseip      = 'baseip'      # NODE_tcpipport    ->  NODE_ipaddr
    REL_tcpservice  = 'tcpservice'  # NODE_tcpipport    ->  NODE_ipproc
    REL_ipphost     = 'ipphost'     # NODE_tcpipport    ->  NODE_drone
    REL_hosting     = 'hosting'     # NODE_drone        ->  NODE_ipproc
    REL_monitoringon= 'monitoringon'# NODE_ipproc       ->  NODE_drone
    REL_tcpclient   = 'tcpclient'   # NODE_ipproc       ->  NODE_tcpipport
    #                  RingMember_* # NODE_drone        ->  NODE_ring
    #                  RingNext_*   # NODE_drone        ->  NODE_drone
#
#   Node_System (or Node_Drone) Roles that we've heard of... Other roles are possible...
#
    ROLE_netfirewall    = 'netfirewall'
    ROLE_netbalancer    = 'loadbalancer'
    ROLE_repeater       = 'repeater'        # 802.11AB - Section 9.5.8.1
    ROLE_bridge         = 'bridge'          # 802.11AB - Section 9.5.8.1 (AKA a "switch")
    ROLE_router         = 'router'          # 802.11AB - Section 9.5.8.1
    ROLE_phone          = 'phone'           # 802.11AB - Section 9.5.8.1
    ROLE_AccessPoint    = 'WLANAP'          # 802.11AB - Section 9.5.8.1
    ROLE_DOCSIS         = 'DOCSIS'          # 802.11AB - Section 9.5.8.1
    ROLE_Station        = 'station'         # 802.11AB - Section 9.5.8.1
    ROLE_UPS            = 'UPS'
    ROLE_CRAC           = 'crac'
    ROLE_sensor         = 'sensor'
    ROLE_drone          = 'drone'           # http://bit.ly/197K7e9
    ROLE_host           = 'host'
    ROLE_client         = 'client'
    ROLE_server         = 'server'

#
#   Which object types are indexed
#
    is_indexed = {
        NODE_nodetype: True
    ,   NODE_ring:     True
    ,   NODE_drone:    True
    ,   NODE_system:   True
    ,   NODE_NIC:      True    # NICs are indexed by MAC address
                               # MAC addresses are not always unique...
    ,   NODE_ipaddr:   True    # Note that IPaddrs also might not be unique
    ,   NODE_tcpipport:True    # We index IP and port - handy to have...
    ,   NODE_ipproc:   True
    }

#
#   Which object types have unique indexes
#
    uniqueindexes = {
        NODE_nodetype: True
    ,   NODE_ring:     True
    ,   NODE_drone:    True
    ,   NODE_system:   True
    ,   NODE_NIC:      True    # NICs are indexed by MAC address
                               # MAC addresses are not always unique...
    ,   NODE_ipaddr:   True    # Note that IPaddrs also might not be unique
    ,   NODE_tcpipport:True
    ,   NODE_ipproc:   True
    }
    classkeymap = {
        NODE_nodetype:  {'index':NODE_nodetype,  'key': 'global',   'vattr': 'name'}
    ,   NODE_ring:      {'index':NODE_ring,      'key': 'global',   'vattr': 'name'}
    ,   NODE_drone:     {'index':NODE_drone,     'kattr':'domain',  'vattr': 'designation'}
    ,   NODE_system:    {'index':NODE_system,    'kattr':'domain',  'vattr': 'name'}
    ,   NODE_NIC:       {'index':NODE_NIC,       'kattr':'domain',  'vattr': 'macaddr'}
    ,   NODE_ipaddr:    {'index':NODE_ipaddr,    'kattr':'domain',  'vattr': 'ipaddr'}
    ,   NODE_tcpipport: {'index':NODE_tcpipport, 'kattr':'domain',  'vattr': 'ipport'}
    ,   NODE_ipproc:    {'index':NODE_ipproc,    'kattr':'domain',  'vattr': 'processname'}
    }
