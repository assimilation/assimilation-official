# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
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
sys.path.insert(0, "../cma")
sys.path.insert(0, "..")
sys.path.append("/usr/local/lib/python2.7/dist-packages")
from py2neo import neo4j

from frameinfo import *
from AssimCclasses import *
import gc, sys, time, collections, os, subprocess, re
from graphnodes import nodeconstructor, ProcessNode
from cmainit import CMAinit
from cmadb import CMAdb
from packetlistener import PacketListener
from messagedispatcher import MessageDispatcher
from dispatchtarget import DispatchSTARTUP, DispatchHBDEAD, DispatchJSDISCOVERY, DispatchSWDISCOVER, DispatchHBSHUTDOWN
from hbring import HbRing
from droneinfo import Drone
import optparse
from graphnodes import GraphNode
from monitoring import MonitorAction, LSBMonitoringRule, MonitoringRule, OCFMonitoringRule
from transaction import Transaction
from assimevent import AssimEvent
from cmaconfig import ConfigFile
from graphnodeexpression import ExpressionContext
import assimglib as glib # This is now our glib bindings...
import discoverylistener
from store import Store


os.environ['G_MESSAGES_DEBUG'] =  'all'
WorstDanglingCount = 0

CheckForDanglingClasses = True
AssertOnDanglingClasses = True

DEBUG=True
DEBUG=False
DoAudit=True
doHBDEAD=True
BuildListOnly = False
SavePackets=True
MaxDrone=5


if BuildListOnly:
    doHBDEAD=False
    SavePackets=False
    DoAudit=False
    CheckForDanglingClasses=False
    DEBUG=False


t1 = MaxDrone
if t1 < 1000: t1 = 1000
t2 = MaxDrone/100
if t2 < 10: t2 = 10
t3 = t2

if not DoAudit:
    print >> sys.stderr, 'WARNING: Audits suppressed.'
if not doHBDEAD:
    print >> sys.stderr, 'WARNING: Server death tests disabled.'
if not CheckForDanglingClasses:
    print >> sys.stderr, 'WARNING: Memory Leak Detection disabled.'
elif not AssertOnDanglingClasses:
    print >> sys.stderr, 'WARNING: Memory Leak assertions disabled (detection still enabled).'


#gc.set_threshold(t1, t2, t3)

AssimEvent.disable_all_observers()

def assert_no_dangling_Cclasses(doassert=None):
    global CheckForDanglingClasses
    global WorstDanglingCount
    if not CheckForDanglingClasses:
        return
    sys._clear_type_cache()
    if doassert is None:
        doassert = AssertOnDanglingClasses
    print 'ASSERTNODANGLING SHUTDOWN CALL'
    IOTestIO.shutdown()
    print 'DANGLING UNINIT CALL'
    CMAinit.uninit()
    gc.collect()    # For good measure...
    count =  proj_class_live_object_count()
    #print >>sys.stderr, "CHECKING FOR DANGLING CLASSES (%d)..." % count
    # Avoid cluttering the output up with redundant messages...
    if count > WorstDanglingCount and CheckForDanglingClasses:
        WorstDanglingCount = count
        if doassert:
            print >> sys.stderr, 'STARTING OBJECT DUMP'
            dump_c_objects()
            print >> sys.stderr, 'OBJECT DUMP COMPLETE'
            print 'stdout OBJECT DUMP COMPLETE'
            raise AssertionError("Dangling C-class objects - %d still around" % count)
        else:
            print >> sys.stderr,  ("*****ERROR: Dangling C-class objects - %d still around" % count)


class TestCase(object):
    def assertEqual(self, a, b):
        assert a == b

    def assertNotEqual(self, a, b):
        assert a != b

    def assertTrue(self, a):
        assert a is True

    def assertFalse(self, a):
        assert a is False

    def assertRaises(self, exception, function, *args):
        try:
            function(*args)
            raise Exception('Did not raise exception %s: %s(%s)', exception, function, str(args))
        except exception as e:
            return True

    def teardown_method(self, method):
        print 'teardown_method CALL for %s' % str(method)
        assert_no_dangling_Cclasses()


