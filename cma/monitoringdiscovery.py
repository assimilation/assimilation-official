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

"""
Discovery Listener infrastructure
This is the base class for code that wants to hear about various
discovery packets as they arrive.

More details are documented in the DiscoveryListener class
"""
import sys
from sys import stderr
import hashlib
from monitoring import MonitoringRule, MonitorAction
from systemnode import SystemNode
from graphnodes import ProcessNode
from discoverylistener import DiscoveryListener
from cmaconfig import ConfigFile


@SystemNode.add_json_processor
class TCPDiscoveryGenerateMonitoring(DiscoveryListener):
    "Class for generating and activating monitoring from the TCP discovery data"
    prio = DiscoveryListener.PRI_OPTION
    wanted_packets = ("tcpdiscovery",)

    def processpkt(self, drone, _unused_srcaddr, jsonobj, _discoverychanged):
        """Send commands to monitor services for this Systems's listening processes
        We ignore discoverychanged because we always want to monitor even if a system
        has just come up with the same discovery as before it went down."""

        drone.monitors_activated = True
        # self.log.debug('In TCPDiscoveryGenerateMonitoring::processpkt for %s with %s (%s)'
        #               %    (drone, _discoverychanged, str(jsonobj)))
        data = jsonobj["data"]  # The data portion of the JSON message
        for procname in data.keys():  # List of nanoprobe-assigned names of processes...
            procinfo = data[procname]
            processproc = self.store.load_or_create(
                ProcessNode,
                domain=drone.domain,
                processname=procname,
                host=drone.designation,
                pathname=procinfo.get("exe", "unknown"),
                argv=procinfo.get("cmdline", "unknown"),
                uid=procinfo.get("uid", "unknown"),
                gid=procinfo.get("gid", "unknown"),
                cwd=procinfo.get("cwd", "/"),
            )
            if "listenaddrs" not in procinfo:
                # We only monitor services, not clients...
                continue
            montuple = MonitoringRule.findbestmatch((processproc, drone))
            if montuple[0] == MonitoringRule.NOMATCH:
                processproc.is_monitored = False
                print("**don't know how to monitor %s" % str(processproc.argv), file=stderr)
                self.log.warning(
                    "No rules to monitor %s service %s" % (drone.designation, str(processproc.argv))
                )
            elif montuple[0] == MonitoringRule.PARTMATCH:
                processproc.is_monitored = False
                print(
                    "Automatic monitoring not possible for %s -- %s is missing %s"
                    % (str(processproc.argv), str(montuple[1]), str(montuple[2])),
                    file=sys.stderr,
                )
                self.log.warning(
                    "Insufficient information to monitor %s service %s"
                    ". %s is missing %s"
                    % (drone.designation, str(processproc.argv), str(montuple[1]), str(montuple[2]))
                )
            else:
                processproc.is_monitored = True
                agent = montuple[1]
                self._add_service_monitoring(drone, processproc, agent)
                if agent["monitorclass"] == "NEVERMON":
                    print("NEVER monitor %s" % (str(agent["monitortype"])), file=sys.stderr)
                else:
                    print(
                        "START monitoring %s using %s agent"
                        % (agent["monitortype"], agent["monitorclass"]),
                        file=sys.stderr,
                    )

    # pylint - too many local variables
    # pylint: disable=R0914
    def _add_service_monitoring(self, drone, monitoredservice, moninfo):
        """
        We start the monitoring of 'monitoredservice' using the information
        in 'moninfo' - which came from MonitoringRule.constructaction()
        and is based on discovery and general rules for that monitoring action
        Moninfo includes the following kinds of metadata:
            - identification parameters - class, provider, type
            - environment variables
            - command line arguments
        """
        monitorclass = moninfo["monitorclass"]
        monitortype = moninfo["monitortype"]
        monitorprovider = moninfo.get("provider", None)
        if monitorprovider is not None:
            classtype = "%s::%s:%s" % (monitorclass, moninfo["provider"], monitortype)
        else:
            classtype = "%s::%s" % (monitorclass, monitortype)
        # Compute interval and timeout - based on global 'config'
        agent_params = ConfigFile.agent_params(
            self.config, "monitoring", classtype, drone.designation
        )
        # This produces the following metadata:
        #   - class-independent parameters: repeat, timeout, etc
        #   - environment variables
        #   - command line arguments
        # These are merged together with the moninfo parameters in the following way
        #   - Class-independent variables are taken from 'params' if conflicting
        #   - Environment variables are taken from 'params' if there's a conflict
        #   - command line arguments from params come first, followed by the
        #     any that come from 'moninfo'
        parameters = agent_params["parameters"]
        paraminterval = parameters["repeat"]
        paramtimeout = parameters["timeout"]
        paramwarntime = parameters["warn"]
        paramargv = parameters.get("argv", [])
        paramenv = parameters.get("env", {})
        monargv = moninfo.get("argv", [])
        monenv = moninfo.get("arglist", {})
        argv = []  # pyConfigContext doesn't handle arrays well...
        if paramargv is not None:
            argv.extend(paramargv)
        if monargv is not None:
            argv.extend(monargv)
        environ = {}
        for envset in (monenv, paramenv):
            if envset is not None:
                for env in envset:
                    environ[env] = envset[env]

        # Make up a monitor name that should be unique to us -- but reproducible
        # We create the monitor name from the host name, the monitor class,
        # monitoring type and a hash of the arguments to the monitoring agent
        # Note that this is different from the hashed service/entity name, since we could
        # have multiple ways of monitoring the same entity
        d = hashlib.md5()
        # pylint mistakenly thinks md5 objects don't have update member
        # pylint: disable=E1101
        hash_str = "%s:%s:%s:%s" % (drone.designation, monitorclass, monitortype, monitorprovider)
        d.update(hash_str.encode('utf-8'))
        if environ is not None:
            names = environ.keys()
            names.sort()
            for name in names:
                # pylint thinks md5 objects don't have update member
                # pylint: disable=E1101
                d.update('"%s": "%s"' % (name, environ[name]))
        for arg in argv:
            d.update('"%s"' % str(arg))

        monitorname = "%s:%s:%s::%s" % (drone.designation, monitorclass, monitortype, d.hexdigest())
        monnode = self.store.load_or_create(
            MonitorAction,
            domain=drone.domain,
            monitorname=monitorname,
            monitorclass=monitorclass,
            monitortype=monitortype,
            interval=paraminterval,
            timeout=paramtimeout,
            warntime=paramwarntime,
            provider=monitorprovider,
            arglist=environ if environ else None,
            argv=argv if argv else None,
        )  # Neo4j restriction...
        if monitorclass == "nagios":
            monnode.nagiospath = self.config["monitoring"]["nagiospath"]
        if not monnode.association.is_abstract:
            print(
                "Previously monitored %s on %s" % (monitortype, drone.designation), file=sys.stderr
            )
        monnode.activate(monitoredservice, drone)


