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
_suites = ['all', 'cclass']
import sys, os
import traceback
#traceback.print_exc()
sys.path.append("../cma")
os.environ['G_MESSAGES_DEBUG'] =  'all'
from testify import *

from frameinfo import *
from AssimCclasses import *
import gc
import re
from AssimCtypes import proj_class_incr_debug, proj_class_decr_debug


CheckForDanglingClasses = True
WorstDanglingCount = 0
DEBUG=True
DEBUG=False
BROKENDNS=False
if 'BROKENDNS' in os.environ:
    BROKENDNS=True

CheckForDanglingClasses = True
AssertOnDanglingClasses = True

if not CheckForDanglingClasses:
    print >> sys.stderr, 'WARNING: Memory Leak Detection disabled.'
elif not AssertOnDanglingClasses:
    print >> sys.stderr, 'WARNING: Memory Leak assertions disabled (detection still enabled).'

def assert_no_dangling_Cclasses():
    global CheckForDanglingClasses
    global WorstDanglingCount
    gc.collect()
    count =  proj_class_live_object_count()
    # Avoid cluttering the output up with redundant messages...
    if count > WorstDanglingCount and CheckForDanglingClasses:
        WorstDanglingCount = count
        if AssertOnDanglingClasses:
            dump_c_objects()
            raise AssertionError, "Dangling C-class objects - %d still around" % count
        else:
            print >> sys.stderr,  ("*****ERROR: Dangling C-class objects - %d still around" % count)

