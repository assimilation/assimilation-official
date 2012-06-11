#
#	Design outline:
#
#	All incoming network messages come in and get sent to a client who is a dispatcher.
#
#	The dispatcher looks at the message type and computes which queue to send the
#	message to based on the message type and contents.
#
#		For death notices, the dispatcher forwards the message to the worker
#		assigned to the switch the system is on - if known, or the worker
#		assigned to the subnet.
#
#	Each worker handles one or more rings - probably handling the per-switch rings
#	for a subnet and the subnet ring as well.  It is important to ensure that a ring
#	is handled by only one worker.  This eliminates locking concerns.  When a given
#	worker receives a death notice for a drone that is also in higher-level rings,
#	it does its at its level and also forwards the request to the worker handling
#	the higher level ring as well.  The first subnet worker will also handle the work
#	for the top-level (global) ring.
#
#	Packets are ACKed by workers after all work has been completed.  In the case of
#	a drone on multiple rings, it is only ACKed after both rings have been fully
#	repaired.
#
#	The reason for this is that until it is fully repaired, the system might crash
#	before completing its work.  Retransmission timeouts will need to be set
#	accordingly...
#
#	Although congestion is normally very unlikely, this is not true for full
#	datacenter powerons - where it is reasonably likely - depending on how
#	quickly one can power on the servers and not pop circuit breakers or
#	damage UPSes
#		(it would be good to know how fast hosts can come up worst case).
#
#
#	Misc Workers with well-known-names
#	Request-To-Create-Ring
#
#
#	Mappings:
#
#	Drone-related information-------------------------
#	NetAddr-to-drone-name
#	drone-name to NetAddr
#	(drone-name,ifname) to interface-info (including switch info)
#	drone-neighbor-info:
#		drone-name-to-neighbor-info (drone-name, NetAddr, ring-name)
#
#	Ring-related information--------------------------
#	drone-name to ring-name(s)
#	ring-names to ring-information (level, #members, etc)
#	ring-links-info	??
#	Subnet-to-ring-name
#	Switch-to-ring-name
#	Global-ring-name [TheOneRing]
#
#	Discovery-related information---------------------
#	(drone-name, Interface-name) to LLDP/CDP packet
#	(drone-name, discovery-type) to JSON info
#
#
#	Misc Info-----------------------------------------
#	NetAddr(MAC)-to-NetAddr(IP)
#
#
#	Dispatcher logic:
#	For now sends all requests to TheOneRing because we don't have
#	a database yet ;-)
#
#	We will need a database RealSoonNow :-D.
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
#       Indexes:
#       ringindex - index of all Ring objects [nodetype=ring]
#       droneindex - index of all Drone objects [nodetype=drone]
#       ipindex - index of all IP address objects [nodetype=ipaddr]
#       macindex - index of all interfaces by MAC address [nodetype=nic]

#       Node types [nodetype enumeration values]:
#       ring    - heartbeat ring objects
#       drone   - systems running our nanoprobes
#       nic     - interfaces on drones
#       ipaddr  - IP addresses (ipv4 or ipv6)

