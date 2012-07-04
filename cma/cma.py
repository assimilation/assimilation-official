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
#       ringmember      ring            ipaddr

    def __init__(self, pathname):
        # Code for the Java-deficient (like me)
        if not os.environ.has_key('JAVA_HOME'):
            altjava='/etc/alternatives/java'
            if os.path.islink(altjava):
                javahome = os.path.dirname(os.path.dirname(os.readlink(altjava)))
                os.environ['JAVA_HOME'] = javahome
        import neo4j
        self.db = neo4j.GraphDatabase(pathname)
        indexes = {'ringindex':'exact', 'droneindex':'exact', 'ipindex':'exact', 'macindex':'exact'}
        for idx in indexes.keys():
            if not self.db.node.indexes.exists(idx):
                self.db.node.indexes.create(idx, type=indexes[idx])
        self.ringindex = self.db.node.indexes.get('ringindex')		# Rings
        self.droneindex = self.db.node.indexes.get('droneindex')	# Drones
        self.ipindex = self.db.node.indexes.get('ipindex')		# IP addresses
        self.macindex = self.db.node.indexes.get('macindex')		# MAC addresses

    def getring(self, name):
        'Find a unique ring in the ring index'
        ringhits = self.ringindex['name'][name]
        for ring in ringhits:
            ringhits.close()
            return ring
        ringhits.close()
        return None

    def add_ringindex(self, node):
        'Add this ring node to our ring index'
        name = node['name']
        assert node['nodetype'] == 'ring'
        assert self.getring(name) is None
        self.ringindex['name'][name] = node

    def getdrone(self, designation):
        'Find a unique drone node in the drone index'
        dronehits = self.droneindex['designation'][designation]
        try:
            for drone in dronehits:
                dronehits.close()
                return drone
        except RuntimeError as e:
            print 'Caught runtime error searching drone index'
        dronehits.close()
        return None

    def add_droneindex(self, drone):
        'Add this drone node to our drone index'
        designation = drone['designation']
        assert drone['nodetype'] == 'drone'
        assert self.getdrone(designation) is None
        self.ringindex['designation'][designation] = drone

    def getMACaddr(self, address):
        'Find an interface node with a unique MAC address in the MAC address index'
        machits = self.macindex['macaddr'][address]
        for mac in machits:
            machits.close()
            return mac
        machits.close()
        return None

    def add_MACindex(self, node):
        'Add this NIC node to our MAC address index'
        mac = node['macaddr']
        assert node['nodetype'] == 'nic'
        assert self.getMACaddr(mac) is None  # Probably too strict
        self.ringindex['macaddr'][mac] = node

    def getIPaddr(self, address):
        'Find a unique IP address node in our IP address index'
        iphits = self.ringindex['ipaddr'][address]
        for ip in iphits:
            iphits.close()
            return ip
        iphits.close()
        return None

    def add_IPindex(self, node):
        'Add this IP address node to our IP address index'
        ip = node['ipaddr']
        assert node['nodetype'] == 'ipaddr'
        assert self.getIPaddr(ip) is None  # Probably too strict
        self.ringindex['ipaddr'][ip] = node

    def new_ring(self, name, **kw):
        'Create a new ring (or return a pre-existing one), and put it in the ring index'
        ring = self.getring(name)
        if ring is not None:
            print >>sys.stderr, 'Returning pre-existing ring [%s]' % ring.name
            return ring
        with self.db.transaction:
            ring = self.db.node(nodetype='ring', name=name, **kw)
            self.add_ringindex(ring)
            print >>sys.stderr, 'Creating new ring [%s]' % ring.name
        return ring

    def new_drone(self, designation, **kw):
        'Create a new drone (or return a pre-existing one), and put it in the drone index'
        print 'Adding drone', designation
        drone = self.getdrone(designation)
        if drone is not None:
            print 'Found drone %s in drone index' %  designation
            return drone
        with self.db.transaction:
            print self
            print self.db
            print self.db.node
            drone = self.db.node(nodetype='drone', designation=designation, **kw)
            self.add_droneindex(drone)
        return drone

    def new_nic(self, drone, macaddr, **kw):
        '''Create a new NIC (or return a pre-existing one), and put it in the mac address index,
        and point it at its parent drone.'''
        machits = self.macindex['macaddr'][macaddr]
        for mac in machits:
            if mac.ipowner[0].outgoing.designation == drone.designation:
                machits.close()
                return mac
            else:
                print "Duplicate MAC address for %s: %s vs %s" % \
                    (macaddr, drone.designation, mac.ipowner[0].outgoing.designation)
        machits.close()
        with self.db.transaction:
            nic = self.db.node(nodetype='nic', macaddr=macaddr, **kw)
            self.add_MACindex(nic)
            # Point this NIC at the drone that owns it.
            nic.relationships.create('nichost', drone, hostname=drone['designation'], reltype='nichost')
        return nic

    def new_IPaddr(self, nic, ipaddr, **kw):
        '''Create a new IP address (or return a pre-existing one), and point it at its parent
        NIC and its grandparent drone'''
        iphits = self.ipindex['ipaddr'][macaddr]
        drone =  nic.nichost[0].outgoing
        for ip in iphits:
            # This works because we point at our grandparent as well as our parent...
            if ip.iphost[0].outgoing.designation == drone.designation:
                iphits.close()
                return ip
            else:
                print "Duplicate IP address for %s: %s vs %s" % \
                    (ipaddr, drone.designation, ip.ipowner[0].outgoing.designation)
        iphits.close()
        with self.db.transaction:
            ip = self.db.node(nodetype='ipaddr', ipaddr=ipaddr, **kw)
            self.add_IPindex(ip)
            # Point this IP address at the NIC that owns it.
            nic.relationships.create('ipowner', nic, reltype='ipowner')
            # Also point this IP address at the drone that owns its NIC (our grandparent)
            nic.relationships.create('iphost', drone, reltype='iphost')
        return ip


