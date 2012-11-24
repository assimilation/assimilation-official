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

import sys
import logging, logging.handlers
from py2neo import neo4j, cypher
from hbring import HbRing

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
    NODE_nodetype   = 'nodetype'    # A type node - for all nodes of that type
    NODE_ring       = 'Ring'        # A ring of Drones
    NODE_drone      = 'Drone'       # A server running our nanoprobes
    NODE_switch     = 'Switch'      # An IP communications device
    NODE_NIC        = 'NIC'         # A network interface card (connection)
    NODE_ipaddr     = 'IPaddr'      # IP address
    NODE_ipproc     = 'tcp-process' # A TCP client and/or server process
    NODE_tcpipport  = 'IP:tcpport'  # (ip, port) tuple for a TCP service
#
#       Relationship types [reltype enumeration values]
# ---------------------------------------------------------------
#   Constant name    reltype        fromnodetype       tonodetype
# ---------------    --------       ------------       ----------
    REL_isa         = 'IS_A'        # Any node          ->  NODE_nodetype
    REL_nicowner    = 'nicowner'    # NODE_NIC          ->  NODE_drone (or NODE_switch)
    REL_wiredto     = 'wiredto'     # NODE_NIC          ->  NODE_drone (or NODE_switch)
    REL_iphost      = 'iphost'      # NODE_ipaddr       ->  NODE_drone (or NODE_switch)
    REL_ipowner     = 'ipowner'     # NODE_ipaddr       ->  NODE_NIC
    REL_parentring  = 'parentring'  # NODE_ring         ->  NODE_ring
    REL_baseip      = 'baseip'      # NODE_tcpipport    ->  NODE_ipaddr
    REL_ipphost     = 'ipphost'     # NODE_tcpipport    ->  NODE_drone
    REL_tcpservice  = 'tcpservice'  # NODE_tcpipport    ->  NODE_ipproc
    REL_ipphost     = 'ipphost'     # NODE_tcpipport    ->  NODE_drone
    REL_runningon   = 'runningon'   # NODE_ipproc       ->  NODE_drone
    REL_tcpclient   = 'tcpclient'   # NODE_ipproc       ->  NODE_tcpipport

    debug = False


    def __init__(self, host='localhost', port=7474):
        url = ('http://%s:%d/db/data/' % (host, port))
        self.db = neo4j.GraphDatabaseService(url)
        self.dbversion = self.db.neo4j_version
        if CMAdb.debug:
            CMAdb.log.debug('Neo4j version: %s' % str(self.dbversion))
    #
    #   Make sure all our indexes are present and that we
    #   have a top level node for each node type for creating
    #   IS_A relationships to.  Not sure if the IS_A relationships
    #   are really needed, but they're kinda cool...
    #
        nodetypes = {
            CMAdb.NODE_ring:    True
        ,   CMAdb.NODE_drone:   True
        ,   CMAdb.NODE_switch:  True
        ,   CMAdb.NODE_NIC:     True    # NICs are indexed by MAC address
                                        # MAC addresses are not always unique...
        ,   CMAdb.NODE_ipaddr:  True    # Note that IPaddrs also might not be unique
        ,   CMAdb.NODE_tcpipport:  True    # We index IP and port - handy to have...
        ,   CMAdb.NODE_ipproc:  False
        }
        
        indices = [key for key in nodetypes.keys() if nodetypes[key]]
        self.indextbl = {}
        self.nodetypetbl = {}
        for index in indices:
            #print >>sys.stderr, ('Ensuring index %s exists' % index)
            self.indextbl[index] = self.db.get_or_create_index(neo4j.Node, index)
        #print >>sys.stderr, ('Ensuring index %s exists' % 'nodetype')
        self.indextbl['nodetype'] = self.db.get_or_create_index(neo4j.Node, 'nodetype')
        nodetypeindex = self.indextbl['nodetype']
        nodezero = self.db.get_node(0)
        for index in nodetypes.keys():
            top =  nodetypeindex.get_or_create('nodetype', index
        ,                      {'name':index, 'nodetype':'nodetype'})
            self.nodetypetbl[index] = top
            #print >>sys.stderr, 'Relating type %s to node zero' % index
            if not top.has_relationship_with(nodezero):
               top.create_relationship_to(nodezero, CMAdb.REL_isa)
            
        self.ringindex = self.indextbl[CMAdb.NODE_ring]
        self.ipindex = self.indextbl[CMAdb.NODE_ipaddr]
        self.macindex = self.indextbl[CMAdb.NODE_NIC]
        self.switchindex = self.indextbl[CMAdb.NODE_switch]
        self.droneindex = self.indextbl[CMAdb.NODE_drone]

    @staticmethod
    def initglobal(io, cleanoutdb=False):
        CMAdb.io = io
        CMAdb.cdb = CMAdb()
        if cleanoutdb:
            #print >>sys.stderr, 'Re-initializing the database'
            CMAdb.cdb.delete_all()
            CMAdb.cdb = CMAdb()
        CMAdb.TheOneRing =  HbRing('The_One_Ring', HbRing.THEONERING)
        CMAdb.log = logging.getLogger('cma')
        syslog = logging.handlers.SysLogHandler(address='/dev/log'
        ,       facility=logging.handlers.SysLogHandler.LOG_DAEMON)
        syslog.setFormatter(logging.Formatter('%(name)s %(levelname)s: %(message)s'))
        CMAdb.log.addHandler(syslog)
        CMAdb.log.setLevel(logging.DEBUG)

    def delete_all(self):
        query = cypher.Query(self.db
        ,   'start n=node(*) match n-[r?]-() where id(n) <> 0 delete n,r')
        result = query.execute()
        if CMAdb.debug:
            CMAdb.log.debug('Cypher query to delete all relationships and nonzero nodes executing: %s' % query)
            CMAdb.log.debug('Execution results: %s' % str(result))

    def node_new(self, nodetype, nodename, unique=True, **properties):
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
        properties['nodetype'] = nodetype
        properties['name'] = nodename
        tbl = {}
        for key in properties.keys():
            tbl[key] = properties[key]
        tbl['nodetype'] = nodetype
        tbl['name'] = nodename
        if nodetype in self.indextbl:
             idx = self.indextbl[nodetype]
             #print 'CREATING A [%s] object named [%s] with attributes %s' % (nodetype, nodename, str(tbl.keys()))
             if unique:
                 #print >>sys.stderr, 'NODETYPE: %s; NODENAME:%s tbl:%s' % (nodetype, nodename, str(tbl))
                 obj = idx.get_or_create(nodetype, nodename, tbl)
             else:
                 obj = self.db.create_node(tbl)
                 idx.add(nodetype, nodename, obj)
        else:
            #print >>sys.stderr, 'self.db.CREATING AN UNINDEXED[%s] object named [%s] with attributes %s [%s]' % (nodetype, nodename, str(tbl.keys()), str(tbl))
            #print >>sys.stderr, 'self.db.attribute: attribute table: %s' % (str(tbl))

            obj = self.db.create_node(tbl)
        ntt = self.nodetypetbl[nodetype]
        self.db.relate((obj, CMAdb.REL_isa, ntt),)
        #print 'CREATED/reused %s object with id %d' % (nodetype, obj.id)
        return obj


    def new_ring(self, name, parentring=None, **kw):
        'Create a new ring (or return a pre-existing one), and put it in the ring index'
        ring = self.node_new(CMAdb.NODE_ring, name, unique=True,  **kw)
        if parentring is not None:
            self.db.relate((ring, CMAdb.REL_parentring, parentring.node),)
        return ring

    def new_drone(self, designation, **kw):
        'Create a new drone (or return a pre-existing one), and put it in the drone index'
        #print 'Adding drone', designation
        drone = self.node_new(CMAdb.NODE_drone, designation, unique=True, **kw)
        if not 'status' in drone:
            drone['status'] = 'created'
        return drone

    def new_switch(self, designation, **kw):
        'Create a new switch (or return a pre-existing one), and put it in the switch index'
        #print 'Adding switch', designation
        switch = self.node_new(CMAdb.NODE_switch, designation, unique=True, **kw)
        if not 'status' in switch:
            switch['status'] = 'created'
        return switch

    def new_nic(self, nicname, macaddr, owner, **kw):
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
                    CMAdb.log.debug('MAC %s is nicowner related to owner %s' % (str(mac), str(owner)))
                    CMAdb.log.debug('MAC address = %s, NICname = %s for owner %s' % (mac['address'], mac['nicname'], owner))
                else:
                    CMAdb.log.debug('MAC %s is NOT nicowner related to owner %s' (str(mac), str(owner)))

            if mac.is_related_to(owningnode, neo4j.Direction.OUTGOING, CMAdb.REL_nicowner) \
            and mac['address'] == macaddr and mac['nicname'] == nicname:
                return mac
        mac = self.node_new(CMAdb.NODE_NIC, macaddr, address=macaddr, unique=False, nicname=nicname, **kw)
        mac.create_relationship_to(owningnode, CMAdb.REL_nicowner)
        return mac

    def new_IPaddr(self, nic, ipaddr, **kw):
        '''Create a new IP address (or return a pre-existing one), and point it at its parent
        NIC and its grandparent drone'''
        #print 'Adding IP address %s' % (ipaddr)
        ipaddrs = self.ipindex.get(CMAdb.NODE_ipaddr, ipaddr)
        if nic is not None:
            for ip in ipaddrs:
                if ip.is_related_to(nic, neo4j.Direction.OUTGOING, CMAdb.REL_ipowner):
                    #print 'Found this IP address (%s) ipowner-related to NIC %s' % (ipaddr, nic)
                    return ip
        if len(ipaddrs) == 0:
            ip = self.node_new(CMAdb.NODE_ipaddr, ipaddr, unique=False, **kw)
        else:
            ip = ipaddrs[0] # May have been created by a client - pick the first one...
        if nic is not None:
            ip.create_relationship_to(nic, CMAdb.REL_ipowner)
            drone = nic.get_single_related_node(neo4j.Direction.OUTGOING, CMAdb.REL_nicowner)
            ip.create_relationship_to(drone, CMAdb.REL_iphost)
        return ip

    #NODE_ipproc     = 'ipproc'     # A client and/or server process
    def new_ipproc(self,            ##< Self... The usual self object
                   name,            ##< What should we be called? (no index)
                   jsonobj,         ##< The JSON ConfigContext object for us alone...
                   drone):          ##< Drone we are running on
        '''Create a new ipproc object from its JSON discovery data'''
        table = {}
        for key in jsonobj.keys():
            type = jsonobj.gettype(key)
            if not (type == CFG_BOOL or type == CFG_INT64 or type == CFG_STRING
            or      type == CFG_FLOAT or type == CFG_ARRAY):
                continue
            if jsonobj[key] is None: continue
            # We assume any arrays are of same-typed simple objects (presumably Strings)
            # This is a reasonable assumption for our process discovery data
            table[key] = jsonobj[key]
        ipproc = self.node_new(CMAdb.NODE_ipproc, name, unique=False, **table)
        self.db.relate((ipproc, CMAdb.REL_runningon, drone),)

        return ipproc


    def new_tcpipport(self,            ##< Self... The usual self object
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
            type = jsonobj.gettype(key)
            if not (type == CFG_BOOL or type == CFG_INT64 or type == CFG_STRING
            or      type == CFG_FLOAT or type == CFG_ARRAY):
                continue
            table[key] = jsonobj[key]
        tcpipport = self.node_new(CMAdb.NODE_tcpipport, name, unique=True, **table)
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
        CMAdb.cdb.db.relate(*args)



    def empty(self):
        indexes = self.db.get_node_indexes()
        
        for nodeid in range(0,self.db.get_node_count()+100):
            node = get_node(nodeid)
            nodetype = node['nodetype']
            nodename = node['name']
            l = [node,]
            if l.nodetype in indexes:
                indexes[nodetype].remove(nodetype, name)
            l.append(l.get_relationships())
            self.db.delete(*l)
            l = None
