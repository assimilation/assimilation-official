#!/usr/bin/python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
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
allqueries = {}

app = Flask(__name__)

@app.route('/')
def hello_world():
    'Dummy code for printing hello world on the root (/) page'
    return 'Hello World! %s' % request.args.keys()

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
        query.validate_parameters(request.args)
    except ValueError, e:
        return 'Invalid Parameters to %s [%s]' % (queryname, str(e))
    return Response(query.execute(None, idsonly=False, expandJSON=True)
    ,               mimetype='application/javascript')

if __name__ == '__main__':
    def setup(host='localhost', port=7474, url=None, querypath=None):
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
        if url is None:
            url = ('http://%s:%d/db/data/' % (host, port))
        print >> sys.stderr, 'CREATING GraphDatabaseService("%s")' % url
        neodb = neo4j.GraphDatabaseService(url)
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
    setup()
    app.debug = True
    app.run()
