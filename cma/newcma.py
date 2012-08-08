# vim: smartindent tabstop=4 shiftwidth=4 expandtab
#
#
#   Design outline:
#
#   All incoming network messages come in and get sent to a client who is a dispatcher.
#
#   The dispatcher looks at the message type and computes which queue to send the
#   message to based on the message type and contents.
#
#       For death notices, the dispatcher forwards the message to the worker
#       assigned to the switch the system is on - if known, or the worker
#       assigned to the subnet.
#
#   Each worker handles one or more rings - probably handling the per-switch rings
#   for a subnet and the subnet ring as well.  It is important to ensure that a ring
#   is handled by only one worker.  This eliminates locking concerns.  When a given
#   worker receives a death notice for a drone that is also in higher-level rings,
#   it does its at its level and also forwards the request to the worker handling
#   the higher level ring as well.  The first subnet worker will also handle the work
#   for the top-level (global) ring.
#
#   Packets are ACKed by workers after all work has been completed.  In the case of
#   a drone on multiple rings, it is only ACKed after both rings have been fully
#   repaired.
#
#   The reason for this is that until it is fully repaired, the system might crash
#   before completing its work.  Retransmission timeouts will need to be set
#   accordingly...
#
#   Although congestion is normally very unlikely, this is not true for full
#   datacenter powerons - where it is reasonably likely - depending on how
#   quickly one can power on the servers and not pop circuit breakers or
#   damage UPSes
#       (it would be good to know how fast hosts can come up worst case).
#
#
#   Misc Workers with well-known-names
#   Request-To-Create-Ring
#
#
#   Mappings:
#
#   Drone-related information-------------------------
#   NetAddr-to-drone-name
#   drone-name to NetAddr
#   (drone-name,ifname) to interface-info (including switch info)
#   drone-neighbor-info:
#       drone-name-to-neighbor-info (drone-name, NetAddr, ring-name)
#
#   Ring-related information--------------------------
#   drone-name to ring-name(s)
#   ring-names to ring-information (level, #members, etc)
#   ring-links-info ??
#   Subnet-to-ring-name
#   Switch-to-ring-name
#   Global-ring-name [TheOneRing]
#
#   Discovery-related information---------------------
#   (drone-name, Interface-name) to LLDP/CDP packet
#   (drone-name, discovery-type) to JSON info
#
#
#   Misc Info-----------------------------------------
#   NetAddr(MAC)-to-NetAddr(IP)
#
#
#   Dispatcher logic:
#   For now sends all requests to TheOneRing because we don't have
#   a database yet ;-)
#
#   We will need a database RealSoonNow :-D.
#
################################################################################
#
# It is readily observable that the code is headed that way, but is a long
# way from that structure...
#
################################################################################

import sys, time, weakref, os
sys.path.append("../pyclasswrappers")
sys.path.append("pyclasswrappers")
from frameinfo import FrameTypes, FrameSetTypes
from AssimCclasses import *
from py2neo import neo4j, cypher
import re


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
            print 'Neo4j version: %s' % str(self.dbversion)
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

    def delete_all(self):
        query = cypher.Query(self.db
        ,   'start n=node(*) match n-[r?]-() where id(n) <> 0 delete n,r')
        result = query.execute()
        if CMAdb.debug:
            print >>sys.stderr, 'Cypher query to delete all relationships and nonzero nodes executing:', query
            print >>sys.stderr, 'Execution results:', result

    def node_new(self, nodetype, nodename, unique=True, **properties):
        '''Possibly creates a new node, puts it in its appropriate index and creates an IS_A
    relationship with the nodetype object corresponding its nodetype.
        It is created and added to indexes if it doesn't already exist in its corresponding index
    - if there is one.
        If it already exists, the pre-existing node is returned.
        If this object type doesn't have an index, it will always be created.
        Note that the nodetype has to be in the nodetypetable - even if it's NULL
            (for error detection).
        The IS_A relationship may be useful -- or not.  Hard to say at this point...'''
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
                print 'MAC IS:', mac
                if mac.is_related_to(owningnode, neo4j.Direction.OUTGOING, CMAdb.REL_nicowner):
                    print 'MAC %s is nicowner related to owner %s' % (str(mac), str(owner))
                    print 'MAC address = %s, NICname = %s for owner %s' % (mac['address'], mac['nicname'], owner)
                else:
                    print 'MAC %s is NOT nicowner related to owner %s' (str(mac), str(owner))
                
                
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
        
