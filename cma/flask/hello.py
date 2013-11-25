#!/usr/bin/python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
import sys
sys.path.append('..')
from flask import Flask, request, Response
from py2neo import neo4j
from consts import CMAconsts
from store import Store
from graphnodes import GraphNode
from query import ClientQuery
global qstore, allqueries
qstore = None
queryquery = None
allqueries = {}
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World! %s' % request.args.keys()

@app.route('/querymeta/<queryname>')
def query_meta(queryname):
    return 'Hello Query Metadata "%s"!'  % queryname

@app.route('/doquery/<queryname>')
def doquery(queryname):
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
    
    host = 'localhost'
    port = 7474
    url = ('http://%s:%d/db/data/' % (host, port))
    print >> sys.stderr, 'CREATING GraphDatabaseService("%s")' % url
    neodb = neo4j.GraphDatabaseService(url)
    qstore = Store(neodb, None, None)
    print GraphNode.classmap
    for classname in GraphNode.classmap:
        GraphNode.initclasstypeobj(qstore, classname)
    print "LOADING TREE!"
    queries = ClientQuery.load_tree(qstore, "/home/alanr/monitor/src/queries")
    for q in queries:
        allqueries[q.queryname] = q
    qstore.commit()
    for q in allqueries:
        allqueries[q].bind_store(qstore)
    #queryquery = qstore.load_or_create(ClientQuery, queryname='GetAQuery')
    #queryquery.bind_store(qstore)
    Q='START q1=node:ClientQuery({queryname}) RETURN q1 LIMIT 1'
    queryquery = neo4j.CypherQuery(neodb, Q)
    #print 'Neodb =', neodb
    #print 'qstore =', qstore
    app.debug = True
    app.run()