class HbRing:
    'Class defining the behavior of a heartbeat ring.'
    SWITCH      =  1
    SUBNET      =  2
    THEONERING  =  3 # And The One Ring to rule them all...

    ringnames = {}

    def __init__(self, name, ringtype, parentring=None):
        'Constructor for a heartbeat ring.'
        if ringtype < HbRing.SWITCH or ringtype > HbRing.THEONERING: 
            raise ValueError("Invalid ring type [%s]" % str(ringtype))
        if HbRing.ringnames.has_key(name):
            raise ValueError("ring name [%s] already exists." % str(naem))
        HbRing.ringnames[name] = self
        self.members = {}
        self.memberlist = []
        self.ringtype = ringtype
        self.name = str(name)
        self.parentring = parentring
        NEO.new_ring(name, ringtype=ringtype)

    def join(self, drone):
        'Add this drone to our ring'
        # Make sure he's not already in our ring according to our 'database'
        if self.members.has_key(drone.designation):
            print self.members
            raise ValueError("Drone %s is already a member of this ring [%s]"
            %               (drone.designation, self.name))

        # Insert this drone into our 'database', and us into the drone's
        self.members[drone.designation] = weakref.proxy(drone)
        drone.ringmemberships[self.name] = weakref.proxy(self)
        partners = self._findringpartners(drone)	# Also adds drone to memberlist

        #print >>sys.stderr,'Adding drone %s to talk to partners'%drone.designation, partners
        if partners == None: return
        if len(self.memberlist) == 2:
            drone.start_heartbeat(self, partners[0])
            partners[0].start_heartbeat(self, drone)
            return
        elif len(self.memberlist) > 3:
            partners[0].stop_heartbeat(self, partners[1])
            partners[1].stop_heartbeat(self, partners[0])
        drone.start_heartbeat(self, partners[0], partners[1])
        partners[0].start_heartbeat(self, drone)
        partners[1].start_heartbeat(self, drone)

    def leave(self, drone):
        'Remove a drone from this heartbeat Ring.'
        if not self.members.has_key(drone.designation):
            raise ValueError("Drone %s is not a member of this ring [%s]"
            %               (drone.designation, self.name))
        location = None
        for j in range(0,len(self.memberlist)): # Index won't work due to weakproxy
            if self.memberlist[j].designation == drone.designation:
                location = j
                break
        # Remove the associations from the 'database'
        del self.memberlist[location]
        del self.members[drone.designation]
        del drone.ringmemberships[self.name]

        if len(self.memberlist) == 0:  return   # Previous length: 1
        if len(self.memberlist) == 1:           # Previous length: 2
            drone.stop_heartbeat(self, self.memberlist[0])
            self.memberlist[0].stop_heartbeat(self, drone)
            return
        # Previous length had to be >= 3
        partner1loc=location
        partner2loc=location-1
        if location >= len(self.memberlist):
            partner1loc = 0
        if location == 0:
            partner2loc = len(self.memberlist)-1

	partner1 = self.memberlist[partner1loc]
        partner2 = None
        partner1.stop_heartbeat(self, drone)
        if partner1loc != partner2loc:
            partner2 = self.memberlist[partner2loc]
            partner2.stop_heartbeat(self, drone)
            partner1.start_heartbeat(self, partner2)
            partner2.start_heartbeat(self, partner1)
        # Poor drone -- all alone in the universe... (maybe even dead...)
        drone.stop_heartbeat(self, partner1, partner2)
        
    def _findringpartners(self, drone):
        'Find (one or) two partners for this drone to heartbeat with.'
        # It would be nice to not keep updating the drone on the end of the list
        # I suppose walking through the ring would be a good choice
        # or maybe choosing a random insert position.

	# Insert the partner into the 'database'
        self.memberlist.insert(0, weakref.proxy(drone))
        nummember = len(self.memberlist)
        if nummember == 1: return None
        if nummember == 2: return (self.memberlist[1],)
        return (self.memberlist[1], self.memberlist[nummember-1])

    def __len__(self):
        'Length function - returns number of members in this ring.'
        return len(self.memberlist)

    def __str__(self):
        ret = 'Ring("%s", [' % self.name
        comma=''
        for drone in memberlist:
            ret += '%s%s' % (comma, drone)
            comma=','
        ret += ']'
        return ret
        

    @staticmethod
    def reset():
        global TheOneRing
        HbRing.ringnames = {}
        TheOneRing = HbRing('The One Ring', HbRing.THEONERING)


