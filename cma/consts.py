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


# R0903: too few public methods
# pylint: disable=R0903
class CMAconsts(object):
    '''
    This class holds the constants we use for the CMA.
    We make it a class to minimize namespace pollution.
    '''
    globaldomain    = 'global'
    metadomain      = 'metadata'

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
    NODE_monitoraction  = 'MonitorAction' # A (hopefully active) monitoring action
#
#       Relationship types [reltype enumeration values]
# ---------------------------------------------------------------
#   Constant name    reltype        fromnodetype       tonodetype
# ---------------    --------       ------------       ----------
    REL_isa         = 'IS_A'        # Any node          ->  NODE_nodetype
    REL_nicowner    = 'nicowner'    # NODE_NIC          ->  NODE_system - or subclass
    REL_wiredto     = 'wiredto'     # NODE_NIC          ->  NODE_NIC
    REL_ipowner     = 'ipowner'     # NODE_ipaddr       ->  NODE_NIC
    REL_parentring  = 'parentring'  # NODE_ring         ->  NODE_ring
    REL_baseip      = 'baseip'      # NODE_tcpipport    ->  NODE_ipaddr
    REL_tcpservice  = 'tcpservice'  # NODE_tcpipport    ->  NODE_ipproc
    REL_ipphost     = 'ipphost'     # NODE_tcpipport    ->  NODE_system or subclass
    REL_hosting     = 'hosting'     # NODE_drone        ->  NODE_ipproc
    REL_monitoring  = 'monitoring'  # NODE_monitoraction->  NODE_ipproc OR SystemNode
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
    ROLE_tb_bridge      = 'tb_bridge'       # Cisco CDP_CAPMASK_TBBRIDGE - TB (transparent) bridge
    ROLE_srcbridge      = 'srcbridge'       # Cisco SP (source route) Bridge CDP_CAPMASK_SPBRIDGE
    ROLE_router         = 'router'          # 802.11AB - Section 9.5.8.1
    ROLE_phone          = 'phone'           # 802.11AB - Section 9.5.8.1
    ROLE_AccessPoint    = 'WLANAP'          # 802.11AB - Section 9.5.8.1
    ROLE_DOCSIS         = 'DOCSIS'          # 802.11AB - Section 9.5.8.1
    ROLE_igmp           = 'igmp-filter'     # Cisco IGMP_FILTER CDP_CAPMASK_IGMPFILTER
    ROLE_Station        = 'station'         # 802.11AB - Section 9.5.8.1
    ROLE_UPS            = 'UPS'
    ROLE_CRAC           = 'crac'
    ROLE_sensor         = 'sensor'
    ROLE_drone          = 'drone'           # http://bit.ly/197K7e9
    ROLE_host           = 'host'
    ROLE_client         = 'client'
    ROLE_server         = 'server'


    classkeymap = {}
    uniqueindexes = {}