class HbRing:
    'Class defining the behavior of a heartbeat ring.'
    SWITCH      =  1
    SUBNET      =  2
    THEONERING  =  3 # And The One Ring to rule them all...
    memberprefix = 'RingMember_'
    nextprefix = 'RingNext_'

    ringnames = {}

    def __init__(self, name, ringtype, parentring=None):
        '''Constructor for a heartbeat ring.
        Although we generally avoid keeping hash tables of nodes in the
        database, I'm currently making an exception for rings.  There are
        many fewer of those than any other kind of node.
        '''
        if ringtype < HbRing.SWITCH or ringtype > HbRing.THEONERING: 
            raise ValueError("Invalid ring type [%s]" % str(ringtype))
        self.node = CMAdb.cdb.new_ring(name, parentring, ringtype=ringtype)
        self.ringtype = ringtype
        self.name = str(name)
        self.parentring = parentring
        self.ourreltype = HbRing.memberprefix + self.name # Our relationship type
        self.ournexttype = HbRing.nextprefix + self.name # Our 'next' relationship type
        self.insertpoint1 = None
        self.insertpoint2 = None

        try:
            ip1node = self.node.get_single_related_node(neo4j.Direction.OUTGOING, self.ourreltype)
            if ip1node is not None:
                self.insertpoint1 = DroneInfo(ip1node)
                if self.insertpoint1 is not None:
                    try:
                      #print 'INSERTPOINT1: ', self.insertpoint1
                      ip2 = self.insertpoint1.node.get_single_related_node(neo4j.Direction.OUTGOING, self.ournexttype)
                      self.insertpoint2 = DroneInfo(ip2)
                    except ValueError:
                        pass
        except ValueError:
            pass
        # Need to figure out what to do about pre-existing members of this ring...
        # For the moment, let's make the entirely inadequate assumption that
        # the data in the database is correct.
        ## FIXME - assumption about database being correct
        HbRing.ringnames[self.name] = self

        
    def _findringpartners(self, drone):
        '''Find (one or) two partners for this drone to heartbeat with.
        We do this in such a way that we don't continually beat on the same
        nodes in the ring as we insert new nodes into the ring.'''
        partners=None
        if self.insertpoint1 is not None:
            partners=[]
            partners.append(self.insertpoint1)
            if self.insertpoint2 is not None:
                partners.append(self.insertpoint2)
        return partners

    def join(self, drone):
        'Add this drone to our ring'
        #print 'Adding Drone %s to ring %s' % (str(drone), str(self))
        # Make sure he's not already in our ring according to our 'database'
        if drone.node.has_relationship_with(self.node, neo4j.Direction.OUTGOING, self.ourreltype):
            print ("Drone %s is already a member of this ring [%s] - removing and re-adding."
            %               (drone.node['name'], self.name))
            self.leave(drone)
        
        # Create a 'ringmember' relationship to this drone
        drone.node.create_relationship_to(self.node, self.ourreltype)
        #print 'New ring membership: %s' % (str(self))
        # Should we keep a 'ringip' relationship for this drone?
        # Probably eventually...

        #print >>sys.stderr,'Adding drone %s to talk to partners'%drone.node['name'], self.insertpoint1, self.insertpoint2

        if self.insertpoint1 is None:   # Zero nodes previously
            self.insertpoint1 = drone
            #print >>sys.stderr, 'RING1 IS NOW:', str(self)
            return

        if self.insertpoint2 is None:   # One node previously
        # Create the initial circular list.
            ## FIXME: Ought to label ring membership relationships with IP involved
            # (see comments below)
            CMAdb.cdb.db.relate((drone.node, self.ournexttype, self.insertpoint1.node),
                      (self.insertpoint1.node, self.ournexttype, drone.node))
            drone.start_heartbeat(self, self.insertpoint1)
            self.insertpoint1.start_heartbeat(self, drone)
            self.insertpoint2 = self.insertpoint1
            self.insertpoint1 = drone
            #print >>sys.stderr, 'RING2 IS NOW:', str(self)
            return
        
        #print >>sys.stderr, 'Finding insert point [%s: %s]' % \
    #   (self.insertpoint2.node['name'], self.ournexttype)
        # Two or more nodes previously
        #print >>sys.stderr, 'DRONE:', drone.node
        #print >>sys.stderr, 'INSERTPOINT1:', self.insertpoint1.node
        #print >>sys.stderr, 'INSERTPOINT2:', self.insertpoint2.node
        #print >>sys.stderr, 'OURNEXTTYPE:', self.ournexttype
        nextnext = self.insertpoint2.node.get_single_related_node(neo4j.Direction.OUTGOING, self.ournexttype)
        if nextnext is not None and nextnext.id != self.insertpoint1.node.id:
            # At least 3 nodes before
            self.insertpoint1.stop_heartbeat(self, self.insertpoint2)
            self.insertpoint2.stop_heartbeat(self, self.insertpoint1)
        drone.start_heartbeat(self, self.insertpoint1, self.insertpoint2)
        self.insertpoint1.start_heartbeat(self, drone)
        self.insertpoint2.start_heartbeat(self, drone)
        point1rel = self.insertpoint1.node.get_single_relationship(neo4j.Direction.OUTGOING, self.ournexttype)
        point1rel.delete()
        point1rel = None
        # In the future we might want to mark these relationships with the IP addresses involved
        # so that even if the systems change network configurations we can still know what IP to
        # remove.  Right now we rely on the configuration not changing "too much".
        ## FIXME: Ought to label relationships with IP addresses involved.
        CMAdb.cdb.db.relate((self.insertpoint1.node, self.ournexttype, drone.node),
                      (drone.node, self.ournexttype, self.insertpoint2.node))
        # This should ensure that we don't keep beating the same nodes over and over
        # again as new nodes join the system.  Instead the latest newbie becomes the next
        # insert point in the ring - spreading the work to the new guys as they arrive.
        #self.insertpoint2 = self.insertpoint1
        self.insertpoint1 = drone
        #print >>sys.stderr, 'RING3 IS NOW:', str(self), 'DRONE ADDED:', drone

    def leave(self, drone):
        'Remove a drone from this heartbeat Ring.'
        try: 
            prevnode = drone.node.get_single_related_node(neo4j.Direction.INCOMING, self.ournexttype)
        except ValueError:
            prevnode = None
        try: 
            nextnode = drone.node.get_single_related_node(neo4j.Direction.OUTGOING, self.ournexttype)
        except ValueError:
            nextnode = None

        if nextnode is None and prevnode is None:   # Previous length:  1
                self.insertpoint1 = None        # result length:    0
                self.insertpoint2 = None
                # No database links to remove
        return

    # Clean out the next link relationships to our dearly departed drone
        ringrel = drone.node.get_single_relationship(neo4j.Direction.OUTGOING, self.ourreltype)
        ringrel.delete()
        ringrel = None
    # Clean out the next link relationships to our dearly departed drone
        relationships = drone.node.get_relationships('all', self.ournexttype)
        # Should have exactly two link relationships (one incoming and one outgoing)
        assert len(relationships) == 2
        for rel in relationships:
            rel.delete()
            rel = None
        relationships = None
        rel = None

        if prevnode.id == nextnode.id:          # Previous length:  2
            node = prevnode             # Result length:    1
            if node is None: node = nextnode
            partner = DroneInfo(node)
            drone.stop_heartbeat(self, partner)
            partner.stop_heartbeat(self, drone)
            #prevnode.create_relationship_to(nextnode, self.ournexttype)
            self.insertpoint2 = None
            self.insertpoint1 = partner
            return

        # Previous length had to be >= 3        # Previous length:  >=3
                            # Result length:    >=2
        prevdrone = DroneInfo(prevnode['name'])
        nextdrone = DroneInfo(nextnode['name'])
        nextnext = nextnode.get_single_related_node(neo4j.Direction.OUTGOING, self.ournexttype)
        prevdrone.stop_heartbeat(self, drone)
        nextdrone.stop_heartbeat(self, drone)
        if nextnext.id != prevnode.id:          # Previous length:  >= 4
            nextdrone.start_heartbeat(self, prevdrone)  # Result length:    >= 3
            prevdrone.start_heartbeat(self, nextdrone)
        # Poor drone -- all alone in the universe... (maybe even dead...)
        drone.stop_heartbeat(self, prevdrone, nextdrone)
        self.insertpoint1 = prevdrone   # non-minimal, but correct and cheap change
        self.insertpoint2 = nextdrone
        prevnode.create_relationship_to(nextnode, self.ournexttype)

    def members(self):
        ret = []
        for node in self.node.get_related_nodes(neo4j.Direction.INCOMING, self.ourreltype):
            ret.append(DroneInfo.find(node))
        return ret

    def membersfromlist(self):
        firstdrone=self.insertpoint1
        if firstdrone is None:
           return []
        ret = [firstdrone]
        firstdrone = firstdrone.node
        nextdrone = firstdrone
        while True:
            nextdrone = nextdrone.get_single_related_node(neo4j.Direction.OUTGOING, self.ournexttype)
            if nextdrone is None or nextdrone.id == firstdrone.id:  break
            ret.append(DroneInfo.find(nextdrone))
        return ret

    def __str__(self):
        ret = 'Ring("%s", [' % self.node['name']
        comma=''
        for drone in self.membersfromlist():
             ret += '%s%s' % (comma, drone.node['name'])
             comma=', '
        ret += '])'
        return ret
      