class pyNetAddrTest(TestCase):
    "A pyNetAddr is a network address of some kind... - let's test it"
    def test_constructor(self): 
        if DEBUG: print >>sys.stderr, "===============test_constructor(pyNetAddrTest)"
        ipv4 = pyNetAddr((1,2,3,4),)
        ipv4b = pyNetAddr((1,2,3,5),)
        mac48 = pyNetAddr((1,2,3,4,5,6),)
        mac64 = pyNetAddr( (1,2,3,4,5,6,7,8),)
        ipv6 = pyNetAddr((1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16),)
        self.assertEqual(str(ipv4), "1.2.3.4")
        self.assertEqual(str(ipv4b), "1.2.3.5")
        self.assertEqual(str(mac48), "01-02-03-04-05-06")
        self.assertEqual(str(mac64), "01-02-03-04-05-06-07-08")
        self.assertFalse(ipv4 != ipv4)
        self.assertTrue(ipv4   ==  ipv4)
        self.assertTrue(mac48  ==  mac48)
        self.assertTrue(mac64  ==  mac64)
        self.assertFalse(ipv4  ==  ipv4b)
        self.assertFalse(ipv4  ==  mac48)
        self.assertFalse(mac48 ==  ipv4)
        self.assertFalse(ipv4  ==  mac64)
        self.assertFalse(mac64 ==  ipv4)
        self.assertFalse(mac48 ==  mac64)
        self.assertFalse(mac64 ==  mac48)
        self.assertRaises(ValueError, pyNetAddr, (1,))
        self.assertRaises(ValueError, pyNetAddr, (1,2,))
        self.assertRaises(ValueError, pyNetAddr, (1,2,3))
        self.assertRaises(ValueError, pyNetAddr, (1,2,3,4,5))
        self.assertRaises(ValueError, pyNetAddr, (1,2,3,4,5,6,7))
        self.assertRaises(ValueError, pyNetAddr, (1,2,3,4,5,6,7,8,9))
        self.assertRaises(ValueError, pyNetAddr, (1,2,3,4,5,6,7,8,9,10))
        self.assertRaises(ValueError, pyNetAddr, (1,2,3,4,5,6,7,8,9,10,11))
        self.assertRaises(ValueError, pyNetAddr, (1,2,3,4,5,6,7,8,9,10,11,12))
        self.assertRaises(ValueError, pyNetAddr, (1,2,3,4,5,6,7,8,9,10,11,12,13))
        self.assertRaises(ValueError, pyNetAddr, (1,2,3,4,5,6,7,8,9,10,11,12,13,14))
        self.assertRaises(ValueError, pyNetAddr, (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15))
        self.assertRaises(ValueError, pyNetAddr, (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17))

    def test_ipv4_eq(self): 
        'Test if various ipv4 addresses are equal'
        self.assertEqual(pyNetAddr((1,2,3,4),80), pyNetAddr('1.2.3.4:80'))
        self.assertEqual(pyNetAddr((1,2,3,4),), pyNetAddr('1.2.3.4'),)
        self.assertEqual(pyNetAddr('1.2.3.4:80'), pyNetAddr((1,2,3,4),80))
        self.assertNotEqual(pyNetAddr('1.2.3.4:80'), pyNetAddr((1,2,3,4),81))
        self.assertNotEqual(pyNetAddr('1.2.3.4:80'), pyNetAddr((1,2,3,4),))

    def test_ipv6_eq(self): 
        'Test if various ipv6 addresses are equal'
        self.assertEqual(pyNetAddr('::1'), pyNetAddr('::1'))
        self.assertEqual(pyNetAddr('::'), pyNetAddr('::'))
        self.assertNotEqual(pyNetAddr('::'), pyNetAddr('::1'))
        self.assertNotEqual(pyNetAddr('::1'), pyNetAddr('[::1]:80'))
        self.assertEqual(pyNetAddr('[::1]:1984'), pyNetAddr('[::1]:1984'))
        self.assertNotEqual(pyNetAddr('::1:2:3:4:1'), pyNetAddr('::1'))

    def test_mixed_eq(self): 
        'Test if various ipv4/v6 addresses are equal to each other'
        self.assertEqual(pyNetAddr('::1'), pyNetAddr('127.0.0.1'))
        self.assertEqual(pyNetAddr('127.0.0.1'), pyNetAddr('::1'))
        self.assertEqual(pyNetAddr('::ffff:7f00:1'), pyNetAddr('::1'))
        self.assertEqual(pyNetAddr('::ffff:7f00:1'), pyNetAddr('127.0.0.1'))
        self.assertEqual(pyNetAddr((0,0,0,0,0,0,0,0,0,0, 0xff, 0xff, 127, 0, 0, 1),), pyNetAddr('::1'))

    def test_mixed_hash(self): 
        'Test if various ipv4/v6 addresses hash to the same values - or not'
        self.assertEqual(pyNetAddr('::1').__hash__(), pyNetAddr('::1').__hash__())
        self.assertEqual(pyNetAddr('::1').__hash__(), pyNetAddr('127.0.0.1').__hash__())
        self.assertEqual(pyNetAddr('[::1]:80').__hash__(), pyNetAddr('127.0.0.1:80').__hash__())
        self.assertNotEqual(pyNetAddr('[::1]:80').__hash__(), pyNetAddr('127.0.0.1:1984').__hash__())
        self.assertEqual(pyNetAddr('::ffff:7f00:1').__hash__(), pyNetAddr('::1').__hash__())
        self.assertEqual(pyNetAddr('[::ffff:7f00:1]:25').__hash__(), pyNetAddr('[::1]:25').__hash__())
        self.assertNotEqual(pyNetAddr('[::ffff:7f00:1]:25').__hash__(), pyNetAddr('[::1]:26').__hash__())
        self.assertNotEqual(pyNetAddr('::').__hash__(), pyNetAddr('::1').__hash__())
        self.assertEqual(pyNetAddr('::ffff:7f00:1').__hash__(), pyNetAddr('127.0.0.1').__hash__())
        self.assertEqual(pyNetAddr((0,0,0,0,0,0,0,0,0,0, 0xff, 0xff, 127, 0, 0, 1),).__hash__(), pyNetAddr('::1').__hash__())

    def test_ipv6_str(self): 
        'Test the str() function for ipv6 - worth a separate test.'
        if DEBUG: print >>sys.stderr, "===============test_ipv6_str(pyNetAddrTest)"
        ipv6 = pyNetAddr((0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0),)
        self.assertEqual(str(ipv6),"::")
        ipv6 = pyNetAddr((0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,01),)
        self.assertEqual(str(ipv6),"::1")
        ipv6 = pyNetAddr((0,0,0,0,0,0,0,0,0,0,0,0,0,0,01,02),)
        self.assertEqual(str(ipv6),"::102")
        ipv6 = pyNetAddr((0,0,0,1,0,2,0,3,0,4,0,5,0,6,0,7),)
        self.assertEqual(str(ipv6),"0:1:2:3:4:5:6:7")
        ipv6 = pyNetAddr((0,0,0,0,0,2,0,3,0,4,0,5,0,6,0,7),)
        self.assertEqual(str(ipv6),"::2:3:4:5:6:7")
        # Example below is from http://en.wikipedia.org/wiki/IPv6_address
        # Note that we now convert it into the equivalent IPv4 address as
        # suggested: ::ffff:192.0.2.128
        ipv6 = pyNetAddr((0,0,0,0,0,0,0,0,0,0,255,255,192,0,2,128),)
        self.assertEqual(str(ipv6),"::ffff:192.0.2.128")

    def test_ipv4_strinit(self): 
        'Test constructing ipv4 addresses from strings.'
        if DEBUG: print >>sys.stderr, "===============test_ipv4_strinit(pyNetAddrTest)"
        ipv4 = pyNetAddr('1.2.3.4')
        self.assertEqual(str(ipv4),'1.2.3.4')
        ipv4 = pyNetAddr('1.2.3.5')
        self.assertEqual(str(ipv4),'1.2.3.5')
        ipv4 = pyNetAddr('1.2.3.4:80')
        self.assertEqual(str(ipv4),'1.2.3.4:80')
        ipv4 = pyNetAddr('1.2.3.5:80')
        self.assertEqual(str(ipv4),'1.2.3.5:80')
        try:
            pyNetAddr('1.2.ff.5')
        except ValueError:
            # This is correct behavior
            pass
        else:
            if not BROKENDNS:
                raise ValueError('Your DNS seems to be broken. Set environment variable BROKENDNS')
        self.assertRaises(ValueError, pyNetAddr, '1.2.3.4:')
        self.assertRaises(ValueError, pyNetAddr, '1.2.3.4:ff')

    def test_toIPv6(self): 
        'Test converting IPv4 addresses to IPv6'
        ipstr= '213.138.100.204:57225'
        ipv4 = pyNetAddr(ipstr)
        self.assertEqual(str(ipv4),ipstr)
        ipv6 = ipv4.toIPv6()
        self.assertEqual(str(ipv6),'[::ffff:213.138.100.204]:57225')
        ipv6 = ipv6.toIPv6()
        self.assertEqual(str(ipv6),'[::ffff:213.138.100.204]:57225')
        ipv6 = pyNetAddr(str(ipv6))
        self.assertEqual(str(ipv6),'[::ffff:213.138.100.204]:57225')
        #
        ipstr= '213.138.100.255:65535'
        ipv4 = pyNetAddr(ipstr)
        self.assertEqual(str(ipv4),ipstr)
        ipv6 = ipv4.toIPv6()
        self.assertEqual(str(ipv6),'[::ffff:213.138.100.255]:65535')
        ipv6 = ipv6.toIPv6()
        self.assertEqual(str(ipv6),'[::ffff:213.138.100.255]:65535')
        ipv6 = pyNetAddr(str(ipv6))
        self.assertEqual(str(ipv6),'[::ffff:213.138.100.255]:65535')
        #
        ipstr= '255.255.255.255:65535'
        ipv4 = pyNetAddr(ipstr)
        self.assertEqual(str(ipv4),ipstr)
        ipv6 = ipv4.toIPv6()
        self.assertEqual(str(ipv6),'[::ffff:255.255.255.255]:65535')
        ipv6 = ipv6.toIPv6()
        self.assertEqual(str(ipv6),'[::ffff:255.255.255.255]:65535')
        ipv6 = pyNetAddr(str(ipv6))
        self.assertEqual(str(ipv6),'[::ffff:255.255.255.255]:65535')

    def test_ipv6_strinit(self): 
        'Test constructing ipv6 addresses from strings.'
        if DEBUG:
            for j in range(1,5):
                proj_class_incr_debug('NetAddr')
        if DEBUG: print >>sys.stderr, "===============test_ipv6_strinit(pyNetAddrTest)"
        ipv6 = pyNetAddr('::1')
        self.assertEqual(str(ipv6),'::1')

        ipv6 = pyNetAddr('::')
        self.assertEqual(str(ipv6),'::')

        ipv6 = pyNetAddr('0:1:2:3:4:5:6:7')
        self.assertEqual(str(ipv6),'0:1:2:3:4:5:6:7')

        ipv6 = pyNetAddr('::2:3:4:5:6:7')
        self.assertEqual(str(ipv6),'::2:3:4:5:6:7')

        ipv6 = pyNetAddr('[::]:1984')
        self.assertEqual(str(ipv6),'[::]:1984')

        ipv6 = pyNetAddr('[::1]:80')
        self.assertEqual(str(ipv6),'[::1]:80')

        ipv6 = pyNetAddr('[0:1:2:3:4:5:6:7]:8080')
        self.assertEqual(str(ipv6),'[0:1:2:3:4:5:6:7]:8080')

        ipv6 = pyNetAddr('::2:3:4:5:6:7')
        self.assertEqual(str(ipv6),'::2:3:4:5:6:7')

        ipv6 = pyNetAddr('::a:b:c:d:e:f')
        self.assertEqual(str(ipv6),'::a:b:c:d:e:f')

        ipv6 = pyNetAddr('::ffff:1.2.3.4')
        self.assertEqual(str(ipv6),'::ffff:1.2.3.4')

        ipv6 = pyNetAddr('[::ffff:1.2.3.4]:80')
        self.assertEqual(str(ipv6),'[::ffff:1.2.3.4]:80')

        ipv6 = pyNetAddr('[::ffff:255.255.255.255]:65535')
        self.assertEqual(str(ipv6), '[::ffff:255.255.255.255]:65535')

        self.assertRaises(ValueError, pyNetAddr, '0:1:2:3:4:5:6:7::')
        self.assertRaises(ValueError, pyNetAddr, '::fffff')
        self.assertRaises(ValueError, pyNetAddr, '[0:1:2:3:4:5:6:7]10')
        self.assertRaises(ValueError, pyNetAddr, '[0:1:2:3:4:5:6:7]:ff')
        self.assertRaises(ValueError, pyNetAddr, '0:1:2:3:4:5g:6:7')
        self.assertRaises(ValueError, pyNetAddr, '[0:1:2:3:4:5g:6:7]:10')
        self.assertRaises(ValueError, pyNetAddr, 'ffff:1.2.3.256')
        self.assertRaises(ValueError, pyNetAddr, 'ffff:1.2.3:4')
        self.assertRaises(ValueError, pyNetAddr, '[ffff:1.2.3:4]:99')
        self.assertRaises(ValueError, pyNetAddr, '[ffff:1.2.3.4]:65536')
        if DEBUG:
            for j in range(1,5):
                proj_class_decr_debug('NetAddr')

    def test_dns_strinit(self): 
        'Test constructing DNS addresses from strings.'
        if DEBUG:
            for j in range(1,5):
                proj_class_incr_debug('NetAddr')
        if DEBUG: print >>sys.stderr, "===============test_DNS_strinit(pyNetAddrTest)"
        addr1 = pyNetAddr('www.linux-ha.org:80')
        self.assertEqual(addr1.port(), 80)
        try:
            addr2 = pyNetAddr('www.linux-ha.org:http')
        except ValueError:
            # Some systems use www instead of http...
            addr2 = pyNetAddr('www.linux-ha.org:www')
        # Note that this next test assumes that we're not getting round robin DNS...
        self.assertEqual(addr1, addr2)

        self.assertRaises(ValueError, pyNetAddr, 'www.google.com:')
        self.assertRaises(ValueError, pyNetAddr, 'www.google.com:nosuchport')
        self.assertRaises(ValueError, pyNetAddr, 'www.google.com:65536')
        self.assertRaises(ValueError, pyNetAddr, 'www.google.com:65537')
        self.assertRaises(ValueError, pyNetAddr, 'www.google.com:-1')
        # These next two may fail to raise ValueError - if your DNS is broken...
        try:
            pyNetAddr('www.frodo.middleearth')
        except ValueError:
            # This is correct behavior
            pass
        else:
            if not BROKENDNS:
                raise ValueError('Your DNS seems to be broken. Set environment variable BROKENDNS')
        try:
            pyNetAddr('www.frodo.middleearth:80')
        except ValueError:
            # This is correct behavior
            pass
        else:
            if not BROKENDNS:
                raise ValueError('Your DNS is broken - in kind of a weird way')

        if DEBUG:
            for j in range(1,5):
                proj_class_decr_debug('NetAddr')

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

