#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
#
# bestpractices - prototypical implementation of best practices evaluation
#                 As of now, this is toy code.  Really...
#
# This implementation has several deficiencies which must be eliminated in
# a more final/production implementation.
#	1) The best practices are hard-wired into the code
#       They probably should be stored in the database
#       They should probably be initialized from some JSON describing them
#	2) There are no alert objects to track the failure or repair of best
#      practices
#	3) We need to be able to dynamically request the things we're interested in
#      not just statically.  This is related to Drone.add_json_processor()
#   4) No doubt more deficiencies to be discovered as the code is written.
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2015 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community
#   - http://assimproj.org
# Paid support is available from Assimilation Systems Limited
# - http://assimilationsystems.com
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
This module defines some classes related to evaluating best practices based
on discovery information
'''
from droneinfo import Drone
from consts import CMAconsts
from graphnodes import BPRules, BPRuleSet
from discoverylistener import DiscoveryListener
from graphnodeexpression import GraphNodeExpression, ExpressionContext
from AssimCclasses import pyConfigContext
from store import Store
from assimevent import AssimEvent
from assimeventobserver import AssimEventObserver
import os, logging, sys

class BestPractices(DiscoveryListener):
    'Base class for evaluating changes against best practices'
    prio = DiscoveryListener.PRI_OPTION
    prio = DiscoveryListener.PRI_OPTION   # What priority are we?
    wantedpackets = []  # Used to register ourselves for discovery packets
    eval_objects = {}
    eval_classes = {}
    evaled_classes = {}
    application = None
    discovery_name = None
    application = 'os'
    BASEURL = 'http://ITBestPractices.info:500'

    def __init__(self, config, packetio, store, log, debug):
        'Initialize our BestPractices object'
        DiscoveryListener.__init__(self, config, packetio, store, log, debug)
        if self.__class__ != BestPractices:
            return
        for pkttype in config['allbpdiscoverytypes']:
            BestPractices.register_sensitivity(BestPracticesCMA, pkttype)
        for pkttype in BestPractices.eval_classes:
            if pkttype not in BestPractices.eval_objects:
                BestPractices.eval_objects[pkttype] = []
            if pkttype not in BestPractices.evaled_classes:
                BestPractices.evaled_classes[pkttype] = {}

            for bpcls in BestPractices.eval_classes[pkttype]:
                if bpcls not in BestPractices.evaled_classes[pkttype]:
                    BestPractices.eval_objects[pkttype]                 \
                        .append(bpcls(config, packetio, store, log, debug))
                BestPractices.evaled_classes[pkttype][bpcls] = True


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
        "Register that class 'bpcls' wants to see packet of type 'pkttype'"
        #print >> sys.stderr, '%s is looking for packet of type %s' % (bpcls, pkttype)
        if pkttype not in BestPractices.wantedpackets:
            BestPractices.wantedpackets.append(pkttype)
            Drone.add_json_processor(BestPractices)
        if pkttype not in BestPractices.eval_classes:
            BestPractices.eval_classes[pkttype] = []
        if bpcls not in BestPractices.eval_classes[pkttype]:
            BestPractices.eval_classes[pkttype].append(bpcls)

    @staticmethod
    def load_json(store, json, bp_class, rulesetname, basedon=None):
        '''Load JSON for a single JSON ruleset into the database.'''
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
        return store.load_cypher_nodes(CMAconsts.QUERY_RULESET_RULES, BPRules
        ,       params={'rulesetname': rulesetname})


    def url(self, drone, ruleid, ruleobj):
        '''
        Return the URL in the IT Best Practices project that goes with this
        particular rule.

        Emily Ratliff <ejratl@gmail.com> defines the API this way:

        .../v1.0/doquery?app=os&domain=security&class=posix
            &os=linux&osname=redhat&release=6&tipname=nist_V-58901
        '''
        values={'app':      'os',
                'class':    'posix',
                'domain':   ruleobj['category'],
                'tipname':  ruleid}
        osinfo = drone.jsonval('os')
        if osinfo is not None and 'data' in osinfo:
            osdata = osinfo['data']
            if 'kernel-name' in osdata:
                values['os'] = osdata['kernel-name']
            if 'Distributor ID' in osdata:
                values['osname'] = osdata['Distributor ID']
            if 'Release' in osdata:
                values['release'] = osdata['Release']
        else:
            print >> sys.stderr, 'OOPS: osinfo is %s' % str(osinfo)
        names = values.keys()
        names.sort()

        ret = 'v1.0/doquery'
        delim='?'
        for name in names:
            ret += '%s%s=%s' % (delim, name, values[name])
            delim='&'
        return '%s/%s' % (self.BASEURL, ret)

    def processpkt(self, drone, srcaddr, jsonobj):
        '''Inform interested rule objects about this change'''
        self = self
        discovertype = jsonobj['discovertype']
        if discovertype not in BestPractices.eval_objects:
            print >> sys.stderr, 'NO %s in eval objects %s' % \
                (discovertype, str(BestPractices.eval_objects))
            return
        #print >> sys.stderr, 'IN PROCESSPKT for %s: %s %s' % \
        #   (drone, discovertype, BestPractices.eval_objects[discovertype])
        for rule_obj in BestPractices.eval_objects[discovertype]:
            #print  >> sys.stderr, 'Fetching %s rules for %s' % (discovertype, drone)
            rulesobj = rule_obj.fetch_rules(drone, srcaddr, discovertype)
            #print >> sys.stderr, 'RULES ARE:', rulesobj
            statuses = pyConfigContext(rule_obj.evaluate(drone, srcaddr,
                                       jsonobj, rulesobj))
            #print >> sys.stderr, 'RESULTS ARE:', statuses
            self.log_rule_results(statuses, drone, srcaddr, discovertype, rulesobj)

    @staticmethod
    def send_rule_event(oldstat, newstat, drone, ruleid, _ruleobj):
        ''' Newstat can never be None. '''
        if oldstat is None:
            if newstat == 'fail':
                AssimEvent(drone, AssimEvent.OBJWARN, extrainfo = {'ruleid' : ruleid})
        elif oldstat == 'pass':
            if newstat == 'fail':
                AssimEvent(drone, AssimEvent.OBJWARN, extrainfo = {'ruleid' : ruleid})
        elif oldstat == 'fail':
            if newstat == 'pass' or newstat == 'ignore' or newstat == 'NA':
                AssimEvent(drone, AssimEvent.OBJUNWARN, extrainfo = {'ruleid' : ruleid})
        elif oldstat == 'ignore':
            if newstat == 'fail':
                AssimEvent(drone, AssimEvent.OBJWARN, extrainfo = {'ruleid' : ruleid})
        elif oldstat == 'NA':
            if newstat == 'fail':
                AssimEvent(drone, AssimEvent.OBJWARN, extrainfo = {'ruleid' : ruleid})

    def log_rule_results(self, results, drone, _srcaddr, discovertype, rulesobj):
        '''Log the results of this set of rule evaluations'''
        status_name = 'BP_%s_rulestatus' % discovertype
        if hasattr(drone, status_name):
            oldstats = pyConfigContext(getattr(drone, status_name))
        else:
            oldstats = {'pass': [], 'fail': [], 'ignore': [], 'NA': []}
        for stat in ('pass', 'fail', 'ignore', 'NA'):
            logmethod = self.log.info if stat == 'pass' else self.log.warning
            for ruleid in results[stat]:
                oldstat = None
                for statold in ('pass', 'fail', 'ignore', 'NA'):
                    if ruleid in oldstats[statold]:
                        oldstat = statold
                        break
                if oldstat == stat or stat == 'NA':
                    # No change
                    continue
                BestPractices.send_rule_event(oldstat, stat, drone, ruleid, rulesobj)
                thisrule = rulesobj[ruleid]
                rulecategory = thisrule['category']
                logmethod('%s %sED %s rule %s: %s [%s]' % (drone,
                                 stat.upper(), rulecategory, ruleid,
                                 self.url(drone, ruleid, rulesobj[ruleid]),
                                 thisrule['rule']))
        setattr(Drone, status_name, str(results))

    def fetch_rules(self, _drone, _unusedsrcaddr, _discovertype):
        '''Evaluate our rules given the current/changed data.
        Note that fetch_rules is separate from rule evaluation to simplify
        testing.
        '''
        raise NotImplementedError('class BestPractices is an abstract class')

    @staticmethod
    def evaluate(_unused_drone, _unusedsrcaddr, wholejsonobj, ruleobj):
        '''Evaluate our rules given the current/changed data.
        '''

        jsonobj = wholejsonobj['data']
        #oldcontext = ExpressionContext((drone,), prefix='JSON_proc_sys')
        newcontext = ExpressionContext((jsonobj,))
        if hasattr(ruleobj, '_jsonobj'):
            ruleobj = getattr(ruleobj, '_jsonobj')
        ruleids = ruleobj.keys()
        ruleids.sort()
        statuses = {'pass': [], 'fail': [], 'ignore': [], 'NA': []}
        if len(ruleids) < 1:
            return statuses
        print >> sys.stderr, '\n==== Evaluating %d Best Practices rules on "%s"' \
            % (len(ruleids)-1, wholejsonobj['description'])
        for ruleid in ruleids:
            ruleinfo = ruleobj[ruleid]
            rule = ruleinfo['rule']
            rulecategory = ruleinfo['category']
            result = GraphNodeExpression.evaluate(rule, newcontext)
            if result is None:
                print >> sys.stderr, 'n/a:    %s ID %s %s' \
                    % (rulecategory, ruleid, rule)
                statuses['NA'].append(ruleid)
            elif not isinstance(result, bool):
                print >> sys.stderr, 'Rule id %s %s returned %s (%s)' \
                    % (ruleid, rule, result, type(result))
                statuses['fail'].append(ruleid)
            elif result:
                if rule.startswith('IGNORE'):
                    if not rulecategory.lower().startswith('comment'):
                        statuses['ignore'].append(ruleid)
                        print >> sys.stderr, 'IGNORE: %s ID %s %s' % \
                            (rulecategory, ruleid, rule)
                else:
                    statuses['pass'].append(ruleid)
                    print >> sys.stderr, 'PASS:   %s ID %s %s' \
                        % (rulecategory, ruleid, rule)
            else:
                print >> sys.stderr, 'FAIL:   %s ID %s %s'\
                    % (rulecategory, ruleid, rule)
                statuses['fail'].append(ruleid)
        return statuses

@BestPractices.register('proc_sys')
@Drone.add_json_processor
class BestPracticesCMA(BestPractices):
    'Security Best Practices which are evaluated against Linux /proc/sys values'
    application = 'os'
    discovery_name = 'JSON_proc_sys'

    def __init__(self, config, packetio, store, log, debug):
        BestPractices.__init__(self, config, packetio, store, log, debug)


    def fetch_rules(self, drone, _unusedsrcaddr, discovertype):
        '''Evaluate our rules given the current/changed data.
        Note that fetch_rules is separate from rule evaluation to
        simplify testing.
        In our case, we ask our Drone to provide us with the merged rule
        sets for the current kind of incoming packet.
        '''
        return drone.get_merged_bp_rules(discovertype)

    @staticmethod
    def configcallback(config, changedname, _unusedargs):
        '''Function called when configuration is updated.
        We use it to make sure all we get callbacks for all
        our discovery types.
        this might be overkill, but it's not expensive ;-).
        And, it doesn't do anything useful at the moment...
        '''
        print >> sys.stderr, 'Config Callback for name %s' % changedname
        if changedname in (None, 'allbpdiscoverytypes'):
            for pkttype in config['allbpdiscoverytypes']:
                BestPractices.register_sensitivity(BestPracticesCMA, pkttype)





class DebugEventObserver(AssimEventObserver):
    '''
    Event observer for testing the send event code
    '''
    expectResults = {
                     'f2p' : AssimEvent.OBJUNWARN,
                     'n2f' : AssimEvent.OBJWARN,
                     'p2f' : AssimEvent.OBJWARN,
                     'i2f' : AssimEvent.OBJWARN,
                     'f2i' : AssimEvent.OBJUNWARN,
                     'f2na' : AssimEvent.OBJUNWARN,
                     'na2f' : AssimEvent.OBJWARN
                     }
    def __init__(self):
        AssimEventObserver.__init__(self,None)
    def notifynewevent(self,event):
        if event.eventtype == DebugEventObserver.expectResults[event.extrainfo['ruleid']]:
            print "Success Result for %s is correct" % event.extrainfo['ruleid']
        else:
            print "Failure Result for %s is incorrect" % event.extrainfo['ruleid']
            sys.exit(1)

if __name__ == '__main__':
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
    rulefile = None
    for dirname in ('.', '..', '../..', '../../..'):
        rulefile= '%s/best_practices/proc_sys.json' % dirname
        if os.access(rulefile, os.R_OK):
            break
    with open(rulefile, 'r') as procsys_file:
        testrules = pyConfigContext(procsys_file.read())
    testjsonobj = pyConfigContext(JSON_data)
    logger = logging.getLogger('BestPracticesTest')
    logger.addHandler(logging.StreamHandler(sys.stderr))
    testconfig = {'allbpdiscoverytypes': ['login_defs', 'pam', 'proc_sys', 'sshd']}
    BestPractices(testconfig, None, None, logger, False)
    for procsys in BestPractices.eval_classes['proc_sys']:
        ourstats = procsys.evaluate("testdrone", None, testjsonobj, testrules)
        size = sum([len(ourstats[st]) for st in ourstats.keys()])
        print size, len(testrules)
        assert size == len(testrules)-1 # One rule is an IGNOREd comment
        assert ourstats['fail'] == ['itbp-00001', 'nist_V-38526', 'nist_V-38601']
        assert len(ourstats['NA']) >= 13
        assert len(ourstats['pass']) >= 3
        assert len(ourstats['ignore']) == 0
        print ourstats
    DebugEventObserver()
    BestPractices.send_rule_event('fail', 'pass', 'testdrone', 'f2p', None)
    BestPractices.send_rule_event(None, 'fail', 'testdrone', 'n2f', None)
    BestPractices.send_rule_event('pass', 'fail', 'testdrone', 'p2f', None)
    BestPractices.send_rule_event('ignore', 'fail', 'testdrone', 'i2f', None)
    BestPractices.send_rule_event('fail', 'ignore', 'testdrone', 'f2i', None)
    BestPractices.send_rule_event('fail', 'NA', 'testdrone', 'f2na', None)
    BestPractices.send_rule_event('NA', 'fail', 'testdrone', 'na2f', None)
    print 'Results look correct!'
