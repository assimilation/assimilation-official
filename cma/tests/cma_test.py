# vim: smartindent tabstop=4 shiftwidth=4 expandtab
#
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
_suites = ['all', 'cma']
import sys
sys.path.append("../cma")
sys.path.append("/usr/local/lib/python2.7/dist-packages")
from py2neo import neo4j
from testify import *
from testify.utils import turtle

from frameinfo import *
from AssimCclasses import *
import gc, sys, time, collections, os
from graphnodes import nodeconstructor
from cmainit import CMAinit
from cmadb import CMAdb, CMAclass
from packetlistener import PacketListener
from messagedispatcher import MessageDispatcher
from dispatchtarget import DispatchSTARTUP, DispatchHBDEAD, DispatchJSDISCOVERY, DispatchSWDISCOVER
from hbring import HbRing
from droneinfo import Drone
import optparse
from graphnodes import GraphNode


WorstDanglingCount = 0
CheckForDanglingClasses = False
DEBUG=True
DoAudit=True
SavePackets=True
doHBDEAD=True
MaxDrone=4
MaxDrone=3
MaxDrone=10000
MaxDrone=5

MaxDrone=2
doHBDEAD=True

BuildListOnly = False
if BuildListOnly:
    doHBDEAD=False
    SavePackets=False
    DoAudit=False
    CheckForDanglingClasses=False
    DEBUG=False
BuildListOnly = True

t1 = MaxDrone
if t1 < 1000: t1 = 1000
t2 = MaxDrone/100
if t2 < 10: t2 = 10
t3 = t2


#gc.set_threshold(t1, t2, t3)

def assert_no_dangling_Cclasses():
    global CheckForDanglingClasses
    global WorstDanglingCount
    CMAdb.cdb = None
    CMAdb.io = None
    CMAdb.TheOneRing = None
    CMAdb.store = None
    gc.collect()    # For good measure...
    count =  proj_class_live_object_count()
    #print >>sys.stderr, "CHECKING FOR DANGLING CLASSES (%d)..." % count
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
    byte2 = int(hostnumber / 65536)
    byte3 = int((hostnumber / 256) % 256)
    byte4 = hostnumber % 256
    return pyNetAddr([byte1,byte2,byte3,byte4],1984)

def dronedesignation(hostnumber):
    return 'drone%06d' % hostnumber

def hostdiscoveryinfo(hostnumber):
    byte3 = int(hostnumber / 256)
    byte4 = hostnumber % 256
    s = str(droneipaddress(hostnumber))
    return netdiscoveryformat % (dronedesignation(hostnumber), byte3, byte4, s)
    
def geninitconfig(ouraddr):
    return {
        'cmainit':  ouraddr,    # Initial 'hello' address
        'cmaaddr':  ouraddr,    # not sure what this one does...
        'cmadisc':  ouraddr,    # Discovery packets sent here
        'cmafail':  ouraddr,    # Failure packets sent here
        'cmaport':  1984,
        'hbport':   1984,
        'outsig':   pySignFrame(1),
        'deadtime': 10*1000000,
        'warntime': 3*1000000,
        'hbtime':   1*1000000,
        }

