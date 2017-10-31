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
'''
This file defines classes which perform individual system tests.
'''
import sys, time, os
sys.path.append('..')
sys.path.append('.')
from logwatcher import LogWatcher
from querytest import QueryTest
from sysmgmt import SystemTestEnvironment, TestSystem
# pylint: disable=E0401
import graphnodes as GN
from cmainit import CMAinit
from store import Store
from cmadb import CMAdb
from hbring import HbRing
from droneinfo import Drone

def logger(s, hardquote=True):
    'Log our single argument to syslog'
    print >> sys.stderr, ('LOGGER: %s' % str(s))
    if hardquote:
        s = s.replace("'", "'\\''")
        os.system("logger -s '%s'" % s)
    else:
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        os.system('logger -s "%s"' % s)

def get_ring(store):
    'Return The One Ring'
    if not hasattr(CMAdb, 'TheOneRing'):
        CMAdb.TheOneRing = store.load_or_create(HbRing, name='The_One_Ring',
                                                      ringtype=HbRing.THEONERING)
    return CMAdb.TheOneRing

#def get_ring_members(ring):
#    'Return the members of the ring - in ring-order'
#    return ring.members_ring_order()

def get_nano_neighbors(store, ring, nano):
    'Get the ring-neighbors of this nanoprobe for the given ring'
    if ring is None:
        ring = get_ring(store)
    query = ('''START d=node:Drone('*:*') WHERE d.designation = "%s" return d'''
             % nano.hostname)
    drone = store.load_cypher_node(query, Drone)
    neighbors = []
    prevnode = None
    for prevnode in store.load_in_related(drone, ring.ournexttype, Drone):
        neighbors.append(prevnode.designation)
    assert (len(neighbors) <= 1)
    for nextnode in store.load_related(drone, ring.ournexttype, Drone):
        neighbors.append(nextnode.designation)
    assert (len(neighbors) <= 2)
    return neighbors


