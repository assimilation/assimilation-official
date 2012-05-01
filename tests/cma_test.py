import sys
sys.path.append("../pyclasswrappers")
sys.path.append("../cma")
from testify import *
from testify.utils import turtle

from frameinfo import *
from AssimCclasses import *
import gc, sys, time, collections
from cma import *


CheckForDanglingClasses = False
WorstDanglingCount = 0
DEBUG=False


def assert_no_dangling_Cclasses():
    global CheckForDanglingClasses
    global WorstDanglingCount
    HbRing.reset()	# Clean up static Ring data
    DroneInfo.reset()	# Clean up static Drone data
    gc.collect()	# For good measure...
    count =  proj_class_live_object_count()
    # Avoid cluttering the output up with redundant messages...
    if count > WorstDanglingCount and CheckForDanglingClasses:
        WorstDanglingCount = count
        proj_class_dump_live_objects()
        raise AssertionError, "Dangling C-class objects - %d still around" % count

# Values to substitute into this string via '%' operator:
# dronedesignation (%s) MAC address byte (%02x), MAC address byte (%02x), IP address (%s)
netdiscoveryformat='''
{
  "discovertype": "netconfig",
  "description": "IP Network Configuration",
  "source": "netconfig",
  "host": "%s",
  "data": {
    "eth0": {
	"address": "00:1b:fc:1b:%02x:%02x",
	"carrier": 1,
	"duplex": "full",
	"mtu": 1500,
	"operstate": "up",
	"speed": 1000,
	"default_gw": true,
	"ipaddrs": { "%s/16": {"brd":"10.20.255.255", "scope":"global", "name":"eth0"}}
    }, 
    "lo": {
	"address": "00:00:00:00:00:00",
	"carrier": 1,
	"mtu": 16436,
	"operstate": "unknown",
	"ipaddrs": { "127.0.0.1/8": {"scope":"host"}, "::1/128": {"scope":"host"}}
    }
  }
}
'''


byte1 = 10
byte2 = 20

def droneipaddress(hostnumber):
    byte3 = int(hostnumber / 256)
    byte4 = hostnumber % 256
    return pyNetAddr([byte1,byte2,byte3,byte4],)

def dronedesignation(hostnumber):
    return 'drone%05d' % hostnumber

def hostdiscoveryinfo(hostnumber):
    byte3 = int(hostnumber / 256)
    byte4 = hostnumber % 256
    s = str(droneipaddress(hostnumber))
    return netdiscoveryformat % (dronedesignation(hostnumber), byte3, byte4, s)
    
def geninitconfig(ouraddr):
    configinit = {
	    'cmainit':	ouraddr,	# Initial 'hello' address
	    'cmaaddr':	ouraddr,	# not sure what this one does...
	    'cmadisc':	ouraddr,	# Discovery packets sent here
	    'cmafail':	ouraddr,	# Failure packets sent here
	    'cmaport':	1984,
	    'hbport':	1984,
	    'outsig':	pySignFrame(1),
	    'deadtime':	10*1000000,
	    'warntime':	3*1000000,
	    'hbtime':	1*1000000,
        }
    return configinit;

