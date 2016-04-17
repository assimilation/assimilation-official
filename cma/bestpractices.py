#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
#
# bestpractices - implementation of best practices evaluation
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
    BASEURL = 'http://db.ITBestPractices.info:%d'

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


    def url(self, drone, ruleid, ruleobj, html=True, port=5000):
        '''
        Return the URL in the IT Best Practices project that goes with this
        particular rule.

        Emily Ratliff <ejratl@gmail.com> defines the API this way:

        .../v1.0/doquery?app=os&domain=security&class=posix
            &os=linux&osname=redhat&release=6&tipname=nist_V-58901
        '''
        values={'app':      ruleobj.get('application', 'os'),
                'class':    'posix',
                'domain':   ruleobj['category'],
                'tipname':  ruleid
                }
        osinfo = drone.jsonval('os')
        if osinfo is not None and 'data' in osinfo:
            osdata = osinfo['data']
            if 'kernel-name' in osdata:
                values['os'] = osdata['kernel-name'].lower()
            if 'Distributor ID' in osdata:
                values['osname'] = osdata['Distributor ID'].lower()
            if 'Release' in osdata:
                values['release'] = osdata['Release'].lower()
        names = values.keys()
        names.sort()

        ret = 'itbp/v1.0/%s' % ('show' if html else 'showjson')
        delim='?'
        for name in names:
            ret += '%s%s=%s' % (delim, name, values[name])
            delim='&'
        return '%s/%s' % ((self.BASEURL % port), ret)

    def processpkt(self, drone, srcaddr, jsonobj):
        '''Inform interested rule objects about this change'''
        discovertype = jsonobj['discovertype']
        discoverinstance = jsonobj['instance']
        if discoverinstance in BestPractices.eval_objects:
            #print 'MATCHING ON INSTANCE: %s: %s' % (discoverinstance, str(jsonobj))
            self._processpkt_by_type(drone, srcaddr, discoverinstance, jsonobj)
        elif discovertype in BestPractices.eval_objects:
            #print 'MATCHING BY DISCOVERTYPE: %s: %s' % (discovertype, str(jsonobj))
            self._processpkt_by_type(drone, srcaddr, discovertype, jsonobj)
        else:
            print >> sys.stderr, 'No BP rules for %s/%s' % (discovertype, discoverinstance)

    def _processpkt_by_type(self, drone, srcaddr, evaltype, jsonobj):
        'process a discovery object against its set of rules'
        #print >> sys.stderr, 'IN PROCESSPKT_BY_TYPE for %s: %s %s' % \
        #   (drone, evaltype, BestPractices.eval_objects[evaltype])
        for rule_obj in BestPractices.eval_objects[evaltype]:
            #print  >> sys.stderr, 'Fetching %s rules for %s' % (evaltype, drone)
            rulesobj = rule_obj.fetch_rules(drone, srcaddr, evaltype)
            #print >> sys.stderr, 'RULES ARE:', rulesobj
            statuses = pyConfigContext(rule_obj.evaluate(drone, srcaddr,
                                       jsonobj, rulesobj, evaltype))
            #print >> sys.stderr, 'RESULTS ARE:', statuses
            self.log_rule_results(statuses, drone, srcaddr, jsonobj, evaltype, rulesobj)

    @staticmethod
    def send_rule_event(oldstat, newstat, drone, ruleid, ruleobj, url):
        ''' Newstat, ruleid, and ruleobj can never be None. '''
        extrainfo = {'ruleid': ruleid, 'category': ruleobj[ruleid]['category'], 'url': url}
        if oldstat is None:
            if newstat == 'fail':
                AssimEvent(drone, AssimEvent.OBJWARN, extrainfo=extrainfo)
        elif oldstat == 'pass':
            if newstat == 'fail':
                AssimEvent(drone, AssimEvent.OBJWARN, extrainfo=extrainfo)
        elif oldstat == 'fail':
            if newstat == 'pass' or newstat == 'ignore' or newstat == 'NA':
                AssimEvent(drone, AssimEvent.OBJUNWARN, extrainfo=extrainfo)
        elif oldstat == 'ignore':
            if newstat == 'fail':
                AssimEvent(drone, AssimEvent.OBJWARN, extrainfo=extrainfo)
        elif oldstat == 'NA':
            if newstat == 'fail':
                AssimEvent(drone, AssimEvent.OBJWARN, extrainfo=extrainfo)

    def basic_rule_score_algorithm(self, _drone, rule, status):
        'A very basic best practice scoring algorithm'
        if status != 'fail':
            return 0.0
        category = rule.get('category', 'security')
        if category == 'comment':
            return 0.0
        severity = rule.get('severity', 'medium')
        default_sevmap = {'high': 3.0, 'medium': 2.0, 'low': 1.0}
        if 'score_severity_map' in self.config:
            sevmap = self.config['score_severity_map'].get(category, default_sevmap)
        else:
            sevmap = default_sevmap
        return sevmap.get(severity, sevmap['medium'])

    #R0914 -- too many local variables
    #pylint: disable=R0914
    def log_rule_results(self, results, drone, _srcaddr, discoveryobj, discovertype, rulesobj):
        '''Log the results of this set of rule evaluations'''
        status_name = Drone.bp_discoverytype_result_attrname(discovertype)
        if hasattr(drone, status_name):
            oldstats = pyConfigContext(getattr(drone, status_name))
        else:
            oldstats = {'pass': [], 'fail': [], 'ignore': [], 'NA': [], 'score': 0.0}
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
                url = self.url(drone, ruleid, rulesobj[ruleid])
                BestPractices.send_rule_event(oldstat, stat, drone, ruleid, rulesobj, url)
                thisrule = rulesobj[ruleid]
                rulecategory = thisrule['category']
                logmethod('%s %sED %s rule %s: %s [%s]' %
                          (drone, stat.upper(), rulecategory, ruleid, url, thisrule['rule']))
        self.compute_score_updates(discoveryobj, drone, rulesobj, results, oldstats)
        setattr(drone, status_name, str(results))

    def compute_scores(self, drone, rulesobj, statuses):
        '''Compute the scores from this set of statuses - organized by category
        We return the total score, scores organized by category
        and the scoring detailed on a rule-by-rule basis.
        '''
        scores = {}
        rulescores = {}
        totalscore=0
        if isinstance(statuses, (str, unicode)):
            statuses = pyConfigContext(statuses)
        for status in statuses:
            if status == 'score':
                continue
            for ruleid in statuses[status]:
                rule = rulesobj[ruleid]
                rulecat = rule['category']
                rulescore = self.basic_rule_score_algorithm(drone, rule, status)
                if rulecat not in rulescores:
                    rulescores[rulecat] = {}
                rulescores[rulecat][ruleid] = rulescore
                totalscore += rulescore
                if rulecat not in scores:
                    scores[rulecat] = 0.0
                scores[rulecat] += rulescore
        return totalscore, scores, rulescores

    #pylint  disable=R0914 -- too many local variables
    #pylint: disable=R0914
    def compute_score_updates(self, discovery_json, drone, rulesobj, newstats, oldstats):
        '''We compute the score updates for the rules and results we've been given.
        The drone is a Drone (or host), the 'rulesobj' contains the rules and their categories.
        Statuses contains the results of evaluating the rules.
        Our job is to compute the scores for each of the categories of rules in the
        statuses, issue events for score changes, and update the category scores in the host.

        We're storing the successes, failures, etc, for this discovery object for this drone.

        Note that this can fail if we change our algorithm - because we don't know the values
            the old algorithm gave us, only what the current algorithm gives us on the old results.

        @TODO: We eventually want to update the scores for the domain to which this drone
        belongs.


        '''
        _, oldcatscores, _ = self.compute_scores(drone, rulesobj, oldstats)
        _, newcatscores, _ = self.compute_scores(drone, rulesobj, newstats)
        keys = set(newcatscores)
        keys |= set(oldcatscores)
        # I have no idea why "keys = set(newcatscores) | set(oldcatscores)" did not work...
        # It worked fine in an interactive python session...

        diffs = {}

        for category in keys:
            newscore = newcatscores.get(category, 0.0)
            oldscore = oldcatscores.get(category, 0.0)
            catattr = Drone.bp_category_score_attrname(category)
            # I just compare two floating point numbers without a lot of formality.
            # This should be OK because they're both computed by the same algorithm
            # And at this level algorithms mostly produce integers
            # This is not a numerical analysis problem ;-)
            if newscore != oldscore:
                diff = newscore - oldscore
                if category in diffs:
                    diffs[category] += diff
                else:
                    diffs[category] = diff
                eventtype = AssimEvent.OBJWARN if newscore > oldscore else AssimEvent.OBJUNWARN
                extrainfo = {'category':    category,
                             'oldscore': str(oldscore),
                             'newscore': str(newscore),
                             'discovery_type': discovery_json['discovertype'],
                             'discovery_description': discovery_json['description']
                             }
                # POTENTIALCONCURRENCY
                # As long as no one else is updating this attribute for this drone
                # we shouldn't have concurrency problems.
                oldval = getattr(drone, catattr) if hasattr(drone, catattr) else 0.0
                setattr(drone, catattr, oldval + diff)
                print >> sys.stderr, 'Setting %s.%s to %d' % (drone, catattr, oldval+diff)
                AssimEvent(drone, eventtype, extrainfo=extrainfo)
        return newcatscores, diffs


    def fetch_rules(self, _drone, _unusedsrcaddr, _discovertype):
        '''Evaluate our rules given the current/changed data.
        Note that fetch_rules is separate from rule evaluation to simplify
        testing.
        '''
        raise NotImplementedError('class BestPractices is an abstract class')

    @staticmethod
    def evaluate(_unused_drone, _unusedsrcaddr, wholejsonobj, ruleobj, description):
        '''Evaluate our rules given the current/changed data.
        '''
        jsonobj = wholejsonobj['data']
        #oldcontext = ExpressionContext((drone,), prefix='JSON_proc_sys')
        newcontext = ExpressionContext((jsonobj,))
        if hasattr(ruleobj, '_jsonobj'):
            ruleobj = getattr(ruleobj, '_jsonobj')
        ruleids = ruleobj.keys()
        ruleids.sort()
        statuses = {'pass': [], 'fail': [], 'ignore': [], 'NA': [], 'score': 0.0}
        if len(ruleids) < 1:
            return statuses
        print >> sys.stderr, '\n==== Evaluating %d Best Practice rules on "%s" [%s]' \
            % (len(ruleids)-1, wholejsonobj['description'], description)
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
    'Security Best Practices which are evaluated against various discovery modules'
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