class AssimSysTest(object):
    '''AssimSysTest is an abstract base class for all our system-level tests.
    '''
    SUCCESS = 1
    FAIL    = 2
    SKIPPED = 3

    testnames = {}
    testset = []
    stats = {}


    @staticmethod
    def register(ourclass):
        'Decorator for registering a TestCase'
        AssimSysTest.testset.append(ourclass)
        AssimSysTest.testnames[ourclass.__name__] = ourclass
        AssimSysTest.stats[ourclass.__name__] = {
            AssimSysTest.SUCCESS:0, AssimSysTest.FAIL: 0, AssimSysTest.SKIPPED:0
        }
        return ourclass

    def nano_start_regexes(self, nano):
        'Return a list of the expected regexes for a nanoprobe starting'
        cma = self.testenviron.cma
        return [
            r' %s cma INFO: Drone %s registered from address \[::ffff:%s]'
            %           (cma.hostname, nano.hostname, nano.ipaddr),
            r' (%s) nanoprobe\[.*]: NOTICE: Connected to CMA.  Happiness :-D'     % (nano.hostname),
            r' (%s) nanoprobe\[.*]: INFO: .* Configuration from CMA is complete.' % (nano.hostname),
            r' %s cma INFO: Processed u?n?changed tcpdiscovery JSON data from (%s) into graph.'
            %       (cma.hostname, nano.hostname),
        ]
    def nano_stop_regexes(self, nano):
        'Return a list of the expected regexes for a nanoprobe stopping'
        cma = self.testenviron.cma
        return [
        r' %s .*NOTICE: nanoprobe: exiting on SIGTERM' % (nano.hostname),
        r' %s cma INFO: System %s at \[::ffff:%s]:1984 reports graceful shutdown'
        %               (cma.hostname, nano.hostname, nano.ipaddr),
        r" %s nanoprobe.*: INFO: Count of 'other' pkts received: " % (nano.hostname),
        ]

    def nano_kill9_regexes(self, nano):
        'Return a list of the expected regexes for a nanoprobe being kill-9ed'
        cma = self.testenviron.cma
        #print >> sys.stderr, 'NANO NEIGHBORS', get_nano_neighbors(self.store, None, nano)
        regexes = [
        (r' %s cma INFO: Node %s has been reported as dead by address .* Reason: HBDEAD packet'
         %  (cma.hostname, nano.hostname))
        ]
        neighbors = set()
        for peer in get_nano_neighbors(self.store, None, nano):
            if peer in neighbors:
                continue
            neighbors.add(peer)
            #%s nanoprobe[345]: WARN: Peer at address [::ffff:172.17.0.3]:1984 is dead
            regexes.append(' %s nanoprobe.*: WARN: Peer at address \\[::ffff:%s]:1984 is dead.*'
                           % (peer, nano.ipaddr))
        return regexes

    def cma_start_regexes(self):
        'Return a list of the expected regexes for the CMA starting'
        cma = self.testenviron.cma
        return [
            (' %s .* INFO: Neo4j version .* // py2neo version .*'
                ' // Python version .* // (java|openjdk) version.*' % cma.hostname),
        ]

    def nano_startmonitor_regexes(self, nano, monitorname):
        'Return a list of the expected regexes for starting the given service monitoring'
        cma = self.testenviron.cma
        return [
            r' %s cma INFO: Monitoring of service %s:.*:%s::.* activated'
            %       (cma.hostname, nano.hostname, monitorname),
        ]

    def nano_service_start_regexes(self, nano, monitorname):
        'Return a list of regexes of messages expected when starting the given monitored service'
        cma = self.testenviron.cma
        return [
            r' %s cma INFO: Service %s:.*:%s::.* is now operational'
            %       (cma.hostname, nano.hostname, monitorname)
        ]

    def nano_service_stop_regexes(self, nano, monitorname):
        'Return a list of regexes of messages expected when stopping the given monitored service'
        cma = self.testenviron.cma
        return [
            r' %s cma INFO: Service %s:.*:%s::.* failed with'
            %       (cma.hostname, nano.hostname, monitorname),
        ]

    # [R0201:AssimSysTest.cma_stop_regexes] Method could be a function
    # pylint: disable=R0201
    def cma_stop_regexes(self):
        'Return a list of the expected regexes for the CMA stopping'
        #cma = self.testenviron.cma
        return []

    def __init__(self, store, logfilename, testenviron, debug=False):
        'Initializer for the AssimSysTest class'
        self.store = store
        self.logfilename = logfilename
        self.testenviron = testenviron
        self.debug = debug
        self.result = None

    def _record(self, result):
        'Record results from a test -- success or failure'
        AssimSysTest.stats[self.__class__.__name__][result] += 1
        #print >> sys.stderr, '_RECORD RETURNING', result
        self.result = result
        return result

    def replace_result(self, newresult):
        'Replace this test result with an updated result (usually failure)'
        AssimSysTest.stats[self.__class__.__name__][self.result] -= 1
        self.result = newresult
        AssimSysTest.stats[self.__class__.__name__][newresult] += 1

    # pylint - R0913: too mary arguments
    # pylint: disable=R0913
    def checkresults(self, watcher, timeout, querystring, validator
        ,   nano, service=None, allregexes=True, debug=False, minrows=1, maxrows=1):
        '''
        A utility function for checking the results of a test.  It assumes
        that you have already done a watcher.setwatch and initiated the
        test.  We then wait for the test results in the logs and
        perform the query to validate the results.
        '''

        query = QueryTest(self.store, querystring, GN.nodeconstructor, debug=debug)
        if allregexes:
            match = watcher.lookforall(timeout=timeout)
        else:
            match = watcher.look(timeout=timeout)
        if debug:
            print >> sys.stderr, ('DEBUG: Match returned %s' % match)
        if match is None:
            logger('ERROR: Test %s timed out waiting for %s [timeout:%s]'
            %   (self.__class__.__name__, str(watcher.unmatched), timeout))
            return self._record(AssimSysTest.FAIL)
        if debug:
            print('DEBUG: Test %s found regex %s'
            %   (self.__class__.__name__, str(watcher.regexes)))
        if query.check((nano, self.testenviron.cma, service), validator
            ,       minrows=minrows, maxrows=maxrows):
            if debug:
                print('DEBUG: Test %s passed query %s'
                %   (self.__class__.__name__, querystring))
            return self._record(AssimSysTest.SUCCESS)

        print >> sys.stderr, ('DEBUG: query.check() FAILED')
        logger('ERROR: Test %s failed query %s' % (self.__class__.__name__, querystring))
        return self._record(AssimSysTest.FAIL)

    def run(self, nano=None, debug=None, timeout=30):
        'Abstract run method'
        raise NotImplementedError('AssimSysTest.run is an abstract method')

    @staticmethod
    # too many local variables
    # pylint: disable=R0914
    def initenviron(logname, maxdrones, mgmtsystem, debug=False, cmaimage='', nanoimages=[], timeout=90, nanodebug=0, cmadebug=0):
        'Initialize the test environment.'
        logwatch = LogWatcher(logname, [], timeout, returnonlymatch=True, debug=debug)
        logwatch.setwatch()
    
        sysenv = SystemTestEnvironment(logname, maxdrones, mgmtsystem, cmaimage=cmaimage, nanoimages=nanoimages, nanodebug=nanodebug, cmadebug=cmadebug)
        CMAinit(None, host=str(sysenv.cma.ipaddr), readonly=True,
                neologin=SystemTestEnvironment.NEO4JLOGIN, neopass=SystemTestEnvironment.NEO4JPASS)
        url = 'http://%s:%d/db/data/' % (sysenv.cma.ipaddr, 7474)
        print >> sys.stderr, 'OPENING Neo4j at URL %s' % url
        neo4j.authenticate('%s:7474' % sysenv.cma.ipaddr,
                           SystemTestEnvironment.NEO4JLOGIN,
                           SystemTestEnvironment.NEO4JPASS)
        store = Store(neo4j.Graph(url), readonly=True)
        for classname in GN.GraphNode.classmap:
            GN.GraphNode.initclasstypeobj(store, classname)

        logger('$(grep MemFree: /proc/meminfo)', hardquote=False)
        tq = QueryTest(store
        ,   '''START drone=node:Drone('*:*') WHERE drone.status = "up" RETURN drone'''
        ,   GN.nodeconstructor, debug=debug)

        if not tq.check([None,], minrows=maxdrones+1, maxrows=maxdrones+1
            ,   delay=0.5, maxtries=20):
            sysenv.cma.cleanupwhendone = False
            raise RuntimeError('Query of "up" status failed. Weirdness')
        return sysenv, store


