#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2014 - Assimilation Systems Limited
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
Assimilation Command Line tool.
We support the following commands:
    query - perform one of our canned ClientQuery queries
'''

import sys, os, getent
from operator import itemgetter
from query import ClientQuery
from consts import CMAconsts
from graphnodes import GraphNode
from droneinfo import Drone
from store import Store
from py2neo import neo4j
from AssimCtypes import QUERYINSTALL_DIR, cryptcurve25519_gen_persistent_keypair,   \
    cryptcurve25519_cache_all_keypairs, CMA_KEY_PREFIX, CMAUSERID, BPINSTALL_DIR,   \
    CMAINITFILE, CMAUSERID
from AssimCclasses import pyCryptFrame, pyCryptCurve25519
from cmaconfig import ConfigFile
from cmadb import Neo4jCreds, CMAdb
#
# These imports really are necessary - in spite of what pylint thinks...
# pylint: disable=W0611
import droneinfo, hbring, monitoring
from cmainit import CMAinit
from bestpractices import BestPractices

commands = {}

def RegisterCommand(classtoregister):
    'Register the given function as being a main command'
    commands[classtoregister.__name__] = classtoregister()
    return classtoregister

#too many local variables
#pylint: disable=R0914
@RegisterCommand
class query(object):
    "Class for the 'query' action (sub-command)"

    def __init__(self):
        pass

    @staticmethod
    def usage():
        "reports usage for this sub-command"
        return 'query queryname [query-parameter=value ...]'

    # pylint R0911 -- too many return statements
    # pylint: disable=R0911
    @staticmethod
    def execute(store, executor_context, otherargs, flagoptions):
        'Perform command line query and format output as requested.'
        language = flagoptions.get('language', 'en')
        fmtstring = flagoptions.get('format', None)

        if len(otherargs) < 1:
            usage()
            print >> sys.stderr, 'Need to supply a query name.'
            return 1
        queryname = otherargs[0]
        nvpairs = otherargs[1:]

        cypher = ('START q=node:ClientQuery("%s:*") WHERE q.queryname="%s" RETURN q LIMIT 1'
                  % (queryname, queryname))

        request = store.load_cypher_node(cypher, ClientQuery)

        if request is None:
            print >> sys.stderr, ("No query named '%s'." % queryname)
            return 1

        param_names = request.cypher_parameter_names()

        params = {}
        # Convert name=value strings into a Dict
        for elem in nvpairs:
            try:
                (name, value) = nvpairs.split('=')
                params[name] = value
            except AttributeError as err:
                if len(param_names) == 0:
                    print >> sys.stderr, ('%s query does not take any parameters' % queryname)
                    return 1
                elif len(param_names) == 1:
                    # It's reasonable to not require the name if there's only one possibility
                    params[param_names[0]] = elem
                else:
                    print >> sys.stderr, ('[%s] is not a name=value pair' % nvpairs)
                    return 1
        request.bind_store(store)
        if not request.supports_cmdline():
            print >> sys.stderr, (
                "Query '%s' does not support command line queries" % queryname)
            return 1
        try:
            iterator = request.cmdline_exec(executor_context, language, fmtstring, **params)
            for line in iterator:
                print line
        except ValueError as err:
            print >> sys.stderr, ('Invalid query [%s %s]: %s.' % (queryname, str(params), str(err)))
            # pylint W0212 -- access to a protected member
            # pylint: disable=W0212
            print >> sys.stderr, ('CYPHER IS: %s' % request._query)
            return 1
        return 0

@RegisterCommand
class loadqueries(object):
    "Class for the 'loadquery' action (sub-command). We reload the query table"

    def __init__(self):
        'Default init function'
        pass

    @staticmethod
    def usage():
        "reports usage for this sub-command"
        return 'loadqueries [optional-querydirectory]'

    # pylint R0911 -- too many return statements
    # pylint: disable=R0911
    @staticmethod
    def execute(store, executor_context, otherargs, flagoptions):
        'Load queries from the specified directory.'

        executor_context = executor_context
        flagoptions = flagoptions

        if len(otherargs) > 1:
            return usage()
        elif len(otherargs) == 1:
            querydir = otherargs[0]
        else:
            querydir = QUERYINSTALL_DIR

        qcount = 0
        for q in ClientQuery.load_tree(store, querydir):
            qcount += 1
            q = q
        #Store.debug = True
        store.commit()
        return 0 if qcount > 0 else 1

@RegisterCommand
class loadbp(object):
    "Class for the 'loadbp' action (sub-command). We load up a set of best practices"

    def __init__(self):
        'Default init function'
        pass

    @staticmethod
    def usage():
        "reports usage for this sub-command"
        return 'loadbp [ruleset-directory ruleset-name [based-on-ruleset-name]]'

    @staticmethod
    def execute(store, executor_context, otherargs, flagoptions):
        'Load all best practice files we find in the specified directory.'
        executor_context = executor_context
        flagoptions = flagoptions
        basedon = None

        if len(otherargs) not in (0,2,3):
            return usage()
        elif len(otherargs) >= 2:
            bpdir = otherargs[0]
            rulesetname = otherargs[1]
            if len(otherargs) > 2:
                basedon = otherargs[2]
        else:
            bpdir = BPINSTALL_DIR
            rulesetname = CMAconsts.BASERULESETNAME

        qcount = 0
        for q in BestPractices.load_directory(store, bpdir, rulesetname, basedon):
            qcount += 1
            q = q
        store.commit()
        return 0 if qcount > 0 else 1

@RegisterCommand
class genkeys(object):
    'Generate two CMA keys and store in optional directory.'

    def __init__(self):
        'Default init function'
        pass

    @staticmethod
    def usage():
        "reports usage for this sub-command"
        return 'genkeys'

    @staticmethod
    def execute(store, _executor_context, otherargs, _flagoptions):
        'Generate the desired key-pairs'
        store = store

        if os.geteuid() != 0 or len(otherargs) > 0:
            return usage()
        cryptcurve25519_cache_all_keypairs()
        cmaidlist = pyCryptFrame.get_cma_key_ids()
        cmaidlist.sort()
        if len(cmaidlist) == 0:
            print ('No CMA keys found. Generating two CMA key-pairs to start.')
            for sequence in (0, 1):
                print >> sys.stderr, "Generating key id", sequence
                cryptcurve25519_gen_persistent_keypair('%s%05d' % (CMA_KEY_PREFIX, sequence))
            cryptcurve25519_cache_all_keypairs()
            cmaidlist = pyCryptFrame.get_cma_key_ids()
        elif len(cmaidlist) == 1:
            lastkey = cmaidlist[0]
            lastseqno = int(lastkey[len(CMA_KEY_PREFIX):])
            newkeyid = ('%s%05d' % (CMA_KEY_PREFIX, lastseqno + 1))
            print ('Generating an additional CMA key-pair.')
            cryptcurve25519_gen_persistent_keypair(newkeyid)
            cryptcurve25519_cache_all_keypairs()
            cmaidlist = pyCryptFrame.get_cma_key_ids()
        if len(cmaidlist) != 2:
            print ('Unexpected number of CMA keys.  Expecting 2, but got %d.'
            %       len(cmaidlist))
        extras = []
        privatecount = 0
        userinfo = getent.passwd(CMAUSERID)
        if userinfo is None:
            raise OSError('CMA user id "%s" is unknown' % CMAUSERID)
        for keyid in cmaidlist:
            privatename = pyCryptCurve25519.key_id_to_filename(keyid, pyCryptFrame.PRIVATEKEY)
            pubname = pyCryptCurve25519.key_id_to_filename(keyid, pyCryptFrame.PUBLICKEY)
            # pylint doesn't understand about getent...
            # pylint: disable=E1101
            os.chown(pubname, userinfo.uid, userinfo.gid)
            # pylint: disable=E1101
            os.chown(privatename, userinfo.uid, userinfo.gid)
            privatecount += 1
            if privatecount > 1:
                print ('SECURELY HIDE *private* key %s' % privatename)
                extras.append(keyid)
@RegisterCommand
class neo4jpass(object):
    'Generate and remember a new neo4j password'

    @staticmethod
    def usage():
        "reports usage for this sub-command"
        return 'neo4jpass [optional-new-password]'

    @staticmethod
    def execute(_store, _executor_context, otherargs, _flagoptions):
        'Generate and remember a new neo4j password'
        if os.geteuid() != 0 or len(otherargs) > 1:
            return usage()
        Neo4jCreds().update(newauth=otherargs[0] if len(otherargs) > 0 else None)

def ourjoin(listarg, delim=','):
    'We join anything as though it were a string...'
    curdelim = ''
    result = ''
    for elem in listarg:
        result += '%s%s' % (curdelim, str(elem))
        curdelim=delim
    return result


@RegisterCommand
class dtypescores(object):
    'Compute and print scores for the given categories'

    @staticmethod
    def usage():
        "reports usage for this sub-command"
        return 'dtypescores [--hostnames|--rulenames] [list of score categories...]'

    @staticmethod
    def execute(store, _executor_context, otherargs, flagoptions):
        'Compute and print scores for the given categories'
        delim=','
        dtype_totals, drone_totals, rule_totals = grab_category_scores(store, otherargs)
        dropfirstfield = otherargs and len(otherargs) == 1
        if 'hostnames' in flagoptions:
            # 0:  category name
            # 1:  discovery-type
            # 2:  total score for this discovery type _across all drones_
            # 3:  drone designation (name)
            # 4:  total score for this drone for this discovery type
            sortkeys = itemgetter(0,2,4,1,3)
            for tup in sorted(yield_drone_scores(otherargs, drone_totals, dtype_totals),
                              key=sortkeys, reverse=True):
                if dropfirstfield:
                    print ourjoin(tup[1:], delim=delim)
                else:
                    print ourjoin(tup, delim=delim)
        elif 'rulenames' in flagoptions:
            # 0:  category name
            # 1:  discovery-type
            # 2:  total score for this discovery type _across all rules
            # 3:  rule id
            # 4:  total score for this rule id
            sortkeys = itemgetter(0,2,4,1,3)
            for tup in sorted(yield_rule_scores(otherargs, dtype_totals, rule_totals),
                              key=sortkeys, reverse=True):
                if dropfirstfield:
                    print ourjoin(tup[1:], delim=delim)
                else:
                    print ourjoin(tup, delim=delim)
        else:
            # 0:  category name
            # 1:  discovery-type
            # 2:  total score for this discovery-type _across all drones_
            sortkeys = itemgetter(0,2,1)
            for tup in sorted(yield_category_scores(otherargs, dtype_totals),
                              key=sortkeys, reverse=True):
                if dropfirstfield:
                    print ourjoin(tup[1:], delim=delim)
                else:
                    print ourjoin(tup, delim=delim)

@RegisterCommand
class secdtypes (object):
    'Compute and print security scores'
    @staticmethod
    def usage():
        'reports usage for this sub-command'
        return 'secdtypes [--hostnames]'

    @staticmethod
    def execute(store, executor_context, _otherargs, flagoptions):
        'Compute and print security scores as requested'
        dtypescores.execute(store, executor_context, ('security',), flagoptions)


def grab_category_scores(store, categories=None, debug=False):
    '''Program to create and return some python Dicts with security scores and totals by category
    and totals by drone/category
    Categories is None or a list of desired categories.
    '''
    cypher = '''START drone=node:Drone('*:*') RETURN drone'''

    BestPractices(CMAdb.io.config, CMAdb.io, store, CMAdb.log, debug=debug)
    dtype_totals = {} # scores organized by (category, discovery-type)
    drone_totals = {} # scores organized by (category, discovery-type, drone)
    rule_totals = {} # scores organized by (category, discovery-type, rule)

    for drone in store.load_cypher_nodes(cypher, Drone):
        designation = drone.designation
        discoverytypes = drone.bp_discoverytypes_list()
        for dtype in discoverytypes:
            dattr = Drone.bp_discoverytype_result_attrname(dtype)
            statuses = getattr(drone, dattr)
            for rule_obj in BestPractices.eval_objects[dtype]:
                rulesobj = rule_obj.fetch_rules(drone, None, dtype)
                _, scores, rulescores = BestPractices.compute_scores(drone, rulesobj, statuses)
                for category in scores:
                    if category not in categories and categories:
                        continue
                    # Accumulate scores by (category, discovery_type)
                    if category not in dtype_totals:
                        dtype_totals[category] = {}
                    if dtype not in dtype_totals[category]:
                        dtype_totals[category][dtype] = 0.0
                    dtype_totals[category][dtype] += scores[category]
                    # Accumulate scores by (category, discovery_type, drone)
                    if category not in drone_totals:
                        drone_totals[category] = {}
                    if dtype not in drone_totals[category]:
                        drone_totals[category][dtype] = {}
                    if designation not in drone_totals[category][dtype]:
                        drone_totals[category][dtype][designation] = 0.0
                    drone_totals[category][dtype][designation] += scores[category]
                    if category not in rule_totals:
                        rule_totals[category] = {}
                    if dtype not in rule_totals[category]:
                        rule_totals[category][dtype] = {}
                    for ruleid in rulescores[category]:
                        if ruleid not in rule_totals[category][dtype]:
                            rule_totals[category][dtype][ruleid] = 0.0
                        rule_totals[category][dtype][ruleid] += rulescores[category][ruleid]

    return dtype_totals, drone_totals, rule_totals

def yield_category_scores(categories, dtype_totals):
    '''Return the dtype_totals as a CSV-style output.
    We output the following fields:
        0:  category name
        1:  discovery-type
        2:  total score for this discovery-type _across all drones_
   '''
    cats = sorted(dtype_totals.keys(), reverse=True)
    dtypes = set()
    for cat in cats:
        for dtype in dtype_totals[cat]:
            dtypes.add(dtype)
    dtypes = list(dtypes)
    for cat in cats:
        for dtype in dtypes:
            if dtype not in dtype_totals[cat]:
                continue
            score = dtype_totals[cat][dtype]
            if score > 0:
                yield (cat, dtype, score)

def yield_drone_scores(categories, drone_totals, dtype_totals):
    '''Format the drone_totals + dtype_totals as a CSV-style output
    We output the following fields:
        0:  category name
        1:  discovery-type
        2:  total score for this discovery type _across all drones_
        3:  drone designation (name)
        4:  total score for this drone for this discovery type
    '''
    cats = sorted(drone_totals.keys(), reverse=True)
    dtypes = set()
    for cat in cats:
        for dtype in drone_totals[cat]:
            dtypes.add(dtype)
    dtypes = list(dtypes)
    for cat in cats:
        for dtype in dtypes:
            if dtype not in drone_totals[cat]:
                continue
            for drone in drone_totals[cat][dtype]:
                score = drone_totals[cat][dtype][drone]
                if score > 0:
                    yield (cat, dtype, dtype_totals[cat][dtype], drone, score)

def yield_rule_scores(categories, dtype_totals, rule_totals):
    '''Format the rule totals + dtype_totals as a CSV-style output
    We output the following fields:
        0:  category name
        1:  discovery-type
        2:  total score for this discovery type _across all rules
        3:  rule id
        4:  total score for this rule id
    '''
    dtypes = set()
    # rule_totals = # scores organized by (category, discovery-type, rule)
    for cat in sorted(rule_totals, reverse=True):
        for dtype in rule_totals[cat]:
            for ruleid in rule_totals[cat][dtype]:
                score = rule_totals[cat][dtype][ruleid]
                if score > 0:
                    yield (cat, dtype, dtype_totals[cat][dtype], ruleid, score)

options = {'language':True, 'format':True, 'hostnames':False, 'rulenames': False}
def usage():
    'Construct and print usage message'
    argv = sys.argv

    optlist = ''
    for opt in options:
        optlist += "[--%s <%s>] " % (opt, opt)

    cmds = []
    for cmd in commands.keys():
        cmds.append(cmd)
    cmds.sort()

    print >> sys.stderr, 'Usage: %s %ssub-command [sub-command-args]' % (argv[0], optlist)
    print >> sys.stderr, '    Legal sub-command usages are:'
    for cmd in cmds:
        print >> sys.stderr, '    %s' % commands[cmd].usage()
    print >> sys.stderr, '(all sub-commands must be run as root or %s)' % CMAUSERID
    return 1

# pylint too few public methods...
# pylint: disable=R0903
class DummyIO(object):
    '''
    A Dummy I/O object which has a config member...
    '''
    def __init__(self, config=None):
        if config is None:
            try:
                config = ConfigFile(filename=CMAINITFILE)
            except IOError:
                config = ConfigFile()
        self.config = config

def dbsetup(readonly=False, url=None):
    'Set up our connection to Neo4j'
    if url is None:
        url = 'localhost.com:7474'
    Neo4jCreds().authenticate(url)
    ourstore = Store(neo4j.Graph(), uniqueindexmap={}, classkeymap={})
    CMAinit(DummyIO(), readonly=readonly, use_network=False)
    for classname in GraphNode.classmap:
        GraphNode.initclasstypeobj(ourstore, classname)
    CMAdb.store = ourstore
    return ourstore


def main(argv):
    'Main program for command line tool'
    ourstore = None
    executor_context = None

    nodbcmds = {'genkeys', 'neo4jpass'}
    rwcmds = {'loadqueries', 'loadbp'}
    selected_options = {}
    narg = 0
    skipnext = False
    for narg in range(1, len(argv)):
        arg = argv[narg]
        if skipnext:
            skipnext = False
            continue
        if arg.startswith('--'):
            skipnext = True
            option = arg[2:]
            if option not in options:
                usage()
                return 1
            if options[option]:
                selected_options[option] = argv[narg+1]
                skipnext = True
            else:
                selected_options[option] = True
                skipnext = False
        else:
            command=arg
            break

    if len(argv) < 2 or command not in commands:
        usage()
        return 1
    if command not in nodbcmds:
        ourstore=dbsetup(readonly=(command not in rwcmds))
    return commands[command].execute(ourstore, executor_context, sys.argv[narg+1:],
                                     selected_options)


if __name__ ==  '__main__':
    sys.exit(main(sys.argv))