#       Relationship types [reltype enumeration values]
#       ------------------------------------------
#       reltype         fromnodetype    tonodetype
#       --------        ------------    ----------
#       nichost         nic             drone
#       iphost          ipaddr          drone
#       ipowner         ipaddr          nic
#       ringnext        drone           drone
#       ringip		ring            ipaddr
#       ringmember	ring            drone
#       parentring      ring            ring

    def __init__(self, host='localhost', port=7474):
        url = ('http://%s:%d/db/data/' % (host, port))
        self.db = neo4j.GraphDatabaseService(url)
        self.dbversion = self.db.neo4j_version
        print 'Neo4j version: %s' % str(self.dbversion)
        #
	#	Make sure all our indexes are present and that we
	#	have a top level node for each node type for creating
	#	IS_A relationships to.  Not sure if the IS_A relationships
	#	are really needed, but they're kinda cool...
	#
        nodetypes = {	'Ring':		True
		,	'Drone':	True
		,	'Switch':	True
		,	'NIC':		True	# NICs are indexed by MAC address
						# MAC addresses are not always unique...
		,	'IPaddr':	True	# Note that IPaddrs also might not be unique
		}
        
        indices = [key for key in nodetypes.keys() if nodetypes[key]]
        self.indextbl = {}
        self.nodetypetbl = {}
        for index in indices:
            print ('Ensuring index %s exists' % index)
            self.indextbl[index] = self.db.get_or_create_index(neo4j.Node, index)
        print ('Ensuring index %s exists' % 'nodetype')
        self.indextbl['nodetype'] = self.db.get_or_create_index(neo4j.Node, 'nodetype')
        nodetypeindex = self.indextbl['nodetype']
        for index in nodetypes.keys():
            top =  nodetypeindex.get_or_create('nodetype', index
	    ,				       {'name':index, 'nodetype':'nodetype'})
            self.nodetypetbl[index] = top
        self.ringindex = self.indextbl['Ring']
        self.ipindex = self.indextbl['IPaddr']
        self.macindex = self.indextbl['NIC']
        self.switchindex = self.indextbl['Switch']

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
        properties['nodetype'] = nodetype
        properties['name'] = nodename
        if self.indextbl.has_key(nodetype):
             idx = self.indextbl[nodetype]
             tbl = {}
             for key in properties.keys():
                tbl[key] = properties[key]
             tbl['nodetype'] = nodetype
             tbl['name'] = nodename
             print 'CREATING A [%s] object named [%s] with attributes %s' % (nodetype, nodename, str(tbl.keys()))
             if unique:
                 obj = idx.get_or_create(nodetype, nodename, tbl)
             else:
                 obj = self.db.create_node(tbl)
                 idx.add(nodetype, nodename, obj)
        else:
            obj = self.db.create(properties)
        ntt = self.nodetypetbl[nodetype]
        if ntt is not None:
            self.db.relate((obj, 'IS_A', ntt),)
        print 'CREATED/reused %s object with id %d' % (nodetype, obj.id)
        return obj


    def new_ring(self, name, parentring=None, **kw):
        'Create a new ring (or return a pre-existing one), and put it in the ring index'
        ring = self.node_new('Ring', name, unique=True,  **kw)
        if parentring is not None:
            self.db.relate((ring, 'parentring', parentring.node),)
        return ring

    def new_drone(self, designation, **kw):
        'Create a new drone (or return a pre-existing one), and put it in the drone index'
        print 'Adding drone', designation
        drone = self.node_new('Drone', designation, unique=True, **kw)
        return drone

    def new_nic(self, nicname, macaddr, drone, **kw):
        '''Create a new NIC (or return a pre-existing one), and put it in the mac address index,
        and point it at its parent drone.'''
        
        macnics = self.macindex.get('NIC', macaddr)
        for mac in macnics:
            print 'MAC IS:', mac
            if mac.is_related_to(drone.node, 'outgoing', 'nicowner'):
                print 'MAC %s is nicowner related to drone %s' % (str(mac), str(drone))
                print 'MAC address = %s, NICname = %s for drone %s' % (mac['address'], mac['nicname'], drone)
            else:
                print 'MAC %s is NOT nicowner related to drone %s' (str(mac), str(drone))
                
            if mac.is_related_to(drone.node, 'outgoing', 'nicowner') \
            and mac['address'] == macaddr and mac['nicname'] == nicname:
                return mac
        mac = self.node_new('NIC', macaddr, address=macaddr, unique=False, nicname=nicname, **kw)
        mac.create_relationship_to(drone.node, 'nicowner')
        return mac

    def new_IPaddr(self, nic, ipaddr, **kw):
        '''Create a new IP address (or return a pre-existing one), and point it at its parent
        NIC and its grandparent drone'''
        print 'Adding IP address %s' % (ipaddr)
        ipaddrs = self.ipindex.get('IPaddr', ipaddr)
        for ip in ipaddrs:
            if ip.is_related_to(nic, 'outgoing', 'ipowner'):
                print 'Found this IP address (%s) ipowner related to NIC %s' % (ipaddr, nic)
                return ip
        ip = self.node_new('IPaddr', ipaddr, unique=False, **kw)
        ip.create_relationship_to(nic, 'ipowner')
        drone = nic.get_single_related_node('outgoing', 'nicowner')
        ip.create_relationship_to(drone, 'iphost') # Not sure if I need the grandparent link or not...
        return ip