# Values to substitute into this string via '%' operator:
# dronedesignation (%s) MAC address byte (%02x), MAC address byte (%02x), IP address (%s)
netdiscoveryformat='''
{
  "discovertype": "netconfig",
  "description": "IP Network Configuration",
  "instance": "netconfig",
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
    ip =droneipaddress(hostnumber)
    ip.setport(0)
    s = str(ip)
    return netdiscoveryformat % (dronedesignation(hostnumber), byte3, byte4, s)

def geninitconfig(ouraddr):
    configinfo = ConfigFile()
    for j in ('cmainit', 'cmaaddr', 'cmadisc', 'cmafail'):
        configinfo[j] = ouraddr
    configinfo['outsig'] = pySignFrame(1)
    return configinfo.complete_config()

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
        json = drone['netconfig']
        jsobj = pyConfigContext(init=json)
        jsdata = jsobj['data']
        eth0obj = jsdata['eth0']
        eth0addrcidr = eth0obj['ipaddrs'].keys()[0]
        eth0addrstr, cidrmask = eth0addrcidr.split('/')
        eth0addr = pyNetAddr(eth0addrstr)
        self.assertTrue(eth0addr == ipnodeaddr)

        # Do we know that eth0 is the default gateway?
        self.assertEqual(eth0obj['default_gw'], True)

        # the JSON should have exactly 6 top-level keys
        self.assertEqual(len(jsobj.keys()), 6)
        # Was the JSON host name saved away correctly?
        self.assertEqual(jsobj['host'], designation)
        assert drone.get_active_nic_count() == 1

    def auditSETCONFIG(self, packetreturn, droneid, configinit):
        toaddr = packetreturn[0]
        sentfs = packetreturn[1]
        droneip = droneipaddress(droneid)

        # Was it a SETCONFIG packet?
        self.assertEqual(sentfs.get_framesettype(), FrameSetTypes.SETCONFIG)
        # Was the SETCONFIG sent back to the drone?
        self.assertEqual(toaddr, droneip)
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
            print >> sys.stderr, 'RINGMEMBERS: %s: members:%s' % (str(drone), listmembers)
            self.assertTrue(drone in listmembers)


def auditalldrones():
    print 'DRONE1: CMADB', CMAdb
    print 'DRONE1: CMADB.IO:', CMAdb.io
    print 'DRONE1: CMADB.store', CMAdb.store
    audit = AUDITS()
    qtext = "MATCH (drone) WHERE drone.nodetype = 'Drone' RETURN drone"
    droneobjs = CMAdb.store.load_cypher_nodes(qtext, Drone)
    droneobjs = [drone for drone in droneobjs]
    print 'DRONE2: CMADB', CMAdb
    print 'DRONE2: CMADB.IO:', CMAdb.io
    print 'DRONE2: CMADB.store', CMAdb.store
    numdrones = len(droneobjs)
    for droneid in range(0, numdrones):
        droneid = int(droneobjs[droneid].designation[6:])
        audit.auditadrone(droneid)
    queryobjs = CMAdb.store.load_cypher_nodes('''START n=node:Drone('*:*') RETURN n''', Drone)
    queryobjs = [drone for drone in queryobjs]
    dronetbl = {}
    for drone in droneobjs:
        dronetbl[drone.designation] = drone
    querytbl = {}
    for drone in queryobjs:
        querytbl[drone.designation] = drone
    # Now compare them
    for drone in dronetbl:
        assert(querytbl[drone] is dronetbl[drone])
    for drone in querytbl:
        assert(querytbl[drone] is dronetbl[drone])
    print 'DRONE3: CMADB', CMAdb
    print 'DRONE3: CMADB.IO:', CMAdb.io
    print 'DRONE3: CMADB.store', CMAdb.store


def auditallrings():
    print 'AUDIT: CMADB', CMAdb
    print 'AUDIT: CMADB.IO:', CMAdb.io
    print 'AUDIT: CMADB.store', CMAdb.store

    if CMAdb.store is None:
        print 'SKIPPING RING AUDIT' 
        raise ValueError('STORE IS NONE')
        return
    print 'PERFORMING RING AUDIT' 
    audit = AUDITS()
    for ring in CMAdb.store.load_cypher_nodes("START n=node:HbRing('*:*') RETURN n", HbRing):
        ring.AUDIT()

ASSIMCLI='assimcli'
inityet = False
def assimcli_check(command, expectedcount=None):
    'This code only works if you have assimcli installed'
    cmd='%s %s' % (ASSIMCLI, command)
    #print >> sys.stderr, 'RUNNING COMMAND: %s' % str(command)
    if expectedcount is None:
        subprocess.check_call(('sh', '-c', cmd))
    else:
        linecount = 0
        fd = os.popen(cmd)
        while True:
            if not fd.readline():
                break
            linecount += 1
        rc = fd.close()
        if expectedcount != linecount:
            print >> sys.stderr, 'Rerunning query [%s]:' % cmd
            subprocess.check_call(('sh', '-c', cmd))
            raise RuntimeError('%s command produced %s lines instead of %s'
            %   (cmd, linecount, expectedcount))
        assert rc is None or rc == 0

class IOTestIO:
    '''A pyNetIOudp replacement for testing.  It is given a list of packets to be 'read'
    and in turn saves all the packets it 'writes' for us to inspect.
    '''
    mainloop = None
    @staticmethod
    def shutdown():
        if IOTestIO.singleinstance is not None:
            print 'CLEANING OUT SINGLEINSTANCE IO OBJECT'
            IOTestIO.singleinstance.cleanio()
            IOTestIO.singleinstance = None

    def __init__(self, addrframesetpairs, sleepatend=0):
        IOTestIO.singleinstance = self
        if isinstance(addrframesetpairs, tuple):
            addrframesetpairs = addrframesetpairs
        self.inframes = addrframesetpairs
        self.packetswritten=[]
        self.packetsread=0
        self.sleepatend=sleepatend
        self.index=0
        self.writecount=0
        self.config = ConfigFile().complete_config()
        (self.pipe_read, self.pipe_write) = os.pipe()
        os.write(self.pipe_write, ' ')
        os.close(self.pipe_write)
        self.pipe_write = -1
        self.atend = False
        self.readfails = 0
        self.initpackets = len(self.inframes)
        print >> sys.stderr, 'INITPACKETS: self.initpackets'

    @staticmethod
    def shutdown_on_timeout(io):
        if IOTestIO.mainloop is not None:
            IOTestIO.mainloop.quit()
        return False

    def recvframesets(self):
        print 'RECV: CMADB', CMAdb
        print 'RECV: CMADB.IO:', CMAdb.io
        print 'RECV: CMADB.store', CMAdb.store
        # Audit after each packet is processed - and once before the first packet.
        assert CMAdb.io.config is not None
        if DoAudit:
            if self.packetsread < 200 or (self.packetsread % 500) == 0:
                print 'RECV2: CMADB', CMAdb
                print 'RECV2: CMADB.IO:', CMAdb.io
                print 'RECV2: CMADB.store', CMAdb.store
                CMAdb.store.commit()
                print 'RECV3: CMADB', CMAdb
                print 'RECV3: CMADB.IO:', CMAdb.io
                print 'RECV3: CMADB.store', CMAdb.store
                auditalldrones()
                print 'RECV4: CMADB', CMAdb
                print 'RECV4: CMADB.IO:', CMAdb.io
                print 'RECV4: CMADB.store', CMAdb.store
                auditallrings()
                print 'RECV5: CMADB', CMAdb
                print 'RECV5: CMADB.IO:', CMAdb.io
                print 'RECV5: CMADB.store', CMAdb.store
        if self.index >= len(self.inframes):
            if not self.atend:
                self.timeout = glib.GMainTimeout(int(self.sleepatend*1000), IOTestIO.shutdown_on_timeout, self)
                self.atend = True
                #self.config = None
            else:
                #self.mainloop.quit()
                if self.pipe_read >= 0:
                    os.close(self.pipe_read)
                    self.pipe_read = -1
            self.readfails += 1
            if self.readfails > self.initpackets+4:
                self.mainloop.quit()

            return (None, None)
        ret = self.inframes[self.index]
        self.index += 1
        self.packetsread += len(ret[1])
        return ret

    def sendframesets(self, dest, fslist):
        print >> sys.stderr, 'SENDING FRAMESET'
        if not isinstance(fslist, collections.Sequence):
            return self._sendaframeset(dest, fslist)
        for fs in fslist:
            self._sendaframeset(dest, fs)

    def sendreliablefs(self, dest, fslist):
        self.sendframesets(dest, fslist)

    def ackmessage(self, dest, fs):
        pass

    def connactive(self, ioaddr, qid=0):
        ioaddr = ioaddr
        return True

    def closeconn(self, qid, dest):
        pass

    def _sendaframeset(self, dest, fs):
        self.writecount += 1
        if SavePackets:
            self.packetswritten.append((dest,fs))

    def cleanio(self):
        print 'CLEANING OUT IO OBJECT'
        if IOTestIO.mainloop is not None:
            IOTestIO.mainloop.quit()
        if self.pipe_read >= 0:
            os.close(self.pipe_read)
            self.pipe_read = -1
        IOTestIO.mainloop = None
        # Note that this having to do this implies that our I/O object persists
        # longer than I would have expected...
        # Is this because uninit needs to be done as part of the test instead of
        # as part of the cleanup action?
        self.inframes = []
        self.packetswritten = 0
        self.config = None
        self.timeout = None
        if CMAdb.store:
            CMAdb.store.abort()
            CMAdb.store.weaknoderefs = {}
            CMAdb.store = None
        CMAinit.uninit()

    def getmaxpktsize(self):    return 60000
    def fileno(self):        	return self.pipe_read
    def bindaddr(self, addr):   return True
    def mcastjoin(self, addr):  return True
    def setblockio(self, tf):   return

    def dumppackets(self):
        print >>sys.stderr, 'Sent %d packets' % len(self.packetswritten)
        for packet in self.packetswritten:
            print 'PACKET: %s (%s)' % (packet[0], packet[1])

class FakeDrone(dict):
    def __init__(self, json):
        self['monitoringagents'] = json

    def get(self, name, ret):
        return ret



class TestTestInfrastructure(TestCase):
    def test_eof(self):
        'Get EOF with empty input'
        if BuildListOnly: return
        if DEBUG:
            print >> sys.stderr, 'Running test_test_eof()'
        AssimEvent.disable_all_observers()
        framesets=[]
        io = IOTestIO(framesets, 0)
        CMAinit(io, cleanoutdb=True, debug=DEBUG)
        print 'IO:', io
        print 'CMADB', CMAdb
        print 'CMADB.store', CMAdb.store
        # just make sure it seems to do the right thing
        (foo, bar) = io.recvframesets()
        assert foo is None
        #assert_no_dangling_Cclasses()

    def test_get1pkt(self):
        'Read a single packet'
        if BuildListOnly: return
        if DEBUG:
            print >> sys.stderr, 'Running test_test_eof()'
        AssimEvent.disable_all_observers()
        otherguy = pyNetAddr([1,2,3,4],)
        strframe1=pyCstringFrame(FrameTypes.CSTRINGVAL, "Hello, world.")
        fs = pyFrameSet(42)
        fs.append(strframe1)
        framesets=((otherguy, (strframe1,)),)
        io = IOTestIO(framesets, 0)
        CMAinit(io, cleanoutdb=True, debug=DEBUG)
        gottenfs = io.recvframesets()
        self.assertEqual(len(gottenfs), 2)
        self.assertEqual(gottenfs, framesets[0])
        gottenfs = io.recvframesets()
        self.assertEqual(len(gottenfs), 2)
        assert gottenfs[0] is None
        #assert_no_dangling_Cclasses()

    def test_echo1pkt(self):
        'Read a packet and write it back out'
        if BuildListOnly: return
        if DEBUG:
            print >> sys.stderr, 'Running test_echo1pkt()'
        AssimEvent.disable_all_observers()
        strframe1=pyCstringFrame(FrameTypes.CSTRINGVAL, "Hello, world.")
        fs = pyFrameSet(42)
        fs.append(strframe1)
        otherguy = pyNetAddr([1,2,3,4],)
        framesets=((otherguy, (strframe1,)),)
        io = IOTestIO(framesets, 0)
        CMAinit(io, cleanoutdb=True, debug=DEBUG)
        fslist = io.recvframesets()     # read in a packet
        self.assertEqual(len(fslist), 2)
        self.assertEqual(fslist, framesets[0])
        io.sendframesets(fslist[0], fslist[1])  # echo it back out
        self.assertEqual(len(io.packetswritten), len(framesets))
        gottenfs = io.recvframesets()
        self.assertEqual(len(gottenfs), 2)
        assert gottenfs[0] is None
        #assert_no_dangling_Cclasses()

class TestCMABasic(TestCase):
    OS_DISCOVERY = '''{
  "discovertype": "os",
  "description": "OS information",
  "host": "drone000001",
  "instance": "os",
  "source": "../discovery_agents/os",
  "data": {
    "nodename": "drone000001",
    "operating-system": "GNU/Linux",
    "machine": "x86_64",
    "processor": "x86_64",
    "hardware-platform": "x86_64",
    "kernel-name": "Linux",
    "kernel-release": "3.19.0-31-generic",
    "kernel-version": "#36-Ubuntu SMP Wed Oct 7 15:04:02 UTC 2015",
    "Distributor ID":   "Ubuntu",
    "Description":      "Ubuntu 15.04",
    "Release":  "15.04",
    "Codename": "vivid"
  }
}'''
    ULIMIT_DISCOVERY= '''{
  "discovertype": "ulimit",
  "description": "ulimit values for root",
  "host": "drone000001",
  "instance": "ulimit",
  "source": "../discovery_agents/ulimit",
  "data": {
    "hard": {"c":null,"d":null,"f":null,"l":null,"m":null,"n":65536,"p":63557,"s":null,"t":null,"v":null},
    "soft": {"c":0,"d":null,"f":null,"l":null,"m":null,"n":1024,"p":63557,"s":8192,"t":null,"v":null}
  }
}'''
    DRAWING_PRODUCER = 'drawwithdot'

    def check_discovery(self, drone, expectedjson):
        'We check to see if the discovery JSON object thingy is working...'
        disctypes = []

        for json in expectedjson:
            jsobj = pyConfigContext(json)
            dtype = jsobj['instance']
            # Compare hash sums - without retrieving the big string from Neo4j
            self.assertTrue(drone.json_eq(dtype, json))
            # Fetch string from the database and compare for string equality
            self.assertEqual(str(pyConfigContext(json)), str(drone[dtype]))
            disctypes.append(dtype)

        disctypes.sort()
        dronekeys = drone.keys()
        dronekeys.sort()
        self.assertEqual(dronekeys, disctypes)



    def test_startup(self):
        '''A semi-interesting test: We send a STARTUP message and get back a
        SETCONFIG message with lots of good stuff in it.
        and for good measure, we also send along some discovery packets.
        '''
        if BuildListOnly: return
        if DEBUG:
            print >> sys.stderr, 'Running test_startup()'
        AssimEvent.disable_all_observers()
        droneid = 1
        droneip = droneipaddress(droneid)
        designation = dronedesignation(droneid)
        designationframe=pyCstringFrame(FrameTypes.HOSTNAME, designation)
        dronediscovery=hostdiscoveryinfo(droneid)
        discoveryframe=pyCstringFrame(FrameTypes.JSDISCOVER, dronediscovery)
        fs = pyFrameSet(FrameSetTypes.STARTUP)
        fs.append(designationframe)
        fs.append(discoveryframe)

        fs2 = pyFrameSet(FrameSetTypes.JSDISCOVERY)
        osdiscovery=pyCstringFrame(FrameTypes.JSDISCOVER, self.OS_DISCOVERY)
        fs2.append(osdiscovery)
        fs3 = pyFrameSet(FrameSetTypes.JSDISCOVERY)
        ulimitdiscovery=pyCstringFrame(FrameTypes.JSDISCOVER, self.ULIMIT_DISCOVERY)
        fs3.append(ulimitdiscovery)
        fsin = ((droneip, (fs,)), (droneip, (fs2,)), (droneip, (fs3,)))
        io = IOTestIO(fsin,0)
        #print >> sys.stderr, 'CMAinit: %s' % str(CMAinit)
        #print >> sys.stderr, 'CMAinit.__init__: %s' % str(CMAinit.__init__)
        OurAddr = pyNetAddr((127,0,0,1),1984)
        configinit = geninitconfig(OurAddr)
        config = pyConfigContext(init=configinit)
        io.config = config
        CMAinit(io, cleanoutdb=True, debug=DEBUG)
        CMAdb.io.config = config
        assimcli_check('loadqueries')
        from dispatchtarget import DispatchTarget
        disp = MessageDispatcher(DispatchTarget.dispatchtable, encryption_required=False)
        listener = PacketListener(config, disp, io=io, encryption_required=False)
        io.mainloop = listener.mainloop
        IOTestIO.mainloop = listener.mainloop
        # We send the CMA an intial STARTUP packet
        listener.listen()
        # Let's see what happened...
        print >> sys.stderr, ('READ: %s' % io.packetsread)
        print >> sys.stderr, ('WRITTEN: %s' % len(io.packetswritten))
        print >> sys.stderr, ('PACKETS WRITTEN: %s' % str(io.packetswritten))

        self.assertEqual(len(io.packetswritten), 2) # Did we send out four packets?
                            # Note that this change over time
                            # As we change discovery...
        self.assertEqual(io.packetsread, 3) # Did we read 3 packets?
        AUDITS().auditSETCONFIG(io.packetswritten[0], droneid, configinit)
        assimcli_check("query allips", 1)
        assimcli_check("query allservers", 1)
        assimcli_check("query findip %s" % str(droneip), 1)
        assimcli_check("query shutdown", 0)
        assimcli_check("query crashed", 0)
        assimcli_check("query unknownips", 0)
        CMAdb.io.config = config
        Drones = CMAdb.store.load_cypher_nodes("START n=node:Drone('*:*') RETURN n", Drone)
        Drones = [drone for drone in Drones]
        for drone in Drones:
            self.check_discovery(drone, (dronediscovery, self.OS_DISCOVERY, self.ULIMIT_DISCOVERY))
        self.assertEqual(len(Drones), 1) # Should only be one drone
        io.config = None
        del ulimitdiscovery, osdiscovery, Drones, disp, listener
        DispatchTarget.dispatchtable = {}
        del DispatchTarget
        #assert_no_dangling_Cclasses()

    def check_live_counts(self, expectedlivecount, expectedpartnercount, expectedringmembercount):
        Drones = CMAdb.store.load_cypher_nodes(query, Drone)
        Drones = [drone for drone in Drones]
        partnercount = 0
        livecount = 0
        ringcount = 0
        for drone1 in Drones:
            if drone1.status != 'dead': livecount += 1
            for partner in CMAdb.store.load_related(drone1, CMAdb.TheOneRing.ournexttype, Drone):
                partnercount += 1
            for partner in CMAdb.store.load_in_related(drone1, CMAdb.TheOneRing.ournexttype, Drone):
                partnercount += 1
            for ring in CMAdb.store.load_in_related(drone1, CMAdb.TheOneRing.ourreltype, HbRing):
                ringcount += 1
        print >> sys.stderr, 'PARTNERCOUNT: (%s, %s)' % (partnercount, expectedpartnercount)
        print >> sys.stderr, 'LIVECOUNT: (%s, %s)' % (livecount, expectedlivecount)
        print >> sys.stderr, 'RINGCOUNT: (%s, %s)' % (ringcount, expectedringmembercount)
        self.assertEqual(partnercount, expectedpartnercount)
        self.assertEqual(livecount, expectedlivecount)
        self.assertEqual(ringcount, expectedringmembercount)

    def construct_and_verify_diagram(self, diagramtype, patterncounts):
        'Construct a "drawithdot" diagram and then validate it'
        #print >> sys.stderr, 'PROCESSING DIAGRAM TYPE: %s' % diagramtype
        dot = subprocess.Popen((self.DRAWING_PRODUCER, diagramtype), stdout=subprocess.PIPE, shell=True)
        foundcounts = {}
        for line in dot.stdout.readlines():
            #print >> sys.stderr, 'GOT: %s' % line.strip()
            for pattern in patterncounts:
                if re.search(pattern, line) is not None:
                    if pattern not in foundcounts:
                        foundcounts[pattern] = 0
                    foundcounts[pattern] += 1
        dot.stdout.close()

        errcount = 0
        for pattern in patterncounts:
            found = foundcounts[pattern] if pattern in foundcounts else 0
            if found != patterncounts[pattern]:
                print >> sys.stderr, ('Expecting %d matches of %s. Found %d instead.'
                        % (patterncounts[pattern], pattern, found))
                errcount += 1
        self.assertEqual(errcount, 0)

    def diagram_patterns(self, diagramtype, nodecount):
        upnode='shape=house color=green penwidth=3.*label="%s'
        downnode='shape=house style="filled,dashed" fillcolor=gray90 .*label="%s'
        anynode='shape=house'
        ringnext='node_.*->node_.* \[label=RingNext_The_One_Ring\]'

        pats = {
                'node_.*->node_.* label=nicowner':  nodecount*2,
                '\[shape=octagon color=navy label="00-00-00-00-00-00': 1,
                # Is having only one loopback NIC a bug?? I think maybe so!
                # Some Python versions have this wrong...
                #'\[shape=octagon color=navy label="00-1b-fc-.*ASUSTek COMPUTER INC\.': nodecount,
                '\[shape=octagon color=navy label="00-1b-fc-': nodecount,

                'node_.*->node_.* label=ipowner':   nodecount,
        }
        pats[upnode % dronedesignation(1)] = 1
        if doHBDEAD:
            for node in range(2, nodecount+1):
                pats[downnode % dronedesignation(node)] = 1
            pats[ringnext] = 0
        else:
            for node in range(2, nodecount+1):
                pats[upnode % dronedesignation(node)] = 1
            pats[ringnext] = nodecount if nodecount > 2 else 1
        return pats


    # Drone and Ring tables are automatically audited after each packet
    def test_several_startups(self):
        '''A very interesting test: We send a STARTUP message and get back a
        SETCONFIG message and then send back a bunch of discovery requests.'''
        if Store.debug:
            raise ValueError('Debug enabled')
        if DEBUG:
            print >> sys.stderr, 'Running test_several_startups()'
        AssimEvent.disable_all_observers()
        OurAddr = pyNetAddr((10,10,10,5), 1984)
        configinit = geninitconfig(OurAddr)
        # Create the STARTUP FrameSets that our fake Drones should appear to send
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
            # Create the HBDEAD FrameSets that our first fake Drone should appear to send
            # concerning the death of its dearly departed peers
            #print >> sys.stderr, 'KILLING THEM ALL!!!'
            for droneid in range(2,maxdrones+1):
                droneip = droneipaddress(droneid)
                designation = dronedesignation(droneid)
                #deadframe=pyIpPortFrame(FrameTypes.IPPORT, addrstring=droneip)
                fs = pyFrameSet(FrameSetTypes.HBSHUTDOWN)
                #fs.append(deadframe)
                hostframe=pyCstringFrame(FrameTypes.HOSTNAME, designation)
                fs.append(hostframe)
                fsin.append((droneip, (fs,)))
        io = IOTestIO(fsin)
        CMAinit(io, cleanoutdb=True, debug=DEBUG)
        assert CMAdb.io.config is not None
        assimcli_check('loadqueries')
        disp = MessageDispatcher( {
            FrameSetTypes.STARTUP: DispatchSTARTUP(),
            FrameSetTypes.HBDEAD: DispatchHBDEAD(),
            FrameSetTypes.HBSHUTDOWN: DispatchHBSHUTDOWN(),
        }, encryption_required=False)
        config = pyConfigContext(init=configinit)
        listener = PacketListener(config, disp, io=io, encryption_required=False)
        io.mainloop = listener.mainloop
        IOTestIO.mainloop = listener.mainloop
        # We send the CMA a BUNCH of intial STARTUP packets
        # and (optionally) a bunch of HBDEAD packets
        assert CMAdb.io.config is not None
        listener.listen()
        # We audit after each packet is processed
        # The auditing code will make sure all is well...
        # But it doesn't know how many drones we just registered
        Drones = CMAdb.store.load_cypher_nodes("START n=node:Drone('*:*') RETURN n", Drone)
        Drones = [drone for drone in Drones]
        #print >> sys.stderr, 'WE NOW HAVE THESE DRONES:', Drones
        self.assertEqual(len(Drones), maxdrones)
        if doHBDEAD:
            # Verify that all drones except one are dead
            #livecount, partnercount, ringmemberships
            #self.check_live_counts(1, 0, 1)
            assimcli_check("query allservers", maxdrones)
            assimcli_check("query down", maxdrones-1)
            assimcli_check("query crashed", 0)
            assimcli_check("query shutdown", maxdrones-1)
        else:
            if maxdrones == 1:
                partnercount=0
            elif maxdrones == 2:
                partnercount = 2
            else:
                partnercount=2*maxdrones
            #                      livecount  partnercount  ringmemberships
            #self.check_live_counts(maxdrones, partnercount, maxdrones)
            assimcli_check("query allservers", maxdrones)
            assimcli_check("query down", 0)
            assimcli_check("query shutdown", 0)
        assimcli_check("query unknownips", 0)
        for droneid in range(1,MaxDrone+1):
            droneip = droneipaddress(droneid)
            assimcli_check("query findip %s" % str(droneip), 1)
        if DoAudit:
            auditalldrones()
            auditallrings()
        for dtype in ('monitoring', 'network', 'service', 'monring', 'everything'):
            self.construct_and_verify_diagram(dtype, self.diagram_patterns(dtype, MaxDrone))

        if DEBUG:
            print "The CMA read %d packets."  % io.packetsread
            print "The CMA wrote %d packets." % io.writecount
        #io.dumppackets()
        #assert_no_dangling_Cclasses()


class TestMonitorBasic(TestCase):
    def test_activate(self):
        AssimEvent.disable_all_observers()
        io = IOTestIO([],0)
        CMAinit(io, cleanoutdb=True, debug=DEBUG)
        dummy = CMAdb.store.load_or_create(MonitorAction, domain='global', monitorname='DummyName'
        ,       monitorclass='OCF', monitortype='Dummy', interval=1, timeout=120, provider='heartbeat')

        self.assertEqual(len(CMAdb.transaction.tree['packets']), 0)
        CMAdb.store.commit()
        CMAdb.transaction.commit_trans(io)
        self.assertEqual(len(io.packetswritten), 0) # Shouldn't have sent out any pkts yet...
        CMAdb.transaction = Transaction(encryption_required=False)

        droneid = 1
        droneip = droneipaddress(droneid)
        designation = dronedesignation(droneid)
        droneAddr = pyNetAddr((127,0,0,1),1984)
        droneone = CMAdb.store.load_or_create(Drone, designation=designation, port=1984
        ,       startaddr=droneip, primary_ip_addr=droneip)
        self.assertTrue(not dummy.isactive)
        dummy.activate(droneone)
        CMAdb.store.commit()
        count=0
        for obj in CMAdb.store.load_related(droneone, CMAconsts.REL_hosting, MonitorAction):
            self.assertTrue(obj is dummy)
            count += 1
        self.assertEqual(count, 1)
        self.assertTrue(dummy.isactive)
        count=0
        for obj in CMAdb.store.load_related(dummy, CMAconsts.REL_monitoring, Drone):
            self.assertTrue(obj is droneone)
            count += 1
        self.assertEqual(count, 1)

#worked if we returned at or before here
        CMAdb.transaction.commit_trans(io)
#failed if we return here or later
        self.assertEqual(len(io.packetswritten), 1) # Did we send out exactly one packet?
        if SavePackets:
            #io.dumppackets()
            for fstuple in io.packetswritten:
                (dest, frameset) = fstuple
                self.assertEqual(frameset.get_framesettype(), FrameSetTypes.DORSCOP)
                for frame in frameset.iter():
                    self.assertEqual(frame.frametype(), FrameTypes.RSCJSON)
                    table = pyConfigContext(init=frame.getstr())
                    for field in ('class', 'type', 'instance', 'repeat'):
                        self.assertTrue(field in table)
                        if field == 'monitorclass' and table['monitorclass'] == 'OCF':
                            self.assertTrue('provider' in table)
                    for tup in (('class', str), ('type', str), ('resourcename', str)
                    ,           ('monitorclass', str), ('provider', str)
                    ,           ('repeat_interval', (int, long))
                    ,           ('timeout', (int,long))):
                        (n, t) = tup
                        if n in table:
                            self.assertTrue(isinstance(table[n], t))

        # TODO: Add test for deactivating the resource(s)
        #assert_no_dangling_Cclasses()

    def test_automonitor_LSB_basic(self):
        AssimEvent.disable_all_observers()
        drone = FakeDrone({
                'data': {
                        'lsb': {
                            'ssh',
                            'neo4j-service',
                        }
                }
            })
        neoargs = (
                    ('$argv[0]', r'.*/[^/]*java[^/]*$'),   # Might be overkill
                    ('$argv[3]', r'-server$'),             # Probably overkill
                    ('$argv[-1]', r'org\.neo4j\.server\.Bootstrapper$'),
            )
        neorule = LSBMonitoringRule('neo4j-service', neoargs)

        sshnode = ProcessNode('global', 'foofred', 'fred', '/usr/bin/sshd', ['/usr/bin/sshd', '-D' ]
        #ProcessNode:
        #   (domain, host, nodename, pathname, argv, uid, gid, cwd, roles=None):
        ,   'root', 'root', '/', roles=(CMAconsts.ROLE_server,))

        sshargs = (
                    # This means one of our nodes should have a value called
                    # pathname, and it should end in '/sshd'
                    ('@basename()', 'sshd$'),
            )
        sshrule = LSBMonitoringRule('ssh', sshargs)

        udevnode = ProcessNode('global', 'foofred', 'fred', '/usr/bin/udevd', ['/usr/bin/udevd']
        ,   'root', 'root', '/', roles=(CMAconsts.ROLE_server,))


        neoprocargs = ("/usr/bin/java", "-cp"
        , "/var/lib/neo4j/lib/concurrentlinkedhashmap-lru-1.3.1.jar:"
        "AND SO ON:"
        "/var/lib/neo4j/system/lib/slf4j-api-1.6.2.jar:"
        "/var/lib/neo4j/conf/", "-server", "-XX:"
        "+DisableExplicitGC"
        ,   "-Dorg.neo4j.server.properties=conf/neo4j-server.properties"
        ,   "-Djava.util.logging.config.file=conf/logging.properties"
        ,   "-Dlog4j.configuration=file:conf/log4j.properties"
        ,   "-XX:+UseConcMarkSweepGC"
        ,   "-XX:+CMSClassUnloadingEnabled"
        ,   "-Dneo4j.home=/var/lib/neo4j"
        ,   "-Dneo4j.instance=/var/lib/neo4j"
        ,   "-Dfile.encoding=UTF-8"
        ,   "org.neo4j.server.Bootstrapper")

        neonode = ProcessNode('global', 'foofred', 'fred', '/usr/bin/java', neoprocargs
        ,   'root', 'root', '/', roles=(CMAconsts.ROLE_server,))

        for tup in (sshrule.specmatch(ExpressionContext((udevnode, drone)))
        ,   sshrule.specmatch(ExpressionContext((neonode, drone)))
        ,   neorule.specmatch(ExpressionContext((sshnode, drone)))):
            (prio, table) = tup
            self.assertEqual(prio, MonitoringRule.NOMATCH)
            self.assertTrue(table is None)

        (prio, table) = sshrule.specmatch(ExpressionContext((sshnode, drone)))
        self.assertEqual(prio, MonitoringRule.LOWPRIOMATCH)
        self.assertEqual(table['monitorclass'], 'lsb')
        self.assertEqual(table['monitortype'], 'ssh')

        (prio, table) = neorule.specmatch(ExpressionContext((neonode, drone)))
        self.assertEqual(prio, MonitoringRule.LOWPRIOMATCH)
        self.assertEqual(table['monitorclass'], 'lsb')
        self.assertEqual(table['monitortype'], 'neo4j-service')

    def test_automonitor_LSB_failures(self):
        AssimEvent.disable_all_observers()
        self.assertRaises(ValueError, LSBMonitoringRule, 'neo4j-service', [])
        self.assertRaises(ValueError, LSBMonitoringRule, 'neo4j-service',
            (('a.b.c', ')'),))
        self.assertRaises(ValueError, LSBMonitoringRule, 'neo4j-service',
            ((1,2,3,4,5),))
        self.assertRaises(ValueError, LSBMonitoringRule, 'neo4j-service',
            ((1,),))
        self.assertRaises(ValueError, LSBMonitoringRule, 'neo4j-service',
            ((),))
        #assert_no_dangling_Cclasses()


    def test_automonitor_LSB_complete(self):
        # @TODO What I have in mind for this test is that it
        # actually construct an auto-generated LSB monitoring node and activate it
        # It will have to add name, timeout and repeat intervals before activating it.
        pass

    def test_automonitor_OCF_failures(self):
        AssimEvent.disable_all_observers()
        self.assertRaises(ValueError, OCFMonitoringRule, 'assimilation', 'neo4j',
            ((1,2,3,4,5),))
        self.assertRaises(ValueError, OCFMonitoringRule, 'assimilation', 'neo4j',
            ((),))
        #assert_no_dangling_Cclasses()

    def test_automonitor_OCF_basic(self):
        AssimEvent.disable_all_observers()
        drone = FakeDrone({
                'data': {
                        'ocf': {
                            'assimilation/neo4j',
                        }
                    }
                })
        kitchensink = OCFMonitoringRule('assimilation', 'neo4j',
        (   ('cantguess',)                  #   length 1 - name
        ,   ('port', '$port')               #   length 2 - name, expression
        ,   (None, '$port')                 #   length 2 - name, expression
        ,   ('-', '$pathname')              #   length 2 - name, expression
        ,   ('port', '$port', '[0-9]+$')    #   length 3 - name, expression, regex
        ,   (None, '$pathname', '.*/java$') #   length 3 - name, expression, regex
        ,   (None, '@basename()', 'java$')  #   length 3 - name, expression, regex
        ,   ('-', '$argv[-1]', r'org\.neo4j\.server\.Bootstrapper$')
                                            #   length 3 - name, expression, regex
        ,   ('port', '@serviceport()', '[0-9]+$', re.I)  #   length 4 - name, expression, regex, flags
        ))
        keys = kitchensink.nvpairs.keys()
        keys.sort()
        self.assertEqual(str(keys), "['cantguess', 'port']")
        values = []
        for key in keys:
            values.append(kitchensink.nvpairs[key])
        self.assertEqual(str(values), "[None, '@serviceport()']")
        regex = re.compile('xxx')
        regextype = type(regex)
        exprlist = []
        for tup in kitchensink._tuplespec:
            self.assertEqual(type(tup[1]), regextype)
            exprlist.append(tup[0])
        self.assertEqual(str(exprlist)
        ,   "['$port', '$pathname', '@basename()', '$argv[-1]', '@serviceport()']")
        #
        # That was a pain...
        #
        # Now, let's test the basics in a little more depth by creating what should be a working
        # set of arguments to a (hypothetical) OCF resource agent
        #
        neo4j = OCFMonitoringRule('assimilation', 'neo4j',
            (   ('port', '$port')
            ,   (None, '$pathname', '.*/java$')
            ,   ('-', '$argv[-1]', r'org\.neo4j\.server\.Bootstrapper$')
            ,   ('home', '@argequals(-Dneo4j.home)', '/.*')
            ,   ('neo4j', '@basename(@argequals(-Dneo4j.home))', '.')
            )
        )
        neoprocargs = ("/usr/bin/java", "-cp"
        , "/var/lib/neo4j/lib/concurrentlinkedhashmap-lru-1.3.1.jar:"
        "AND SO ON:"
        "/var/lib/neo4j/system/lib/slf4j-api-1.6.2.jar:"
        "/var/lib/neo4j/conf/", "-server", "-XX:"
        "+DisableExplicitGC"
        ,   "-Dorg.neo4j.server.properties=conf/neo4j-server.properties"
        ,   "-Djava.util.logging.config.file=conf/logging.properties"
        ,   "-Dlog4j.configuration=file:conf/log4j.properties"
        ,   "-XX:+UseConcMarkSweepGC"
        ,   "-XX:+CMSClassUnloadingEnabled"
        ,   "-Dneo4j.home=/var/lib/neo4j"
        ,   "-Dneo4j.instance=/var/lib/neo4j"
        ,   "-Dfile.encoding=UTF-8"
        ,   "org.neo4j.server.Bootstrapper")

        neonode = ProcessNode('global', 'foofred', 'fred', '/usr/bin/java', neoprocargs
        ,   'root', 'root', '/', roles=(CMAconsts.ROLE_server,))
        # We'll be missing the value of 'port'
        neocontext = ExpressionContext((neonode, drone))
        match = neo4j.specmatch(neocontext)
        (prio, table, missing) = neo4j.specmatch(neocontext)
        self.assertEqual(prio, MonitoringRule.PARTMATCH)
        self.assertEqual(missing, ['port'])
        # Now fill in the port value
        neonode.port=7474
        (prio, table) = neo4j.specmatch(neocontext)
        self.assertEqual(prio, MonitoringRule.HIGHPRIOMATCH)
        self.assertEqual(table['monitortype'], 'neo4j')
        self.assertEqual(table['monitorclass'], 'ocf')
        self.assertEqual(table['provider'], 'assimilation')
        keys = table.keys()
        keys.sort()
        self.assertEqual(str(keys), "['arglist', 'monitorclass', 'monitortype', 'provider']")
        arglist = table['arglist']
        keys = arglist.keys()
        keys.sort()
        self.assertEqual(keys, ['home', 'neo4j', 'port'])
        self.assertEqual(arglist['port'], '7474')
        self.assertEqual(arglist['home'], '/var/lib/neo4j')
        self.assertEqual(arglist['neo4j'], 'neo4j')
        #assert_no_dangling_Cclasses()

    def test_automonitor_strings_basic(self):
        # Clean things out so we only see what we want to see...
        AssimEvent.disable_all_observers()
        ocf_string = '''{
#       comment
        "class":        "ocf",
        "type":         "neo4j",
        "provider":     "assimilation",
        "classconfig": [
            [null,      "@basename()",              "java$"],
            [null,      "$argv[-1]",                 "org\\.neo4j\\.server\\.Bootstrapper$"],
            ["PORT",    "serviceport",              "[0-9]+$"],
            ["NEOHOME", "@argequals(-Dneo4j.home)", "/.*"]
        ]
}'''
        ocf = MonitoringRule.ConstructFromString(ocf_string)
        self.assertTrue(isinstance(ocf, OCFMonitoringRule))
        lsb_string = '''{
#       comment
        "class":        "lsb",
        "type":         "neo4j",
        "classconfig": [
            ["@basename()",    "java$"],
            ["$argv[-1]",       "org\\.neo4j\\.server\\.Bootstrapper$"],
        ]
}'''
        lsb = MonitoringRule.ConstructFromString(lsb_string)
        self.assertTrue(isinstance(lsb, LSBMonitoringRule))
        #assert_no_dangling_Cclasses()

    def test_automonitor_search_basic(self):
        AssimEvent.disable_all_observers()
        drone = FakeDrone({
                'data': {
                        'ocf': {
                            'assimilation/neo4j',
                        },
                        'lsb': {
                            'neo4j-service',
                        }
                    }
                })
        MonitoringRule.monitor_objects = {'service': {}, 'host':{}}
        ocf_string = '''{
        "class":        "ocf", "type":         "neo4j", "provider":     "assimilation",
        "classconfig": [
            [null,      "@basename()",          "java$"],
            [null,      "$argv[-1]",             "org\\.neo4j\\.server\\.Bootstrapper$"],
            ["PORT",    "$serviceport"],
            ["NEOHOME", "@argequals(-Dneo4j.home)", "/.*"]
        ]
        }'''
        MonitoringRule.ConstructFromString(ocf_string)
        lsb_string = '''{
        "class":        "lsb", "type":         "neo4j-service",
        "classconfig": [
            ["@basename()",    "java$"],
            ["$argv[-1]", "org\\.neo4j\\.server\\.Bootstrapper$"],
        ]
        }'''
        MonitoringRule.ConstructFromString(lsb_string)
        neoprocargs = ("/usr/bin/java", "-cp"
        , "/var/lib/neo4j/lib/concurrentlinkedhashmap-lru-1.3.1.jar:"
        "AND SO ON:"
        "/var/lib/neo4j/system/lib/slf4j-api-1.6.2.jar:"
        "/var/lib/neo4j/conf/", "-server", "-XX:"
        "+DisableExplicitGC"
        ,   "-Dneo4j.home=/var/lib/neo4j"
        ,   "-Dneo4j.instance=/var/lib/neo4j"
        ,   "-Dfile.encoding=UTF-8"
        ,   "org.neo4j.server.Bootstrapper")

        neonode = ProcessNode('global', 'foofred', 'fred', '/usr/bin/java', neoprocargs
        ,   'root', 'root', '/', roles=(CMAconsts.ROLE_server,))
        #neonode.serviceport=7474
        context = ExpressionContext((neonode, drone))
        first = MonitoringRule.findbestmatch(context)
        second = MonitoringRule.findbestmatch(context, False)
        list1 = MonitoringRule.findallmatches(context)
        neonode.serviceport=7474
        third = MonitoringRule.findbestmatch(context)
        list2 = MonitoringRule.findallmatches(context)

        # first should be the LSB instance
        self.assertEqual(first[1]['monitorclass'], 'lsb')
        self.assertEqual(first[0], MonitoringRule.LOWPRIOMATCH)
        # second should be the incomplete OCF instance
        self.assertEqual(second[1]['monitorclass'], 'ocf')
        self.assertEqual(second[0], MonitoringRule.PARTMATCH)
        # third should be the high priority OCF instance
        self.assertEqual(third[1]['monitorclass'], 'ocf')
        self.assertEqual(third[0], MonitoringRule.HIGHPRIOMATCH)
        # list1 should be the incomplete OCF and the complete LSB - in that order
        self.assertEqual(len(list1), 2)
        # They should come out sorted by monitorclass
        self.assertEqual(list1[0][0], MonitoringRule.LOWPRIOMATCH)
        self.assertEqual(list1[0][1]['monitorclass'], 'lsb')
        self.assertEqual(list1[1][0], MonitoringRule.PARTMATCH)
        self.assertEqual(list1[1][1]['monitorclass'], 'ocf')
        # third should be a complete OCF match
        # list2 should be the complete OCF and the complete OCF - in that order
        self.assertEqual(len(list2), 2)
        self.assertEqual(list2[0][0], MonitoringRule.LOWPRIOMATCH)
        self.assertEqual(list2[0][1]['monitorclass'], 'lsb')
        self.assertEqual(list2[1][0], MonitoringRule.HIGHPRIOMATCH)
        self.assertEqual(list2[1][1]['monitorclass'], 'ocf')
        #assert_no_dangling_Cclasses()

    def test_automonitor_functions(self):
        AssimEvent.disable_all_observers()
        MonitoringRule.monitor_objects = {'service': {}, 'host':{}}
        drone = FakeDrone({
                'data': {
                        'ocf': {
                            'assimilation/neo4j',
                        },
                        'lsb': {
                            'bacula',
                        },
                        'nagios': {
                            'check_ssh',
                        },
                    }
                })
        ocf_string = '''{
        "class":        "ocf", "type":         "neo4j", "provider":     "assimilation",
        "classconfig": [
            [null,          "@basename()", "java"],
            ["classpath",   "@flagvalue(-cp)", "..."],
            ["ipaddr",      "@serviceip($procinfo.listenaddrs)", "..."],
            ["port",        "@serviceport()",   "[0-9]+$"]
        ]
        }'''
        nagios_string = '''{
    "class":    "nagios",
    "type":     "check_ssh",
    "prio":     "med",
    "objclass":  "service",     # possible values are "service" or "host"
    "initargs": ["-t", "3600"], # Nanoprobes have their own timeouts...
    "classconfig": [
        [null,          "@basename()",          "sshd$"],
        ["-p",          "@serviceport()",       "[0-9]+"],
        ["__ARGV__",    "@serviceip()",         "..."]
	]
}'''
        ssh_json = '''{
          "exe": "/usr/sbin/sshd",
          "argv": [ "/usr/sbin/sshd", "-D" ],
          "uid": "root",
          "gid": "root",
          "cwd": "/",
          "listenaddrs": {
            "127.0.0.1:22": {
              "proto": "tcp",
              "addr": "127.0.0.1",
              "port": 22
            },
            ":::22": {
              "proto": "tcp6",
              "addr": "::",
              "port": 22
            }
          }
        }'''
        neo4j_json = '''{
          "exe": "/usr/lib/jvm/java-7-openjdk-amd64/jre/bin/java",
          "argv": [ "/usr/bin/java", "-cp", "/var/lib/neo4j/lib/concurrentlinkedhashmap-lru-1.3.1.jar: ...", "-server", "-XX:+DisableExplicitGC", "-Dorg.neo4j.server.properties=conf/neo4
    j-server.properties", "-Djava.util.logging.config.file=conf/logging.properties", "-Dlog4j.configuration=file:conf/log4j.properties", "-XX:
    +UseConcMarkSweepGC", "-XX:+CMSClassUnloadingEnabled", "-Dneo4j.home=/var/lib/neo4j", "-Dneo4j.instance=/var/lib/neo4j", "-Dfile.encoding=
    UTF-8", "org.neo4j.server.Bootstrapper" ],
          "uid": "neo4j",
          "gid": "neo4j",
          "cwd": "/var/lib/neo4j",
          "listenaddrs": {
            "::1:1337": {
              "proto": "tcp6",
              "addr": "::1",
              "port": 1337
            },
            ":::39185": {
              "proto": "tcp6",
              "addr": "::",
              "port": 39185
            }
          }
        }'''
        bacula_json = '''{
      "exe": "/usr/sbin/bacula-dir",
      "argv": [ "/usr/sbin/bacula-dir", "-c", "/etc/bacula/bacula-dir.conf", "-u", "bacula", "-g", "bacula" ],
      "uid": "bacula",
      "gid": "bacula",
      "cwd": "/",
      "listenaddrs": {
        "10.10.10.5:9101": {
          "proto": "tcp",
          "addr": "10.10.10.5",
          "port": 9101
        }
      }
    }'''
        MonitoringRule.ConstructFromString(ocf_string)
        MonitoringRule.ConstructFromString(nagios_string)
        neoargs = pyConfigContext(neo4j_json)['argv']
        testnode = ProcessNode('global', 'foofred', 'fred', '/usr/bin/java', neoargs
        ,   'root', 'root', '/', roles=(CMAconsts.ROLE_server,))

        testnode.procinfo = neo4j_json
        context = ExpressionContext((testnode, drone))
        (prio, match) = MonitoringRule.findbestmatch(context)
        self.assertEqual(prio, MonitoringRule.HIGHPRIOMATCH)
        self.assertEqual(match['arglist']['ipaddr'], '::1')
        self.assertEqual(match['arglist']['port'], '1337')

        sshargs = pyConfigContext(ssh_json)['argv']
        testnode = ProcessNode('global', 'foofred', 'fred', '/usr/bin/sshd', sshargs
        ,   'root', 'root', '/', roles=(CMAconsts.ROLE_server,))
        testnode.procinfo = ssh_json
        context = ExpressionContext((testnode, drone))
        (prio, match) = MonitoringRule.findbestmatch(context)
        #print >> sys.stderr, 'MATCH:', match
        self.assertEqual(prio, MonitoringRule.MEDPRIOMATCH)
        self.assertEqual(match['argv'], ['-t', '3600', '-p', '22', '127.0.0.1'])
        #assert_no_dangling_Cclasses()


    def test_automonitor_OCF_complete(self):
        # @TODO What I have in mind for this test is that it
        # actually construct an auto-generated OCF monitoring node and activate it
        # It will have to add name, timeout and repeat intervals before activating it.
        pass


if __name__ == "__main__":
    run()