class pyFrameTest(TestCase):
    '''Frames are our basic superclass for things we put on the wire.
       This base class just has a generic binary blob with no special
       properties.  They are all valid (if they have a value)'''
    def test_constructor(self): 
        if DEBUG: print >>sys.stderr, "===============test_constructor(pyFrameTest)"
        pyf = pyFrame(100)
        self.assertEqual(pyf.frametype(), 100)
        self.assertTrue(pyf.isvalid())

    def test_setvalue(self): 
        if DEBUG: print >>sys.stderr, "===============test_setvalue(pyFrameTest)"
        pyf = pyFrame(101)
        pyf.setvalue('fred')
        self.assertTrue(pyf.isvalid(), "PyFrame('fred') failed isvalid())")
        self.assertEqual(pyf.framelen(), 5)
        self.assertEqual(pyf.dataspace(), 10) # Total space for this Frame on the wire
        self.assertEqual(string_at(pyf.framevalue()), 'fred') # Raw from 'C'

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

class pyAddrFrameTest(TestCase):
    'An AddrFrame wraps a NetAddr for sending on the wire'
    def test_constructor(self): 
        if DEBUG: print >>sys.stderr, "===============test_constructor(pyAddrFrameTest)"
        pyf = pyAddrFrame(200, addrstring=(1,2,3,4))
        self.assertEqual(pyf.frametype(), 200)
        self.assertEqual(pyf.framelen(), 6)
        self.assertEqual(str(pyf), 'pyAddrFrame(200, (1.2.3.4))')
        self.assertEqual(pyf.addrtype(), 1)
        self.assertTrue(pyf.isvalid(), "AddrFrame(200, (1,2,3,4)) failed isvalid()")
        self.assertRaises(ValueError, pyAddrFrame, 201, addrstring=(1,2,3))

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()


class pyIpPortFrameTest1(TestCase):
    'An IpPortFrame wraps a NetAddr (with port!) for sending on the wire'
    def test_constructor(self): 
        if DEBUG: print >>sys.stderr, '===============test_constructor(pyIpPortFrameTest1)'
        addrv4=pyNetAddr('1.2.3.4:1984')
        py4 = pyIpPortFrame(201, addrv4)
        self.assertEqual(py4.frametype(), 201)
        self.assertEqual(py4.framelen(), 8)
        self.assertEqual(str(py4), '201: IpPortFrame(201, 1.2.3.4:1984)')
        self.assertEqual(py4.addrtype(), 1)
        self.assertTrue(py4.isvalid(), 'pyIpPortFrame(201, (1.2.3.4:1984)) failed isvalid()')
        self.assertRaises(ValueError, pyIpPortFrame, 201, pyNetAddr((1,2,3,4,5,6),)) # MAC address
        addrv6=pyNetAddr('[::1]:79')
        py6 = pyIpPortFrame(302, addrv6)
        self.assertEqual(py6.frametype(), 302)
        self.assertEqual(py6.framelen(), 20)
        self.assertEqual(str(py6), '302: IpPortFrame(302, [::1]:79)')

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()