@AssimSysTest.register
class StopNanoprobe(AssimSysTest):
    'A stop nanoprobe test'
    def run(self, nano=None, debug=None, timeout=180):
        'Actually stop the nanoprobe and see if it worked'
        if debug is None:
            debug = self.debug
        if nano is None:
            nanozero = self.testenviron.select_nano_service()
            if len(nanozero) > 0:
                nano = nanozero[0]
        if (nano is None or nano.status != TestSystem.RUNNING or
            SystemTestEnvironment.NANOSERVICE not in nano.runningservices):
            return self._record(AssimSysTest.SKIPPED)
        regexes = self.nano_stop_regexes(nano)
        watch = LogWatcher(self.logfilename, regexes, timeout=timeout, debug=debug)
        watch.setwatch()
        qstr =  (   '''START drone=node:Drone('*:*') '''
                     '''WHERE drone.designation = "{0.hostname}" and drone.status = "dead" '''
                     '''and drone.reason = "HBSHUTDOWN"       RETURN drone''')
        nano.stopservice(SystemTestEnvironment.NANOSERVICE)
        return self.checkresults(watch, timeout, qstr, None, nano)

@AssimSysTest.register
class KillNanoprobe(AssimSysTest):
    'A kill -9 nanoprobe test'
    def run(self, nano=None, debug=None, timeout=180):
        'Actually stop the nanoprobe and see if it worked'
        if debug is None:
            debug = self.debug
        if nano is None:
            nanozero = self.testenviron.select_nano_service()
            if len(nanozero) > 0:
                nano = nanozero[0]
        if (nano is None or nano.status != TestSystem.RUNNING or
            SystemTestEnvironment.NANOSERVICE not in nano.runningservices):
            return self._record(AssimSysTest.SKIPPED)
        regexes = self.nano_kill9_regexes(nano)
        print >> sys.stderr, 'KILL9_REGEXES ARE:', regexes
        watch = LogWatcher(self.logfilename, regexes, timeout=timeout, debug=debug)
        watch.setwatch()
        qstr =  (   '''START drone=node:Drone('*:*') '''
                     '''WHERE drone.designation = "{0.hostname}" and drone.status = "dead" '''
                     '''and drone.reason = "HBDEAD packet received"       RETURN drone''')
        nano.kill9service(SystemTestEnvironment.NANOSERVICE)
        #print >> sys.stderr, 'NANO NEIGHBORS', get_nano_neighbors(self.store, None, nano)
        return self.checkresults(watch, timeout, qstr, None, nano)