@SystemNode.add_json_processor
class DiscoveryGenerateHostMonitoring(TCPDiscoveryGenerateMonitoring):
    """This class performs host-level monitoring.
    For the moment, that's only using Nagios agents.
    """

    def processpkt(self, drone, _unused_srcaddr, _unused_jsonobj, _discoverychanged):
        """Send commands to monitor host aspects for the given System.
        We ignore discoverychanged because we always want to monitor even if a system
        has just come up with the same discovery as before it went down.
        """

        drone.monitors_activated = True
        # self.log.debug('In DiscoveryGenerateHostMonitoring::processpkt for %s with %s (%s)'
        #               %    (drone, _discoverychanged, str(_unused_jsonobj)))
        montuples = MonitoringRule.findallmatches((drone,), objclass="host")
        for montuple in montuples:
            if montuple[0] == MonitoringRule.NOMATCH:
                continue
            elif montuple[0] == MonitoringRule.PARTMATCH:
                print(
                    "Automatic host monitoring of %s not possible with %s: missing %s"
                    % (drone.designation, str(montuple[1]), str(montuple[2])),
                    file=sys.stderr,
                )
                self.log.warning(
                    "Insufficient information to monitor host %s"
                    " using %s: %s is missing."
                    % (drone.designation, str(montuple[1]), str(montuple[2]))
                )
            else:
                agent = montuple[1]
                self._add_service_monitoring(drone, drone, agent)
                print(
                    "START monitoring host %s using %s:%s agent"
                    % (drone.designation, agent["monitorclass"], agent["monitortype"]),
                    file=sys.stderr,
                )