class DroneInfo:
    'Everything about Drones - endpoints that run our nanoprobes'
    _droneweakrefs = {}
    _JSONprocessors = {}
    def __init__(self, designation, node=None, **kw):
        self.io = CMAdb.io
        if isinstance(designation, neo4j.Node):
            self.node = designation
        else:
            #print >>sys.stderr, 'New DroneInfo(designation = %s", kw=%s)' % (designation, str(**kw))
            self.node = CMAdb.cdb.new_drone(designation, **kw)
        DroneInfo._droneweakrefs[designation] = weakref.ref(self)
        

    def __getitem__(self, key):
       return self.node[key]

    def getport(self):
        '''Return the port we talk to this drone on'''
        return self.io.config[CONFIGNAME_CMAPORT]
        
   
    def logjson(self, jsontext):
        'Process and save away JSON discovery data'
        jsonobj = pyConfigContext(jsontext)
        if not jsonobj.has_key('discovertype') or not jsonobj.has_key('data'):
            print >>sys.stderr, 'Invalid JSON discovery packet.'
            return
        dtype = jsonobj['discovertype']
        #print "Saved discovery type %s for endpoint %s." % \
        #   (dtype, self.designation)
        self.node['JSON_' + dtype] = jsontext
        if dtype in DroneInfo._JSONprocessors:
            if CMAdb.debug: print >>sys.stderr, ('Processed %s JSON data into graph.' % dtype)
            DroneInfo._JSONprocessors[dtype](self, jsonobj)
        else:
            print >>sys.stderr, ('Stored %s JSON data without processing.' % dtype)

    def add_netconfig_addresses(self, jsonobj, **kw):
        '''Save away the network configuration data we got from JSON discovery.
        This includes all our NICs, their MAC addresses, all our IP addresses and so on
        for any non-loopback interface.  Whee!
        In theory we could make a giant 'create' for everything and do all the db creation
        in one swell foop - or at most two...
        '''
        # Ought to protect this code by try blocks...
        data = jsonobj['data'] # The data portion of the JSON message
        primaryip = None
        for ifname in data.keys(): # List of interfaces just below the data section
            ifinfo = data[ifname]
            isprimaryif= ifinfo.has_key('default_gw')
            #print 'IFINFO: [%s]' % str(ifinfo)
            if not ifinfo.has_key('address'):
                continue
            ifaddr = ifinfo['address']
            #print 'ADDRESS: [%s]' % str(ifaddr)
            if ifaddr.startswith('00:00:00:'):
                continue
            nicnode = CMAdb.cdb.new_nic(ifname, ifaddr, self, isprimaryif=isprimaryif, **kw)
            iptable = ifinfo['ipaddrs'] # look in the 'ipaddrs' section
            for ip in iptable.keys():   # keys are 'ip/mask' in CIDR format
                ipinfo = iptable[ip]
                ipname = ':::INVALID:::'
                if ipinfo.has_key('name'):
                    ipname = ipinfo['name']
                if ipinfo['scope'] != 'global':
                    continue
                (iponly,mask) = ip.split('/')
                isprimaryip = False
                ## FIXME: May want to consider looking at 'brd' for broadcast as well...
                ## otherwise this can be a little fragile...
                if isprimaryif and primaryip == None and ipname == ifname:
                    isprimaryip = True
                    primaryip = iponly
                    #print >>sys.stderr, 'PRIMARY IP is %s' % iponly
                ipnode = CMAdb.cdb.new_IPaddr(nicnode, iponly, ifname=ifname, hostname=self.node['name'])
                # Save away whichever IP address is our primary IP address...
                if isprimaryip:
                    rel = self.node.get_single_relationship(neo4j.Direction.OUTGOING, 'primaryip')
                    if rel is not None and rel.end_node.id != ipnode.id:
                        rel.delete()
                        rel = None
                    if rel is None:
                      CMAdb.cdb.db.relate((self.node, 'primaryip', ipnode),)

    def add_tcplisteners(self, jsonobj, **kw):
        '''Add TCP listeners and/or clients.  Same or separate messages - we don't care.'''
        data = jsonobj['data'] # The data portion of the JSON message
        primaryip = None
        allourips = self.node.get_related_nodes(neo4j.Direction.INCOMING, CMAdb.REL_iphost)
        for procname in data.keys(): # List of names of processes...
            procinfo = data[procname]
            ipproc = CMAdb.cdb.new_ipproc(procname, procinfo, self.node)
            if 'listenaddrs' in procinfo:
                tcpipportinfo = procinfo['listenaddrs']
                for tcpipport in tcpipportinfo.keys():
                    self.add_tcpipports(True, tcpipportinfo[tcpipport], ipproc, allourips)
            if 'clientaddrs' in procinfo:
                tcpipportinfo = procinfo['clientaddrs']
                for tcpipport in tcpipportinfo.keys():
                    self.add_tcpipports(False, tcpipportinfo[tcpipport], ipproc, None)

    def add_tcpipports(self, isserver, jsonobj, ipproc, allourips):
        '''We create tcpipports objects that correspond to the given json object in
        the context of the set of IP addresses that we support - including support
        for the ANY ipv4 and ipv6 addresses'''
        addr = str(jsonobj['addr'])
        port = jsonobj['port']
        name = addr + ':' + str(port)
        # Were we given the ANY address?
        if isserver and (addr == '0.0.0.0' or addr == '::'):
            for ipaddr in allourips:
                name = ipaddr['name'] + ':' + str(port)
                tcpipport = CMAdb.cdb.new_tcpipport(name, isserver, jsonobj, self.node, ipproc, ipaddr)
        elif isserver:
            for ipaddr in allourips:
                if ipaddr['name'] == addr:
                    CMAdb.cdb.new_tcpipport(name, isserver, jsonobj, self.node, ipproc, ipaddr)
                    return
            raise ValueError('IP Address mismatch for Drone %s - could not find address %s'
                            % (self.node['name'], addr))
        else:
            name = addr + ':' + str(port)
            ipaddr = CMAdb.cdb.new_IPaddr(None, addr)
            CMAdb.cdb.new_tcpipport(name, isserver, jsonobj, None, ipproc, ipaddr)

    def add_linkdiscovery(self, jsonobj, **kw):
        data = jsonobj['data']
        if 'ChassisId' not in data:
            print >>sys.stderr, 'Chassis ID missing for switch [%s]' (str(data))
            return
        ChassisId = data['ChassisId']
        attrs = {}
        for key in data.keys():
            if key == 'ports':  continue
            value = data[key]
            if isinstance(value, pyNetAddr):
                value = str(value)
            attrs[key] = value
        switch = CMAdb.cdb.new_switch(ChassisId, **attrs)
        if ('ManagementAddress' in attrs):
            mgmtaddr = attrs['ManagementAddress']
            adminnic = CMAdb.cdb.new_nic('(adminNIC)', ChassisId, switch)
            CMAdb.cdb.new_IPaddr(adminnic, mgmtaddr)
        ports = data['ports']
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
                nicmac = ChassisId # Hope that works ;-)
            nicnode = CMAdb.cdb.new_nic(portname, nicmac, switch, **attrs)
            try:
                assert thisport['ConnectsToHost'] == self.node['name']
                matchnic = thisport['ConnectsToInterface']
                niclist = self.node.get_related_nodes(neo4j.Direction.INCOMING, CMAdb.REL_nicowner)
                for dronenic in niclist:
                    if dronenic['nicname'] == matchnic:
                        nicnode.create_relationship_from(dronenic, CMAdb.REL_wiredto)
                        break
            except KeyError:
                print 'OOPS! got an exception...'
                pass




    def primary_ip(self, ring=None):
        '''Return the "primary" IP for this host'''
        primaryIP = self.node.get_single_related_node(neo4j.Direction.OUTGOING, 'primaryip')
        return str(primaryIP['name'])

    def select_ip(self, ring=None):
        '''Select an appropriate IP address for talking to a partner on this ring
        or our primary IP if ring is None'''
        # Current code is not really good enough for the long term,
        # but is good enough for now...
        # In particular, when talking on a particular switch ring, or
        # subnet ring, we want to choose an IP that's on that subnet,
        # and preferably on that particular switch for a switch-level ring.
        # For TheOneRing, we want their primary IP address.
        return self.primary_ip()
    
    def send_hbmsg(self, dest, fstype, port, addrlist):
        '''Send a message with an attached address list and optional port.
           This is intended primarily for start or stop heartbeating messages.'''
        fs = pyFrameSet(fstype)
        pframe = None
        if port is not None and port > 0 and port < 65536:
           pframe = pyIntFrame(FrameTypes.PORTNUM, intbytes=2, initval=int(port))
        for addr in addrlist:
            if addr is None: continue
            if pframe is not None:
                fs.addframe(pframe)
            aframe = pyAddrFrame(FrameTypes.IPADDR, addrstring=addr)
            fs.append(aframe)
        self.io.sendframesets(dest, (fs,))

    def death_report(self, status, reason, fromaddr, frameset):
        'Process a death/shutdown report for us.  RIP us.'
        if CMAdb.debug:
            print >>sys.stderr, 'Node %s has been reported as %s by address %s. Reason: %s' \
            %   (self.node['name'], status, str(fromaddr), reason)
        self.status = status
        self.reason = reason
        #print >>sys.stderr, 'Drone %s is %s because of %s' %(self, status, reason)
        self.node['status'] = status
        self.node['reason'] = reason
        # There is a need for us to be a little more sophisticated
        # in terms of the number of peers this particular drone had
        # It's here in this place that we will eventually add the ability
        # to distinguish death of a switch or subnet or site from death of a single drone
        rellist = self.node.get_relationships(direction=neo4j.Direction.OUTGOING)
        for rel in rellist:
            if rel.type.startswith(HbRing.memberprefix):
                ringname = rel.end_node['name']
                #print >>sys.stderr, 'Drone %s is a member of ring %s' % (self, ringname)
            HbRing.ringnames[ringname].leave(self)


    def start_heartbeat(self, ring, partner1, partner2=None):
        '''Start heartbeating to the given partners.
        We insert ourselves between partner1 and partner2.
        We only use forward links - because we can follow them in both directions in Neo4J.
        So, we need to create a forward link from partner1 to us and from us to partner2 (if any)
        '''
        ourip = self.select_ip(ring)
        partner1ip = partner1.select_ip(ring)
        if partner2 is not None:
            partner2ip = partner2.select_ip(ring)
        else:
            partner2ip = None
        self.send_hbmsg(ourip, FrameSetTypes.SENDEXPECTHB, 0, (partner1ip, partner2ip))

    def stop_heartbeat(self, ring, partner1, partner2=None):
        '''Stop heartbeating to the given partners.'
    We don't know which node is our forward link and which our back link,
        but we need to remove them either way ;-).
    '''
        ourip = self.select_ip(ring)
        partner1ip = partner1.select_ip(ring)
        if partner2 is not None:
            partner2ip = partner2.select_ip(ring)
        else:
            partner2ip = None
        # Stop sending the heartbeat messages between these (former) peers
        self.send_hbmsg(ourip, FrameSetTypes.STOPSENDEXPECTHB, 0, (partner1ip, partner2ip))

    def request_discovery(self, *args): ##< A vector of arguments formed like this:
        ##< instance       Which (unique) discovery instance is this?
        ##< interval=0     How often to perform it?
        ##< json=None):    JSON string (or ConfigContext) describing discovery
        ##<                If json is None, then instance is used for JSON type
        '''Send our drone a request to perform discovery
        We send a           DISCNAME frame with the instance name
        then an optional    DISCINTERVAL frame with the repeat interval
        then a              DISCJSON frame with the JSON data for the discovery operation.
        '''
        fs = pyFrameSet(FrameSetTypes.DODISCOVER)
        if type(args[0]) is str:
            if len(args) == 1:
                args = ((args[0], 0, None),)
            elif len(args) == 2:
                args = ((args[0], args[1], None),)
            elif len(args) == 3:
                args = ((args[0], args[1], args[2]),)
            else:
               raise ValueError('Incorrect argument length: %d vs 1,2 or 3' % len(args))

        for tuple in args:
            if len(tuple) != 2 and len(tuple) != 3:
               raise ValueError('Incorrect argument tuple length: %d vs 2 or 3 [%s]' % (len(tuple), args))
            instance = tuple[0]
            interval = tuple[1]
            json = None
            if len(tuple) == 3: json = tuple[2]

            discname = pyCstringFrame(FrameTypes.DISCNAME)
            #print >>sys.stderr, 'SETTING VALUE TO: (%s)' % instance
            discname.setvalue(instance)
            fs.append(discname)
            if interval is not None and interval > 0:
                discint = pyIntFrame(FrameTypes.DISCINTERVAL, intbytes=4, initval=int(interval))
                fs.append(discint)
            instframe = pyCstringFrame(FrameTypes.DISCNAME)
            if isinstance(json, pyConfigContext):
                json = str(json)
            elif json is None:
                json = instance
            if not json.startswith('{'):
                json = '{"type":"%s","parameters":{}}' % json
            jsonframe = pyCstringFrame(FrameTypes.DISCJSON)
            jsonframe.setvalue(json)
            fs.append(jsonframe)
        # This doesn't work if the client has bound to a VIP
        ourip = self.primary_ip()    # meaning select our primary IP
        ourip = pyNetAddr(ourip)
        ourip.setport(self.getport())
        #print 'PORT IS ', self.getport()
        self.io.sendframesets(ourip, (fs,))
        if CMAdb.debug:
            print >>sys.stderr, 'Sent Discovery request(%s,%s) to %s Framesets: %s' \
            %	(instance, str(interval), str(ourip), str(fs))


    def __str__(self):
        'Give out our designation'
        return 'Drone(%s)' % self.node['name']

    @staticmethod
    def find(designation):
        'Find a drone with the given designation or IP address, or Neo4J node.'
        if isinstance(designation, str):
            drone = None
            if designation in DroneInfo._droneweakrefs:
                drone = DroneInfo._droneweakrefs[designation]()
            if drone is None:
                drone = DroneInfo(designation)
            assert drone.node['name'] == designation
            return drone
        if isinstance(designation, pyNetAddr):
            #Is there a concern about non-canonical IP address formats?
            ipaddrs = CMAdb.cdb.ipindex.get(CMAdb.NODE_ipaddr, str(designation))
            for ip in ipaddrs:
                # Shouldn't have duplicates, but they happen...
                # FIXME: Think about how to manage duplicate IP addresses...
                # Do we really want to be looking up just by IP addresses here?
                node = ip.get_single_related_node(neo4j.Direction.OUTGOING, CMAdb.REL_iphost)
                return DroneInfo.find(node)
        if isinstance(designation, neo4j.Node):
            nodedesig = designation['name']
            if nodedesig in DroneInfo._droneweakrefs:
                ret = DroneInfo._droneweakrefs[nodedesig]()
                if ret is not None:  return ret
            return DroneInfo(designation)
           
        if designation in DroneInfo._droneweakrefs:
            ret = DroneInfo._droneweakrefs[designation]()
        return None

    @staticmethod
    def add(designation, reason, status='up'):
        'Add a drone to our set unless it is already there.'
        ret = None
        if designation in DroneInfo._droneweakrefs:
            ret = DroneInfo._droneweakrefs[designation]()
        if ret is None:
            ret = DroneInfo.find(designation)
        if ret is None:
            ret = DroneInfo(designation)
        ret.node['reason'] = reason
        ret.node['status'] = status
        return ret

    @staticmethod
    def add_json_processors(*args):
        for tuple in args:
            DroneInfo._JSONprocessors[tuple[0]] = tuple[1]