class pyIpPortFrameTest2(TestCase):
    'An AddrFrame wraps a NetAddr *with a port* for sending on the wire'
    def test_constructor(self): 
        if DEBUG: print >>sys.stderr, "===============test_constructor(pyIpAddrFrameTest)"
        pyf = pyIpPortFrame(200, (1,2,3,4), 1984)
        self.assertEqual(pyf.frametype(), 200)
        self.assertEqual(pyf.framelen(), 8)
        self.assertEqual(str(pyf), '200: IpPortFrame(200, 1.2.3.4:1984)')
        self.assertEqual(pyf.getnetaddr(), pyNetAddr('1.2.3.4:1984'))
        self.assertEqual(pyf.addrtype(), 1)
        self.assertTrue(pyf.isvalid(), "pyIpPortFrame(200, (1,2,3,4:1984)) failed isvalid()")
        self.assertRaises(ValueError, pyIpPortFrame, 201, (1,2,3),80)
        pyf = pyIpPortFrame(202, (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16), 1984)
        self.assertEqual(pyf.frametype(), 202)
        self.assertEqual(pyf.framelen(), 20)
        self.assertEqual(pyf.addrtype(), 2)
        self.assertTrue(pyf.isvalid(), 'pyIpPortFrame(202, ([102:304:506:708:90a:b0c:d0e:f10]:1984))')
        self.assertEqual(str(pyf), '202: IpPortFrame(202, [102:304:506:708:90a:b0c:d0e:f10]:1984)')
        sameaddr = pyNetAddr([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10], port=1984)
        self.assertEqual(pyf.getnetaddr(), sameaddr)
        pyf = pyIpPortFrame(202, sameaddr, None)
        self.assertEqual(str(pyf), '202: IpPortFrame(202, [102:304:506:708:90a:b0c:d0e:f10]:1984)')
        self.assertEqual(pyf.getnetaddr(), sameaddr)


    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

class pyIntFrameTest(TestCase):
    'An IntFrame wraps various sizes of unsigned integers for sending on the wire'
    def test_constructor(self): 
        if DEBUG: print >>sys.stderr, "========================test_constructor(pyIntFrameTest)"
        # Test a variety of illegal/unsupported integer sizes
        for size in (5, 6, 7, 9, 10):
            self.assertRaises(ValueError, pyIntFrame, 300+size-1, intbytes=size)
        # Some network protocols have 3-byte integers.  So I implemented them.
        for size in (1, 2, 3, 4, 8):
            pyf = pyIntFrame(310+size, initval=42, intbytes=size)
            self.assertTrue(pyf.isvalid())
            self.assertEqual(pyf.intlength(), size)
            self.assertEqual(int(pyf), 42)
            self.assertEqual(str(pyf), 'pyIntFrame(%d, (42))' % (310+size))

    def test_set(self): 
        'Test setting integer values for all the size integers'
        if DEBUG: print >>sys.stderr, "========================test_set(pyIntFrameTest)"
        for size in (1, 2, 3, 4, 8):
            pyf = pyIntFrame(320, initval=0, intbytes=size)
            val = 42 + size
            pyf.setint(val)
            self.assertEqual(int(pyf), val)
            self.assertEqual(str(pyf), ('pyIntFrame(320, (%d))' % val))
        

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

class pyUnknownFrameTest(TestCase):
    "An unknown frame is one we don't recognize the type of."
    def test_constructor(self): 
        if DEBUG: print >>sys.stderr, "========================test_constructor(pyUnknownFrameTest)"
        pyf = pyUnknownFrame(400)
        self.assertEqual(pyf.frametype(), 400)
        # All Unknown frames are invalid...
        self.assertFalse(pyf.isvalid(), "pyUnkownFrame(400) should not have passed isvalid()")

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()


class pySeqnoFrameTest(TestCase):
    'A SeqnoFrame is a frame wrapping an ordered pair for a sequence number'
    def test_constructor(self): 
        if DEBUG: print >>sys.stderr, "========================test_constructor(pySeqnoFrameTest)"
        pyf = pySeqnoFrame(500)
        self.assertEqual(pyf.frametype(), 500)
        self.assertTrue(pyf.isvalid(), 'pySeqnoFrame(500) did not pass isvalid()')
        pyf = pySeqnoFrame(501,(1,2))
        self.assertEqual(pyf.frametype(), 501)
        self.assertTrue(pyf.isvalid(), 'pySeqnoFrame(501) did not pass isvalid()')

    def test_reqid(self):
        'reqid is the request id of a sequence number'
        if DEBUG: print >>sys.stderr, "========================test_reqid(pySeqnoFrameTest)"
        pyf = pySeqnoFrame(502)
        pyf.setreqid(42)
        self.assertTrue(pyf.getreqid, 42)
        pyf.setreqid(43)
        self.assertTrue(pyf.getreqid, 43)

    def test_qid(self):
        'qid is analogous to a port - it is the id of a queue on the other side'
        if DEBUG: print >>sys.stderr, "========================test_qid(pySeqnoFrameTest)"
        pyf = pySeqnoFrame(503)
        pyf.setqid(6)
        self.assertTrue(pyf.getqid, 6)
        pyf.setqid(7)
        self.assertTrue(pyf.getqid, 7)

    def test_equal(self):
        'A bit of overkill, but nothing really wrong with it'
        if DEBUG: print >>sys.stderr, "========================test_equal(pySeqnoFrameTest)"
        seqFrame1 = pySeqnoFrame( 504, (1,1))
        seqFrame1b = pySeqnoFrame(505, (1,1))
        seqFrame2 = pySeqnoFrame( 506, (1,2))
        seqFrame3 = pySeqnoFrame( 507, (2,1))
        seqFrame4 = pySeqnoFrame( 508, (2,2))
        seqFrame4b = pySeqnoFrame(509, (2,2))
        self.assertTrue(seqFrame1  == seqFrame1)
        self.assertTrue(seqFrame1  == seqFrame1b)
        self.assertTrue(seqFrame1b == seqFrame1)
        self.assertFalse(seqFrame1 == seqFrame2)
        self.assertFalse(seqFrame1 == seqFrame3)
        self.assertFalse(seqFrame1 == seqFrame4)
        self.assertFalse(seqFrame1 == seqFrame4b)
        self.assertFalse(seqFrame2  == seqFrame1)
        self.assertFalse(seqFrame2  == seqFrame1b)
        self.assertFalse(seqFrame2 == seqFrame1)
        self.assertTrue (seqFrame2 == seqFrame2)
        self.assertFalse(seqFrame2 == seqFrame3)
        self.assertFalse(seqFrame2 == seqFrame4)
        self.assertFalse(seqFrame1 == seqFrame4b)
        self.assertFalse(seqFrame3  == seqFrame1)
        self.assertFalse(seqFrame3  == seqFrame1b)
        self.assertFalse(seqFrame3 == seqFrame1)
        self.assertFalse(seqFrame3 == seqFrame2)
        self.assertTrue (seqFrame3 == seqFrame3)
        self.assertFalse(seqFrame3 == seqFrame4)
        self.assertFalse(seqFrame3 == seqFrame4b)
        self.assertFalse(seqFrame4  == seqFrame1)
        self.assertFalse(seqFrame4  == seqFrame1b)
        self.assertFalse(seqFrame4 == seqFrame1)
        self.assertFalse(seqFrame4 == seqFrame2)
        self.assertFalse(seqFrame4 == seqFrame3)
        self.assertTrue (seqFrame4 == seqFrame4)
        self.assertTrue (seqFrame4 == seqFrame4b)
        self.assertTrue(seqFrame4b == seqFrame4)

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()