class DroneInfo:
    'Everything about Drones - endpoints that run our nanoprobes'
    droneset = {}
    droneIPs = {}
    def __init__(self, designation, io,**kw):
        self.designation = designation
        self.addresses = {}
        self.jsondiscovery = {}
        self.ringpeers = {}
        self.ringmemberships = {}
        self.io = io
        self.drone = NEO.new_drone(designation, **kw)
   
    @staticmethod
    def reset():
        DroneInfo.droneset = {}
        DroneInfo.droneIPs = {}

    def addaddr(self, addr, ifname=None):
        'Record what IPs this drone has - and on what interfaces'
        #print >>sys.stderr, 'Address %s is on interface %s on %s' % \
        #    (addr, ifname, self.designation)
        self.addresses[str(addr)] = (addr, ifname)

    def logjson(self, jsontext):
       'Process and save away JSON discovery data'
       jsonobj = pyConfigContext(jsontext)
       if not jsonobj.has_key('discovertype') or not jsonobj.has_key('data'):
           print >>sys.stderr, 'Invalid JSON discovery packet.'
           return
       dtype = jsonobj['discovertype']
       #print "Saved discovery type %s for endpoint %s." % \
       #   (dtype, self.designation)
       self.jsondiscovery[dtype] = jsonobj
       if dtype == 'netconfig':
           self.add_netconfig_addresses(jsonobj)

    def add_netconfig_addresses(self, jsonobj):
        'Save away the network configuration data we got from JSON discovery.'
        # Ought to protect this code by try blocks...
        # Also ought to figure out which IP is the primary IP for contacting
	# this system
        data = jsonobj['data'] # The data portion of the JSON message
        primaryip = None
        for intf in data.keys(): # List of interfaces just below the data cection
            ifinfo = data[intf]
            isprimaryif= ifinfo.has_key('default_gw')
            iptable = ifinfo['ipaddrs'] # look in the 'ipaddrs' section
            for ip in iptable.keys():   # keys are 'ip/mask' in CIDR format
                ipinfo = iptable[ip]
                if ipinfo['scope'] != 'global':
                    continue
                (iponly,mask) = ip.split('/')
                self.addaddr(iponly, intf)
                DroneInfo.droneIPs[iponly] = self
		
                if isprimaryif and primaryip == None:
                    primaryip = iponly
                    self.primaryIP = iponly
                    self.primaryIF = intf

    def select_ip(self, ring, partner):
        'Select an appropriate IP address for talking to this partner on this ring'
        # Not really good enough for the long term, but good enough for now...
        # In particular, when talking on a particular switch ring, or
	# subnet ring, we want to choose an IP that's on that subnet.
	# For TheOneRing, we want their primary IP address.
        try:
            return partner.primaryIP
        except AttributeError as e:
            # This shouldn't happen, but it's a reasonable recovery,
            # because we _have_ to know the address they're sending from.
            return partner.startaddr
    
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
        'Start heartbeating to the given partners'
        ourip = self.select_ip(ring, self)
        partner1ip = self.select_ip(ring, partner1)
        if partner2 is not None:
            partner2ip = self.select_ip(ring, partner2)
        else:
            partner2ip = None
        #print >>sys.stderr, 'We want to start heartbeating %s to %s' \
        #%	(self.designation, partner1ip)
        #print >>sys.stderr, "%s now peering with %s" % (self, partner1)
        self.ringpeers[partner1.designation] = partner1
        if partner2 is not None:
            #print >>sys.stderr, 'We also want to start heartbeating %s to %s' \
            #%		(self.designation, partner2ip)
            self.ringpeers[partner2.designation] = partner2
            #print >>sys.stderr, "%s now peering with %s" % (self, partner2)
        #print >>sys.stderr, self, self.ringpeers
        self.send_hbmsg(ourip, FrameSetTypes.SENDEXPECTHB, 0, (partner1ip, partner2ip))

    def stop_heartbeat(self, ring, partner1, partner2=None):
        'Stop heartbeating to the given partners.'
        ourip = self.select_ip(ring, self)
        partner1ip = self.select_ip(ring, partner1)
        if partner2 is not None:
            partner2ip = self.select_ip(ring, partner2)
        else:
            partner2ip = None
        #print >>sys.stderr, 'We want to stop heartbeating %s to %s' \
        #        % (self.designation, partner1ip)
        #print >>sys.stderr, "IN STOP: %s, %s" % (self.designation, partner1.designation)
	#print >>sys.stderr, "PARTNERS:", self.ringpeers.keys()
        # Remove partner1 from our 'database'
        del self.ringpeers[partner1.designation]
        if partner2 is not None:
            #print >>sys.stderr, 'We also want to stop heartbeating %s to %s' \
            #%		(self.designation, partner2ip)
            # Remove partner2 from our 'database'
            del self.ringpeers[partner2.designation]
        #print >>sys.stderr, self, self.ringpeers
        self.send_hbmsg(ourip, FrameSetTypes.STOPSENDEXPECTHB, 0, (partner1ip, partner2ip))

    def __str__(self):
        'Give out our designation'
        return 'Drone(%s)' % self.designation

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
    #

    NEO =  CMAdb('/backups/neo1')

    TheOneRing = HbRing('The One Ring', HbRing.THEONERING)
    print 'Ring created!!'

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
