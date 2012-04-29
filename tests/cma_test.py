import sys
sys.path.append("../pyclasswrappers")
sys.path.append("../cma")
from testify import *
from testify.utils import turtle

from frameinfo import *
from AssimCclasses import *
import gc, sys, time, collections

CheckForDanglingClasses = True
WorstDanglingCount = 0
DEBUG=False

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

class TestIO(turtle.Turtle):
    def __init__(self, addrframesetpairs, sleepatend=0):
        if isinstance(addrframesetpairs, tuple):
            addrframesetpairs = list(addrframesetpairs)
        self.inframes = addrframesetpairs
        self.packetswritten=[]
        self.sleepatend=sleepatend
        turtle.Turtle.__init__(self)
        self.index=0

    def recvframesets(self):
        if self.index >= len(self.inframes):
            time.sleep(self.sleepatend)
            raise StopIteration('End of Packets')
        ret = self.inframes[self.index]
        self.index += 1
        return (ret,)

    def sendframesets(self, dest, fslist):
	if not isinstance(fslist, collections.Sequence):
            return self._sendaframeset(dest, fslist)
        for fs in fslist:
            self._sendaframeset(dest, fs)

    def _sendaframeset(self, dest, fslist):
        self.packetswritten.append((dest,fslist))
    

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
       framesets=((otherguy, strframe1),)
       io = TestIO(framesets, 0)
       gottenfs = io.recvframesets()
       self.assertEqual(gottenfs, framesets)
       self.assertRaises(StopIteration, io.recvframesets)

   def test_echo1pkt(self):
       'Read a packet and write it back out'
       strframe1=pyCstringFrame(FrameTypes.CSTRINGVAL, "Hello, world.")
       fs = pyFrameSet(42)
       fs.append(strframe1)
       otherguy = pyNetAddr([1,2,3,4],)
       framesets = ((otherguy, strframe1),)
       io = TestIO(framesets, 0)
       fslist = io.recvframesets()			# read in a packet
       self.assertEqual(len(fslist), 1)
       self.assertEqual(fslist, framesets)
       io.sendframesets(fslist[0][0], fslist[0][1])	# write it back out
       self.assertEqual(len(io.packetswritten), 1)
       self.assertEqual(len(io.packetswritten), len(framesets))
       self.assertRaises(StopIteration, io.recvframesets)

if __name__ == "__main__":
    run()
