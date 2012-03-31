import sys
sys.path.append("../pyclasswrappers")
from testify import *

from AssimCclasses import *
import gc
import re

CheckForDanglingClasses = True
WorstDanglingCount = 0

def assert_no_dangling_Cclasses():
    global CheckForDanglingClasses
    global WorstDanglingCount
    gc.collect()
    count =  proj_class_live_object_count()
    # Avoid cluttering the output up with redundant messages...
    if count > WorstDanglingCount and CheckForDanglingClasses:
        WorstDanglingCount = count
        proj_class_dump_live_objects()
        raise AssertionError, "Dangling C-class objects - %d still around" % count

class pyNetAddrTest(TestCase):
    "A pyNetAddr is a network address of some kind... - let's test it"
    def test_constructor(self): 
        ipv4 = pyNetAddr((1,2,3,4),)
        ipv4b = pyNetAddr((1,2,3,5),)
        mac48 = pyNetAddr((1,2,3,4,5,6),)
        mac64 = pyNetAddr( (1,2,3,4,5,6,7,8),)
        ipv6 = pyNetAddr((1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16),)
        self.assertEqual(str(ipv4), "1.2.3.4")
        self.assertEqual(str(ipv4b), "1.2.3.5")
        self.assertEqual(str(mac48), "01:02:03:04:05:06")
        self.assertEqual(str(mac64), "01:02:03:04:05:06:07:08")
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

    def test_ipv6_str(self): 
        'Test the str() function for ipv6 - worth a separate test.'
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

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

class pyFrameTest(TestCase):
    '''Frames are our basic superclass for things we put on the wire.
       This base class just has a generic binary blob with no special
       properties.  They are all valid (if they have a value)'''
    def test_constructor(self): 
        pyf = pyFrame(100)
        self.assertEqual(pyf.frametype(), 100)
        self.assertTrue(pyf.isvalid())

    def test_setvalue(self): 
        pyf = pyFrame(101)
        pyf.setvalue('fred')
        self.assertTrue(pyf.isvalid(), "PyFrame('fred') failed isvalid())")
        self.assertEqual(pyf.framelen(), 5)
        self.assertEqual(pyf.dataspace(), 9) # Total space for this Frame on the wire
        self.assertEqual(string_at(pyf.framevalue()), 'fred') # Raw from 'C'

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

class pyAddrFrameTest(TestCase):
    'An AddrFrame wraps a NetAddr for sending on the wire'
    def test_constructor(self): 
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

class pyIntFrameTest(TestCase):
    'An IntFrame wraps various sizes of unsigned integers for sending on the wire'
    def test_constructor(self): 
        # Test a variety of illegal/unsupported integer sizes
        for size in (5, 6, 7, 9, 10):
            self.assertRaises(ValueError, pyIntFrame, 300+size-1, intbytes=size)
        # Some network protocols have 3-byte integers.  So I implemented them.
        for size in (1, 2, 3, 4, 8):
            pyf = pyIntFrame(310+size, initval=42, intbytes=size)
            self.assertTrue(pyf.isvalid())
            self.assertEqual(pyf.intlength(), size)
            self.assertEqual(int(pyf), 42)
            self.assertEqual(str(pyf), '42')

    def test_set(self): 
        'Test setting integer values for all the size integers'
        for size in (1, 2, 3, 4, 8):
            pyf = pyIntFrame(320, initval=0, intbytes=size)
            val = 42 + size
            pyf.setint(val)
            self.assertEqual(int(pyf), val)
            self.assertEqual(str(pyf), str(val))
        

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

class pyUnknownFrameTest(TestCase):
    "An unknown frame is one we don't recognize the type of."
    def test_constructor(self): 
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
        pyf = pySeqnoFrame(500)
        self.assertEqual(pyf.frametype(), 500)
        self.assertTrue(pyf.isvalid(), 'pySeqnoFrame(500) did not pass isvalid()')
        pyf = pySeqnoFrame(501,(1,2))
        self.assertEqual(pyf.frametype(), 501)
        self.assertTrue(pyf.isvalid(), 'pySeqnoFrame(501) did not pass isvalid()')

    def test_reqid(self):
        'reqid is the request id of a sequence number'
        pyf = pySeqnoFrame(502)
        pyf.setreqid(42)
        self.assertTrue(pyf.getreqid, 42)
        pyf.setreqid(43)
        self.assertTrue(pyf.getreqid, 43)

    def test_qid(self):
        'qid is analogous to a port - it is the id of a queue on the other side'
        pyf = pySeqnoFrame(503)
        pyf.setqid(6)
        self.assertTrue(pyf.getqid, 6)
        pyf.setqid(7)
        self.assertTrue(pyf.getqid, 7)

    def test_equal(self):
        'A bit of overkill, but nothing really wrong with it'
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
        pyf = pyCstringFrame(600, "Hello, World.")
        self.assertTrue(pyf.isvalid())
        self.assertEqual(str(pyf), 'CstringFrame(600, "Hello, World.")')
        pyf2 = pyCstringFrame(601)
        self.assertFalse(pyf2.isvalid())
        pyf2.setvalue("42")
        self.assertTrue(pyf2.isvalid())
        self.assertEqual(str(pyf2), 'CstringFrame(601, "42")')

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