@AssimSysTest.register
class StartNanoprobe(AssimSysTest):
    'A start nanoprobe test'
    def run(self, nano=None, debug=None, timeout=240):
        'Actually start the nanoprobe and see if it worked'
        if debug is None:
            debug = self.debug
        if nano is None:
            nanozero = self.testenviron.select_nano_noservice()
            if len(nanozero) > 0:
                nano = nanozero[0]
        if (nano is None or nano.status != TestSystem.RUNNING
            or  SystemTestEnvironment.NANOSERVICE in nano.runningservices):
            return self._record(AssimSysTest.SKIPPED)

        regexes = self.nano_start_regexes(nano)

        watch = LogWatcher(self.logfilename, regexes, timeout=timeout, debug=debug)
        watch.setwatch()
        qstr = (    '''START drone=node:Drone('*:*') '''
                     '''WHERE drone.designation = "{0.hostname}" and drone.status = "up" '''
                     '''RETURN drone''')
        nano.startservice(SystemTestEnvironment.NANOSERVICE)
        return self.checkresults(watch, timeout, qstr, None, nano)

@AssimSysTest.register
class FlipNanoprobe(AssimSysTest):
    '''A flip nanoprobe test - if it's up, bring it down -- and vice versa'''
    def run(self, nano=None, debug=None, timeout=240):
        'Actually flip the nanoprobe and see if it worked'
        if debug is None:
            debug = self.debug
        if nano is None:
            nanozero = self.testenviron.select_nanoprobe()
            if len(nanozero) > 0:
                nano = nanozero[0]
        if nano is None:
            return self._record(AssimSysTest.SKIPPED)
        if SystemTestEnvironment.NANOSERVICE in nano.runningservices:
            return self._record(
                StopNanoprobe(self.store
                ,   self.logfilename, self.testenviron).run
                (nano, debug=self.debug, timeout=timeout))
        return self._record(
            StartNanoprobe(self.store, self.logfilename
            ,   self.testenviron).run(nano, debug=self.debug, timeout=timeout))