class HbRing:
    'Class defining the behavior of a heartbeat ring.'
    SWITCH      =  1
    SUBNET      =  2
    THEONERING  =  3 # And The One Ring to rule them all...

    ringnames = {}

    def __init__(self, name, ringtype, parentring=None):
        '''Constructor for a heartbeat ring.
	Although we generally avoid keeping hash tables of nodes in the
	database, I'm currently making an exception for rings.  There are
	many fewer of those than any other kind of node.
        '''
        if ringtype < HbRing.SWITCH or ringtype > HbRing.THEONERING: 
            raise ValueError("Invalid ring type [%s]" % str(ringtype))
        self.node = NEO.new_ring(name, parentring, ringtype=ringtype)
        self.ringtype = ringtype
        self.name = str(name)
        self.parentring = parentring
        self.ourreltype = 'RingMember_' + self.name # Our relationship type
        self.ournexttype = 'RingNext_' + self.name # Our 'next' relationship type
        self.insertpoint1 = None
        self.insertpoint2 = None

        try:
            self.insertpoint1 = self.node.get_single_related_node('incoming', self.ourreltype)
            if self.insertpoint1 is not None:
                try:
                  print 'INSERTPOINT1: ', self.insertpoint1
                  self.insertpoint2 = self.insertpoint1.get_single_related_node('outgoing', self.ournexttype)
                except ValueError:
                    pass
        except ValueError:
            pass
	# Need to figure out what to do about pre-existing members of this ring...
	# For the moment, let's make the entirely inadequate assumption that
	# the data in the database is correct.
	## FIXME - assumption about database being correct

        
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
        print 'Adding Drone %s to ring %s' % (str(drone), str(self))
        # Make sure he's not already in our ring according to our 'database'
        if drone.node.has_relationship_with(self.node, 'outgoing', self.ourreltype):
            print ("Drone %s is already a member of this ring [%s] - removing and re-adding."
            %               (drone.node['name'], self.name))
            self.leave(drone)
        
        # Create a 'ringmember' relationship to this drone
        drone.node.create_relationship_to(self.node, self.ourreltype)
        print 'New ring membership: %s' % (str(self))
        # Should we keep a 'ringip' relationship for this drone?
        # Probably eventually...

        print >>sys.stderr,'Adding drone %s to talk to partners'%drone.node['name'], self.insertpoint1, self.insertpoint2

        if self.insertpoint1 is None:	# Zero nodes previously
           self.insertpoint1 = drone
           return

        if self.insertpoint2 is None:	# One node previously
	    # Create the initial circular list.
            ## FIXME: Ought to label link relationships with IP addresses involved
            # (see comments below)
            NEO.db.relate((drone.node, ring.ournexttype, self.insertpoint1.node)
            		  (self.insertpoint1.node, ring.ournexttype, drone.node))
            drone.start_heartbeat(self, self.insertpoint1)
            self.insertpoint1.start_heartbeat(self, drone)
            self.insertpoint2 = self.insertpoint1
            self.insertpoint1 = drone
            return
        
        # Two or more nodes previously
        nextnext = self.insertpoint2.node.get_single_related_node('outgoing', self.ournexttype)
        if nextnext is not None and nextnext.id != insertpoint1.id:
            # At least 3 nodes before
            insertpoint1.stop_heartbeat(self, self.insertpoint2)
            insertpoint2.stop_heartbeat(self, self.insertpoint1)
        drone.start_heartbeat(self, self.insertpoint1, self.insertpoint2)
        self.insertpoint1.start_heartbeat(self, drone)
        self.insertpoint2.start_heartbeat(self, drone)
        point1rel = insertpoint1.node.get_single_relationship('outgoing', self.ournexttype)
        point1rel.delete()
        # In the future we might want to mark these relationships with the IP addresses involved
        # so that even if the systems change network configurations we can still know what IP to
        # remove.  Right now we rely on the configuration not changing "too much".
        ## FIXME: Ought to label relationships with IP addresses involved.
        NEO.db.relate((self.insertpoint1.node, ring.ournexttype, drone.node)
                      (drone.node, ring.ournexttype, self.insertpoint2.node))
        # This should ensure that we don't keep beating the same nodes over and over
        # again as new nodes join the system.  Instead the latest newbie becomes the next
        # insert point in the ring - spreading the work to the new guys as they arrive.
        self.insertpoint2 = self.insertpoint1
        self.insertpoint1 = drone

    def leave(self, drone):
        'Remove a drone from this heartbeat Ring.'
        try: 
            prevnode = drone.node.get_single_related_node('incoming', self.ournexttype)
        except ValueError:
            prevnode = None
        try: 
            nextnode = drone.node.get_single_related_node('outgoing', self.ournexttype)
        except ValueError:
            nextnode = None

        if nextnode is None and prevnode is None:	# Previous length:	1
                self.insertpoint1 = None		# result length:	0
                self.insertpoint2 = None
                # No database links to remove
		return

	# Clean out the next link relationships to our dearly departed drone
        relationships = drone.node.get_relationships('all', self.ournexttype)
        # Should have exactly two link relationships (one incoming and one outgoing)
        assert len(relationships) == 2
        for rel in relationships:
            rel.delete()
        relationships = None
        rel = None

        if prevnode.id == nextnode.id:			# Previous length:	2
            node = prevnode				# Result length:	1
            if node is None: node = nextnode
            partner = DroneInfo(node['name'])
            drone.stop_heartbeat(self, partner)
            partner.stop_heartbeat(self, drone)
            prevnode.create_relationship_to(nextnode, self.ournexttype)
            self.insertpoint2 = None
            self.insertpoint1 = partner
            return

        # Previous length had to be >= 3		# Previous length:	>=3
							# Result length:	>=2
        prevdrone = DroneInfo(prevnode['name'])
        nextdrone = DroneInfo(nextnode['name'])
        nextnext = nextnode.get_single_related_node('outgoing', self.ournexttype)
        prevdrone.stop_heartbeat(self, drone)
        nextdrone.stop_heartbeat(self, drone)
        if nextnext.id != prevnode.id:			# Previous length:	>= 4
            nextdrone.start_heartbeat(self, prevdrone)	# Result length:	>= 3
            prevdrone.start_heartbeat(self, nextdrone)
        # Poor drone -- all alone in the universe... (maybe even dead...)
        drone.stop_heartbeat(self, prevdrone, nextdrone)
        self.insertpoint1 = prevdrone	# non-minimal, but correct and cheap change
        self.insertpoint2 = nextdrone
        prevnode.create_relationship_to(nextnode, self.ournexttype)

    def __str__(self):
        ret = 'Ring("%s", [' % self.node['name']
        firstdrone=self.insertpoint1
        if firstdrone is not None:
           ret += firstdrone['name']
           nextdrone=firstdrone
           while True:
             try:
                 nextdrone = nextdrone.get_single_related_node('outgoing', self.ournexttype)
                 if nextdrone is None or nextdrone.id == firstdrone.id:  break
                 ret += ', %s' % nextdrone['name']
             except ValueError:
                 break
        ret += '])'
        return ret
        

    @staticmethod
    def reset():
        'Used for testing...'
        global TheOneRing
        HbRing.ringnames = {}
        TheOneRing = HbRing('The One Ring', HbRing.THEONERING)


