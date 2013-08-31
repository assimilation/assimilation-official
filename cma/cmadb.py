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
            print >> sys.stderr,  'self.store:', self.store
            result = self.store.commit()
            print >> sys.stderr, 'COMMIT results:', result
        else:
            print >> sys.stderr, 'Cool! Everything already created!'


    def delete_all(self):
        'Empty everything out of our database - start over!'
        query = neo4j.CypherQuery(self.db
        ,   'start n=node(*) match n-[r?]-() where id(n) <> 0 delete n,r')
        result = query.execute()
        if CMAdb.debug:
            CMAdb.log.debug('Cypher query to delete all relationships'
                ' and nonzero nodes executing: %s' % query)
            CMAdb.log.debug('Execution results: %s' % str(result))

    @staticmethod
    def dump_nodes(nodetype='Drone', stream=sys.stderr):
        'Dump all our drones out to the given stream (defaults to sys.stderr)'
        idx = CMAdb.cdb.indextbl[nodetype]
        query= '%s:*' % nodetype
        #print >> stream, 'QUERY against %s IS: "%s"' % (idx, query)
        dronelist = idx.query(query)
        print >> stream, 'List of %ss: %s' % (nodetype, dronelist)
        for drone in dronelist:
            print >> stream, ('%s %s (%s,%s)' % (nodetype, drone['name']
            ,   drone.id, drone.get_properties()))
            for rel in drone.match(bidirectional=True):
                start=rel.start_node
                end=rel.end_node
                if start.id == drone.id:
                    print >> stream, '    (%s)-[%s]->(%s:%s,%s)' \
                    %       (drone['name'], rel.type, end['nodetype'], end['name'], end.id)
                else:
                    print >> stream, '    (%s:%s,%s)-[%s]->(%s)' \
                    %       (start['name'], start['nodetype'], start.id, rel.type, drone['name'])
                if start.id == end.id:
                    print >> stream, 'SELF-REFERENCE to %s' % start.id
        



    def node_OLDnew(self, nodetype, nodename, unique=True, **properties):
        '''Possibly creates a new node, puts it in its appropriate index and creates an IS_A
        relationship with the nodetype object corresponding its nodetype.
        It is created and added to indexes if it doesn't already exist in its corresponding index
        - if there is one.
        If it already exists, the pre-existing node is returned.
        If this object type doesn't have an index, it will always be created.
        Note that the nodetype has to be in the nodetypetable - even if it's NULL
            (for error detection).
        The IS_A relationship may be useful -- or not.  Hard to say at this point...
        '''
        assert nodetype is not None and nodename is not None
        unique = False
        if nodetype in CMAdb.uniqueindexes and CMAdb.uniqueindexes[nodetype]:
            unique = True
        tbl = {}
        obj = None
        for key in properties.keys():
            tbl[key] = str(properties[key])
        tbl['name'] = nodename
        tbl['type'] = nodetype
        print >> sys.stderr, 'CREATING %s object with name %s [u=%s]' % (nodetype, nodename, unique)
        if unique:
            idx = self.indextbl[nodetype]
            obj = idx.get(nodetype, nodename)
            print >> sys.stderr, 'idx.get(%s,%s) returned %s' % (nodetype, nodename, obj)
            if len(obj) > 0:
                obj = obj[0]
                for key in tbl.keys():
                    obj[key] = tbl[key]
                print >> sys.stderr, 'Retrieved %s object named %s [%s]' % (nodetype, nodename, obj)
            else:
                print >> sys.stderr, 'did NOT Retrieve %s object named %s' % (nodetype, nodename)
                obj = None
        if obj is None:
            obj = neo4j.Node.abstract(**tbl)
            trans  = CMAdb.transaction
            obj.LABELID = self.next_label()
            trans.namespace[obj.LABELID] = True
            trans.add_nodes({'type':nodetype, 'name': nodename, 'attributes': tbl
            ,       'defines': obj.LABELID})
        for key in tbl.keys():
            obj[key] = tbl[key]
        print >> sys.stderr, 'CREATED %s object with id %s' % (nodetype, obj.id)
        return obj

    def OLDnew_ring(self, name, parentring=None, **kw):
        'Create a new ring (or return a pre-existing one), and put it in the ring index'
        ring = self.node_OLDnew(CMAdb.NODE_ring, name, unique=True,  **kw)

        if parentring is not None:
            self.db.get_or_create_relationships((ring, CMAdb.REL_parentring, parentring.node),)
        return ring

    def OLDnew_drone(self, designation, **kw):
        'Create a new drone (or return a pre-existing one), and put it in the drone index'
        #print >> sys.stderr,  'Adding drone', designation
        drone = self.node_OLDnew(CMAdb.NODE_drone, designation, unique=True, **kw)
        if not 'status' in drone:
            drone['status'] = 'created'
        return drone

    def OLDnew_switch(self, designation, **kw):
        'Create a new switch (or return a pre-existing one), and put it in the switch index'
        #print >> sys.stderr,  'Adding switch', designation
        switch = self.node_OLDnew(CMAdb.NODE_system, designation, unique=True, **kw)
        if not 'status' in switch:
            switch['status'] = 'created'
        return switch

    def OLDnew_nic(self, nicname, macaddr, owner, **kw):
        '''Create a new NIC (or return a pre-existing one), and put it in the mac address index,
        and point it at its parent owner.'''

        try:
            owningnode = owner.node
        except AttributeError:
            owningnode = owner
        
        macnics = self.macindex.get(CMAdb.NODE_NIC, macaddr)
        for mac in macnics:
            if CMAdb.debug:
                CMAdb.log.debug('MAC IS: %s' %  mac)
                if mac.is_related_to(owningnode, neo4j.Direction.OUTGOING, CMAdb.REL_nicowner):
                    CMAdb.log.debug('MAC %s is nicowner related to owner %s' \
                    %       (str(mac), str(owner)))
                    CMAdb.log.debug('MAC address = %s, NICname = %s for owner %s' \
                    %       (mac['address'], mac['nicname'], owner))
                else:
                    CMAdb.log.debug('MAC %s is NOT nicowner related to owner %s' 
                    %       (str(mac), str(owner)))

            if mac.is_related_to(owningnode, neo4j.Direction.OUTGOING, CMAdb.REL_nicowner) \
            and mac['address'] == macaddr and mac['nicname'] == nicname:
                return mac
        mac = self.node_OLDnew(CMAdb.NODE_NIC, macaddr, address=macaddr
        ,       unique=False, nicname=nicname, **kw)
        ###mac.create_relationship_to(owningnode, CMAdb.REL_nicowner)
        CMAdb.transaction.add_rels({'from': mac, 'to': owningnode, 'type': CMAdb.REL_nicowner})
        return mac

    def OLDnew_ipaddr(self, nic, ipaddr, **kw):
        '''Create a new IP address (or return a pre-existing one), and point it at its parent
        NIC and its grandparent drone'''
        ipaddr = str(pyNetAddr(ipaddr).toIPv6())
        if CMAdb.debug:
            CMAdb.log.debug('Adding IP address %s' % (ipaddr))
        ipaddrs = self.ipindex.get(CMAdb.NODE_ipaddr, ipaddr)
        if nic is not None:
            for ip in ipaddrs:
                if ip.is_related_to(nic, neo4j.Direction.OUTGOING, CMAdb.REL_ipowner):
                    #print >> sys.stderr \
                    #,  'Found this IP address (%s) ipowner-related to NIC %s' % (ipaddr, nic)
                    return ip
        if len(ipaddrs) == 0:
            ip = self.node_OLDnew(CMAdb.NODE_ipaddr, ipaddr, unique=False, **kw)
        else:
            ip = ipaddrs[0] # May have been created by a client - pick the first one...
        if nic is not None:
            CMAdb.transaction.add_rels({'from': ip, 'to': nic, 'type': CMAdb.REL_nicowner})
            ###ip.create_relationship_to(nic, CMAdb.REL_ipowner)
            ###>drone = nic.get_single_related_node(neo4j.Direction.OUTGOING, CMAdb.REL_nicowner)
            ###ip.create_relationship_to(drone, CMAdb.REL_iphost)
            ###>CMAdb.transaction.add_rels({'from': ip, 'to': drone, 'type': CMAdb.REL_iphost})
        return ip

    #NODE_ipproc     = 'ipproc'     # A client and/or server process
    def OLDnew_ipproc(self,            ##< Self... The usual self object
                   name,            ##< What should we be called? (no index)
                   jsonobj,         ##< The JSON ConfigContext object for us alone...
                   drone):          ##< Drone we are running on
        '''Create a new ipproc object from its JSON discovery data'''
        table = {}
        if CMAdb.debug:
            CMAdb.log.debug('Entering new_ipproc()')
        if CMAdb.debug:
            CMAdb.log.debug('new_ipproc(): keys = %s' % jsonobj.keys())
        for key in jsonobj.keys():
            if CMAdb.debug:
                CMAdb.log.debug('new_ipproc(): processing key = %s' % key)
            objtype = jsonobj.gettype(key)
            if CMAdb.debug:
                CMAdb.log.debug('new_ipproc(): key is of type %s' % type)
            if CMAdb.debug and objtype == CFG_ARRAY:
                CMAdb.log.debug('new_ipproc(): key %s is an array' % (key))
            if not (objtype == CFG_BOOL or objtype == CFG_INT64 or objtype == CFG_STRING
            or      objtype == CFG_FLOAT or objtype == CFG_ARRAY):
                continue
            if jsonobj[key] is None:
                continue
            if CMAdb.debug and objtype == CFG_ARRAY:
                CMAdb.log.debug('jsonobj[%s] is NOT None' % (key))
            # We assume any arrays are of same-typed simple objects (presumably Strings)
            # This is a reasonable assumption for our process discovery data
            if CMAdb.debug:
                CMAdb.log.debug('new_ipproc(): jsonobj[%s] = %s' % (key, jsonobj[key]))
            table[key] = jsonobj[key]
        ipproc = self.node_OLDnew(CMAdb.NODE_ipproc, name, unique=False, **table)
        self.db.get_or_create_relationships((ipproc, CMAdb.REL_runningon, drone),)

        return ipproc


    def OLDnew_tcpipport(self,         ##< Self... The usual self object
                   name,            ##< What is our name? (not indexed - yet)
                   isserver,        ##< Either CMAdb.REL_
                   jsonobj,         ##< The JSON object for this listen object
                   dronenode,       ##< The drone hosting this service
                   ipproc,          ##< The process running here...
                   ipaddrnode):     ##< A Neo4j IPaddr node
        '''Create a new (ip, port) object related to some IPaddr object'''
        port = jsonobj['port']
        table = {}
        for key in jsonobj.keys():
            objtype = jsonobj.gettype(key)
            if not (objtype == CFG_BOOL or objtype == CFG_INT64 or objtype == CFG_STRING
            or      objtype == CFG_FLOAT or objtype == CFG_ARRAY):
                continue
            table[key] = jsonobj[key]
        tcpipport = self.node_OLDnew(CMAdb.NODE_tcpipport, name, unique=True, **table)
        ## FIXME? Should I make this relationship a REL_baseip + ':' + port type?
        if isserver:
            args =    (
                (tcpipport,    CMAdb.REL_baseip,        ipaddrnode, {'port':port}),
                (tcpipport,    CMAdb.REL_tcpservice,    ipproc),
                (tcpipport,    CMAdb.REL_ipphost,       dronenode))
        else:
            args =    (
                (tcpipport, CMAdb.REL_baseip,           ipaddrnode, {'port':port}),
                (ipproc,    CMAdb.REL_tcpclient,        tcpipport))
        CMAdb.cdb.db.get_or_create_relationships(*args)

if __name__ == '__main__':
    print >> sys.stderr, 'Starting'
    CMAdb.initglobal(None, cleanoutdb=True)
    print >> sys.stderr, 'Init done'
