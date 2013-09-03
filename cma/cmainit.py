
#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2011, 2012 - Alan Robertson <alanr@unix.sh>
#
#  The Assimilation software is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  The Assimilation software is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
'''
This module defines our CMAdb class and so on...
'''

import os
import sys
import logging, logging.handlers
from py2neo import neo4j
from AssimCtypes import CFG_ARRAY, CFG_BOOL, CFG_INT64, CFG_STRING, CFG_ARRAY, CFG_FLOAT
from AssimCclasses import pyNetAddr
from store import Store
from cmadb import CMAdb

class CMAinit(object):

    def __init__(self, io, host='localhost', port=7474, cleanoutdb=False, debug=False):
        'Initialize and construct a global database instance'
        print >> sys.stderr, 'CALLING NEW initglobal'
        CMAdb.log = logging.getLogger('cma')
        CMAdb.debug = debug
        CMAdb.io = io
        from hbring import HbRing
        syslog = logging.handlers.SysLogHandler(address='/dev/log'
        ,       facility=logging.handlers.SysLogHandler.LOG_DAEMON)
        syslog.setFormatter(logging.Formatter('%(name)s %(levelname)s: %(message)s'))
        CMAdb.log.addHandler(syslog)
        CMAdb.log.setLevel(logging.DEBUG)
        url = ('http://%s:%d/db/data/' % (host, port))
        print >> sys.stderr, 'CREATING GraphDatabaseService("%s")' % url
        neodb = neo4j.GraphDatabaseService(url)
        if cleanoutdb:
            print >> sys.stderr, 'CLEANINGOUT DB (new)'
            CMAdb.log.info('Re-initializing the NEO4j database')
            self.delete_all(neodb)
            print >> sys.stderr, 'DB CLEANED (new)'
            print >> sys.stderr, 'Reiniting database'
        CMAdb.cdb = CMAdb(db=neodb)
        CMAdb.store = Store(neodb, CMAdb.uniqueindexes,CMAdb.classkeymap)
        from transaction import Transaction
        CMAdb.transaction = Transaction()
        print >> sys.stderr,  'CMAdb:', CMAdb
        print >> sys.stderr,  'CMAdb.store(cmadb.py):', CMAdb.store
        CMAdb.TheOneRing = CMAdb.store.load_or_create(HbRing, name='The_One_Ring'
        ,           ringtype= HbRing.THEONERING)
        CMAdb.transaction.commit_trans(io)
        print >> sys.stderr, 'COMMITTING Store'
        print >> sys.stderr, 'Transaction Commit results:', CMAdb.store.commit()
        print >> sys.stderr, 'Store COMMITTED'


    def delete_all(self, db):
        'Empty everything out of our database - start over!'
        query = neo4j.CypherQuery(db
        ,   'start n=node(*) match n-[r?]-() where id(n) <> 0 delete n,r')
        result = query.execute()
        if CMAdb.debug:
            CMAdb.log.debug('Cypher query to delete all relationships'
                ' and nonzero nodes executing: %s' % query)
            CMAdb.log.debug('Execution results: %s' % str(result))
        indexes = db.get_indexes(neo4j.Node)
        for index in indexes.keys():
            if CMAdb.debug:
                CMAdb.log.debug('Deleting index %s' % str(index))
            db.delete_index(neo4j.Node, index)

        


if __name__ == '__main__':
    print >> sys.stderr, 'Starting'
    CMAinit(None, cleanoutdb=True, debug=True)
    if CMAdb.store.transaction_pending:
        print >> sys.stderr, 'Transaction pending in:', CMAdb.store
        print >> sys.stderr, 'Results:', CMAdb.store.commit()
    print >> sys.stderr, 'Init done'
