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
This file defines classes which perform individual system tests.
'''
import sys, time, os
from py2neo import neo4j
sys.path.append('..')
sys.path.append('.')
from logwatcher import LogWatcher
from querytest import QueryTest
from docker import SystemTestEnvironment, TestSystem
import graphnodes as GN
from cmainit import CMAinit
from store import Store
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

    def __init__(self, store, logfilename, testenviron, debug=False):
        'Initializer for the AssimSysTest class'
        self.store = store
        self.logfilename = logfilename
        self.testenviron = testenviron
        self.debug = debug

    def _record(self, result):
        'Record results from a test -- success or failure'
        AssimSysTest.stats[self.__class__.__name__][result] += 1
        #print >> sys.stderr, '_RECORD RETURNING', result
        return result

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
            os.system("logger 'ERROR: Test %s timed out waiting for %s [timeout:%s]'"
            %   (self.__class__.__name__, str(watcher.regexes), timeout))
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
        os.system("logger -s 'ERROR: Test %s failed query %s'"
        %       (self.__class__.__name__, querystring))
        return self._record(AssimSysTest.FAIL)

    def run(self, nano=None, debug=None, timeout=30):
        'Abstract run method'
        raise NotImplementedError('AssimSysTest.run is an abstract method')

    @staticmethod
    def initenviron(logname, maxdrones, debug=False, timeout=90, nanodebug=0, cmadebug=0):
        'Initialize the test environment.'
        logwatch = LogWatcher(logname, [], timeout, returnonlymatch=True, debug=debug)
        logwatch.setwatch()
        sysenv = SystemTestEnvironment(logname, maxdrones, nanodebug=nanodebug, cmadebug=cmadebug)
        CMAinit(None)
        store = Store(neo4j.GraphDatabaseService
        (   'http://%s:%d/db/data/' % (sysenv.cma.ipaddr, 7474))
        ,   readonly=True)
        for classname in GN.GraphNode.classmap:
            GN.GraphNode.initclasstypeobj(store, classname)

        regexes = []
        for nano in sysenv.nanoprobes:
            regexes.append(r' %s cma INFO: Stored OS JSON data from (%s) '
            %       (sysenv.cma.hostname, nano.hostname))
            regexes.append(r' (%s) rsyslogd: \[.*] start' % (nano.hostname))
            regexes.append(r' (%s) nanoprobe\[.*]: NOTICE: Connected to CMA.  Happiness :-D'
            %   (nano.hostname))
        logwatch.setregexes(regexes)

        match = logwatch.lookforall(timeout=int(timeout+maxdrones*3))
        os.system('logger "$(grep MemFree: /proc/meminfo)"')
        if match is None:
            raise RuntimeError('Not all nanoprobes started.  Do you have another CMA running?')
        tq = QueryTest(store
        ,   '''START drone=node:Drone('*:*') WHERE drone.status = "up" RETURN drone'''
        ,   GN.nodeconstructor, debug=debug)

        if not tq.check([None,], minrows=maxdrones+1, maxrows=maxdrones+1
            ,   delay=0.5, maxtries=100):
            raise RuntimeError('Query of "up" status failed. Weirdness')
        return sysenv, store


@AssimSysTest.register
class StopNanoprobe(AssimSysTest):
    'A stop nanoprobe test'
    def run(self, nano=None, debug=None, timeout=30):
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
        regexes = (
        (r'%s cma INFO: System %s at \[::ffff:%s]:1984 reports graceful shutdown'
        %               (self.testenviron.cma.hostname, nano.hostname, nano.ipaddr)),
        (r" %s nanoprobe.*: INFO: Count of 'other' pkts received: "
        %           (nano.hostname)))
        watch = LogWatcher(self.logfilename, regexes, timeout=timeout, debug=debug)
        watch.setwatch()
        qstr =  (   '''START drone=node:Drone('*:*') '''
                     '''WHERE drone.designation = "{0.hostname}" and drone.status = "dead" '''
                     '''and drone.reason = "HBSHUTDOWN"       RETURN drone''')
        nano.stopservice(SystemTestEnvironment.NANOSERVICE)
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

        regexes = ( (r' %s cma INFO: Drone %s registered from address \[::ffff:%s]'
        %           (self.testenviron.cma.hostname, nano.hostname, nano.ipaddr))
        ,           (r' %s nanoprobe\[.*]: NOTICE: Connected to CMA.  Happiness :-D'
        %           (nano.hostname))
        )

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
        regex = (' %s .* INFO: Neo4j version .* // py2neo version .*'
                ' // Python version .* // java version.*') % cma.hostname
        watch = LogWatcher(self.logfilename, (regex,), timeout=timeout, debug=debug)
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
    def __init__(self, store, logfilename, testenviron, debug=False, delay=0):
        AssimSysTest.__init__(self, store, logfilename, testenviron, debug)
        self.delay = delay

    def run(self, nano=None, debug=None, timeout=180):
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
        regexes = (
        (           ' %s .* INFO: Neo4j version .* // py2neo version .*'
                    ' // Python version .* // java version.*' % (cma.hostname)),
        (r'%s cma INFO: System %s at \[::ffff:%s]:1984 reports graceful shutdown'
        %               (self.testenviron.cma.hostname, nano.hostname, nano.ipaddr)),
        (r" %s nanoprobe.*: INFO: Count of 'other' pkts received: "
        %           (nano.hostname)))
        watch = LogWatcher(self.logfilename, regexes, timeout=timeout, debug=debug)
        watch.setwatch()
        cma.stopservice(SystemTestEnvironment.CMASERVICE)
        nano.stopservice(SystemTestEnvironment.NANOSERVICE, async=True)
        cma.startservice(SystemTestEnvironment.CMASERVICE)
        if self.delay > 0:
            time.sleep(self.delay)
        qstr =  (   '''START drone=node:Drone('*:*') '''
                     '''WHERE drone.designation = "{0.hostname}" and drone.status = "dead" '''
                     '''and drone.reason = "HBSHUTDOWN"       RETURN drone''')
        rc = self.checkresults(watch, timeout, qstr, None, nano)
        if rc != AssimSysTest.SUCCESS:
            return rc
        # We have to do this in two parts because of the asynchronous shutdown above
        regexes = (
        (           r' %s cma INFO: Drone %s registered from address \[::ffff:%s]'
        %               (self.testenviron.cma.hostname, nano.hostname, nano.ipaddr)),
        (r' %s nanoprobe\[.*]: NOTICE: Connected to CMA.  Happiness :-D'
        %           (nano.hostname)))
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
    ,   service='bind9', monitorname=None):
        'Initializer for the DiscoverService class'
        AssimSysTest.__init__(self, store, logfilename, testenviron, debug)
        self.service=service
        if monitorname is None:
            monitorname = service
        self.monitorname = monitorname

    # W0221:Arguments number differs from overridden method
    # pylint: disable=W0221
    def run(self, nano=None, debug=None, timeout=240, service=None, monitorname=None):
        if service is None:
            service = self.service
        if monitorname is None:
            monitorname = self.monitorname
        if nano is None:
            nanozero = self.testenviron.select_nano_noservice(service=service)
            if nanozero is None or len(nanozero) < 1:
                return self._record(AssimSysTest.SKIPPED)
            nano = nanozero[0]
        assert service not in nano.runningservices
        if SystemTestEnvironment.NANOSERVICE not in nano.runningservices:
            startregexes = (r' %s cma INFO: Drone %s registered from address \[::ffff:%s]'
            %           (self.testenviron.cma.hostname, nano.hostname, nano.ipaddr)
            ,           (r' %s nanoprobe\[.*]: NOTICE: Connected to CMA.  Happiness :-D'
            %           (nano.hostname)))
            watch = LogWatcher(self.logfilename, startregexes, timeout=timeout, debug=debug)
            watch.setwatch()
            nano.startservice(SystemTestEnvironment.NANOSERVICE)
            match = watch.look(timeout=timeout)
            if match is None:
                return self._record(AssimSysTest.FAIL)
        regexes = (
        (r'%s cma INFO: System %s at \[::ffff:%s]:1984 reports graceful shutdown'
        %               (self.testenviron.cma.hostname, nano.hostname, nano.ipaddr)),
        (r" %s nanoprobe.*: INFO: Count of 'other' pkts received: "
        %           (nano.hostname)))
        watch = LogWatcher(self.logfilename, regexes, timeout=timeout, debug=debug)
        watch.setwatch()
        nano.stopservice(SystemTestEnvironment.NANOSERVICE)
        if watch.lookforall(timeout=timeout) is None:
            return self._record(AssimSysTest.FAIL)
        regexes = (
                    (r' %s cma INFO: Drone %s registered from address \[::ffff:%s]'
        %               (self.testenviron.cma.hostname, nano.hostname, nano.ipaddr)),
                    (r' %s nanoprobe\[.*]: NOTICE: Connected to CMA.  Happiness :-D'
        %           (nano.hostname)),
                    (r'%s cma INFO: Monitoring of service %s:.*:%s::.* activated'
        %               (self.testenviron.cma.hostname, nano.hostname, monitorname)),
                    (r'%s cma INFO: Service %s:.*:%s::.* is now operational'
        %               (self.testenviron.cma.hostname, nano.hostname, monitorname)))
        watch = LogWatcher(self.logfilename, regexes, timeout=timeout, debug=debug)
        watch.setwatch()
        nano.startservice(service)
        nano.startservice(SystemTestEnvironment.NANOSERVICE)
        # @TODO make a better query
        # but it should be enough to let us validate the rest
        qstr = (    '''START drone=node:Drone('*:*') '''
                     '''WHERE drone.designation = "{0.hostname}" and drone.status = "up" '''
                     '''RETURN drone''')
        return self.checkresults(watch, timeout, qstr, None, nano)


# A little test code...
if __name__ == "__main__":
    # pylint: disable=R0914
    def testmain(logname, maxdrones=3, debug=False):
        'Test our test cases'
        import datetime
        os.system("logger 'Starting test of our test cases'")
        try:
            sysenv, ourstore = AssimSysTest.initenviron(logname, maxdrones, debug
            ,       cmadebug=5, nanodebug=3)
        except AssertionError:
            print 'FAILED initial startup - which is pretty basic'
            print 'Any chance you have another CMA running??'
            raise RuntimeError('Another CMA is running(?)')

        #for cls in [DiscoverService for j in range(0,20)]:
        for cls in AssimSysTest.testset:
            badregexes=(' ERROR: ', ' CRIT: ', ' CRITICAL: ')
            #os.system("logger -s 'CREATED LOG WATCH with %s'" % str(badregexes))
            badwatch = LogWatcher(logname, badregexes, timeout=1, debug=0)
            badwatch.setwatch()
            print ('Starting %s test at %s...' % (cls.__name__, str(datetime.datetime.now())))
            os.system("logger 'Starting test %s'" %   (cls.__name__))
            if cls is DiscoverService:
                ret = cls(ourstore, logname, sysenv, debug=debug
                ,       service='bind9', monitorname='named').run()
            else:
                ret = cls(ourstore, logname, sysenv, debug=debug).run()
            #print >> sys.stderr, 'Got return of %s from test %s' % (ret, cls.__name__)
            assert ret == AssimSysTest.SUCCESS
            badmatch = badwatch.look(timeout=1)
            if badmatch is not None:
                print 'OOPS! Got bad results!', badmatch
                raise RuntimeError('Test %s said bad words! [%s]' % (cls.__name__, badmatch))
            os.system("logger -s 'BAD MATCH IS %s'" % str(badmatch))
        print >> sys.stderr, 'WOOT! All tests were successful!'

    if os.access('/var/log/syslog', os.R_OK):
        sys.exit(testmain('/var/log/syslog', debug=False))
    elif os.access('/var/log/messages', os.R_OK):
        sys.exit(testmain('/var/log/messages', debug=False))