class DispatchTarget:
    '''Base class for handling incoming FrameSets.
    This base class is designated to handle unhandled FrameSets.
    All it does is print that we received them.
    '''
    def __init__(self):
        pass
    def dispatch(self, origaddr, frameset):
        fstype = frameset.get_framesettype()
        print "Received unhandled FrameSet of type [%s] from [%s]" \
        %     (FrameSetTypes.get(fstype)[0], str(origaddr))
        for frame in frameset.iter():
            frametype=frame.frametype()
            print "\tframe type [%s]: [%s]" \
            %     (FrameTypes.get(frametype)[1], str(frame))

    def setconfig(self, io, config):
        self.io = io
        self.config = config
        
class DispatchHBDEAD(DispatchTarget):
    'DispatchTarget subclass for handling incoming HBDEAD FrameSets.'
    def dispatch(self, origaddr, frameset):
        'Dispatch function for HBDEAD FrameSets'
        json = None
        fstype = frameset.get_framesettype()
        fromdrone = DroneInfo.find(origaddr)
        #print>>sys.stderr, "DispatchHBDEAD: received [%s] FrameSet from [%s]" \
    #%      (FrameSetTypes.get(fstype)[0], str(origaddr))
        for frame in frameset.iter():
            frametype=frame.frametype()
            if frametype == FrameTypes.IPADDR:
                deaddrone = DroneInfo.find(frame.getnetaddr())
                deaddrone.death_report('dead', 'HBDEAD packet', origaddr, frameset)