class AUDITS(TestCase):
    def auditadrone(self, droneid):
        designation = dronedesignation(droneid)
        droneip = droneipaddress(droneid)
        droneipstr = str(droneip)
        # Did the drone get put in the Drone table?
        drone=Drone.find(designation)
        self.assertTrue(drone is not None)
        # Did the drone's list of addresses get updated?
        ipnodes = drone.get_owned_ips()
        ipnodes = [ip for ip in ipnodes]
        self.assertEqual(len(ipnodes), 1)
        ipnode = ipnodes[0]
        ipnodeaddr = pyNetAddr(ipnode.ipaddr)
        json = drone.JSON_netconfig
        jsobj = pyConfigContext(init=json)
        jsdata = jsobj['data']
        eth0obj = jsdata['eth0']
        print >> sys.stderr, 'ETH0OBJ = ', eth0obj
        eth0addrcidr = eth0obj['ipaddrs'].keys()[0]
        print 'ETH0 ADDRCIDR:', eth0addrcidr
        eth0addrstr, cidrmask = eth0addrcidr.split('/')
        eth0addr = pyNetAddr(eth0addrstr)
        self.assertTrue(eth0addr == ipnodeaddr)

        # Do we know that eth0 is the default gateway?
        self.assertEqual(eth0obj['default_gw'], True)
        
        # the JSON should have exactly 5 top-level keys
        self.assertEqual(len(jsobj.keys()), 5)
        # Was the JSON host name saved away correctly?
        self.assertEqual(jsobj['host'], designation)
    
        return
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
            #print >>sys.stderr, "DRONE is %s status %s" % (drone.designation, drone.status)
            #print >>sys.stderr, "DRONE ringmemberships:", drone.ringmemberships.keys()
            self.assertEqual(ring.members[drone.designation].designation, drone.designation)
            self.assertEqual(len(ring.members), len(ring.memberlist))
        if drone.status != 'dead':
            # We have to be members of at least one ring...
            self.assertTrue(ringcount >= 1)
            # Drone should be a member of one ring (for now)
            self.assertEqual(len(drone.ringmemberships),1)
        # Do we have the right number of ring peers?
        #print >>sys.stderr, "Checking peer count for drone %s (%d)" % (drone, len(drone.ringpeers))
        self.assertEqual(len(drone.ringpeers), peercount)

    def auditSETCONFIG(self, packetreturn, droneid, configinit):
        toaddr = packetreturn[0]
        sentfs = packetreturn[1]
        droneip = droneipaddress(droneid)
        
        # Was it a SETCONFIG packet?
        self.assertEqual(sentfs.get_framesettype(), FrameSetTypes.SETCONFIG)
        # Was the SETCONFIG sent back to the drone?
        self.assertEqual(toaddr,droneip)
        # Lets check the number of Frames in the SETCONFIG Frameset
        self.assertEqual(1, len(sentfs))  # Was it the right size?

    def auditaRing(self, ring):
        'Verify that each ring has its neighbor pairs set up properly'
        # Check that each element of the ring is connected to its neighbors...
        print "Ring %s" % (str(ring))
        listmembers = {}
        ringmembers = {}
        for drone in ring.members():
            ringmembers[drone.designation] = None
        for drone in ring.membersfromlist():
            listmembers[drone.designation] = None
        for drone in listmembers.keys():
            self.assertTrue(drone in ringmembers)
        for drone in ringmembers.keys():
            self.assertTrue(drone in listmembers)
        

def auditalldrones():
    audit = AUDITS()
    dronetype = CMAdb.cdb.nodetypetbl['Drone']
    droneobjs = CMAdb.store.load_in_related(dronetype, 'IS_A', Drone)
    droneobjs = [drone for drone in droneobjs]
    numdrones = len(droneobjs)
    for droneid in range(0,numdrones):
        audit.auditadrone(droneid+1)

def auditallrings():
    audit = AUDITS()
    query = neo4j.CypherQuery(CMAdb.cdb.db, '''START n=node:HbRing('*:*') RETURN n''')
    for ring in CMAdb.store.load_cypher_nodes(query, HbRing):
        audit.auditaRing(ring)

class TestIO:
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
        self.writecount=0
        self.config = {CONFIGNAME_CMAPORT: 1984}

    def recvframesets(self):
        # Audit after each packet is processed - and once before the first packet.
        if DoAudit:
            if self.packetsread < 200 or (self.packetsread % 500) == 0:
                auditalldrones()
                auditallrings()
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

    def sendreliablefs(self, dest, fslist):
        self.sendframesets(dest, fslist)

    def ackmessage(self, dest, fs):
        pass

    def closeconn(self, qid, dest):
        pass

    def _sendaframeset(self, dest, fslist):
        self.writecount += 1
        if SavePackets:
            self.packetswritten.append((dest,fslist))

    def getmaxpktsize(self):    return 60000
    def getfd(self):        	return 4
    def bindaddr(self, addr):   return True
    def mcastjoin(self, addr):  return True
    def setblockio(self, tf):   return

    def dumppackets(self):
        print >>sys.stderr, 'Sent %d packets' % len(self.packetswritten)
        for packet in self.packetswritten:
            print '%s (%s)' % (packet[0], packet[1])
    