@AssimSysTest.register
class RestartNanoprobe(AssimSysTest):
    'A restart nanoprobe test, stop then restart a nanoprobe'
    def __init__(self, store, logfilename, testenviron, debug=False, delay=0):
        AssimSysTest.__init__(self, store, logfilename, testenviron, debug)
        self.delay = delay

    def run(self, nano=None, debug=None, timeout=240):
        'Actually stop and start (restart) the nanoprobe and see if it worked'
        if debug is None:
            debug = self.debug
        if nano is None:
            try:
                nano = self.testenviron.select_nano_service()[0]
            except IndexError:
                nano = None
        if nano is None:
            return self._record(AssimSysTest.SKIPPED)
        rc = StopNanoprobe(self.store
            ,   self.logfilename, self.testenviron).run(nano, debug=self.debug, timeout=timeout)
        if rc != AssimSysTest.SUCCESS:
            return self._record(rc)
        if self.delay > 0:
            time.sleep(self.delay)
        return self._record(StartNanoprobe(self.store
        ,   self.logfilename, self.testenviron).run(nano, debug=self.debug, timeout=timeout))


@AssimSysTest.register
class RestartCMA(AssimSysTest):
    'A restart CMA test: stop then restart the CMA.  Scary stuff!'
    def __init__(self, store, logfilename, testenviron, debug=False, delay=0):
        AssimSysTest.__init__(self, store, logfilename, testenviron, debug)
        self.delay = delay

    def run(self, nano=None, debug=None, timeout=60):
        'Actually stop and start (restart) the CMA and see if it worked'
        if debug is None:
            debug = self.debug
        cma = self.testenviron.cma
        cma.stopservice(SystemTestEnvironment.CMASERVICE)
        regexes = self.cma_start_regexes()
        watch = LogWatcher(self.logfilename, regexes, timeout=timeout, debug=debug)
        watch.setwatch()
        if self.delay > 0:
            time.sleep(self.delay)
        cma.startservice(SystemTestEnvironment.CMASERVICE)
        # This just makes sure the database is still up - which it should be...
        # Once we receive the CMA update message, we really should already be good to go
        qstr =  '''START one=node(*) RETURN one LIMIT 1'''
        return self.checkresults(watch, timeout, qstr, None, nano)

@AssimSysTest.register
class RestartCMAandNanoprobe(AssimSysTest):
    'A restart CMA+nanoprobe test: stop then restart the CMA followed by a nanoprobe reset'
    def __init__(self, store, logfilename, testenviron, debug=False, delay=0):
        AssimSysTest.__init__(self, store, logfilename, testenviron, debug)
        self.delay = delay

    def run(self, nano=None, debug=None, timeout=240):
        'Actually stop and start (restart) the CMA and see if it worked'
        if debug is None:
            debug = self.debug
        rc = RestartCMA(self.store, self.logfilename, self.testenviron, debug=debug
        ,       delay=self.delay).run(timeout=timeout)
        if rc != AssimSysTest.SUCCESS:
            return self._record(rc)
        return self._record(RestartNanoprobe(self.store, self.logfilename, self.testenviron
        ,   debug=debug, delay=self.delay).run(timeout=timeout))

