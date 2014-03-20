#!/usr/bin/python
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

import sys
from query import ClientQuery
from graphnodes import GraphNode
from store import Store
from py2neo import neo4j

commands = {}

def RegisterCommand(classtoregister):
    'Register the given function as being a main command'
    commands[classtoregister.__name__] = classtoregister()
    return classtoregister

#too many local variables
#pylint: disable=R0914 
@RegisterCommand
class query:
    @staticmethod
    def usage():
        return 'query queryname [query-parameter=value ...]'

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
            except ValueError as err:
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
        try:
            iterator = request.cmdline_exec(executor_context, language, fmtstring, **params)
        except ValueError as err:
            print >> sys.stderr, ('Invalid %s query. Reason: %s' % (queryname, err))
            return 1
        for line in iterator:
            print line
        return 0

options = {'language', 'format'}
def usage():
    'Construct and print usage message'
    argv = sys.argv

    optlist=''
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
    

def main(argv):
    'Main program for command line tool'
    executor_context = None

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

    ourstore = Store(neo4j.GraphDatabaseService(), uniqueindexmap={}, classkeymap={})
    for classname in GraphNode.classmap:
        GraphNode.initclasstypeobj(ourstore, classname)

    if len(argv) < 2 or argv[1] not in commands:
        usage()
        return 1
    return commands[argv[1]].execute(ourstore, executor_context, sys.argv[2:], selected_options)


if __name__ ==  '__main__':
    sys.exit(main(sys.argv))