class AUDITS(TestCase):
    def auditadrone(self, droneid):
        designation = dronedesignation(droneid)
        droneip = droneipaddress(droneid)
        dronecount = len(DroneInfo.droneset)
        droneipstr = str(droneip)
        # Did the drone get put in the DroneInfo table?
        drone=DroneInfo.find(designation)
        self.assertTrue(drone is not None)
        # Did the drone's list of addresses get updated?
        self.assertEqual(len(drone.addresses), 1)
        # Does the drone address table match the info from JSON?
        self.assertEqual(drone.addresses[droneipstr], (droneipstr, 'eth0'))
        # the JSON should have exactly 5 top-level keys
        self.assertEqual(len(drone.jsondiscovery['netconfig'].keys()), 5)
        # Was the JSON host name saved away correctly?
        self.assertEqual(drone.jsondiscovery['netconfig']['host'], designation)
    
        peercount=0
        ringcount=0
        for ring in drone.ringmemberships.values():
            ringcount += 1
            # How many peers should it have?
            if len(ring.memberlist) == 1:
                pass # No peers in this ring...
            elif len(ring.memberlist) == 2:
                peercount += 1
            else:
                peercount += 2
            # Make sure we're listed under our designation
            self.assertTrue(ring.members[drone.designation] is drone)
            self.assertEqual(len(ring.members), len(ring.memberlist))
        # We have to be members of at least one ring...
        self.assertTrue(ringcount >= 1)
        # Do we have the right number of ring peers?
        #print >>sys.stderr, "Checking peer count for drone %s (%d)" % (drone, len(drone.ringpeers))
        self.assertEqual(len(drone.ringpeers), peercount)
        # Drone should be a member of one ring (for now)
        self.assertEqual(len(drone.ringmemberships),1)

    def auditSETCONFIG(self, packetreturn, droneid, configinit):
        toaddr = packetreturn[0]
        sentfs = packetreturn[1]
        droneip = droneipaddress(droneid)
        
        # Was it a SETCONFIG packet?
        self.assertEqual(sentfs.get_framesettype(), FrameSetTypes.SETCONFIG)
        # Was the SETCONFIG sent back to the drone?
        self.assertEqual(toaddr,droneip)
        # Lets check the number of Frames in the SETCONFIG Frameset
        configlen =  len(configinit)-1  # We do not send Frames in configinfo
        expectedlen = 2 * configlen + 4 # each address has a port that goes with it
        self.assertEqual(expectedlen, len(sentfs))	# Was it the right size?

def auditalldrones():
    audit = AUDITS()
    dronecount= len(DroneInfo.droneset)
    for droneid in range(1,dronecount+1):
        audit.auditadrone(droneid)

class TestIO(turtle.Turtle):
    '''A pyNetIOudp replacement for testing.  It is given a list of packets to be 'read' and in turn
    saves all the packets it 'writes' for us to inspect.
    '''
    def __init__(self, addrframesetpairs, sleepatend=0):
        if isinstance(addrframesetpairs, tuple):
            addrframesetpairs = addrframesetpairs
        self.inframes = addrframesetpairs
        self.packetswritten=[]
        self.packetsread=0
        self.sleepatend=sleepatend
        self.index=0
        turtle.Turtle.__init__(self)

    def recvframesets(self):
        # Audit after each packet is processed - and once before the first packet.
        auditalldrones()
        if self.index >= len(self.inframes):
            time.sleep(self.sleepatend)
            raise StopIteration('End of Packets')
        ret = self.inframes[self.index]
        self.index += 1
        self.packetsread += len(ret[1])
        return ret

    def sendframesets(self, dest, fslist):
	if not isinstance(fslist, collections.Sequence):
            return self._sendaframeset(dest, fslist)
        for fs in fslist:
            self._sendaframeset(dest, fs)

    def _sendaframeset(self, dest, fslist):
        self.packetswritten.append((dest,fslist))

    def getmaxpktsize(self):	return 60000
    def getfd(self):		return 4

    def dumppackets(self):
        print >>sys.stderr, 'Sent %d packets' % len(self.packetswritten)
        for packet in self.packetswritten:
            print '%s (%s)' % (packet[0], packet[1])
    