class pyCstringFrameTest(TestCase):
    '''A CstringFrame is a frame which can only hold NUL-terminated C strings.
       The last byte must be the one and only NUL character in a CstringFrame value.'''
    def test_constructor(self): 
        if DEBUG: print >>sys.stderr, "========================test_constructor(pyCstringFrameTest)"
        pyf = pyCstringFrame(600, "Hello, World.")
        self.assertTrue(pyf.isvalid())
        self.assertEqual(str(pyf), '600: CstringFrame(600, "Hello, World.")')
        pyf2 = pyCstringFrame(601)
        self.assertFalse(pyf2.isvalid())
        pyf2.setvalue("42")
        self.assertTrue(pyf2.isvalid())
        self.assertEqual(str(pyf2), '601: CstringFrame(601, "42")')

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

class pySignFrameTest(TestCase):
    'A SignFrame is a digital signature frame.'
    def test_constructor(self): 
        if DEBUG: print >>sys.stderr, "========================test_constructor(pySignFrameTest)"
        pyf = pySignFrame(1) # the 1 determines the type of digital signature
        self.assertTrue(pyf.isvalid())
        self.assertRaises(ValueError, pySignFrame, 935) # Just a random invalid signature type

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()


class pyFrameSetTest(TestCase):
    'A FrameSet is a collection of frames - typically to be sent over the wire'

    @staticmethod
    def cmpstring(frame):
        s=str(frame)
        s = re.sub(' at 0x[^{}]*', ' at 0xsomewhere', s)
        s = re.sub(' address=0x[^{}]*', ' address=0xsomewhere', s)
        return s

    def test_constructor(self): 
        if DEBUG: print >>sys.stderr, "========================test_constructor(pyFrameSetTest)"
        pyf = pyFrameSet(700) # The 700 is the frameset (message) type
        self.assertEqual(pyf.get_framesettype(), 700)

    def test_flags(self): 
        if DEBUG: print >>sys.stderr, "========================test_flags(pyFrameSetTest)"
        'Flags are bit masks, to be turned on or off. They are 16-bits only.'
        pyf = pyFrameSet(701)
        self.assertEqual(pyf.get_flags(), 0x00)
        pyf.set_flags(0x01)
        self.assertEqual(pyf.get_flags(), 0x01)
        pyf.set_flags(0x01)
        self.assertEqual(pyf.get_flags(), 0x01)
        pyf.set_flags(0x02)
        self.assertEqual(pyf.get_flags(), 0x03)
        pyf.clear_flags(0x01)
        self.assertEqual(pyf.get_flags(), 0x02)
        pyf.set_flags(0x0fffffffffffffffff)
        self.assertEqual(pyf.get_flags(), 0x0ffff)
        pyf.clear_flags(0x5555)
        self.assertEqual(pyf.get_flags(), 0x0AAAA)

    def test_buildlistforward(self):
        'Build a FrameSet using append and verify that it gets built right'
        if DEBUG: print >>sys.stderr, "========================test_buildlistforward(pyFrameSetTest)"
        pyfs = pyFrameSet(702)
        sign = pySignFrame(1) # digital signature frame
        flist = (pyFrame(703), pyAddrFrame(704, (42,42,42,42)), pyIntFrame(705,42),
                 pyCstringFrame(706, "HhGttG"),
                 pySeqnoFrame(707, (42, 424242424242)),
                 pyIpPortFrame(200, (1,2,3,4), 1984),
                 pyIpPortFrame(202, (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16), 1984)
                 )
        for frame in flist:
            pyfs.append(frame)
        self.assertEqual(len(pyfs), 7)
        #pyfs.dump()
        ylist = []
        # The iter member function is a generator.  I love it.
        # It goes to a lot of trouble to wrap the underlying C Classes with Python classes.
        for frame in pyfs.iter():
            ylist.append(frame)
        for i in range(0,len(ylist)):
           f=flist[i]
           y=ylist[i]
           # This isn't exhaustive, but it isn't bad.
           self.assertEqual(f.frametype(), y.frametype())
           self.assertEqual(type(f), type(y))
           self.assertEqual(str(f), str(y))
        # Constructing the packet will add a signature frame at the beginning
        # and an END (type 0) frame at the end
        pyfs.construct_packet(sign)
        # So we do it over again to make sure everything still looks OK
        ylist = []
        for frame in pyfs.iter():
            ylist.append(frame)
        self.assertEqual(len(pyfs), 9)
        self.assertEqual(len(ylist), len(pyfs)) # len(pyfs) traverses the linked list
        for i in range(0,len(flist)):
           f=flist[i]
           y=ylist[i+1]
           # This isn't exhaustive, but it isn't bad.
           self.assertEqual(f.frametype(), y.frametype())
           self.assertEqual(type(f), type(y))
        # Check on our automatically added frames.
        self.assertEqual(ylist[0].frametype(), 1)
        self.assertEqual(ylist[8].frametype(), 0)
        
    def test_buildlistbackwards(self):
        '''Build a FrameSet using prepend and verify that it gets built right.
           Similar to the append testing above, but backwards ;-)'''
        if DEBUG: print >>sys.stderr, "========================test_buildlistbackwards(pyFrameSetTest)"
        pyfs = pyFrameSet(707)
        sign = pySignFrame(1)
        flist = (pyFrame(708), pyAddrFrame(709, (42,42,42,42)), pyIntFrame(710,42), pyCstringFrame(711, "HhGttG"),
                 pySeqnoFrame(712, (42, 424242424242)))
        for frame in flist:
            pyfs.prepend(frame)
        self.assertEqual(len(pyfs), 5)
        #pyfs.dump()
        ylist = []
        for frame in pyfs.iter():
            ylist.append(frame)
        for i in range(0,len(flist)):
            f=flist[i]
            y=ylist[4-i]
            # This isn't exhaustive, but it isn't bad.
            self.assertEqual(f.frametype(), y.frametype())
            self.assertEqual(type(f), type(y))
            self.assertEqual(f.__class__, y.__class__)
            if DEBUG: print >>sys.stderr, "Classes are", f.__class__, "lens are", f.framelen(), y.framelen()
            self.assertEqual(f.framelen(), y.framelen())

    def test_buildpacket(self):
        'Build a FrameSet, then make it into a packet, and make a frameset list out of the packet'
        if DEBUG: print >>sys.stderr, "========================test_buildpacket(pyFrameSetTest)"
        pyfs = pyFrameSet(801)
        sign = pySignFrame(1) # digital signature frame
        flist = (pyAddrFrame(FrameTypes.IPADDR, (42,42,42,42)), pyIntFrame(FrameTypes.WALLCLOCK,42), pyCstringFrame(FrameTypes.INTERFACE, "HhGttG"),
                 pyIntFrame(FrameTypes.CINTVAL,3000000, intbytes=4),
                 pyIntFrame(FrameTypes.CINTVAL,3000000000000, intbytes=8),
                 pySeqnoFrame(FrameTypes.REQID, (42, 424242424242)),
                 pyIpPortFrame(FrameTypes.IPPORT, (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16), 1984),
                 pyIntFrame(FrameTypes.CINTVAL,4242, intbytes=3))
        if DEBUG: print >>sys.stderr, "flist:", flist
        decoder = pyPacketDecoder()
        for frame in flist:
            pyfs.append(frame)
        pyfs.construct_packet(sign)
        if DEBUG: print >>sys.stderr, "packet constructed"
        xlist=[]
        for frame in pyfs.iter():
            xlist.append(frame)
        if DEBUG: print >>sys.stderr, "xlist constructed"
        pktdata = pyfs.getpacket()
        if DEBUG: print >>sys.stderr, "getpacket done", pktdata
        cp_pyfs = decoder.fslist_from_pktdata(pktdata)
        if DEBUG: print >>sys.stderr, "decoder done", cp_pyfs
        fs0 = cp_pyfs[0]
        ylist=[]
        for frame in fs0.iter():
            ylist.append(frame)
        for i in range(0,len(xlist)):
            x=xlist[i]
            y=ylist[i]
            self.assertEqual(x.frametype(), y.frametype())
            self.assertEqual(x.framelen(),  y.framelen())
            self.assertEqual(x.dataspace(), y.dataspace())
            self.assertEqual(type(x), type(y))
            self.assertEqual(x.__class__, y.__class__)
            # Not all our classes have a __str__ method defined.
            strx = re.sub(str(x), ' instance at .*>', ' instance at -somewhere- >')
            stry = re.sub(str(y), ' instance at .*>', ' instance at -somewhere- >')
            self.assertEqual(strx, stry)
            self.assertEqual(pyFrameSetTest.cmpstring(x), pyFrameSetTest.cmpstring(y))


    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

