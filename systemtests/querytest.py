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
The querytest module is component of our system test tools architecture.
We can perform various kinds of queries and then validate the results against the
criteria we've been given.

It allows us to (for example) verify that after a nanoprobe goes down that
we updated the database accordingly.

At this point in time, I'm not sure if we should allow parameters to the queries, or just
reparse and recreate the query objects each time.  Since efficiency is not a huge criteria,
it might make sense to just compile them from text each time and not fool with parameters.

So that's what I'm going to do.
'''
import sys
from py2neo import neo4j

# pylint -- too few public methods
# pylint: disable=R0903
class QueryTest(object):
    '''
    This class performs queries and validates that the results
    meet some specific criteria.
    This class is a component of our system test tools - not part of
    the operational software.

    The general idea is that after a test completes, we can see if it updated
    the database correctly by running some particular query whose results
    can be evaluated for correctness.

    As it is currently written, this code might not work.
    It is written to run on the database, but it's on a different machine.
    That can work if we set up the permissions on the database correctly.
    Let it allow inbound connections on 0.0.0.0 -- not just 127.0.0.1.

    Kinda weird.  Maybe not as broken as I first thought.
    Just need to allow for queries from the test-control machine in the db config
    and make sure the Docker networking does what it should...

    The good news is, we should be passed a working database connection in the constructor
    so this is definitely SomebodyElse'sProblem :-D

    '''
    def __init__(self, store, querystring, classfactory, debug=False):
        '''Init function for the QueryTest class
        The querystring we're given will be given to the string <i>format</i> method
        along with a set of objects passed in to runandcheck() to create the final query.
        '''
        self.store = store
        self.db = store.db
        self.querystring = querystring
        self.debug = debug
        self.classfactory = classfactory


    def check(self, objectlist, validator=None, minrows=None, maxrows=None):
        '''
        We run a query and see if we like the results:
        - use the format() method to format the query using the objects in <i>objectlist</i>
        - run the query
        - validate the results of the query by calling <i>validator</i> on each row retrieved

        We return False if the validator dislikes any query row, or if the wrong number of
        rows was returned, and True if everything looks good.
        '''
        finalquerystring = self.querystring.format(*objectlist)
        query = neo4j.CypherQuery(self.db, finalquerystring)
        rowcount = 0
        for row in self.store.load_cypher_query(query, self.classfactory):
            rowcount += 1
            if validator is not None and not validator(row):
                print >> sys.stderr, ("VALIDATOR [%s] doesn't like row [%d] %s"
                %       (validator, rowcount, str(row)))
                return False
        if minrows is not None and rowcount < minrows:
            print >> sys.stderr, "Too few rows in result [%d]" % rowcount
            return False
        if maxrows is not None and rowcount > maxrows:
            print >> sys.stderr, "Too many rows in result [%d]" % rowcount
            return False
        return True