class TestTestInfrastructure(TestCase):
    def test_eof(self):
        'Get EOF with empty input'
        framesets=[]
        io = TestIO(framesets, 0)
        # just make sure it seems to do the right thing
        self.assertRaises(StopIteration, io.recvframesets)

    def test_get1pkt(self):
        'Read a single packet'
        otherguy = pyNetAddr([1,2,3,4],)
        strframe1=pyCstringFrame(FrameTypes.CSTRINGVAL, "Hello, world.")
        fs = pyFrameSet(42)
        fs.append(strframe1)
        framesets=((otherguy, (strframe1,)),)
        io = TestIO(framesets, 0)
        gottenfs = io.recvframesets()
        self.assertEqual(len(gottenfs), 2)
        self.assertEqual(gottenfs, framesets[0])
        self.assertRaises(StopIteration, io.recvframesets)

    def test_echo1pkt(self):
        'Read a packet and write it back out'
        strframe1=pyCstringFrame(FrameTypes.CSTRINGVAL, "Hello, world.")
        fs = pyFrameSet(42)
        fs.append(strframe1)
        otherguy = pyNetAddr([1,2,3,4],)
        framesets=((otherguy, (strframe1,)),)
        io = TestIO(framesets, 0)
        fslist = io.recvframesets()		# read in a packet
        self.assertEqual(len(fslist), 2)
        self.assertEqual(fslist, framesets[0])
        io.sendframesets(fslist[0], fslist[1])	# echo it back out
        self.assertEqual(len(io.packetswritten), 1)
        self.assertEqual(len(io.packetswritten), len(framesets))
        self.assertRaises(StopIteration, io.recvframesets)

class TestCMABasic(TestCase):
    def test_startup(self):
        '''A semi-interesting test: We send a STARTUP message and get back a
        SETCONFIG message with lots of good stuff in it.'''
        droneid = 1
        droneip = droneipaddress(droneid)
        designation = dronedesignation(droneid)
        designationframe=pyCstringFrame(FrameTypes.HOSTNAME, designation)
        dronediscovery=hostdiscoveryinfo(droneid)
        discoveryframe=pyCstringFrame(FrameTypes.JSDISCOVER, dronediscovery)
        fs = pyFrameSet(FrameSetTypes.STARTUP)
        fs.append(designationframe)
        fs.append(discoveryframe)
        fsin = ((droneip, (fs,)),)
        io = TestIO(fsin,0)
        OurAddr = pyNetAddr((10,10,10,200),1984)
        configinit = geninitconfig(OurAddr)
        disp = MessageDispatcher({FrameSetTypes.STARTUP: DispatchSTARTUP()})
        config = pyConfigContext(init=configinit)
        listener = PacketListener(config, disp, io=io)
        # We send the CMA an intial STARTUP packet
        self.assertRaises(StopIteration, listener.listen) # We audit after each packet is processed
        # Let's see what happened...

        self.assertEqual(len(io.packetswritten), 1) # Did we get back one packet?
        AUDITS().auditSETCONFIG(io.packetswritten[0], droneid, configinit)
	# Drone and Ring tables are automatically audited after each packet

    def test_several_startups(self):
        OurAddr = pyNetAddr((10,10,10,200),1984)
        configinit = geninitconfig(OurAddr)
        fsin = []
        for droneid in range(1,1001):
            droneip = droneipaddress(droneid)
            designation = dronedesignation(droneid)
            designationframe=pyCstringFrame(FrameTypes.HOSTNAME, designation)
            dronediscovery=hostdiscoveryinfo(droneid)
            discoveryframe=pyCstringFrame(FrameTypes.JSDISCOVER, dronediscovery)
            fs = pyFrameSet(FrameSetTypes.STARTUP)
            fs.append(designationframe)
            fs.append(discoveryframe)
            fsin.append((droneip, (fs,)))
        io = TestIO(fsin)
        disp = MessageDispatcher({FrameSetTypes.STARTUP: DispatchSTARTUP()})
        config = pyConfigContext(init=configinit)
        listener = PacketListener(config, disp, io=io)
        # We send the CMA a BUNCH of intial STARTUP packets
        self.assertRaises(StopIteration, listener.listen)
	# We audit after each packet is processed
        # The auditing code will make sure all is well...
        # But it doesn't know how may drones we just registered
        self.assertEqual(len(DroneInfo.droneset), droneid)

        print "The CMA read %d packets."  % io.packetsread
        print "The CMA wrote %d packets." % len(io.packetswritten)
        #io.dumppackets()


    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

if __name__ == "__main__":
    run()