@AssimSysTest.register
class SimulCMAandNanoprobeRestart(AssimSysTest):
    'Simultaneously restart the CMA and a nanoprobe'
    def __init__(self, store, logfilename, testenviron, debug=False, delay=1):
        AssimSysTest.__init__(self, store, logfilename, testenviron, debug)
        self.delay = delay

    def run(self, nano=None, debug=None, timeout=300):
        '''Our default timeout is so long because we can take a while to give up shutting down
        the nanoprobe - an ACK timeout might have to occur before it can shut down.
        '''
        if debug is None:
            debug = self.debug
        if nano is None:
            nanozero = self.testenviron.select_nano_service()
            if len(nanozero) < 1:
                return self._record(AssimSysTest.SKIPPED)
        nano = nanozero[0]
        cma = self.testenviron.cma
        regexes = self.nano_stop_regexes(nano)
        regexes.extend(self.cma_stop_regexes())
        regexes.extend(self.cma_start_regexes())
        watch = LogWatcher(self.logfilename, regexes, timeout=timeout, debug=debug)
        watch.setwatch()
        cma.stopservice(SystemTestEnvironment.CMASERVICE)
        nano.stopservice(SystemTestEnvironment.NANOSERVICE, async=True)
        if self.delay > 0:
            time.sleep(self.delay)
        cma.startservice(SystemTestEnvironment.CMASERVICE)
        qstr =  (   '''START drone=node:Drone('*:*') '''
                     '''WHERE drone.designation = "{0.hostname}" and drone.status = "dead" '''
                     '''and drone.reason = "HBSHUTDOWN"       RETURN drone''')
        rc = self.checkresults(watch, timeout, qstr, None, nano)
        if rc != AssimSysTest.SUCCESS:
            return rc
        AssimSysTest.stats[self.__class__.__name__][rc] -= 1
        # We have to do this in two parts because of the asynchronous shutdown above
        regexes = self.nano_start_regexes(nano)
        watch = LogWatcher(self.logfilename, regexes, timeout=timeout, debug=debug)
        watch.setwatch()
        nano.startservice(SystemTestEnvironment.NANOSERVICE)
        qstr = (    '''START drone=node:Drone('*:*') '''
                     '''WHERE drone.designation = "{0.hostname}" and drone.status = "up" '''
                     '''RETURN drone''')
        return self.checkresults(watch, timeout, qstr, None, nano)

@AssimSysTest.register
class DiscoverService(AssimSysTest):
    '''We find a system not running some particular service, then we
    start the service and restart the nanoprobe - forcing it to
    discover the service pretty quickly.
    '''
    def __init__(self, store, logfilename, testenviron, debug=False
    ,   service='ssh', monitorname=None):
        'Initializer for the DiscoverService class'
        AssimSysTest.__init__(self, store, logfilename, testenviron, debug)
        self.service=service
        if monitorname is None:
            monitorname = service
        self.monitorname = monitorname

    # W0221:Arguments number differs from overridden method
    # pylint: disable=W0221
    def run(self, nano=None, debug=None, timeout=240, service=None, monitorname=None):
        if debug is None:
            debug = self.debug
        if service is None:
            service = self.service
        if monitorname is None:
            monitorname = self.monitorname
        if nano is None:
            nanozero = self.testenviron.select_nano_noservice(service=service)
            if nanozero is None or len(nanozero) < 1:
                return self._record(AssimSysTest.SKIPPED)
            else:
                nano = nanozero[0]
        assert service not in nano.runningservices
        if SystemTestEnvironment.NANOSERVICE not in nano.runningservices:
            startregexes = self.nano_start_regexes(nano)
            watch = LogWatcher(self.logfilename, startregexes, timeout=timeout, debug=debug)
            watch.setwatch()
            nano.startservice(SystemTestEnvironment.NANOSERVICE)
            match = watch.look(timeout=timeout)
            if match is None:
                logger('ERROR: Test %s timed out waiting for any of %s [timeout:%s]'
                %   (self.__class__.__name__, str(watch.regexes), timeout))
                return self._record(AssimSysTest.FAIL)
        regexes = self.nano_stop_regexes(nano)
        watch = LogWatcher(self.logfilename, regexes, timeout=timeout, debug=debug)
        watch.setwatch()
        nano.stopservice(SystemTestEnvironment.NANOSERVICE)
        if watch.lookforall(timeout=timeout) is None:
            logger('ERROR: Test %s timed out waiting for all of %s [timeout:%s]'
            %   (self.__class__.__name__, str(watch.unmatched), timeout))
            return self._record(AssimSysTest.FAIL)
        regexes = self.nano_start_regexes(nano)
        regexes.extend(self.nano_startmonitor_regexes(nano, monitorname))
        regexes.extend(self.nano_service_start_regexes(nano, monitorname))
        watch = LogWatcher(self.logfilename, regexes, timeout=timeout, debug=debug)
        watch.setwatch()
        nano.startservice(service)
        nano.startservice(SystemTestEnvironment.NANOSERVICE)
        if watch.lookforall(timeout=timeout) is None:
            logger('ERROR: Test %s timed out waiting for all of %s [timeout:%s]'
            %   (self.__class__.__name__, str(watch.unmatched), timeout))
            return self._record(AssimSysTest.FAIL)
        # @TODO make a better query
        # but it should be enough to let us validate the rest
        qstr = (    '''START drone=node:Drone('*:*') '''
                     '''WHERE drone.designation = "{0.hostname}" and drone.status = "up" '''
                     '''RETURN drone''')
        return self.checkresults(watch, timeout, qstr, None, nano, debug=debug)

