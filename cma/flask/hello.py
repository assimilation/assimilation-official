#!/usr/bin/python
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
'''
Prototype code for providing a REST interface for the Assimilation project.
'''
import sys
sys.path.append('..')
from flask import Flask, request, Response
from py2neo import neo4j
from store import Store
from graphnodes import GraphNode
from query import ClientQuery
import cmainit
from AssimCtypes import QUERYINSTALL_DIR
# These next two imports are actually needed because they register
# some types. But pylint doesn't know that.
# pylint: disable=W0611
from droneinfo import Drone
from hbring import HbRing
allqueries = {}

app = Flask(__name__)

@app.route('/')
def hello_world():
    'Dummy code for printing hello world on the root (/) page'
    return 'Hello World! %s' % str(request.args)

@app.route('/querymeta/<queryname>')
def query_meta(queryname):
    '''Dummy code for returning the metadata for a particular query
    - that doesn't do anything yet.'''
    return 'Hello Query Metadata "%s"!'  % queryname

@app.route('/doquery/<queryname>')
def doquery(queryname):
    '''Prototype code for executing a particular query.
    The error cases are detected, but not handled correctly yet.
    They all return apparent success, just no JSON.
    '''
    if queryname not in allqueries:
        return 'No such query: %s' % queryname
    query = allqueries[queryname]
    try:
        req = {}
        argdict = dict(request.args)
        for arg in argdict:
            req[arg] = str(argdict[arg][0])
        query.validate_parameters(req)
    except ValueError, e:
        return 'Invalid Parameters to %s [%s]' % (queryname, str(e))
    return Response(query.execute(None, idsonly=False, expandJSON=True, maxJSON=1024, **req)
    ,               mimetype='application/javascript')

if __name__ == '__main__':
    def setup(dbhost='localhost', dbport=7474, dburl=None, querypath=None):
        '''
        Program to set up for running our REST server.
        We do these things:
            - Attach to the database
            - Initialize our type objects so things like ClientQuery will work...
            - Load the queries into the database from flat files
                Not sure if doing this here makes the best sense, but it
                works, and currently we're the only one who cares about them
                so it seems reasonable -- at the moment ;-)
                Also we're most likely to iterate changing on those relating to the
                REST server, so fixing them just by restarting the REST server seems
                to make a lot of sense (at the moment)
            - Remember the set of queries in the 'allqueries' hash table
        '''
        if dburl is None:
            dburl = ('http://%s:%d/db/data/' % (dbhost, dbport))
        print >> sys.stderr, 'CREATING GraphDatabaseService("%s")' % dburl
        neodb = neo4j.GraphDatabaseService(dburl)
        qstore = Store(neodb, None, None)
        print GraphNode.classmap
        for classname in GraphNode.classmap:
            GraphNode.initclasstypeobj(qstore, classname)
        print "LOADING TREE!"
        if querypath is None:
            querypath = "/home/alanr/monitor/src/queries"
        queries = ClientQuery.load_tree(qstore, querypath)
        for q in queries:
            allqueries[q.queryname] = q
        qstore.commit()
        for q in allqueries:
            allqueries[q].bind_store(qstore)
        #Q = 'START q1=node:ClientQuery({queryname}) RETURN q1 LIMIT 1'
        #queryquery = neo4j.CypherQuery(neodb, Q)
        #print 'Neodb =', neodb
        #print 'qstore =', qstore

    cmainit.CMAinit(io=None, readonly=True, use_network=False)
    setup(querypath=QUERYINSTALL_DIR)
    app.debug = True
    app.run()