class DispatchSTARTUP(DispatchTarget):
    'DispatchTarget subclass for handling incoming STARTUP FrameSets.'
    def dispatch(self, origaddr, frameset):
        json = None
        fstype = frameset.get_framesettype()
        if CMAdb.debug:
            print >>sys.stderr,"DispatchSTARTUP: received [%s] FrameSet from [%s]" \
        %       (FrameSetTypes.get(fstype)[0], str(origaddr))
        for frame in frameset.iter():
            frametype=frame.frametype()
            if frametype == FrameTypes.HOSTNAME:
                sysname = frame.getstr()
            if frametype == FrameTypes.JSDISCOVER:
                json = frame.getstr()
        fs = CMAlib.create_setconfig(self.config)
        #print 'Telling them to heartbeat themselves.'
        #fs2 = CMAlib.create_sendexpecthb(self.config, FrameSetTypes.SENDEXPECTHB
        #,      origaddr)
        #print 'Sending SetConfig frameset to %s' % origaddr
        #self.io.sendframesets(origaddr, (fs,fs2))
        self.io.sendframesets(origaddr, fs)
        print 'Drone %s registered from address %s' % (sysname, origaddr)
        DroneInfo.add(sysname, 'STARTUP packet')
        drone = DroneInfo.find(sysname)
        #print >>sys.stderr, 'DRONE from find: ', drone, type(drone)
        drone.startaddr=origaddr
        if json is not None:
            drone.logjson(json)
        CMAdb.cdb.TheOneRing.join(drone)
        drone.request_discovery(('tcplisteners',    3555),
                                ('tcpclients',      3333),
                                ('cpu',             36000),
                                ('os',              0),
                                ('arpcache',        45))