#
#   Here are some other tests that I think we should do:
#
#   Kill -9 on a nanoprobe
#       There are two non-skip cases:
#           - Where 2 systems total (CMA+1) are up
#           - Where more than 2 (> CMA+1) are up
#       The software has special cases up to 4 systems, IIRC.
#       Skip this test if all nanoprobes are down
#
#   Move the IP address the nanoprobe is connecting from to an alternate IP address
#       This requires allocating/setting up 2 IP addresses per system
#   Switch the port a nanoprobe is connecting from
#   Shut down all (up) nanoprobes at once
#   Start up all (down) nanoprobes at once
#   Restarting the CMA, its nanoprobe and every other nanoprobe approximately at once
#   Shut down half of the nanoprobes - every other one starting from the CMA's nanoprobe
#
#
#   To do these I'll need to look at:
#   - finding immediate neighbor(s) from the neighbor graph
#   - returning all the systems in the neighbor graph in order by neighbor connectivity
#   - allocating 2 IP addresses per system
#   - choosing a second unoccupied port (1985?)
#


# A little test code...
if __name__ == "__main__":
    # pylint: disable=R0914
    def testmain(logname, maxdrones=3, debug=False):
        'Test our test cases'
        logger('Starting test of our test cases')
        try:
            sysenv, ourstore = AssimSysTest.initenviron(logname, maxdrones, debug
            ,       cmadebug=5, nanodebug=3)
        except AssertionError:
            print 'FAILED initial startup - which is pretty basic'
            print 'Any chance you have another CMA running??'
            raise RuntimeError('Another CMA is running(?)')

        badregexes=(' ERROR: ', ' CRIT: ', ' CRITICAL: '
        # 'HBDEAD'
        #,   r'Peer at address .* is dead'
        ,   r'OUTALLDONE .* while in state NONE'
        )
        #for cls in [SimulCMAandNanoprobeRestart for j in range(0,20)]:
        #for j in range(0,10):
        #for cls in [DiscoverService for j in range(0,100)]:
        for cls in AssimSysTest.testset:
            badwatch = LogWatcher(logname, badregexes, timeout=1, debug=0)
            logger('CREATED LOG WATCH with %s' % str(badregexes))
            badwatch.setwatch()
            logger('Starting test %s' %   (cls.__name__))
            if cls is DiscoverService:
                ret = cls(ourstore, logname, sysenv, debug=debug
                ,       service='ssh', monitorname='check_ssh').run()
            else:
                ret = cls(ourstore, logname, sysenv, debug=debug).run()
            #print >> sys.stderr, 'Got return of %s from test %s' % (ret, cls.__name__)
            badmatch = badwatch.look(timeout=1)
            if badmatch is not None:
                print 'OOPS! Got bad results!', badmatch
                raise RuntimeError('Test %s said bad words! [%s]' % (cls.__name__, badmatch))
            assert ret == AssimSysTest.SUCCESS or ret == AssimSysTest.SKIPPED
            #assert ret == AssimSysTest.SUCCESS
        logger('WOOT! All tests were successful!')

    if os.access('/var/log/syslog', os.R_OK):
        sys.exit(testmain('/var/log/syslog', debug=False))
    elif os.access('/var/log/messages', os.R_OK):
        sys.exit(testmain('/var/log/messages', debug=False))
