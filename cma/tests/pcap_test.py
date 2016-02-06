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
_suites = ['all']
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
CheckForDanglingClasses = False
AssertOnDanglingClasses = True

if not CheckForDanglingClasses:
    print >> sys.stderr, 'WARNING: Memory Leak Detection disabled.'
elif not AssertOnDanglingClasses:
    print >> sys.stderr, 'WARNING: Memory Leak assertions disabled (detection still enabled).'

def assert_no_dangling_Cclasses():
    global CheckForDanglingClasses
    global WorstDanglingCount
    sys._clear_type_cache()
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



    def test_lldp(self): 
        lldp_files = (
                '../pcap/lldp.detailed.pcap',
                '../pcap/lldpmed_civicloc.pcap',
                '../pcap/procurve.lldp.pcap')
        return
        for f in lldp_files:
            for pcap_entry in pyPcapCapture(f):
                pktstart, pktend, pktlen = pcap_entry
                print 'Got %d bytes from %s' % (pktlen, f)
                print pySwitchDiscovery._decode_lldp('me', 'eth0', f, '<now>', pktstart, pktend)

    def test_cdp(self): 
        cdp_files = (
        ('../pcap/cdp-BCM1100.pcap', '{"ChassisId":"0060B9C14027","SystemCapabilities":["host"],"SystemPlatform":"BCM91100","SystemVersion":"BCM1100","ports":{}}'),
        #('../pcap/cdp_v2_hdlc.pcap', ''),
        ('../pcap/cdp_v2_voice.pcap', r'{"ChassisId":"myswitch","ManagementAddress":"192.168.0.4","SystemAddress":"192.168.0.4","SystemCapabilities":["bridge","igmp-filter"],"SystemPlatform":"cisco WS-C2950-12","SystemVersion":"Cisco Internetwork Operating System Software \nIOS (tm) C2950 Software (C2950-I6K2L2Q4-M), Version 12.1(22)EA14, RELEASE SOFTWARE (fc1)\nTechnical Support: http://www.cisco.com/techsupport\nCopyright (c) 1986-2010 by cisco Systems, Inc.\nCompiled Tue 26-Oct-10 10:35 by nburra","VLANManagementDomain":"MYDOMAIN","ports":{"FastEthernet0/1":{"ConnectsToHost":"me","ConnectsToInterface":"eth0","PortId":"FastEthernet0/1","duplex":"full","sourceMAC":"00-0b-be-18-9a-41"}}}'),
        ('../pcap/n0.eth2.cdp-2.pcap', r'{"ChassisId":"csr706a.pbm.ihost.com","SystemAddress":"129.40.0.4","SystemCapabilities":["router","bridge","igmp-filter"],"SystemPlatform":"cisco WS-C3750G-24TS","SystemVersion":"Cisco Internetwork Operating System Software \nIOS (tm) C3750 Software (C3750-I5-M), Version 12.2(20)SE4, RELEASE SOFTWARE (fc1)\nCopyright (c) 1986-2005 by cisco Systems, Inc.\nCompiled Sun 09-Jan-05 00:09 by antonino","VLANManagementDomain":"spbm","ports":{"GigabitEthernet1/0/4":{"ConnectsToHost":"me","ConnectsToInterface":"eth0","PortId":"GigabitEthernet1/0/4","duplex":"full","sourceMAC":"00-0f-23-b0-62-84"}}}'),
        ('../pcap/cdp.pcap', r'{"ChassisId":"R1","SystemAddress":"192.168.0.4","SystemCapabilities":["router"],"SystemPlatform":"cisco 1601 (fc","SystemVersion":"Cisco Internetwork Operating System Software \nIOS (tm) 1600 Software (C1600-NY-L), Version 11.2(12)P, RELEASE SOFTWARE (fc1)\nCopyright (c) 1986-1998 by cisco Systems, Inc.\nCompiled Tue 03-Mar-98 06:33 by dschwart","ports":{"Ethernet0":{"ConnectsToHost":"me","ConnectsToInterface":"eth0","PortId":"Ethernet0","sourceMAC":"00-e0-1e-d5-d5-15"}}}'),
        ('../pcap/cdp_v2.pcap', r'{"ChassisId":"myswitch","ManagementAddress":"192.168.0.4","SystemAddress":"192.168.0.4","SystemCapabilities":["bridge","igmp-filter"],"SystemPlatform":"cisco WS-C2950-12","SystemVersion":"Cisco Internetwork Operating System Software \nIOS (tm) C2950 Software (C2950-I6K2L2Q4-M), Version 12.1(22)EA14, RELEASE SOFTWARE (fc1)\nTechnical Support: http://www.cisco.com/techsupport\nCopyright (c) 1986-2010 by cisco Systems, Inc.\nCompiled Tue 26-Oct-10 10:35 by nburra","VLANManagementDomain":"MYDOMAIN","ports":{"FastEthernet0/1":{"ConnectsToHost":"me","ConnectsToInterface":"eth0","PortId":"FastEthernet0/1","duplex":"full","sourceMAC":"00-0b-be-18-9a-41"}}}'),
        #('../pcap/cdp_v2_voice_vlan.pcap', '')
        )
        for (f, out) in cdp_files:
            for pcap_entry in pyPcapCapture(f):
                pktstart, pktend, pktlen = pcap_entry
                #print >> sys.stderr, 'Got %d bytes from %s' % (pktlen, f)
                json = pySwitchDiscovery._decode_cdp('me', 'eth0', f, '<now>', pktstart, pktend)['data']
                #print >> sys.stderr, 'OUT :', out
                #print >> sys.stderr, 'JSON:', str(json)
                assert out == str(json)



    @class_teardown
    def tearDown(self):
        assert_no_dangling_Cclasses()

if __name__ == "__main__":
    run()
