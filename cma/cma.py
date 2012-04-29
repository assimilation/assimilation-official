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

import sys, time
sys.path.append("../pyclasswrappers")
sys.path.append("pyclasswrappers")
from frameinfo import FrameTypes, FrameSetTypes
from AssimCclasses import *

class HbRing:
    'Class defining the behavior of a heartbeat ring.'
    SWITCH      =  1
    SUBNET      =  2
    THEONERING  =  3 # And The One Ring to rule them all...
    members = {}
    memberlist = []

    def __init__(self, name, ringtype, parentring=None):
        'Constructor for a heartbeat ring.'
        if ringtype < HbRing.SWITCH or ringtype > HbRing.THEONERING: 
            raise ValueError("Invalid ring type [%s]" % str(ringtype))
        self.ringtype = ringtype
        self.name = str(name)
        self.parentring = parentring

    def join(self, drone):
        'Add this drone to our ring'
        if self.members.has_key(drone.designation):
            raise ValueError("Drone %s is already a member of this ring [%s]"
            %               (drone.designation, self.name))

        drone.ringmemberships[self.name] = self
        partners = self._findringpartners(drone)
        print 'Adding drone %s to talk to partners'%drone.designation, partners
        if partners == None: return
        if len(partners) == 1:
            drone.start_heartbeat(self, partners[0])
            partners[0].start_heartbeat(self, drone)
            return
        partners[0].stop_heartbeat(partners[1])
        partners[1].stop_heartbeat(partners[0])
        drone.start_heartbeat(self, partners[0], partners[1])
        partners[0].start_heartbeat(self, drone)
        partners[1].start_heartbeat(self, drone)

    def leave(self, drone):
        'Remove a drone from this heartbeat Ring.'
        if not self.members.has_key(drone.designation):
            raise ValueError("Drone %s is not a member of this ring [%s]"
            %               (drone.designation, self.name))
        location = self.memberlist.index(drone)

        del self.members[drone.designation]
        del self.memberlist[location]
        del drone.ringmemberships[self.name]

        if len(self.memberlist) == 0:  return   # Previous length: 1
        if len(self.memberlist) == 1:           # Previous length: 2
            drone.stop_heartbeat(self.memberlist[0])
            memberlist[0].stop_heartbeat(drone)
            return
        # Previous length had to be >= 3
        partner1=location
        partner2=location-1
        if location >= len(self.memberlist):
            partner1 = 0
        if location == 0:
            partner2 = len(self.memberlist)-1

        partner1.stop_heartbeat(drone)
        partner2.stop_heartbeat(drone)
        partner1.start_heartbeat(self, partner2)
        partner2.start_heartbeat(self, partner1)
        # Poor drone -- all alone in the universe... (maybe even dead...)
        drone.stop_heartbeat(partner1,partner2)
        
    def _findringpartners(self, drone):
        'Find (one or) two partners for this drone to heartbeat with.'
        # It would be nice to not keep updating the drone on the end of the list
        # I suppose walking through the ring would be a good choice
        # or maybe choosing a random insert position.
        self.memberlist.insert(0,drone)
        nummember = len(self.memberlist)
        if nummember == 1: return None
        if nummember == 2: return (self.memberlist[1],)
        return (self.memberlist[0], self.memberlist[nummember-1])

    def __len__(self):
        'Length function - returns number of members in this ring.'
        return len(self.memberlist)

    def __str__(self):
        return 'Ring %s' % self.name

TheOneRing = HbRing('The One Ring', HbRing.THEONERING)

class DroneInfo:
    'Everything about Drones - endpoints that run our nanoprobes'
    droneset = {}
    def __init__(self, name):
        self.designation = name
        self.addresses = {}
        self.jsondiscovery = {}
        self.ringpeers = {}
        self.ringmemberships = {}

    def addaddr(self, addr, ifname=None):
        'Record what IPs this drone has - and on what interfaces'
        print 'Address %s is on interface %s on %s' % \
            (addr, ifname, self.designation)
        self.addresses[str(addr)] = (addr, ifname)

    def logjson(self, jsontext):
       'Process and save away JSON discovery data'
       jsonobj = pyConfigContext(jsontext)
       if not jsonobj.has_key('discovertype') or not jsonobj.has_key('data'):
           print 'Invalid JSON discovery packet.'
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
                if isprimaryif and primaryip == None:
                    primaryip = iponly
                    self.primaryIP = iponly
                    self.primaryIF = intf

    def select_partner_ip(self, ring, partner):
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

    def start_heartbeat(self, ring, partner1, partner2=None):
        'Start heartbeating to the given partners'
        partner1ip = self.select_partner_ip(ring, partner1)
        if partner2 is not None:
            partner2ip = self.select_partner_ip(ring, partner2)
        else:
            partner2ip = None
        print 'We want to start heartbeating %s to %s' % (self.name, partner1ip)
        if partner2 is not None:
            print 'We also want to start heartbeating %s to %s' \
            %		(self.name, partner2ip)

    def stop_heartbeat(self, partner1, partner2=None):
        'Stop heartbeating to the given partners.'
        partner1ip = self.select_partner_ip(ring, partner1)
        if partner2 is not None:
            partner2ip = self.select_partner_ip(ring, partner2)
        else:
            partner2ip = None
        print 'We want to stop heartbeating %s to %s' % (self.name, partner1ip)
        if partner2 is not None:
            print 'We also want to stop heartbeating %s to %s' \
            %		(self.name, partner2ip)

    @staticmethod
    def find(designation):
        'Find a drone with the given designation.'
        if DroneInfo.droneset.has_key(designation):
            return DroneInfo.droneset[designation]
        return None

    @staticmethod
    def add(designation):
        "Add a drone to our set if it isn't already there."
        if DroneInfo.droneset.has_key(designation):
            return DroneInfo.droneset[designation]
        ret = DroneInfo(designation)
        DroneInfo.droneset[designation] = ret
        return ret

    def __str__(self):
        'Give out our designation'
        return 'Drone %s' % self.designation

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
        
class DispatchSTARTUP(DispatchTarget):
    'DispatchTarget subclass for handling incoming STARTUP FrameSets.'
    def dispatch(self, origaddr, frameset):
        json = None
        fstype = frameset.get_framesettype()
        print "DispatchSTARTUP: received [%s] FrameSet from [%s]" \
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
        print 'Sending SetConfig frameset to %s' % origaddr
        #self.io.sendframesets(origaddr, (fs,fs2))
        self.io.sendframesets(origaddr, fs)
        DroneInfo.add(sysname)
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
    def __init__(self, config, dispatch):
        self.config = config
	self.io = pyNetIOudp(config, pyPacketDecoder())

        dispatch.setconfig(self.io, config)

	self.io.bindaddr(config["cmainit"])
        self.io.setblockio(True)
        print "IO[socket=%d,maxpacket=%d] created." \
	%	(self.io.getfd(), self.io.getmaxpktsize())
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

#
#	"Main" program starts below...
#

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