class DispatchJSDISCOVERY(DispatchTarget):
    'DispatchTarget subclass for handling incoming JSDISCOVERY FrameSets.'
    def dispatch(self, origaddr, frameset):
        fstype = frameset.get_framesettype()
        if CMAdb.debug:
            print >>sys.stderr,"DispatchJSDISCOVERY: received [%s] FrameSet from [%s]" \
        %       (FrameSetTypes.get(fstype)[0], str(origaddr))
        sysname = None
        for frame in frameset.iter():
            frametype=frame.frametype()
            if frametype == FrameTypes.HOSTNAME:
                sysname = frame.getstr()
            if frametype == FrameTypes.JSDISCOVER:
                json = frame.getstr()
                if sysname is None:
                    jsonconfig = pyConfigContext(init=json)
                    sysname = jsonconfig.getstring('host')
                drone = DroneInfo.find(sysname)
                drone.logjson(json)
                sysname = None

class DispatchSWDISCOVER(DispatchTarget):
    'DispatchTarget subclass for handling incoming SWDISCOVER FrameSets.'

    def dispatch(self, origaddr, frameset):
        fstype = frameset.get_framesettype()
        if CMAdb.debug:
            print >>sys.stderr,"DispatchSWDISCOVER: received [%s] FrameSet from [%s]" \
        %       (FrameSetTypes.get(fstype)[0], str(origaddr))
        wallclock = None
        interface = None
        designation = None
        for frame in frameset.iter():
            frametype=frame.frametype()
            if frametype == FrameTypes.HOSTNAME:
                designation = frame.getstr()
            elif frametype == FrameTypes.INTERFACE:
                interface = frame.getstr()
            elif frametype == FrameTypes.WALLCLOCK:
                wallclock = frame.getint()
            elif frametype == FrameTypes.PKTDATA:
                if wallclock is None or interface is None or designation is None:
                    raise ValueError('Incomplete Switch Discovery Packet')
                pktstart = frame.framevalue()
                pktend = frame.frameend()
                switchjson = SwitchDiscovery.decode_discovery(designation, interface
                ,               wallclock, pktstart, pktend)
                if CMAdb.debug:
                    print 'GOT Link Discovery INFO from %s: %s' % (interface, str(switchjson))
                drone = DroneInfo.find(designation)
                drone.logjson(str(switchjson))
                break


