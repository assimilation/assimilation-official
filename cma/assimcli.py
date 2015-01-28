#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
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
from query import ClientQuery
from graphnodes import GraphNode
from store import Store
from py2neo import neo4j
from AssimCtypes import QUERYINSTALL_DIR, cryptcurve25519_gen_persistent_keypair,   \
    cryptcurve25519_cache_all_keypairs, CMA_KEY_PREFIX, CMAUSERID
from AssimCclasses import pyCryptFrame, pyCryptCurve25519
#
# These imports really are necessary - in spite of what pylint thinks...
# pylint: disable=W0611
import droneinfo, hbring, monitoring
from cmainit import CMAinit

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

        cypher = 'START q=node:ClientQuery("%s:*") WHERE q.queryname="%s" RETURN q LIMIT 1'

        metaquery = neo4j.CypherQuery(store.db, cypher % (queryname, queryname))

        request = store.load_cypher_node(metaquery, ClientQuery)

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
            print >> sys.stderr, ('Invalid query: %s' % (str(err)))
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
        return 'genkeys (must run as root)'

    @staticmethod
    def execute(store, executor_context, otherargs, flagoptions):
        'Generate the desired key-pairs'
        store = store
        executor_context = executor_context
        flagoptions = flagoptions

        if os.geteuid() != 0:
            return usage()
        if len(otherargs) > 0:
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


options = {'language', 'format'}
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
    return 1

def dbsetup():
    'Set up our connection to Neo4j'
    ourstore = Store(neo4j.GraphDatabaseService(), uniqueindexmap={}, classkeymap={})
    CMAinit(None)
    for classname in GraphNode.classmap:
        GraphNode.initclasstypeobj(ourstore, classname)
    return ourstore


def main(argv):
    'Main program for command line tool'
    ourstore = None
    executor_context = None

    nodbcmds = {'genkeys'}
    selected_options = {}
    narg = 0
    skipnext = False
    for narg in range(1, len(argv)):
        arg = argv[narg]
        if skipnext:
            skipnext = False
            continue
        if arg.startswith('--'):
            option = arg[2:]
            if option not in options:
                usage()
                return 1
            selected_options[option] = argv[arg+1]
        else:
            break


    if len(argv) < 2 or argv[1] not in commands:
        usage()
        return 1
    command = argv[1]
    if command not in nodbcmds:
        ourstore=dbsetup()
    return commands[command].execute(ourstore, executor_context, sys.argv[2:], selected_options)


if __name__ ==  '__main__':
    sys.exit(main(sys.argv))
