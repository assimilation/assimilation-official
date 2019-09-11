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
"""
Test code for PCAP parsing...
"""
import json
import sys
import os
import subprocess
import gc

sys.path.append("../cma")
sys.path.append("..")
from AssimCclasses import *

os.environ["G_MESSAGES_DEBUG"] = "all"
stderr = sys.stderr
WorstDanglingCount = 0
DEBUG = False
BROKENDNS = False
if "BROKENDNS" in os.environ:
    BROKENDNS = True

CheckForDanglingClasses = True
AssertOnDanglingClasses = True

if not CheckForDanglingClasses:
    print("WARNING: Memory Leak Detection disabled.", file=stderr)
elif not AssertOnDanglingClasses:
    print("WARNING: Memory Leak assertions disabled (detection still enabled).", file=stderr)


def assert_no_dangling_cclasses():
    """Make sure we don't have any dangling C class objects laying around..."""
    global CheckForDanglingClasses
    global WorstDanglingCount
    # sys._clear_type_cache()
    gc.collect()
    count = proj_class_live_object_count()
    # Avoid cluttering the output up with redundant messages...
    if count > WorstDanglingCount and CheckForDanglingClasses:
        WorstDanglingCount = count
        if AssertOnDanglingClasses:
            dump_c_objects()
            raise AssertionError("Dangling C-class objects - %d still around" % count)
        else:
            print("*****ERROR: Dangling C-class objects - %d still around" % count, file=stderr)


class TestCase(object):
    """"Base class for tests not that useful..."""

    @staticmethod
    def teardown_method(method):
        """Check for dangling C classes!"""
        print("__del__ CALL for %s" % str(method), file=stderr)
        assert_no_dangling_cclasses()


def findfile(f):
    """Find a file somewhere"""
    for first in (".", "..", "../..", "../../.."):
        for second in (
            ".",
            "pcap",
            "src/pcap",
            "root_of_source_tree/pcap",
            "root_of_binary_tree/pcap",
        ):
            if os.access(os.path.join(first, second, f), os.R_OK):
                return os.path.join(first, second, f)
    return f


def output_json(json_s):
    """run jsonlint on our JSON"""
    process = subprocess.Popen(("jsonlint", "-f"), stdin=subprocess.PIPE)
    process.communicate(str(json_s).encode("utf8"))
    process.wait()


def compare_json(f, lhs, rhs):
    """Compare two JSON strings"""
    # print('----> LHS', lhs, file=stderr)
    # print('----> RHS', rhs, file=stderr)
    lhs = json.dumps(json.loads(str(pyConfigContext(lhs))), indent=4, sort_keys=True)
    rhs = json.dumps(json.loads(str(pyConfigContext(rhs))), indent=4, sort_keys=True)
    if lhs == rhs:
        return True
    print(f"LHS:::::::::: {f}::{len(lhs)}")
    output_json(lhs)
    print(f"RHS::::::::::{len(rhs)}")
    output_json(rhs)
    print
    return False


