#!/usr/bin/env python
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
Checksum generation/checking code.
This is the class which wants to perform checksums and also
wants to hear about checksums as they are computed.

It's interesting that we ask for a certain set of files to be checksummed
but the discovery agent actually checksums those files and the ones that
ldd says those files use. So we typically wind up checksumming more files
than we asked for.

If we ask for a file which doesn't exist (like bad JARs in the CLASSPATH),
then those files won't show up in the results.
'''
import sys
from droneinfo import Drone
from AssimCclasses import pyConfigContext
from AssimCtypes import CONFIGNAME_TYPE, CONFIGNAME_INSTANCE
from assimevent import AssimEvent
from cmaconfig import ConfigFile

from discoverylistener import DiscoveryListener

@Drone.add_json_processor
class TCPDiscoveryChecksumGenerator(DiscoveryListener):
    'Class for generating checksums based on the content of tcpdiscovery packets'
    prio = DiscoveryListener.PRI_OPTION
    wantedpackets = ('tcpdiscovery', 'checksum')

    def processpkt(self, drone, srcaddr, jsonobj):
        if jsonobj['discovertype'] == 'tcpdiscovery':
            self.processtcpdiscoverypkt(drone, srcaddr, jsonobj)
        elif jsonobj['discovertype'] == 'checksum':
            self.processchecksumpkt(drone, srcaddr, jsonobj)
        else:
            print >> sys.stderr, 'OOPS! bad packet type [%s]', jsonobj['discovertype']

    def processtcpdiscoverypkt(self, drone, unused_srcaddr, jsonobj):
        "Send commands to generate checksums for this Drone's net-facing things"
        unused_srcaddr = unused_srcaddr
        params = ConfigFile.agent_params(self.config, 'discovery', 'checksums', drone.designation)
        sumcmds = self.config['checksum_cmds']
        filelist = self.config['checksum_files']
        filelist.extend(sumcmds)
        params['parameters'] = pyConfigContext()
        params[CONFIGNAME_TYPE] = 'checksums'
        params[CONFIGNAME_INSTANCE] = '_auto_checksumdiscovery'
        data = jsonobj['data'] # The data portion of the JSON message
        for procname in data.keys():    # List of nanoprobe-assigned names of processes...
            procinfo = data[procname]
            if 'exe' not in procinfo:
                continue
            exename = procinfo.get('exe')
            # dups (if any) are removed by the agent
            filelist.append(exename)
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
                            filelist.append(jar)
                        break

        params['parameters']['ASSIM_sumcmds'] = sumcmds
        params['parameters']['ASSIM_filelist'] = filelist
        # Request discovery of checksums of all the binaries talking (tcp) over the network
        print >> sys.stderr, ('REQUESTING CHECKSUM MONITORING OF %d files'
        %   (len(params['parameters']['ASSIM_filelist'])))
        drone.request_discovery((params,))

    def processchecksumpkt(self, drone, unused_srcaddr, jsonobj):
        'Process updated checksums. Note that our drone-owned-JSON is already updated'
        unused_srcaddr = unused_srcaddr # make pylint happy...
        data = jsonobj['data'] # The data portion of the JSON message
        print >> sys.stderr, 'PROCESSING CHECKSUM DATA'
        if hasattr(drone, 'JSON_OLD_checksums'):
            print >> sys.stderr, 'COMPARING CHECKSUM DATA'
            olddata = pyConfigContext(drone.JSON_OLD_checksums)['data']
            self.compare_checksums(drone, olddata, data)
        print >> sys.stderr, 'UPDATING CHECKSUM DATA for %d files' % len(data)
        drone.JSON_OLD_checksums = str(jsonobj)

    def compare_checksums(self, drone, oldobj, newobj):
        'Compare checksums and complain about those that change'
        designation = drone.designation
        changes = {}
        for oldfile in oldobj.keys():
            if oldfile not in newobj:
                continue
            oldchecksum = oldobj[oldfile]
            newchecksum = newobj[oldfile]
            if oldchecksum == newchecksum:
                continue
            self.log.warning('On system %s: %s had checksum %s which is now %s'
            %   (designation, oldfile, oldchecksum, newchecksum))
            changes[oldfile] = (oldchecksum, newchecksum)
        extrainfo = {'CHANGETYPE': 'checksums', 'changes': changes}
        AssimEvent(drone, AssimEvent.OBJUPDATE, extrainfo=extrainfo)
