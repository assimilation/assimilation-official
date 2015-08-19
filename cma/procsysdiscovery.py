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
Discovery Listener infrastructure
This is the base class for code that wants to hear about various
discovery packets as they arrive.

More details are documented in the DiscoveryListener class
'''
import sys
from droneinfo import Drone
from AssimCclasses import pyConfigContext
from AssimCtypes import CONFIGNAME_TYPE, CONFIGNAME_INSTANCE
from cmaconfig import ConfigFile

from discoverylistener import DiscoveryListener

@Drone.add_json_processor
class ProcSysDiscovery(DiscoveryListener):
    'Class for discovering the contents of /proc/sys'
    prio = DiscoveryListener.PRI_OPTION
    wantedpackets = ('OS', 'os')

    def processpkt(self, drone, unused_srcaddr, jsonobj):
        "Send commands to gather discovery data from /proc/sys"
        unused_srcaddr = unused_srcaddr
        data = jsonobj['data'] # The data portion of the JSON message
        osfield='operating-system'
        if osfield not in data:
            self.log.warning('OS name not found in %s' % str(data))
            return
        osname = data[osfield]
        if osname.find('Linux') == -1 and osname.find('linux') == -1:
            self.log.info('ProcSysDiscovery: OS name is not Linux: %s' % str(osname))
            return

        params = ConfigFile.agent_params(self.config, 'discovery', 'proc_sys', drone.designation)
        params['parameters'] = pyConfigContext({'ASSIM_discoverdir': '/proc/sys' })
        params[CONFIGNAME_TYPE] = 'proc_sys'
        params[CONFIGNAME_INSTANCE] = '_auto_proc_sys'

        # Request discovery of checksums of all the binaries talking (tcp) over the network
        if self.debug:
            self.log.debug('REQUESTING /proc/sys DISCOVERY')
        drone.request_discovery((params,))
