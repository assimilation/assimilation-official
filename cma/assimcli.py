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

def RegisterCommand(funtoregister):
    'Register the given function as being a main command'
    commands[funtoregister.__name__] = funtoregister
    return funtoregister

#too many local variables
#pylint: disable=R0914 
@RegisterCommand
def query(store, executor_context, otherargs, language='en', fmtstring=None):
    'Perform given command line query and format output as requested.'

    if len(otherargs) < 1:
        usage()
        print >> sys.stderr, 'Need to supply a query name.'
        return 1
    queryname = otherargs[0]
    nvpairs = otherargs[1:]

    cypher = 'START q=node:ClientQuery("%s:*") WHERE q.queryname="%s" RETURN q LIMIT 1'
    
    metaquery = neo4j.CypherQuery(store.db, cypher % (queryname, queryname))
    
    request = store.load_cypher_node(metaquery, ClientQuery)

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

    if request is None:
        print >> sys.stderr, ('Query %s is unknown' % queryname)
    request.bind_store(store)
    try:
        iterator = request.cmdline_exec(executor_context, language, fmtstring, **params)
    except ValueError as err:
        print >> sys.stderr, ('Invalid %s query. Reason: %s' % (queryname, err))
        return 1
    for line in iterator:
        print line
    return 0

def usage():
    'print usage message'
    argv = sys.argv
    cmds = []
    for cmd in commands.keys():
        cmds.append(cmd)
    cmds.sort()
    cmdlist = ''
    delim = ''

    for cmd in commands.keys():
        cmdlist += (delim + cmd)
        delim = '|'

    print >> sys.stderr, 'Usage: %s %s' % (argv[0], cmdlist)
    return 1
    

def main(argv):
    'Main program for command line tool'
    executor_context = None
    ourstore = Store(neo4j.GraphDatabaseService(), uniqueindexmap={}, classkeymap={})
    for classname in GraphNode.classmap:
        GraphNode.initclasstypeobj(ourstore, classname)

    if len(argv) < 2 or argv[1] not in commands:
        usage()
        return 1
    return commands[argv[1]](ourstore, executor_context, sys.argv[2:])


if __name__ ==  '__main__':

    sys.exit(main(sys.argv))