class MessageDispatcher:
    'We dispatch incoming messages where they need to go.'
    def __init__(self, dispatchtable):
        'Constructor for MessageDispatcher - requires a dispatch table as a parameter'
        self.dispatchtable = dispatchtable
        self.default = DispatchTarget()

    def dispatch(self, origaddr, frameset):
        'Dispatch a frameset where it will get handled.'
        fstype = frameset.get_framesettype()
        if self.dispatchtable.has_key(fstype):
            self.dispatchtable[fstype].dispatch(origaddr, frameset)
        else:
            self.default.dispatch(origaddr, frameset)

    def setconfig(self, io, config):
        'Save our configuration away.  We need it before we can do anything.'
        self.io = io
        self.default.setconfig(io, config)
        for msgtype in self.dispatchtable.keys():
            self.dispatchtable[msgtype].setconfig(io, config)

class PacketListener:
    'Listen for packets and get them dispatched as any good packet ought to be.'
    def __init__(self, config, dispatch, io=None):
        self.config = config
        if io is None:
            self.io = pyNetIOudp(config, pyPacketDecoder())
        else:
            self.io = io
        dispatch.setconfig(self.io, config)

        self.io.bindaddr(config["cmainit"])
        self.io.setblockio(True)
        #print "IO[socket=%d,maxpacket=%d] created." \
        #%  (self.io.getfd(), self.io.getmaxpktsize())
        self.dispatcher = dispatch
        
    def listen(self):
      'Listen for packets.  Get them dispatched.'
      while True:
        (fromaddr, framesetlist) = self.io.recvframesets()
        if fromaddr is None:
            # BROKEN! ought to be able to set blocking mode on the socket...
            #print "Failed to get a packet - sleeping."
            time.sleep(0.5)
        else:
            if CMAdb.debug: print "Received packet from [%s]" % (str(fromaddr))
            for frameset in framesetlist:
                self.dispatcher.dispatch(fromaddr, frameset)


