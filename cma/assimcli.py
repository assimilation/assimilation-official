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
"""
Assimilation Command Line tool.
We support the following commands:
    query - perform one of our canned ClientQuery queries
"""

from __future__ import print_function, absolute_import
import sys
from sys import stderr
import os
import getent
import inject
from py2neo import Graph
from query import ClientQuery
from consts import CMAconsts
from AssimCtypes import QUERYINSTALL_DIR, cryptcurve25519_gen_persistent_keypair, \
    cryptcurve25519_cache_all_keypairs, CMA_KEY_PREFIX, CMAUSERID, BPINSTALL_DIR, \
    CMAINITFILE
from AssimCclasses import pyCryptFrame, pyCryptCurve25519
from cmaconfig import ConfigFile
from cmadb import CMAdb
from cmainit import Neo4jCreds, CMAInjectables
#
# These imports really are necessary - in spite of what pylint thinks...
# pylint: disable=W0611
from cmainit import CMAinit
from bestpractices import BestPractices

commands = {}


def RegisterCommand(classtoregister):
    'Register the given function as being a main command'
    commands[classtoregister.__name__] = classtoregister()
    return classtoregister


# too many local variables
# pylint: disable=R0914
@RegisterCommand
class query(object):
    "Class for the 'query' action (sub-command)"

    def __init__(self):
        pass

    @staticmethod
    def usage():
        "reports usage for this sub-command"
        return 'query queryname [query-parameter=value ...]'

    @staticmethod
    def load_query_object(store, queryname):
        'Function to return the query object for a given query name'
        cypher = 'MATCH (q:Class_ClientQuery) WHERE q.queryname=$queryname RETURN q LIMIT 1'
        ret = store.load_cypher_node(cypher, {'queryname': queryname})
        if ret is not None:
            ret.bind_store(store)
        return ret

    # pylint R0911 -- too many return statements
    # pylint: disable=R0911
    @staticmethod
    def execute(store, executor_context, otherargs, flagoptions):
        'Perform command line query and format output as requested.'
        language = flagoptions.get('language', 'en')
        fmtstring = flagoptions.get('format', None)

        if len(otherargs) < 1:
            usage()
            print('Need to supply a query name.', file=stderr)
            return 1
        queryname = otherargs[0]
        nvpairs = otherargs[1:]

        request = query.load_query_object(store, queryname)

        if request is None:
            print("No query named '%s'." % queryname, file=stderr)
            return 1

        param_names = request.parameter_names()

        params = {}
        # Convert name=value strings into a Dict
        for elem in nvpairs:
            try:
                (name, value) = elem.split('=')
                params[name] = value
            except (AttributeError, ValueError) as err:
                if len(param_names) == 0:
                    print('%s query does not take any parameters' % queryname, file=stderr)
                    return 1
                elif len(param_names) == 1:
                    # It's reasonable to not require the name if there's only one possibility
                    params[param_names[0]] = elem
                else:
                    print('[%s] is not a name=value pair' % nvpairs, file=stderr)
                    return 1
        request.bind_store(store)
        if not request.supports_cmdline():
            print("Query '%s' does not support command line queries" % queryname, file=stderr)
            return 1
        try:
            iterator = request.cmdline_exec(executor_context, language, fmtstring, **params)
            for line in iterator:
                print(line)
        except ValueError as err:
            print('Invalid query [%s %s]: %s.' % (queryname, str(params), str(err)), file=stderr)
            # pylint W0212 -- access to a protected member
            # pylint: disable=W0212
            # print('CYPHER IS: %s' % request._query), file=stderr)
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
        # Store.debug = True
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

        if len(otherargs) not in (0, 2, 3):
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
        for q in load_directory(store, bpdir, rulesetname, basedon):
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
            print('No CMA keys found. Generating two CMA key-pairs to start.')
            for sequence in (0, 1):
                print("Generating key id", sequence, file=stderr)
                cryptcurve25519_gen_persistent_keypair('%s%05d' % (CMA_KEY_PREFIX, sequence))
            cryptcurve25519_cache_all_keypairs()
            cmaidlist = pyCryptFrame.get_cma_key_ids()
        elif len(cmaidlist) == 1:
            lastkey = cmaidlist[0]
            lastseqno = int(lastkey[len(CMA_KEY_PREFIX):])
            newkeyid = ('%s%05d' % (CMA_KEY_PREFIX, lastseqno + 1))
            print('Generating an additional CMA key-pair.')
            cryptcurve25519_gen_persistent_keypair(newkeyid)
            cryptcurve25519_cache_all_keypairs()
            cmaidlist = pyCryptFrame.get_cma_key_ids()
        if len(cmaidlist) != 2:
            print('Unexpected number of CMA keys.  Expecting 2, but got %d.'
                  % len(cmaidlist))
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
                print('SECURELY HIDE *private* key %s' % privatename)
                extras.append(keyid)


@RegisterCommand
class neo4jpass(object):
    'Generate and remember a new neo4j password'
    creds = None

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


options = {'language': True, 'format': True, 'hostnames': False, 'ruleids': False}


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

    print('Usage: %s %ssub-command [sub-command-args]' % (argv[0], optlist), file=stderr)
    print('       Legal sub-command usages are:', file=stderr)
    for cmd in cmds:
        print('       %s' % commands[cmd].usage(), file=stderr)
    print('(all sub-commands must be run as root or %s)' % CMAUSERID, file=stderr)
    return 1


# pylint too few public methods...
# pylint: disable=R0903
class DummyIO(object):
    """
    A Dummy I/O object which has a config member...
    """

    def __init__(self, config=None):
        if config is None:
            try:
                config = ConfigFile(filename=CMAINITFILE)
            except IOError:
                config = ConfigFile()
        self.config = config


@inject.params(db='py2neo.Graph', store='Store', log='logging.Logger')
def dbsetup(db=None, store=None, log=None):
    """Set up our connection to Neo4j
    """
    assert isinstance(db, Graph)
    CMAinit(DummyIO(), store=store, use_network=False, db=db, log=log)
    CMAdb.store = store
    store.db_transaction = db.begin(autocommit=False)
    return store


def main(argv):
    'Main program for command line tool'
    ourstore = None
    executor_context = None

    nodbcmds = {'genkeys', 'neo4jpass'}
    rwcmds = {'loadqueries', 'loadbp'}
    ourstore = None
    command = None
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
                selected_options[option] = argv[narg + 1]
                skipnext = True
            else:
                selected_options[option] = True
                skipnext = False
        else:
            command = arg
            break

    if len(argv) < 2 or command not in commands:
        usage()
        return 1
    CMAInjectables.default_cma_injection_configuration({'NEO4J_READONLY': command not in rwcmds})
    if command not in nodbcmds:
        ourstore = dbsetup()
    return commands[command].execute(ourstore, executor_context, sys.argv[narg + 1:],
                                     selected_options)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
