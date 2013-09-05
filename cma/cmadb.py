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
from py2neo import neo4j
#from AssimCtypes import *
from store import Store
from consts import CMAconsts
from graphnodes import CMAclass


# R0903: Too few public methods
# pylint: disable=R0903
class CMAdb:
    '''Class defining our Neo4J database.'''
    nodename = os.uname()[1]
    debug = True
    transaction = None
    log = None
    store = None
    globaldomain = 'global'


    def __init__(self, db=None):
        self.db = db
        CMAdb.store = Store(self.db, CMAconsts.uniqueindexes, CMAconsts.classkeymap)
        self.dbversion = self.db.neo4j_version
        self.nextlabelid = 0
        if CMAdb.debug:
            CMAdb.log.debug('Neo4j version: %s' % str(self.dbversion))
            print >> sys.stderr, ('HELP Neo4j version: %s' % str(self.dbversion))
    #
    #   Make sure all our indexes are present and that we
    #   have a top level node for each node type for creating
    #   IS_A relationships to.  Not sure if the IS_A relationships
    #   are really needed, but they're kinda cool...
    #
        
        indices = [key for key in CMAconsts.is_indexed.keys() if CMAconsts.is_indexed[key]]
        self.indextbl = {}
        self.nodetypetbl = {}
        for index in indices:
            #print >>sys.stderr, ('Ensuring index %s exists' % index)
            self.indextbl[index] = self.db.get_index(neo4j.Node, index)
            self.indextbl[index] = self.db.get_or_create_index(neo4j.Node, index)
        #print >>sys.stderr, ('Ensuring index %s exists' % 'nodetype')
        self.indextbl['nodetype'] = self.db.get_or_create_index(neo4j.Node, 'nodetype')
        
        classroot = CMAdb.store.load_or_create(CMAclass, name='object')
        #print >> sys.stderr, 'classroot', classroot

        for index in CMAconsts.is_indexed.keys():
            top = CMAdb.store.load_or_create(CMAclass, name=index)
            assert str(top.name) == str(index)
            CMAdb.store.relate_new(top, CMAconsts.REL_isa, classroot)
            self.nodetypetbl[index] = top
        CMAconsts.classtypeobjs = self.nodetypetbl
            
        self.ringindex = self.indextbl[CMAconsts.NODE_ring]
        self.ipindex = self.indextbl[CMAconsts.NODE_ipaddr]
        self.macindex = self.indextbl[CMAconsts.NODE_NIC]
        self.switchindex = self.indextbl[CMAconsts.NODE_system]
        self.droneindex = self.indextbl[CMAconsts.NODE_drone]
        CMAconsts.classindextable = self.indextbl
        if self.store.transaction_pending:
            #print >> sys.stderr,  'self.store:', self.store
            result = self.store.commit()
            if CMAdb.debug:
                print >> sys.stderr, 'COMMIT results:', result
        else:
            print >> sys.stderr, 'Cool! Everything already created!'


if __name__ == '__main__':
    from cmainit import CMAinit
    print >> sys.stderr, 'Starting'
    CMAinit(None, cleanoutdb=True, debug=True)
    print >> sys.stderr, 'Init done'
