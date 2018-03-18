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
import sys, time

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


    def check(self, objectlist, validator=None, minrows=None, maxrows=None
    ,           maxtries=300, delay=1):
        '''
        We run a query using _checkone_ repeatedly until we like the results or give up...
        It's hard to know when everything is done like it ought to be...
        Maxtries is the maximum of attempts to make for getting good query results
        Delay is the how long to wait between query calls
        '''
        j=0
        while j < maxtries:
            if self.checkone(objectlist, validator, minrows, maxrows):
                return True
            time.sleep(delay)
            j += 1

        print ('Rerunning failed query with debug=True')
        self.checkone(objectlist, validator, minrows, maxrows, debug=True)
        return False

    def checkone(self, objectlist, validator=None, minrows=None, maxrows=None, debug=None):
        '''
        We run a query and see if we like the results:
        - use the format() method to format the query using the objects in <i>objectlist</i>
        - run the query
        - validate the results of the query by calling <i>validator</i> on each row retrieved

        We return False if the validator dislikes any query row, or if the wrong number of
        rows was returned, and True if everything looks good.
        '''
        if debug is None:
            debug = self.debug
        finalquerystring = self.querystring.format(*objectlist)
        if debug:
            print >> sys.stderr, 'Final query string [%s]' % finalquerystring
        self.store.clean_store()
        rowcount = 0
        for row in self.store.load_cypher_nodes(finalquerystring, self.classfactory, debug=debug):
            rowcount += 1
            if debug:
                print >> sys.stderr, ("DEBUG: row [%d] is %s" % (rowcount, str(row)))
            if validator is not None and not validator(row):
                if debug:
                    print >> sys.stderr, ("VALIDATOR [%s] doesn't like row [%d] %s"
                    %       (validator, rowcount, str(row)))
                return False
        if minrows is not None and rowcount < minrows:
            if debug:
                print >> sys.stderr, "Too few rows in result [%d]" % rowcount
            return False
        if maxrows is not None and rowcount > maxrows:
            if debug:
                print >> sys.stderr, "Too many rows in result [%d]" % rowcount
            return False
        return True

# A little test code...
if __name__ == "__main__":
    # pylint: disable=C0411,C0413,E0401
    import os
    from sysmgmt import SystemTestEnvironment
    sys.path.append('..')
    import graphnodes as GN
    from store import Store
    from cmainit import CMAinit
    from logwatcher import LogWatcher


    def downbyshutdown(drone):
        'Return TRUE if this node is down by reason of HBSHUTDOWN'
        #print >> sys.stderr, 'VALIDATOR: status [%s] reason [%s]' % (drone.status, drone.reason)
        return drone.status == 'dead' and drone.reason == 'HBSHUTDOWN'

    def testmain(logname, maxdrones=25, debug=False):
        'A simple test main program'
        regexes = []
        #pylint says: [W0612:testmain] Unused variable 'j'
        #pylint: disable=W0612
        for j in range(0,maxdrones+1):
            regexes.append('Stored packages JSON data from *([^ ]*) ')
        logwatch = LogWatcher(logname, regexes, timeout=90, returnonlymatch=True)
        logwatch.setwatch()
        sysenv = SystemTestEnvironment(maxdrones)
        print >> sys.stderr, 'Systems all up and running.'
        url = ('http://%s:%d/db/data/' % (sysenv.cma.ipaddr, 7474))
        CMAinit(None)
        store = Store(neo4j.Graph(url), readonly=True)
        results = logwatch.lookforall()
        if debug:
            print >> sys.stderr, 'WATCH RESULTS:', results
        tq = QueryTest(store
        ,   "START drone=node:Drone('*:*') RETURN drone"
        ,   GN.nodeconstructor, debug=debug)
        print >> sys.stderr, 'Running Query'
        if tq.check([None,], minrows=maxdrones+1, maxrows=maxdrones+1):
            print 'WOOT! Systems passed query check after initial startup!'
        else:
            print 'Systems FAILED initial startup query check'
            print 'Do you have a second CMA running??'
            print 'Rerunning query with debug=True'
            tq.debug = True
            tq.check([None,], minrows=maxdrones+1, maxrows=maxdrones+1)
            return 1
        cma = sysenv.cma
        nano = sysenv.nanoprobes[0]
        regex = (r'%s cma INFO: System %s at \[::ffff:%s]:1984 reports graceful shutdown'
        %   (cma.hostname, nano.hostname, nano.ipaddr))
        #print >> sys.stderr, 'REGEX IS: [%s]' % regex
        logwatch = LogWatcher(logname, [regex,], timeout=30, returnonlymatch=False)
        logwatch.setwatch()
        nano.stopservice(SystemTestEnvironment.NANOSERVICE)
        logwatch.look()
        time.sleep(30)
        tq = QueryTest(store
        ,   ('''START drone=node:Drone('*:*') '''
                '''WHERE drone.designation = "{0.hostname}" RETURN drone''')
        ,   GN.nodeconstructor, debug=debug)
        if tq.check([nano,], downbyshutdown, maxrows=1):
            print 'WOOT! Systems passed query check after nano shutdown!'
        else:
            print 'Systems FAILED query check after nano shutdown'

    if os.access('/var/log/syslog', os.R_OK):
        sys.exit(testmain('/var/log/syslog'))
    elif os.access('/var/log/messages', os.R_OK):
        sys.exit(testmain('/var/log/messages'))