class pySignFrameTest(TestCase):
    'A SignFrame is a digital signature frame.'
    def test_constructor(self): 
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
        return s

    def test_constructor(self): 
        pyf = pyFrameSet(700) # The 700 is the frameset (message) type
        self.assertEqual(pyf.get_framesettype(), 700)

    def test_flags(self): 
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
        pyfs = pyFrameSet(702)
        sign = pySignFrame(1) # digital signature frame
        flist = (pyFrame(703), pyAddrFrame(704, (42,42,42,42)), pyIntFrame(705,42), pyCstringFrame(706, "HhGttG"),
                 pySeqnoFrame(707, (42, 424242424242)))
        for frame in flist:
            pyfs.append(frame)
        self.assertEqual(len(pyfs), 5)
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
        # Constructing the packet will add a signature frame at the beginning
	# and an END (type 0) frame at the end
        pyfs.construct_packet(sign)
        # So we do it over again to make sure everything still looks OK
        ylist = []
        for frame in pyfs.iter():
            ylist.append(frame)
        self.assertEqual(len(pyfs), 7)
        self.assertEqual(len(ylist), len(pyfs)) # len(pyfs) traverses the linked list
        for i in range(0,len(flist)):
           f=flist[i]
           y=ylist[i+1]
           # This isn't exhaustive, but it isn't bad.
           self.assertEqual(f.frametype(), y.frametype())
           self.assertEqual(type(f), type(y))
        # Check on our automatically added frames.
        self.assertEqual(ylist[0].frametype(), 1)
        self.assertEqual(ylist[6].frametype(), 0)
        
    def test_buildlistbackwards(self):
        '''Build a FrameSet using prepend and verify that it gets built right.
           Similar to the append testing above, but backwards ;-)'''
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

    def test_buildpacket(self):
        'Build a FrameSet, then make it into a packet, and make a frameset list out of the packet'
        pyfs = pyFrameSet(801)
        sign = pySignFrame(1) # digital signature frame
        flist = (pyAddrFrame(9, (42,42,42,42)), pyIntFrame(7,42), pyCstringFrame(8, "HhGttG"),
                 pyIntFrame(11,3000000, intbytes=4),
                 pyIntFrame(12,3000000000000, intbytes=8),
                 pySeqnoFrame(5, (42, 424242424242)),
                 pyIntFrame(11,4242, intbytes=3))
        decoder = pyPacketDecoder(0)
        for frame in flist:
            pyfs.append(frame)
        pyfs.construct_packet(sign)
        xlist=[]
        for frame in pyfs.iter():
            xlist.append(frame)
        pktdata = pyfs.getpacket()
        cp_pyfs = decoder.fslist_from_pktdata(pktdata)
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
        pyConfigContext()
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
        self.assertEqual(str(foo['bar']), '1.2.3.4')
        self.assertEqual(foo['bar'], pyNetAddr((1,2,3,4),))
        self.assertEqual(str(foo['csf']), 'CstringFrame(42, "41+1")')
        self.assertEqual(foo['csf'].__class__, pyCstringFrame(1).__class__)

    def test_string(self):
        foo = pyConfigContext()
        foo['arthur'] = 'dent'
        foo['seven'] = 'ofnine'
        foo['JeanLuc'] = 'Picard'
        foo['important'] = 'towel'
        self.assertEqual(foo['arthur'], 'dent')
        self.assertEqual(foo['seven'], 'ofnine')
        self.assertEqual(foo['JeanLuc'], 'Picard')
        self.assertEqual(foo['important'], 'towel')
        self.assertRaises(IndexError, foo.getstring, ('towel'))
        foo['seven'] = '7'
        self.assertEqual(foo['seven'], '7')
        self.assertEqual(type(foo['seven']), str)
        foo['JeanLuc'] = 'Locutus'
        self.assertEqual(foo['JeanLuc'], 'Locutus')

    def test_int(self):
        foo = pyConfigContext()
        foo['arthur'] = 42
        foo['seven'] = 9
        self.assertEqual(foo['arthur'], 42)
        self.assertEqual(foo['seven'], 9)
        foo['seven'] = 7
        self.assertEqual(type(foo['seven']), int)
        self.assertEqual(foo["seven"], 7)
        

    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

if __name__ == "__main__":
    run()
