#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# bestpractices - prototypical implementation of best practices evaluation
#                 As of now, this is toy code.  Really...
#
# This implementation has several deficiencies which must be eliminated in
# a more final/production implementation.
#	1) The best practices are hard-wired into the code
#       They probably should be stored in the database
#       They should probably be initialized from some JSON describing them
#	2) There are no alert objects to track the failure or repair of best practices
#	3) We need to be able to dynamically request the things we're interested in
#      not just statically.  This is related to Drone.add_json_processor()
#   4) No doubt more deficiencies to be discovered as the code is written.
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2015 - Assimilation Systems Limited
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
This module defines some classes related to evaluating best practices based on discovery information
'''
from droneinfo import Drone
from discoverylistener import DiscoveryListener
from graphnodeexpression import GraphNodeExpression, ExpressionContext
import logging

@Drone.add_json_processor
class BestPractices(DiscoveryListener):
    'Base class for evaluating changes against best practices'
    prio = DiscoveryListener.PRI_OPTION
    wantedpackets = []
    evaluators = {}
    application = None
    discovery_name = None
    sensitive_to = None
    application = 'os'
    BASEURL = 'http://ITBestPractices.info/query'

    def __init__(self, config, packetio, store, log, debug):
        'Initialize our BestPractices object'
        DiscoveryListener.__init__(self, config, packetio, store, log, debug)

    @staticmethod
    def register(*pkttypes):
        '''Register a BestPractices subclass interested in the given discovery types.
        Return value: our decorator function'''
        def decorator(cls):
            '''Register our class with the packet types given to 'register' above.
            Return value: Class that we registered.
            '''
            for pkttype in pkttypes:
                if pkttype not in BestPractices.wantedpackets:
                    BestPractices.wantedpackets.append(pkttype)
                    Drone.add_json_processor(BestPractices)
                if pkttype not in BestPractices.evaluators:
                    BestPractices.evaluators[pkttype] = []
                if cls not in BestPractices.evaluators[pkttype]:
                    BestPractices.evaluators[pkttype].append(cls)
            return cls
        return decorator

    def url(self, drone, ruleid, ruleobj):
        '''
        Return the URL in the IT Best Practices project that goes with this
        particular rule.
        '''
        # We should eventually use the drone to hone in more on the OS and so on...
        drone = drone
        return '%s/%s/%s?application=%s' % (self.BASEURL, ruleobj['category']
        ,   ruleid, self.application)

    def processpkt(self, drone, srcaddr, jsonobj):
        '''Inform interested rule sets about this change'''
        self = self
        discovertype = jsonobj['discovertype']
        if discovertype not in BestPractices.evaluators:
            return
        for rulecls in BestPractices.evaluators[discovertype]:
            rule = rulecls(self.config, self.packetio, self.store, self.log, self.debug)
            failures = rule.evaluate(drone, srcaddr, jsonobj)
            if failures is not None:
                for failure in failures:
                    failure = failure

    def evaluate(self, drone, unusedsrcaddr, jsonobj, ruleobj):
        'Evaluate our rules given the current/changed data'
        unusedsrcaddr = unusedsrcaddr
        drone = drone
        #oldcontext = ExpressionContext((drone,), prefix='JSON_proc_sys')
        newcontext = ExpressionContext((jsonobj,))
        ruleids = ruleobj.keys()
        ruleids.sort()
        statuses = {'pass': [], 'fail': [], 'ignore': [], 'NA': []}
        for ruleid in ruleids:
            ruleinfo = ruleobj[ruleid]
            rule = ruleinfo['rule']
            rulecategory = ruleinfo['category']
            result = GraphNodeExpression.evaluate(rule, newcontext)
            if result is None:
                print >> sys.stderr, 'n/a:    ID %s %s (%s)' % (ruleid, rule, rulecategory)
                statuses['NA'].append(ruleid)
            elif not isinstance(result, bool):
                print >> sys.stderr, 'Rule id %s %s returned %s (%s)' % (ruleid
                ,       rule, result, type(result))
                statuses['fail'].append(ruleid)
            elif result:
                if rule.startswith('IGNORE'):
                    statuses['ignore'].append(ruleid)
                    print >> sys.stderr, 'IGNORE: ID %s %s (%s)' % (ruleid, rule, rulecategory)
                else:
                    statuses['pass'].append(ruleid)
                    print >> sys.stderr, 'PASS:   ID %s %s (%s)' % (ruleid, rule, rulecategory)
            else:
                print >> sys.stderr, 'FAIL:   ID %s %s (%s)' % (ruleid
                ,       rule, rulecategory)
                statuses['fail'].append(ruleid)
                self.log.warning('BESTPRACTICES: Node %s failed %s rule %s: %s'
                ,   drone, rulecategory, ruleid, self.url(drone, ruleid, ruleinfo))
        return statuses

@BestPractices.register('proc_sys')
class BestPracticesProcSys(BestPractices):
    'Security Best Practices which are evaluated agains Linux /proc/sys values'
    application = 'os'
    discovery_name = 'JSON_proc_sys'
    sensitive_to = ('proc_sys',)

if __name__ == '__main__':
    from AssimCclasses import pyConfigContext
    import sys
    JSON_data = '''
{
  "discovertype": "proc_sys",
  "description": "Information derived from /proc/sys",
  "host": "ubuntu72",
  "source": "../../discovery_agents/proc_sys",
  "data": {
    "kernel.core_pattern": "|/usr/share/apport/apport %p %s %c %P",
    "kernel.core_pipe_limit": 0,
    "kernel.core_uses_pid": 0,
    "kernel.ctrl-alt-del": 0,
    "kernel.printk_ratelimit_burst": 10,
    "kernel.pty.max": 4096,
    "kernel.pty.nr": 9,
    "kernel.pty.reserve": 1024,
    "kernel.randomize_va_space": 2,
    "kernel.sysrq": 176,
    "kernel.tainted": 0,
    "kernel.watchdog": 1,
    "kernel.watchdog_thresh": 10,
    "net.core.default_qdisc": "pfifo_fast",
    "net.ipv4.conf.all.accept_redirects": 0,
    "net.ipv4.conf.all.accept_source_route": 0,
    "net.ipv4.conf.all.secure_redirects": 1,
    "net.ipv4.conf.all.send_redirects": 1,
    "net.ipv6.conf.all.accept_redirects": 1,
    "net.ipv6.conf.all.accept_source_route": 0
    }}'''
    with open('../best-practices/proc_sys.json', 'r') as procsys_file:
        testrules = pyConfigContext(procsys_file.read())
    testjsonobj = pyConfigContext(JSON_data)['data']
    logger = logging.getLogger('BestPracticesTest')
    logger.addHandler(logging.StreamHandler(sys.stderr))
    for ruleclass in BestPractices.evaluators['proc_sys']:
        procsys = ruleclass(None, None, None, logger, False)
        ourstats = procsys.evaluate("testdrone", None, testjsonobj, testrules)
        size = sum([len(ourstats[st]) for st in ourstats.keys()])
        assert size == len(testrules)
        assert ourstats['fail'] == ['itbp-00001', 'nist_V-38526', 'nist_V-38601']
        assert len(ourstats['NA']) >= 13
        assert len(ourstats['pass']) >= 3
        assert len(ourstats['ignore']) == 1
    print 'Results look correct!'