class pyConfigContextTest(TestCase):

    def test_constructor(self):
        if DEBUG: print >>sys.stderr, "===============test_constructor(pyConfigContextTest)"
        pyConfigContext()
        foo = pyConfigContext(init={'int1': 42, 'str1': 'forty-two', 'bar': pyNetAddr((1,2,3,4),) })
        foo = pyConfigContext(init={'int1': 42, 'str1': 'forty-two', 'bar': pyNetAddr((1,2,3,4),), 'csf': pyCstringFrame(42, '41+1')})
        self.assertEqual(foo.getint('int1'), 42)
        self.assertEqual(foo.getstring('str1'), 'forty-two')
        self.assertRaises(IndexError, foo.getaddr, ('int1'))
        self.assertRaises(IndexError, foo.getstring, ('int1'))
        self.assertRaises(IndexError, foo.getaddr, ('str1'))
        self.assertRaises(IndexError, foo.getframe, ('str1'))
        self.assertRaises(IndexError, foo.getframe, ('int1'))
        self.assertEqual(foo['int1'], 42)
        self.assertEqual(foo['str1'], 'forty-two')
        self.assertEqual(foo.getint('fred'), -1)
        foo['bar']
        self.assertEqual(foo['bar'], pyNetAddr((1,2,3,4),))
        self.assertEqual(str(foo['bar']), '1.2.3.4')
        self.assertEqual(str(foo['csf']), '42: CstringFrame(42, "41+1")')
        self.assertEqual(str(foo), '{"bar":"1.2.3.4","csf":"CstringFrame(42, \\"41+1\\")","int1":42,"str1":"forty-two"}')

        foo['isf'] = pyIntFrame(310, initval=42, intbytes=3)
        if DEBUG: print >>sys.stderr, "test_constructor.18(pyConfigContextTest)"
        self.assertEqual(str(foo),
        	'{"bar":"1.2.3.4","csf":"CstringFrame(42, \\"41+1\\")","int1":42,"isf":"IntFrame(310, 3, 42)","str1":"forty-two"}')
        if DEBUG: print >>sys.stderr, "test_constructor.19(pyConfigContextTest)"

    def test_string(self):
        if DEBUG: print >>sys.stderr, "test_string(pyConfigContextTest)"
        foo = pyConfigContext()
        foo['arthur'] = 'dent'
        foo['seven'] = 'ofnine'
        foo['JeanLuc'] = 'Picard'
        foo['important'] = 'towel'
        foo['integer'] = 42
        self.assertEqual(foo['arthur'], 'dent')
        self.assertEqual(foo['seven'], 'ofnine')
        self.assertEqual(foo['JeanLuc'], 'Picard')
        self.assertEqual(foo['important'], 'towel')
        self.assertRaises(IndexError, foo.getstring, ('towel'))
        self.assertEqual(str(foo), '{"JeanLuc":"Picard","arthur":"dent","important":"towel","integer":42,"seven":"ofnine"}')
        foo['seven'] = '7'
        self.assertEqual(foo['seven'], '7')
        self.assertEqual(type(foo['seven']), str)
        foo['JeanLuc'] = 'Locutus'
        self.assertEqual(foo['JeanLuc'], 'Locutus')
        self.assertEqual(str(foo), '{"JeanLuc":"Locutus","arthur":"dent","important":"towel","integer":42,"seven":"7"}')

    def test_int(self):
        if DEBUG: print >>sys.stderr, "test_int(pyConfigContextTest)"
        foo = pyConfigContext()
        foo['arthur'] = 42
        foo['seven'] = 9
        self.assertEqual(foo['arthur'], 42)
        self.assertEqual(foo['seven'], 9)
        self.assertEqual(str(foo), '{"arthur":42,"seven":9}')
        foo['seven'] = 7
        foo['negseven'] = -9
        self.assertTrue(isinstance(foo['seven'], (int, long)))
        self.assertEqual(foo["seven"], 7)
        self.assertEqual(foo["negseven"], -9)
        self.assertEqual(str(foo), '{"arthur":42,"negseven":-9,"seven":7}')
        foo['plusfloat'] = 42.42
        foo['negfloat'] = -42.42
        bar = pyConfigContext('{"arthur":42,"negseven":-9,"seven":7, "plusfloat":42.42, "negfloat": -42.42 }')
        self.assertEqual(str(bar), '{"arthur":42,"negfloat":-42.42,"negseven":-9,"plusfloat":42.42,"seven":7}')
        self.assertEqual(str(foo), str(bar))

    def test_child_ConfigContext(self):
        if DEBUG: print >>sys.stderr, "========================test_child_ConfigContext(pyConfigContextTest)"
        foo = pyConfigContext()
        foo['ford'] = 'prefect'
        baz = pyConfigContext()
        baz['Kathryn'] = 'Janeway'
        baz['there\'s no place like'] = pyNetAddr((127,0,0,1),)
        bar = pyConfigContext()
        bar['hhgttg'] = foo
        bar['voyager'] = baz
        if DEBUG: print >>sys.stderr, "EQUAL TEST"
        self.assertEqual(str(bar), '{"hhgttg":{"ford":"prefect"},"voyager":{"Kathryn":"Janeway","there\'s no place like":"127.0.0.1"}}')
        # We make a new pyConfigContext object from the str() of another one.  Cool!
        if DEBUG: print >>sys.stderr, "JSON TEST"
        bar2 = pyConfigContext(str(bar))
        if DEBUG: print >>sys.stderr, "JSON COMPARE"
        self.assertEqual(str(bar), str(bar2))
        self.assertEqual(bar["voyager"]["Kathryn"], "Janeway")
        self.assertEqual(bar["hhgttg"]["ford"], "prefect")
        self.assertEqual(bar2["voyager"]["Kathryn"], "Janeway")
        self.assertEqual(bar2["hhgttg"]["ford"], "prefect")
        if DEBUG: print >>sys.stderr, "COMPARE DONE"
        #	However... The pyNetAddr() was turned into a mere string :-( - at least for the moment... Sigh...
        if DEBUG: print >>sys.stderr, "END OF ========================test_child_ConfigContext(pyConfigContextTest)"


    def test_keys(self):
        if DEBUG: print >>sys.stderr, "===============test_keys(pyConfigContextTest)"
        foo = pyConfigContext()
        foo['arthur'] = 'dent'
        foo['seven'] = 'ofnine'
        foo['JeanLuc'] = 'Picard'
        foo['important'] = 'towel'
        foo['integer'] = 42
        self.assertEqual(str(foo.keys()), "['JeanLuc', 'arthur', 'important', 'integer', 'seven']")

    def test_ConfigContext_array(self):
        if DEBUG: print >>sys.stderr, "===============textConfigContext_array(pyConfigContextTest)"
        array1str = '{"a":[1,2,3,4,"a",{"b":true},[5,6,7,8,3.14]]}'
        array1config = pyConfigContext(array1str)
        self.assertEqual(array1str, str(array1config))

    def test_ConfigContext_array_with_netaddr(self):
        'This problem actually occurred - hence the test case...'
        if DEBUG: print >>sys.stderr, "===============textConfigContext_array_with_netaddr(pyConfigContextTest)"
        array1str = '{"a":["1.2.3.4",1,2,3,4,"a",{"b":true},[5,6,7,8,3.14,"10.10.10.1"],"::1"]}'
        array1str = '{"a":["1.2.3.4"]}'
        array1config = pyConfigContext(array1str)
        #foo = array1config['a']
        self.assertEqual(array1str, str(array1config))

    def test_kitchen_sink(self):
        if DEBUG:
            print >> sys.stderr, "===============testConfigContext_kitchen_sink(pyConfigContextTest)"
            for j in range(1,5):
                proj_class_incr_debug('NetAddr')
        strings = [
                    # The next two originally failed intermittently
                    '{"a":["1.2.3.4"]}',
                    '{"cmdline":["192.168.122.1"]}',
                    # All the remaining ones originally failed pretty reliably...
                    '{"cmdline":["/usr/sbin/dnsmasq","-u","libvirt-dnsmasq","--strict-order","--bind-interfaces","--pid-file=/var/run/libvirt/network/default.pid","--conf-file=","--except-interface","lo","--listen-address","192.168.122.1"]}',
                    '{"cmdline":["--listen-address","192.168.122.1"]}',
                    '{"cmdline":["/usr/sbin/dnsmasq","-u","libvirt-dnsmasq","--strict-order","--bind-interfaces","--pid-file=/var/run/libvirt/network/default.pid","--conf-file=","--except-interface","lo","--listen-address","192.168.122.1","--dhcp-range","192.168.122.2,192.168.122.254","--dhcp-leasefile=/var/lib/libvirt/dnsmasq/default.leases","--dhcp-lease-max=253","--dhcp-no-override" ]}',
                    '{"cmdline":["--listen-address","192.168.122.1","--dhcp-range","192.168.122.2,192.168.122.254","--dhcp-leasefile=/var/lib/libvirt/dnsmasq/default.leases","--dhcp-lease-max=253","--dhcp-no-override" ]}',
                    '{"cmdline":["--listen-address","192.168.122.1","--dhcp-range"]}',
                    '{"cmdline":["192.168.122.1","--dhcp-range"]}',
                    '{"cmdline":["192.168.122.1","anything"]}',
                    '{"cmdline":["192.168.122.1",1]}',
                    '{"cmdline":["192.168.122.1",false]}',
                  ]
        for s in strings:
            if DEBUG: print >>sys.stderr, ('Creating pyConfigContext("%s")' % s)
            sc = pyConfigContext(s)
            if DEBUG: print >>sys.stderr, ('sc.keys() == %s' % sc.keys())
            for key in sc.keys():
                elemcount=0
                if DEBUG: print >>sys.stderr, ('Looking at key %s: sc[key] = %s' % (key, sc[key]))
                for elem in sc[key]:
                    if DEBUG: print >>sys.stderr, ('Looking at element %s' % str(elem))
                    self.assertNotEqual(str(elem), "")
                    if isinstance(elem, pyAssimObj):
                        if DEBUG: print '++++++++++++++++++ REFCOUNT(%s): %d' % (str(elem), elem.refcount())
                        #CCref(elem._Cstruct)
                        self.assertEqual(elem.refcount(), 2)
                        if DEBUG:
                            gc.collect()
                            print >>sys.stderr, ":::::::::::::GC GARBAGE: %s" % gc.garbage
                        foo=elem._Cstruct[0]
                        while (hasattr(foo, 'baseclass')):
                            foo=foo.baseclass
                        if DEBUG:
                            print >>sys.stderr, ":::::::::::::GC refcount %d, REFERRERS: %s" % (sys.getrefcount(elem), gc.get_referrers(elem))
                            print >>sys.stderr, ":::::::::::::FOO: %s" % foo
                        del elem
                        if DEBUG: print '++++++++++++++++++ REFCOUNT SECOND VERSE: %s' % (foo._refcount)

                elemcount += 1
        if DEBUG:
            for j in range(1,5):
                proj_class_decr_debug('NetAddr')

    def test_deepget(self):
        getstr = '{"a": {"b":"a.b", "c": "a.c"}, "d":{"e":{"f": "d.e.f"}}, "e":1}'
        cc = pyConfigContext(init=getstr)
        self.assertTrue(cc is not None)
        self.assertEqual(cc.deepget('e'), 1)
        self.assertEqual(cc.deepget('a.b'), 'a.b')
        self.assertEqual(cc.deepget('a.c'), 'a.c')
        self.assertEqual(cc.deepget('d.e.f'), 'd.e.f')
        self.assertTrue(cc.deepget('a.d', None) is None)
        self.assertTrue(cc.deepget('d.e.g', None) is None)

    def test_deepget_array(self):
        getstr = '{"a": ["b", "c", "d"]}'
        cc = pyConfigContext(init=getstr)
        self.assertTrue(cc is not None)
        self.assertEqual(cc.deepget('a[0]'), 'b')
        self.assertEqual(cc.deepget('a[-1]'), 'd')
        self.assertEqual(cc.deepget('a[-2]'), 'c')
        self.assertEqual(cc.deepget('a[-3]'), 'b')
        self.assertTrue(cc.deepget('a[-4]') is None)

        # Slightly more complicated things...
        getstr = '{"a": ["b", {"c": {"d":0, "e":1}}, "f"]}'
        cc = pyConfigContext(init=getstr)
        self.assertTrue(cc is not None)
        self.assertEqual(cc.deepget('a[1].c.d'), 0)
        self.assertTrue(isinstance(cc.deepget('a[1].c.d'), (int, long)))
        self.assertEqual(cc.deepget('a[1].c.e'), 1)
        self.assertTrue(isinstance(cc.deepget('a[1].c.e'), (int, long)))
        self.assertEqual(cc.deepget('a[-1]'), "f")
        self.assertEqual(cc.deepget('a[-3]'), "b")




    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