class TestTestInfrastructure(TestCase):
    def test_eof(self):
        'Get EOF with empty input'
        if BuildListOnly: return
        if DEBUG:
            print >> sys.stderr, 'Running test_test_eof()'
        framesets=[]
        io = TestIO(framesets, 0)
        CMAinit(io, cleanoutdb=True, debug=DEBUG)
        # just make sure it seems to do the right thing
        self.assertRaises(StopIteration, io.recvframesets)
        assert_no_dangling_Cclasses()

    def test_get1pkt(self):
        'Read a single packet'
        if BuildListOnly: return
        if DEBUG:
            print >> sys.stderr, 'Running test_test_eof()'
        otherguy = pyNetAddr([1,2,3,4],)
        strframe1=pyCstringFrame(FrameTypes.CSTRINGVAL, "Hello, world.")
        fs = pyFrameSet(42)
        fs.append(strframe1)
        framesets=((otherguy, (strframe1,)),)
        io = TestIO(framesets, 0)
        CMAinit(io, cleanoutdb=True, debug=DEBUG)
        gottenfs = io.recvframesets()
        self.assertEqual(len(gottenfs), 2)
        self.assertEqual(gottenfs, framesets[0])
        self.assertRaises(StopIteration, io.recvframesets)

    def test_echo1pkt(self):
        'Read a packet and write it back out'
        if BuildListOnly: return
        if DEBUG:
            print >> sys.stderr, 'Running test_echo1pkt()'
        strframe1=pyCstringFrame(FrameTypes.CSTRINGVAL, "Hello, world.")
        fs = pyFrameSet(42)
        fs.append(strframe1)
        otherguy = pyNetAddr([1,2,3,4],)
        framesets=((otherguy, (strframe1,)),)
        io = TestIO(framesets, 0)
        CMAinit(io, cleanoutdb=True, debug=DEBUG)
        fslist = io.recvframesets()     # read in a packet
        self.assertEqual(len(fslist), 2)
        self.assertEqual(fslist, framesets[0])
        io.sendframesets(fslist[0], fslist[1])  # echo it back out
        self.assertEqual(len(io.packetswritten), 1)
        self.assertEqual(len(io.packetswritten), len(framesets))
        self.assertRaises(StopIteration, io.recvframesets)

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

