#!/usr/bin/python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2013 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community - http://assimproj.org
# Paid support is available from Assimilation Systems Limited - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#

'''
Discovery Listener infrastructure
This is the base class for code that wants to hear about various
discovery packets as they arrive.

More details are documented in the DiscoveryListener class
'''
import sys
from droneinfo import Drone
from assimjson import JSONtree

from discoverylistener import DiscoveryListener

@Drone.add_json_processor
class TCPDiscoveryChecksumGenerator(DiscoveryListener):
    'Class for generating checksums based on the content of tcpdiscovery packets'
    prio = DiscoveryListener.PRI_OPTION
    wantedpackets = ('tcpdiscovery',)

    def processpkt(self, drone, unused_srcaddr, jsonobj):
        "Send commands to generate checksums in for this Drone's net-facing things"
        unused_srcaddr = unused_srcaddr
        checksumparameters = {
            'type': 'checksums',
            'parameters': {
                'ASSIM_sumcmds': [
                        '/usr/bin/sha256sum'
                    ,   '/usr/bin/sha224sum'
                    ,   '/usr/bin/sha384sum'
                    ,   '/usr/bin/sha512sum'
                    ,   '/usr/bin/sha1sum'
                    ,   '/usr/bin/md5sum'
                    ,   '/usr/bin/cksum'
                ,   '/usr/bin/crc32' ],
                'ASSIM_filelist': ['/bin/sh'
                    ,   '/bin/bash'
                    ,   '/bin/login'
                    ,   '/usr/bin/passwd' ]
            }
        }
        data = jsonobj['data'] # The data portion of the JSON message
        for procname in data.keys():    # List of nanoprobe-assigned names of processes...
            procinfo = data[procname]
            if 'exe' not in procinfo:
                continue
            exename = procinfo.get('exe')
            # dups (if any) are removed by the agent
            checksumparameters['parameters']['ASSIM_filelist'].append(exename)
            if exename.endswith('/java'):
                # Special case for some/many JAVA programs - find the jars...
                if 'cmdline' not in procinfo:
                    continue
                cmdline = procinfo.get('cmdline')
                for j in range(0, len(cmdline)):
                    # The argument following -cp is the ':'-separated CLASSPATH
                    if cmdline[j] == '-cp' and j < len(cmdline)-1:
                        jars = cmdline[j+1].split(':')
                        for jar in jars:
                            checksumparameters['parameters']['ASSIM_filelist'].append(jar)
                        break

        # Request discovery of checksums of all the binaries talking (tcp) over the network
        drone.request_discovery('_auto-checksums', 3600, str(JSONtree(checksumparameters)))
        print >> sys.stderr, ('REQUESTING CHECKSUM MONITORING OF: %s'
        %   (str(checksumparameters['parameters']['ASSIM_filelist'])))