class TestpySwitchDiscovery(TestCase):
    """A pyNetAddr is a network address of some kind... - let's test it"""

    @staticmethod
    def validate_switch_discovery(filename, pkt, pktend):
        """Make sure our switch discovery data looks OK"""
        packet_validation_count = 0
        for method in (is_valid_lldp_packet, is_valid_cdp_packet):
            if method(pkt, pktend):
                packet_validation_count += 1
        assert packet_validation_count == 1
        return pySwitchDiscovery.decode_discovery("me", "eth0", filename, "<now>", pkt, pktend)[
            "data"
        ]

    def test_switch_discovery(self):
        """Test swtich discovery parsing..."""
        discovery_files = (
            (
                "lldp.detailed.pcap",
                """{ 
  "ChassisId" : "00-01-30-f9-ad-a0",
  "ManagementAddress" : "00-01-30-f9-ad-a0",
  "ports" : { "1/1" : { 
          "autoneg_enabled" : false,
          "autoneg_supported" : true,
          "ConnectsToHost" : "me",
          "ConnectsToInterface" : "eth0",
          "duplex" : "half",
          "media" : "2 pair category 5 UTP",
          "mtu" : 1522,
          "PortDescription" : "Summit300-48-Port 1001",
          "PortId" : "1/1",
          "ppvid" : 0,
          "pp_vlan_capable" : false,
          "pp_vlan_enabled" : false,
          "pvid" : 488,
          "sourceMAC" : "00-01-30-f9-ad-a0",
          "speed" : 100,
          "vid" : 488,
          "vlan_name" : "v2-0488-03-0505"
        } },
  "SystemCapabilities" : { 
      "bridge" : true,
      "router" : true
    },
  "SystemDescription" : "Summit300-48 - Version 7.4e.1 (Build 5) by Release_Master 05/27/05 04:53:11",
  "SystemName" : "Summit300-48"
}""",
            ),
            (
                "lldpmed_civicloc.pcap",
                """{ 
  "ChassisId" : "00-13-21-57-ca-40",
  "ManagementAddress" : "15.255.122.148",
  "ports" : { "1" : { 
          "autoneg_enabled" : false,
          "autoneg_supported" : true,
          "ConnectsToHost" : "me",
          "ConnectsToInterface" : "eth0",
          "duplex" : "half",
          "media" : "2 pair category 5 UTP",
          "PortDescription" : "1",
          "PortId" : "1",
          "sourceMAC" : "00-13-21-57-ca-7f",
          "speed" : 100
        } },
  "SystemCapabilities" : { 
      "bridge" : true,
      "router" : false
    },
  "SystemDescription" : "ProCurve J8762A Switch 2600-8-PWR, revision H.08.89, ROM H.08.5X (/sw/code/build/fish(ts_08_5))",
  "SystemName" : "ProCurve Switch 2600-8-PWR"
}""",
            ),
            (
                "procurve.lldp.pcap",
                """{ 
  "ChassisId" : "00-25-61-94-32-40",
  "ports" : { "22" : { 
          "ConnectsToHost" : "me",
          "ConnectsToInterface" : "eth0",
          "PortDescription" : "22",
          "PortId" : "22",
          "sourceMAC" : "00-25-61-94-32-4a"
        } },
  "SystemName" : "ProCurve Switch 2824"
}""",
            ),
            (
                "cdp-BCM1100.pcap",
                """{ 
  "ChassisId" : "0060B9C14027",
  "ports" : {  },
  "SystemCapabilities" : [ "host" ],
  "SystemPlatform" : "BCM91100",
  "SystemVersion" : "BCM1100"
}""",
            ),
            (
                "cdp_v2_voice.pcap",
                """{ 
  "ChassisId" : "myswitch",
  "ManagementAddress" : "195.128.194.168",
  "ports" : { "FastEthernet0/1" : { 
          "CiscoUnTrustedPortCOS" : 0,
          "ConnectsToHost" : "me",
          "ConnectsToInterface" : "eth0",
          "duplex" : "full",
          "PortId" : "FastEthernet0/1",
          "sourceMAC" : "00-0b-be-18-9a-41",
          "VlanId" : 1
        } },
  "SystemAddress" : "195.128.194.168",
  "SystemCapabilities" : [ 
      "bridge",
      "igmp-filter"
    ],
  "SystemPlatform" : "cisco WS-C2950-12",
  "SystemVersion" : "Cisco Internetwork Operating System Software \nIOS (tm) C2950 Software (C2950-I6K2L2Q4-M), Version 12.1(22)EA14, RELEASE SOFTWARE (fc1)\nTechnical Support: http://www.cisco.com/techsupport\nCopyright (c) 1986-2010 by cisco Systems, Inc.\nCompiled Tue 26-Oct-10 10:35 by nburra",
  "VLANManagementDomain" : "MYDOMAIN"
}""",
            ),
            (
                "n0.eth2.cdp-2.pcap",
                """
{ 
  "ChassisId" : "csr706a.pbm.ihost.com",
  "ports" : { "GigabitEthernet1/0/4" : { 
          "CiscoUnTrustedPortCOS" : 0,
          "ConnectsToHost" : "me",
          "ConnectsToInterface" : "eth0",
          "duplex" : "full",
          "PortId" : "GigabitEthernet1/0/4",
          "sourceMAC" : "00-0f-23-b0-62-84",
          "VlanId" : 77
        } },
  "SystemAddress" : "194.129.40.0",
  "SystemCapabilities" : [ 
      "router",
      "bridge",
      "igmp-filter"
    ],
  "SystemPlatform" : "cisco WS-C3750G-24TS",
  "SystemVersion" : "Cisco Internetwork Operating System Software \nIOS (tm) C3750 Software (C3750-I5-M), Version 12.2(20)SE4, RELEASE SOFTWARE (fc1)\nCopyright (c) 1986-2005 by cisco Systems, Inc.\nCompiled Sun 09-Jan-05 00:09 by antonino",
  "VLANManagementDomain" : "spbm"
}""",
            ),
            (
                "cdp.pcap",
                """
{ 
  "ChassisId" : "R1",
  "ports" : { "Ethernet0" : { 
          "ConnectsToHost" : "me",
          "ConnectsToInterface" : "eth0",
          "PortId" : "Ethernet0",
          "sourceMAC" : "00-e0-1e-d5-d5-15"
        } },
  "SystemAddress" : "195.128.194.168",
  "SystemCapabilities" : [ "router" ],
  "SystemPlatform" : "cisco 1601",
  "SystemVersion" : "Cisco Internetwork Operating System Software \nIOS (tm) 1600 Software (C1600-NY-L), Version 11.2(12)P, RELEASE SOFTWARE (fc1)\nCopyright (c) 1986-1998 by cisco Systems, Inc.\nCompiled Tue 03-Mar-98 06:33 by dschwart"
}""",
            ),
            (
                "cdp_v2.pcap",
                """{ 
  "ChassisId" : "myswitch",
  "ManagementAddress" : "195.128.194.168",
  "ports" : { "FastEthernet0/1" : { 
          "CiscoUnTrustedPortCOS" : 0,
          "ConnectsToHost" : "me",
          "ConnectsToInterface" : "eth0",
          "duplex" : "full",
          "PortId" : "FastEthernet0/1",
          "sourceMAC" : "00-0b-be-18-9a-41",
          "VlanId" : 1
        } },
  "SystemAddress" : "195.128.194.168",
  "SystemCapabilities" : [ 
      "bridge",
      "igmp-filter"
    ],
  "SystemPlatform" : "cisco WS-C2950-12",
  "SystemVersion" : "Cisco Internetwork Operating System Software \nIOS (tm) C2950 Software (C2950-I6K2L2Q4-M), Version 12.1(22)EA14, RELEASE SOFTWARE (fc1)\nTechnical Support: http://www.cisco.com/techsupport\nCopyright (c) 1986-2010 by cisco Systems, Inc.\nCompiled Tue 26-Oct-10 10:35 by nburra",
  "VLANManagementDomain" : "MYDOMAIN"
}""",
            ),
        )
        for (f, out) in discovery_files:
            for pcap_entry in pyPcapCapture(findfile(f)):
                pktstart, pktend, pktlen = pcap_entry
                # print('Got %d bytes from %s' % (pktlen, f), file=stderr)
                # print('----> Got %d bytes from %s' % (pktlen, f), file=stderr)
                json_str = self.validate_switch_discovery(f, pktstart, pktend)
                # print('<---- Done processing %d bytes from %s' % (pktlen, f), file=stderr)
                assert compare_json(f, out, json_str)
                print(f"PCAP {f} appears to have passed", file=stderr)
        print("Passed %d switch discovery tests" % (len(discovery_files)))

    def not_a_test_output(self):
        """Not sure what this is..."""
        files = (
            "lldp.detailed.pcap",
            "lldpmed_civicloc.pcap",
            "procurve.lldp.pcap",
            "cdp-BCM1100.pcap",
            # 'pcap/cdp_v2_hdlc.pcap',
            "cdp_v2_voice.pcap",
            "n0.eth2.cdp-2.pcap",
            "cdp.pcap",
            "cdp_v2.pcap",
            # 'pcap/cdp_v2_voice_vlan.pcap'
        )
        for f in files:
            for pcap_entry in pyPcapCapture(findfile(f)):
                pktstart, pktend, pktlen = pcap_entry
                print("('%s','''" % f)
                sys.stdout.flush()
                output_json(self.validate_switch_discovery(f, pktstart, pktend))
                print("'''),")
                sys.stdout.flush()
