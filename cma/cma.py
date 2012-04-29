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

class DroneInfo:
    'Everything about Drones - those things that run our nanoprobes'
    droneset = {}
    def __init__(self, name):
        self.name = name
        self.addresses = {}
        self.jsondiscovery = {}

    def addaddr(self, addr, ifname=None):
        'Record what IPs this drone has - and on what interfaces'
        print 'Address %s is on interface %s on %s' % \
            (addr, ifname, self.name)
        self.addresses[str(addr)] = (addr, ifname)

    def logjson(self, jsontext):
       'Process and save away JSON discovery data'
       jsonobj = pyConfigContext(jsontext)
       if not jsonobj.has_key('discovertype') or not jsonobj.has_key('data'):
           print 'Invalid JSON discovery packet.'
           return
       dtype = jsonobj['discovertype']
       #print "Saved discovery type %s for endpoint %s." % \
       #   (dtype, self.name)
       self.jsondiscovery[dtype] = jsonobj
       if dtype == 'netconfig':
           self.add_netconfig_addresses(jsonobj)

    def add_netconfig_addresses(self, jsonobj):
        'Save away the network configuration data we got from JSON discovery.'
        # Ought to protect this code by try blocks...
        data = jsonobj['data']
        for intf in data.keys(): # List of interfaces
            ifinfo = data[intf]
            iptable = ifinfo['ipaddrs']
            for ip in iptable.keys(): # ip/mask in CIDR format
                ipinfo = iptable[ip]
                if ipinfo['scope'] != 'global':
                    continue
                (iponly,mask) = ip.split('/')
                self.addaddr(iponly, intf)

    @staticmethod
    def find(designation):
        'Find a drone with the given designation.'
        if DroneInfo.droneset.has_key(designation):
            return DroneInfo.droneset[designation]
        return None

    @staticmethod
    def add(name):
        "Add a drone to our set if it isn't already there."
        if DroneInfo.droneset.has_key(name):
            return DroneInfo.droneset[name]
        ret = DroneInfo(name)
        DroneInfo.droneset[name] = ret
        return ret

class DispatchTarget:
    '''Base class for handling incoming FrameSets.
    The FrameSet stops here - so to speak.
    This base class is designated to handle unhandled FrameSets.
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
        drone.commaddr=origaddr
        drone.addaddr(origaddr)
        if json is not None:
            drone.logjson(json)
        
        

class MessageDispatcher:
    'We dispatch messages where they need to go'
    def __init__(self, dispatchtable):
        self.dispatchtable = dispatchtable
        self.default = DispatchTarget()
        pass
    def dispatch(self, origaddr, frameset):
        fstype = frameset.get_framesettype()
        if self.dispatchtable.has_key(fstype):
            self.dispatchtable[fstype].dispatch(origaddr, frameset)
        else:
            self.default.dispatch(origaddr, frameset)

    def setconfig(self, io, config):
        self.io = io
        self.default.setconfig(io, config)
        for msgtype in self.dispatchtable.keys():
            self.dispatchtable[msgtype].setconfig(io, config)
        
       
    

class PacketListener:
    'Listen for packets and get them dispatched'
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