DroneInfo.add_json_processors(('netconfig', DroneInfo.add_netconfig_addresses),)
DroneInfo.add_json_processors(('tcplisteners', DroneInfo.add_tcplisteners),)
DroneInfo.add_json_processors(('tcpclients', DroneInfo.add_tcplisteners),)
DroneInfo.add_json_processors(('#LinkDiscovery', DroneInfo.add_linkdiscovery),)

if __name__ == '__main__':
    #
    #   "Main" program starts below...
    #   It is a test program intended to run with some real nanoprobes running
    #   somewhere out there...
    #
    OurAddr = None
    DefaultPort = 1984
    OurPort = None

    skipme = False
    for narg in range(1,len(sys.argv)):
        if skipme:
            skipme = False
            continue
        if sys.argv[narg] == '--bind':
            OurAddr = pyNetAddr(sys.argv[narg+1])
            if OurAddr.port() > 0:
                OurPort = OurAddr.port()
            else:
                OurAddr.setport(OurPort)
            skipme = True
        else:
            print >> sys.stderr, 'Bad argument [%s]' % sys.argv[narg]

    if OurPort is None:
        OurPort = 1984
    if OurAddr is None:
        OurAddr = pyNetAddr((10,10,10,200),OurPort)

    print 'Binding to Address: %s' % str(OurAddr)

    configinit = {
    	CONFIGNAME_CMAINIT:	OurAddr,    # Initial 'hello' address
    	CONFIGNAME_CMAADDR:	OurAddr,    # not sure what this one does...
    	CONFIGNAME_CMADISCOVER:	OurAddr,    # Discovery packets sent here
    	CONFIGNAME_CMAFAIL:	OurAddr,    # Failure packets sent here
    	CONFIGNAME_CMAPORT:	OurPort,
    	CONFIGNAME_HBPORT:	OurPort,
    	CONFIGNAME_OUTSIG:	pySignFrame(1),
    	CONFIGNAME_DEADTIME:	10*1000000,
    	CONFIGNAME_WARNTIME:	3*1000000,
    	CONFIGNAME_HBTIME:	1*1000000,
        CONFIGNAME_OUTSIG:	pySignFrame(1),
    }
    config = pyConfigContext(init=configinit)
    io = pyNetIOudp(config, pyPacketDecoder(0))
    CMAdb.initglobal(io, True)
    print 'Ring created!! - id = %d' % CMAdb.TheOneRing.node.id

    print FrameTypes.get(1)[2]
    disp = MessageDispatcher(
    {   FrameSetTypes.STARTUP: DispatchSTARTUP(),
        FrameSetTypes.HBDEAD: DispatchHBDEAD(),
        FrameSetTypes.JSDISCOVERY: DispatchJSDISCOVERY(),
        FrameSetTypes.SWDISCOVER: DispatchSWDISCOVER()
    })
    listener = PacketListener(config, disp)
    listener.listen()