class DroneInfo:
    'Everything about Drones - endpoints that run our nanoprobes'
    droneset = {}
    droneIPs = {}
    def __init__(self, designation, io,**kw):
        self.io = io
        self.node = NEO.new_drone(designation, **kw)
   
    @staticmethod
    def reset():
        'Used for testing...'
        pass

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
       if dtype == 'netconfig':
           self.add_netconfig_addresses(jsonobj)

    def add_netconfig_addresses(self, jsonobj, **kw):
        '''Save away the network configuration data we got from JSON discovery.
        This includes all our NICs, their MAC addresses, all our IP addresses and so on
        for any non-loopback interface.  Whee!
        In theory we could make a giant 'create' for everything and do all the db creation
        in one swell foop - or at most two...
        '''
        # Ought to protect this code by try blocks...
        # Also ought to figure out which IP is the primary IP for contacting
	# this system
        data = jsonobj['data'] # The data portion of the JSON message
        primaryip = None
        for ifname in data.keys(): # List of interfaces just below the data section
            ifinfo = data[ifname]
            isprimaryif= ifinfo.has_key('default_gw')
            print 'IFINFO: [%s]' % str(ifinfo)
            if not ifinfo.has_key('address'):
                continue
            ifaddr = ifinfo['address']
            print 'ADDRESS: [%s]' % str(ifaddr)
            if ifaddr.startswith('00:00:00:'):
                continue
            nicnode = NEO.new_nic(ifname, ifaddr, self, isprimaryif=isprimaryif, **kw)
            iptable = ifinfo['ipaddrs'] # look in the 'ipaddrs' section
            for ip in iptable.keys():   # keys are 'ip/mask' in CIDR format
                ipinfo = iptable[ip]
                if ipinfo['scope'] != 'global':
                    continue
                (iponly,mask) = ip.split('/')
                isprimaryip = False
                if isprimaryif and primaryip == None:
                    isprimaryip = True
                    primaryip = iponly
                ipnode = NEO.new_IPaddr(nicnode, iponly, ifname=ifname, hostname=self.node['name'])
                # Save away whichever IP address is our primary IP address...
                if isprimaryip:
                    rel = self.node.get_single_relationship('outgoing', 'primaryip')
                    if rel is not None and rel.end_node.id != ipnode.id:
                        rel.delete()
                        rel = None
                    if rel is None:
                      NEO.db.relate((self.node, 'primaryip', ipnode),)


    def select_ip(self, ring):
        'Select an appropriate IP address for talking to a partner on this ring'
        # Current code is not really good enough for the long term,
	# but is good enough for now...
        # In particular, when talking on a particular switch ring, or
	# subnet ring, we want to choose an IP that's on that subnet,
	# and preferably on that particular switch for a switch-level ring.
	# For TheOneRing, we want their primary IP address.
        primaryIP = self.node.get_single_node('outgoing', 'primaryip')
        return primaryIP['name']
    
    def send_hbmsg(self, dest, fstype, port, addrlist):
        '''Send a message with an attached address list and optional port.
           This is intended primarily for start or stop heartbeating messages.'''
        fs = pyFrameSet(fstype)
        pframe = None
        if port is not None and port > 0 and port < 65536:
           pframe = pyIntFrame(FrameTypes.sPORTNUM, intbytes=2, initval=int(port))
        for addr in addrlist:
            if addr is None: continue
            if pframe is not None:
                fs.addframe(pframe)
            aframe = pyAddrFrame(FrameTypes.IPADDR, addrstring=addr)
            fs.append(aframe)
        self.io.sendframesets(dest, (fs,))

    def death_report(self, status, reason, fromaddr, frameset):
        'Process a death/shutdown report for us.  RIP us.'
        print >>sys.stderr, "Node %s has been reported as %s by address %s. Reason: %s" \
        %	(self.designation, status, str(fromaddr), reason)
        self.status = status
        self.reason = reason
        # There is a need for us to be a little more sophisticated
        # in terms of the number of peers this particular drone had
        # It's here in this place that we will eventually add the ability
        # to distinguish death of a switch or subnet or site from death of a single drone
        ringlist = self.ringmemberships.keys()
        for ring in ringlist:
	    HbRing.ringnames[ring].leave(self)


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

    def __str__(self):
        'Give out our designation'
        return 'Drone(%s)' % self.node['name']

    @staticmethod
    def find(designation):
        'Find a drone with the given designation or IP address.'
        if isinstance(designation, str):
            if DroneInfo.droneset.has_key(designation):
                return DroneInfo.droneset[designation]
        elif isinstance(designation, pyNetAddr):
            #Is there a concern about non-canonical IP address formats?
            saddr = str(designation)
            if DroneInfo.droneIPs.has_key(saddr):
                return DroneInfo.droneIPs[saddr]
        return None

    @staticmethod
    def add(designation, io, reason, status='up'):
        "Add a drone to our set if it isn't already there."
        ret = DroneInfo.find(designation);
        if ret is not None:
            return ret
        else:
            ret = DroneInfo(designation, io)
        ret.reason = reason
        ret.status = status
        DroneInfo.droneset[designation] = ret
        return ret

