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
from consts import CMAconsts
from graphnodes import BPRules, BPRuleSet
from discoverylistener import DiscoveryListener
from graphnodeexpression import GraphNodeExpression, ExpressionContext
from store import Store
import os, logging, sys

class BestPractices(DiscoveryListener):
    'Base class for evaluating changes against best practices'
    prio = DiscoveryListener.PRI_OPTION
    prio = DiscoveryListener.PRI_OPTION   # What priority are we?
    wantedpackets = []  # Used to register ourselves for incoming discovery packets
    evaluators = {}
    application = None
    discovery_name = None
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
                BestPractices.register_sensitivity(cls, pkttype)
            return cls
        return decorator

    @staticmethod
    def register_sensitivity(bpcls, pkttype):
        "Register that class 'cls' wants to see packet of type 'pkttype'"
        if pkttype not in BestPractices.wantedpackets:
            BestPractices.wantedpackets.append(pkttype)
            print >> sys.stderr, ('Registering class %s for packet types: %s'
                                  % (bpcls, str(BestPractices.wantedpackets)))
            Drone.add_json_processor(BestPractices)
        if pkttype not in BestPractices.evaluators:
            BestPractices.evaluators[pkttype] = []
        if bpcls not in BestPractices.evaluators[pkttype]:
            BestPractices.evaluators[pkttype].append(bpcls)

    @staticmethod
    def load_json(store, json, bp_class, rulesetname, basedon=None):
        '''Load JSON for a single JSON ruleset into the database.'''
        if bp_class not in BestPractices.wantedpackets:
            raise ValueError('%s is not a valid best practice discovery name' % bp_class)
        rules = store.load_or_create(BPRules, bp_class=bp_class, json=json,
                                           rulesetname=rulesetname)
        if basedon is None or not Store.is_abstract(rules):
            return
        parent = store.load(BPRules, bp_class=bp_class, rulesetname=basedon)
        store.relate_new(rules, CMAconsts.REL_basis, parent,
                         properties={'bp_class': bp_class})
        return rules

    @staticmethod
    def load_from_file(store, filename, bp_class, rulesetname, basedon=None):
        '''Load JSON from a single ruleset file into the database.'''
        with open(filename, 'r') as jsonfile:
            json = jsonfile.read()
            return BestPractices.load_json(store, json, bp_class, rulesetname, basedon)

    @staticmethod
    def load_directory(store, directoryname, rulesetname, basedon=None):
        '''
        Load all the rules in the 'directoryname' directory into our database
        as 'rulesetname' and link them up as being based on the given rule
        set name.

        If 'basedon' is not None, then we derive a set of basis ordering
        which we use to compute the precedence of rule sets.

        For the moment, all rule sets must contain all the different rule sets
        that their predecessor is based on. They can have empty rule sets if
        there is nothing to override, but they have to all be there.
        Dependent rule sets can have new rule sets not present in their basis,
        but the reverse cannot be true.

        It's perfectly normal for a rule set to not contain all the rules that
        a basis rule set specifies, which means they aren't overridden.

        It's also perfectly OK for a dependent rule set to have rules not
        present in the basis rule set.
        '''
        Store.debug = True
        store.load_or_create(BPRuleSet, rulesetname=rulesetname, basisrules=basedon)
        files = os.listdir(directoryname)
        files.sort()
        for filename in files:
            if filename.startswith('.'):
                continue
            path = os.path.join(directoryname, filename)
            classname = filename.replace('.json', '')
            yield BestPractices.load_from_file(store, path, classname, rulesetname, basedon)

    @staticmethod
    def gen_bp_rules_by_ruleset(store, rulesetname):
        '''Return generator providing all BP rules for the given ruleset
        '''
        from py2neo import neo4j
        query = neo4j.CypherQuery(store.db, CMAconsts.QUERY_RULESET_RULES)
        return store.load_cypher_nodes(query, BPRules
        ,       params={'rulesetname': rulesetname})


    def url(self, _drone, ruleid, ruleobj):
        '''
        Return the URL in the IT Best Practices project that goes with this
        particular rule.
        '''
        # We should eventually use the drone to hone in more on the OS and so on...
        return '%s/%s/%s?application=%s' % (self.BASEURL, ruleobj['category']
        ,   ruleid, self.application)

    def processpkt(self, drone, srcaddr, jsonobj):
        '''Inform interested rule objects about this change'''
        self = self
        discovertype = jsonobj['discovertype']
        if discovertype not in BestPractices.evaluators:
            return
        for rulecls in BestPractices.evaluators[discovertype]:
            ruleclsobj = rulecls(self.config, self.packetio, self.store,
                                 self.log, self.debug)
            rulesobj = ruleclsobj.fetch_rules(drone, srcaddr, discovertype)
            statuses = ruleclsobj.evaluate(drone, srcaddr, jsonobj, rulesobj)
            self.log_rule_results(statuses, drone, srcaddr, discovertype, rulesobj)

    def log_rule_results(self, results, drone, _srcaddr, discovertype, rulesobj):
        '''Log the results of this set of rule evaluations'''
        print >> sys.stderr, ('RESULTS of %s RULES EVALUATED FOR %s: %s'
                              % (discovertype, drone, str(results)))
        status_name = 'BP_%s_rulestatus' % discovertype
        if hasattr(drone, status_name):
            oldstats = pyConfigContext(getattr(drone, status_name))
        else:
            oldstats = {'pass': [], 'fail': [], 'ignore': [], 'NA': []}
        attrlist = ('pass', 'fail', 'ignore', 'NA')
        for stat in ('pass', 'fail'):
            ruleids = results[stat]
            for ruleid in ruleids:
                oldstat = None
                for statold in attrlist:
                    if ruleid in oldstats[statold]:
                        oldstat = statold
                        break
                if oldstat == stat or stat == 'NA':
                    # No change
                    continue
                rulecategory = rulesobj[ruleid]
                statusstr = stat.upper()
                self.log.warning('Node %s %sED %s rule %s: %s', drone,
                                 statusstr, rulecategory, ruleid,
                                 self.url(drone, ruleid, rulesobj))
        setattr(Drone, status_name, str(results))



    def fetch_rules(self, _drone, _unusedsrcaddr, _jsonobj):
        '''Evaluate our rules given the current/changed data.
        Note that fetch_rules is separate from rule evaluation to simplify
        testing.
        '''
        raise NotImplementedError('class BestPractices is an abstract class')

    def evaluate(self, drone, _unusedsrcaddr, jsonobj, ruleobj):
        '''Evaluate our rules given the current/changed data.
        '''
        drone = drone
        #oldcontext = ExpressionContext((drone,), prefix='JSON_proc_sys')
        newcontext = ExpressionContext((jsonobj,))
        if hasattr(ruleobj, '_jsonobj'):
            ruleobj = getattr(ruleobj, '_jsonobj')
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
@Drone.add_json_processor
class BestPracticesCMA(BestPractices):
    'Security Best Practices which are evaluated against Linux /proc/sys values'
    application = 'os'
    discovery_name = 'JSON_proc_sys'

    def __init__(self, config, packetio, store, log, debug):
        BestPractices.__init__(self, config, packetio, store, log, debug)
        from cmaconfig import ConfigFile
        ConfigFile.register_callback(BestPracticesCMA.configcallback, args=None)

    def fetch_rules(self, drone, _unusedsrcaddr, jsonobj):
        '''Evaluate our rules given the current/changed data.
        Note that fetch_rules is separate from rule evaluation to
        simplify testing.
        In our case, we ask our Drone to provide us with the merged rule
        sets for the current kind of incoming packet.
        '''
        return drone.get_bp_merged_rules(jsonobj['discovertype'])

    @staticmethod
    def configcallback(config, changedname, _unusedargs):
        '''Function called when configuration is updated.
        We use it to make sure all we get callbacks for all
        our discovery types.
        this might be overkill, but it's not expensive ;-).
        '''
        if changedname in (None, 'allbpdiscoverytypes'):
            for pkttype in config['allbpdiscoverytypes']:
                BestPractices.register_sensitivity(BestPracticesCMA, pkttype)

if __name__ == '__main__':
    from AssimCclasses import pyConfigContext
    #import sys
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
    with open('../best_practices/proc_sys.json', 'r') as procsys_file:
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
        print ruleclass, ourstats
    print 'Results look correct!'