class pyNetIOudpTest(TestCase):

    def test_constructor(self):
        if DEBUG: print >>sys.stderr, "========================test_constructor(pyNetIOudpTest)"
        config = pyConfigContext(init={'outsig': pySignFrame(1)})
        io = pyNetIOudp(config, pyPacketDecoder())
        self.assertTrue(io.fileno() >  2)
        io.config = None

    def test_members(self):
        if DEBUG: print >>sys.stderr, "========================test_members(pyNetIOudpTest)"
        io = pyNetIOudp(pyConfigContext(init={'outsig': pySignFrame(1)}), pyPacketDecoder())
        self.assertTrue(io.getmaxpktsize() >  65000)
        self.assertTrue(io.getmaxpktsize() <  65535)
        io.setmaxpktsize(1500)
        self.assertEqual(io.getmaxpktsize(), 1500)
        # Does signframe really work?  Next statement seems to crash things
        #self.assertEqual(type(io.signframe()), type(pySignFrame(1)))
        io.config = None

    def test_send(self):
        if DEBUG: print >>sys.stderr, "========================test_send(pyNetIOudpTest)"
        home = pyNetAddr((127,0,0,1),1984)
        fs = pyFrameSet(801)
        flist = (pyAddrFrame(FrameTypes.IPADDR, (42,42,42,42)), pyIntFrame(FrameTypes.HBWARNTIME,42), pyCstringFrame(FrameTypes.HOSTNAME, "HhGttG"),
                 pyIntFrame(FrameTypes.PORTNUM,3000000, intbytes=4),
                 pyIntFrame(FrameTypes.HBINTERVAL,3000000000000, intbytes=8),
                 pySeqnoFrame(FrameTypes.REQID, (42, 424242424242)),
                 pyIntFrame(FrameTypes.CINTVAL,4242, intbytes=3))
        for frame in flist:
            fs.append(frame)
        io = pyNetIOudp(pyConfigContext(init={'outsig': pySignFrame(1)}), pyPacketDecoder())
        io.sendframesets(home, fs)
        io.sendframesets(home, (fs,fs,fs))
        io.config = None

    def test_receiveandsend(self):
        if DEBUG: print >>sys.stderr, "========================test_receiveandsend(pyNetIOudpTest)"
        home = pyNetAddr("::1", 1984)
        anyaddr = pyNetAddr("::",1984)
        fs = pyFrameSet(801)
        #flist = (pyIntFrame(7,42), pyCstringFrame(8, "HhGttG"),
        flist = (pyAddrFrame(FrameTypes.IPADDR, (42,42,42,42)), pyIntFrame(7,42), pyCstringFrame(8, "HhGttG"),
                 pyAddrFrame(FrameTypes.IPADDR,(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16)),
                 pyIntFrame(FrameTypes.HBINTERVAL,3000000, intbytes=4),
                 pyIntFrame(FrameTypes.HBDEADTIME,3000000000000, intbytes=8),
                 pySeqnoFrame(FrameTypes.REQID, (42, 424242424242)),
                 pyIntFrame(FrameTypes.PORTNUM,4242, intbytes=3))
        for frame in flist:
            fs.append(frame)
        io = pyNetIOudp(pyConfigContext(init={'outsig': pySignFrame(1)}), pyPacketDecoder())
        io.bindaddr(anyaddr)
        io.sendframesets(home, fs)		# Send a packet with a single frameset containing a bunch of frames
        (addr, framesetlist) = io.recvframesets()	# Receive a packet - with some framesets in it
        #print >>sys.stderr, 'ADDR: [%s] HOME: [%s]' % (addr, home)
        self.assertEqual(addr, home)
        self.assertEqual(len(framesetlist), 1)
        ylist = []
        for frame in framesetlist[0].iter():
            ylist.append(frame)
        self.assertEqual(len(flist), len(ylist)-2)
        for i in range(0,len(flist)):
           x=flist[i]
           y=ylist[i+1]
           self.assertEqual(x.frametype(), y.frametype())
           self.assertEqual(x.framelen(),  y.framelen())
           self.assertEqual(x.dataspace(), y.dataspace())
           self.assertEqual(type(x), type(y))
           self.assertEqual(x.__class__, y.__class__)
           self.assertEqual(pyFrameSetTest.cmpstring(x), pyFrameSetTest.cmpstring(y))
        io.config = None

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

if __name__ == "__main__":
    run()