class DispatchTarget:
    '''Base class for handling incoming FrameSets.
    This base class is designated to handle unhandled FrameSets.
    All it does is print that we received them.
    '''
    def __init__(self):
        pass
    def dispatch(self, origaddr, frameset):
        fstype = frameset.get_framesettype()
        print "Received FrameSet of type [%s] from [%s]" \
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
        print>>sys.stderr, "DispatchHBDEAD: received [%s] FrameSet from [%s]" \
	%		(FrameSetTypes.get(fstype)[0], str(origaddr))
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
        print >>sys.stderr,"DispatchSTARTUP: received [%s] FrameSet from [%s]" \
	%		(FrameSetTypes.get(fstype)[0], str(origaddr))
        for frame in frameset.iter():
            frametype=frame.frametype()
            if frametype == FrameTypes.HOSTNAME:
                sysname = frame.getstr()
            if frametype == FrameTypes.JSDISCOVER:
                json = frame.getstr()
        fs = CMAlib.create_setconfig(self.config)
        #print 'Telling them to heartbeat themselves.'
        #fs2 = CMAlib.create_sendexpecthb(self.config, FrameSetTypes.SENDEXPECTHB
        #,		origaddr)
        #print 'Sending SetConfig frameset to %s' % origaddr
        #self.io.sendframesets(origaddr, (fs,fs2))
        self.io.sendframesets(origaddr, fs)
        print 'ADDING DRONE for system %s' % sysname
        DroneInfo.add(sysname, self.io, 'STARTUP packet')
        drone = DroneInfo.find(sysname)
        drone.startaddr=origaddr
        if json is not None:
            drone.logjson(json)
        TheOneRing.join(drone)
        

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
	#%	(self.io.getfd(), self.io.getmaxpktsize())
        self.dispatcher = dispatch
        
    def listen(self):
      'Listen for packets.  Get them dispatched.'
      while True:
        (fromaddr, framesetlist) = self.io.recvframesets()
        if fromaddr is None:
            # BROKEN! ought to be able to set blocking mode on the socket...
            #print "Failed to get a packet - sleeping."
            time.sleep(1.0)
        else:
            #print "Received packet from [%s]" % (str(fromaddr))
            for frameset in framesetlist:
                self.dispatcher.dispatch(fromaddr, frameset)

if __name__ == '__main__':
    #
    #	"Main" program starts below...
    #   It is a test program intended to run with some real nanoprobes running
    #	somewhere out there...
    #

    #NEO =  CMAdb('/backups/neo1')
    NEO =  CMAdb()

    TheOneRing = HbRing('The One Ring', HbRing.THEONERING)
    print 'Ring created!! - id = %d' % TheOneRing.node.id

    print FrameTypes.get(1)[2]

    OurAddr = pyNetAddr((10,10,10,200),1984)
    configinit = {
	'cmainit':	OurAddr,	# Initial 'hello' address
	'cmaaddr':	OurAddr,	# not sure what this one does...
	'cmadisc':	OurAddr,	# Discovery packets sent here
	'cmafail':	OurAddr,	# Failure packets sent here
	'cmaport':	1984,
	'hbport':	1984,
	'outsig':	pySignFrame(1),
	'deadtime':	10*1000000,
	'warntime':	3*1000000,
	'hbtime':	1*1000000,
    }
    disp = MessageDispatcher(
	{	FrameSetTypes.STARTUP: DispatchSTARTUP()
	})
    config = pyConfigContext(init=configinit)
    listener = PacketListener(config, disp)
    listener.listen()
    NEO.close()
