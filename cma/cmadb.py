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
This module defines our CMAdb class and so on...
'''

import os
import sys
import logging, logging.handlers
from py2neo import neo4j, cypher
#from AssimCtypes import *
from AssimCtypes import CFG_ARRAY, CFG_BOOL, CFG_INT64, CFG_STRING, CFG_ARRAY, CFG_FLOAT
from AssimCclasses import pyNetAddr
from store import Store

class CMAclass(object):
    '''Class defining the relationships of our CMA classes to each other'''
    RELTYPE = "IS_A"

    def __init__(self, name):
        self.name = name
        self.domain = CMAdb.globaldomain
        self.nodetype = CMAdb.NODE_nodetype


class CMAdb:
    '''Class defining our Neo4J database.'''

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
    REL_isa         = CMAclass.RELTYPE# Any node        ->  Any node
    REL_causes      = 'causes'      # Any node          ->  Any node
    REL_nicowner    = 'nicowner'    # NODE_NIC          ->  NODE_system - or subclass
    REL_wiredto     = 'wiredto'     # NODE_NIC          ->  NODE_system - or subclass
    REL_ipowner     = 'ipowner'     # NODE_ipaddr       ->  NODE_NIC
    REL_parentring  = 'parentring'  # NODE_ring         ->  NODE_ring
    REL_baseip      = 'baseip'      # NODE_tcpipport    ->  NODE_ipaddr
    REL_tcpservice  = 'tcpservice'  # NODE_tcpipport    ->  NODE_ipproc
    REL_ipphost     = 'ipphost'     # NODE_tcpipport    ->  NODE_drone
    REL_runningon   = 'runningon'   # NODE_ipproc       ->  NODE_drone
    REL_monitoringon= 'monitoringon'# NODE_ipproc       ->  NODE_drone
    REL_tcpclient   = 'tcpclient'   # NODE_ipproc       ->  NODE_tcpipport
    #                  RingMember_* # NODE_drone        ->  NODE_ring
    #                  RingNext_*   # NODE_drone        ->  NODE_drone
#
#   Node_System (or Node_Drone) Roles that we've heard of... Other roles are possible...
#
    ROLE_switch         = 'switch'
    ROLE_netfirewall    = 'netfirewall'
    ROLE_netbalancer    = 'loadbalancer'
    ROLE_repeater       = 'repeater'        # 802.11AB - Section 9.5.8.1
    ROLE_bridge         = 'bridge'          # 802.11AB - Section 9.5.8.1
    ROLE_router         = 'router'          # 802.11AB - Section 9.5.8.1
    ROLE_telephone      = 'phone'           # 802.11AB - Section 9.5.8.1
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


    nodename = os.uname()[1]
    debug = True
    transaction = None
    log = None
    store = None
    globaldomain = 'global'


    def __init__(self, db=None):
        if db is None:
            url = ('http://%s:%d/db/data/' % (host, port))
            print >> sys.stderr, 'CREATING GraphDatabaseService("%s")' % url
            db = neo4j.GraphDatabaseService(url)
            print >> sys.stderr, 'CREATED %s' % url
        self.db = db
        CMAdb.store = Store(self.db, CMAdb.uniqueindexes,CMAdb.classkeymap)
        self.dbversion = self.db.neo4j_version
        self.nextlabelid = 0
        if CMAdb.debug:
            CMAdb.log.debug('Neo4j version: %s' % str(self.dbversion))
            print >> sys.stderr, ('HELP Neo4j version: %s' % str(self.dbversion))
    #
    #   Make sure all our indexes are present and that we
    #   have a top level node for each node type for creating
    #   IS_A relationships to.  Not sure if the IS_A relationships
    #   are really needed, but they're kinda cool...
    #
        
        indices = [key for key in CMAdb.is_indexed.keys() if CMAdb.is_indexed[key]]
        self.indextbl = {}
        self.nodetypetbl = {}
        for index in indices:
            print >>sys.stderr, ('Ensuring index %s exists' % index)
            self.indextbl[index] = self.db.get_index(neo4j.Node, index)
            self.indextbl[index] = self.db.get_or_create_index(neo4j.Node, index)
        #print >>sys.stderr, ('Ensuring index %s exists' % 'nodetype')
        self.indextbl['nodetype'] = self.db.get_or_create_index(neo4j.Node, 'nodetype')
        nodetypeindex = self.indextbl['nodetype']
        
        nodezero = CMAdb.store.load_or_create(CMAclass, name='object')
        print >> sys.stderr, 'nodezero', nodezero

        for index in CMAdb.is_indexed.keys():
            print >>sys.stderr, 'Creating CMAclass object/node for Class %s' % index
            top = CMAdb.store.load_or_create(CMAclass, name=index)
            print >>sys.stderr, 'Relating type %s to node zero (object)' % index
            CMAdb.store.relate_new(top, CMAclass.RELTYPE, nodezero)
            self.nodetypetbl[index] = top
            
        self.ringindex = self.indextbl[CMAdb.NODE_ring]
        self.ipindex = self.indextbl[CMAdb.NODE_ipaddr]
        self.macindex = self.indextbl[CMAdb.NODE_NIC]
        self.switchindex = self.indextbl[CMAdb.NODE_system]
        self.droneindex = self.indextbl[CMAdb.NODE_drone]
        if self.store.transaction_pending:
            #print >> sys.stderr,  'self.store:', self.store
            result = self.store.commit()
            #print >> sys.stderr, 'COMMIT results:', result
        else:
            print >> sys.stderr, 'Cool! Everything already created!'


if __name__ == '__main__':
    from cmainit import CMAinit
    print >> sys.stderr, 'Starting'
    CMAinit(None, cleanoutdb=True, debug=True)
    print >> sys.stderr, 'Init done'