if __name__ == '__main__':
    #import sys

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
                         'f2na': AssimEvent.OBJUNWARN,
                         'na2f': AssimEvent.OBJWARN
                         }
        def __init__(self):
            AssimEventObserver.__init__(self,None)
        def notifynewevent(self,event):
            if event.eventtype == DebugEventObserver.expectResults[event.extrainfo['ruleid']]:
                print "Success Result for %s is correct" % event.extrainfo['ruleid']
            else:
                print "Failure Result for %s is incorrect" % event.extrainfo['ruleid']
                sys.exit(1)

    #pylint: disable=R0903
    class DummyDrone(object):
        'Really dummy object'
        pass
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
    dummydrone = DummyDrone()
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
    bpobj = BestPractices(testconfig, None, None, logger, False)
    for procsys in BestPractices.eval_classes['proc_sys']:
        ourstats = procsys.evaluate("testdrone", None, testjsonobj, testrules, 'proc_sys')
        size = sum([len(ourstats[st]) for st in ourstats.keys() if st != 'score'])
        #print size, len(testrules)
        assert size == len(testrules)-1 # One rule is an IGNOREd comment
        assert ourstats['fail'] == ['itbp-00001', 'nist_V-38526', 'nist_V-38601']
        assert len(ourstats['NA']) >= 13
        assert len(ourstats['pass']) >= 3
        assert len(ourstats['ignore']) == 0
        score, tstdiffs = bpobj.compute_score_updates(testjsonobj, dummydrone, testrules,
                                                           ourstats, {})
        assert str(pyConfigContext(score)) == '{"networking":1.0,"security":4.0}'
        # pylint: disable=E1101
        assert dummydrone.bp_category_networking_score == 1.0   # should be OK for integer values
        assert dummydrone.bp_category_security_score   == 4.0   # should be OK for integer values
        assert type(dummydrone.bp_category_networking_score) == float
        assert type(dummydrone.bp_category_security_score) == float
        assert str(pyConfigContext(tstdiffs)) == '{"networking":1.0,"security":4.0}'
        score, tstdiffs = bpobj.compute_score_updates(testjsonobj, dummydrone, testrules,
                                                           ourstats, ourstats)
        assert str(pyConfigContext(score)) == '{"networking":1.0,"security":4.0}'
        assert str(pyConfigContext(tstdiffs)) == '{}'
        score, tstdiffs = bpobj.compute_score_updates(testjsonobj, dummydrone, testrules,
                                                           {}, ourstats)
        assert str(pyConfigContext(tstdiffs)) == '{"networking":-1.0,"security":-4.0}'
        assert dummydrone.bp_category_networking_score == 0.0   # should be OK for integer values
        assert dummydrone.bp_category_security_score == 0.0     # should be OK for integer values
    DebugEventObserver()
    atestrule = testrules['itbp-00001']
    # Create temporary rules for the send_rule_event tests
    for case in ('f2p', 'n2f', 'p2f', 'i2f', 'f2i', 'f2na', 'na2f'):
        testrules[case] = atestrule
    BestPractices.send_rule_event('fail', 'pass', 'testdrone', 'f2p', testrules,   'https://URL')
    BestPractices.send_rule_event(None, 'fail', 'testdrone', 'n2f', testrules,     'https://URL')
    BestPractices.send_rule_event('pass', 'fail', 'testdrone', 'p2f', testrules,   'https://URL')
    BestPractices.send_rule_event('ignore', 'fail', 'testdrone', 'i2f', testrules, 'https://URL')
    BestPractices.send_rule_event('fail', 'ignore', 'testdrone', 'f2i', testrules, 'https://URL')
    BestPractices.send_rule_event('fail', 'NA', 'testdrone', 'f2na', testrules,    'https://URL')
    BestPractices.send_rule_event('NA', 'fail', 'testdrone', 'na2f', testrules,    'https://URL')
    # Get rid of the temporary rules for the send_rule_event tests
    for case in ('f2p', 'n2f', 'p2f', 'i2f', 'f2i', 'f2na', 'na2f'):
        del testrules[case]

    print 'Results look correct!'