class TestCMABasic(TestCase):
    def test_startup(self):
        '''A semi-interesting test: We send a STARTUP message and get back a
        SETCONFIG message with lots of good stuff in it.'''
        if BuildListOnly: return
        if DEBUG:
            print >> sys.stderr, 'Running test_startup()'
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
        CMAinit(io, cleanoutdb=True, debug=DEBUG)
        OurAddr = pyNetAddr((127,0,0,1),1984)
        disp = MessageDispatcher({FrameSetTypes.STARTUP: DispatchSTARTUP()})
        configinit = geninitconfig(OurAddr)
        config = pyConfigContext(init=configinit)
        listener = PacketListener(config, disp, io=io)
        # We send the CMA an intial STARTUP packet
        self.assertRaises(StopIteration, listener.listen) # We audit after each packet is processed
        # Let's see what happened...

        self.assertEqual(len(io.packetswritten), 2) # Did we send out two packets?
                            # Note that this change over time
                            # As we change discovery...
        AUDITS().auditSETCONFIG(io.packetswritten[0], droneid, configinit)
    # Drone and Ring tables are automatically audited after each packet

    def test_several_startups(self):
        '''A very interesting test: We send a STARTUP message and get back a
        SETCONFIG message and then send back a bunch of discovery requests.'''
        if DEBUG:
            print >> sys.stderr, 'Running test_several_startups()'
        OurAddr = pyNetAddr((10,10,10,5), 1984)
        configinit = geninitconfig(OurAddr)
        fsin = []
        droneid=0
        for droneid in range(1,MaxDrone+1):
            droneip = droneipaddress(droneid)
            designation = dronedesignation(droneid)
            designationframe=pyCstringFrame(FrameTypes.HOSTNAME, designation)
            dronediscovery=hostdiscoveryinfo(droneid)
            discoveryframe=pyCstringFrame(FrameTypes.JSDISCOVER, dronediscovery)
            fs = pyFrameSet(FrameSetTypes.STARTUP)
            fs.append(designationframe)
            fs.append(discoveryframe)
            fsin.append((droneip, (fs,)))
        addrone = droneipaddress(1)
        maxdrones = droneid
        if doHBDEAD:
            print >> sys.stderr, 'KILLING THEM ALL!!!'
            for droneid in range(2,maxdrones+1):
                droneip = droneipaddress(droneid)
                print >> sys.stderr, 'queueing dead packet for %s' % droneip
                deadframe=pyIpPortFrame(FrameTypes.IPPORT, addrstring=droneip)
                print >> sys.stderr, 'queueing death frame: %s' % deadframe
                fs = pyFrameSet(FrameSetTypes.HBDEAD)
                fs.append(deadframe)
                print >> sys.stderr, 'FS PACKET: %s' % fs
                fsin.append((addrone, (fs,)))
        io = TestIO(fsin)
        CMAinit(io, cleanoutdb=True, debug=DEBUG)
        disp = MessageDispatcher( {
            FrameSetTypes.STARTUP: DispatchSTARTUP(),
            FrameSetTypes.HBDEAD: DispatchHBDEAD(),
        })
        config = pyConfigContext(init=configinit)
        listener = PacketListener(config, disp, io=io)
        # We send the CMA a BUNCH of intial STARTUP packets
        try:
          listener.listen()
        except StopIteration as foo:
            pass
        #self.assertRaises(StopIteration, listener.listen)
        # We audit after each packet is processed
        # The auditing code will make sure all is well...
        # But it doesn't know how many drones we just registered
        droneroot = CMAdb.cdb.nodetypetbl['Drone']
        idx = CMAdb.cdb.indextbl['Drone']
        query = neo4j.CypherQuery(CMAdb.cdb.db, "START n=node:Drone('*:*') RETURN n")
        Drones = CMAdb.store.load_cypher_nodes(query, Drone)
        Drones = [drone for drone in Drones]
        print 'DRONE LIST:', Drones
        #Dronerels = droneroot.get_relationships(neo4j.Direction.INCOMING, 'IS_A')
        #self.assertEqual(len(Dronerels), maxdrones)
        print >> sys.stderr, 'WE NOW HAVE THESE DRONES:', Drones
        self.assertEqual(len(Drones), maxdrones)
        if doHBDEAD:
            partnercount = 0
            livecount = 0
            ringcount = 0
            for drone1 in Drones:
                print 'DRONE1:', drone1, drone1.status
                if drone1.status != 'dead': livecount += 1
                for partner in CMAdb.store.load_related(drone1, CMAdb.TheOneRing.ournexttype, Drone):
                    partnercount += 1
                for partner in CMAdb.store.load_in_related(drone1, CMAdb.TheOneRing.ournexttype, Drone):
                    partnercount += 1
                for ring in CMAdb.store.load_in_related(drone1, CMAdb.TheOneRing.ourreltype, HbRing):
                    ringcount += 1
            print >> sys.stderr, 'DUMPING DRONES'
            GraphNode.dump_nodes()
            self.assertEqual(partnercount, 0)
            self.assertEqual(livecount, 1)
            self.assertEqual(ringcount, 1)
        if DoAudit:
            auditalldrones()
            auditallrings()

        print "The CMA read %d packets."  % io.packetsread
        print "The CMA wrote %d packets." % io.writecount
        #io.dumppackets()


    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

if __name__ == "__main__":
    run()
