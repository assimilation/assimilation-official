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
This is the main program for our Assimilation System Test module.
'''
import os, sys, random, datetime, optparse, struct
sys.path.append('..')
from logwatcher import LogWatcher
from testcases import AssimSysTest

def logit(msg):
    'log things to the system log and to stdout'
    os.system("logger '%s'" %   (msg))
    print ("%s: %s" % (datetime.datetime.now(), msg))

def perform_tests(testset, sysenv, store, itermax, logname, debug=False):
    'Actually perform the given set of tests the given number of times, etc'
    badregexes=(r' (ERROR:|CRIT:|CRITICAL:|nanoprobe\[[0-9]*]: segfault at|'
            #r'Peer at address .* is dead|'
            r'OUTALLDONE .* while in state NONE'
            r')',)
    itercount=1
    while True:
        test = random.choice(testset)
        badwatch = LogWatcher(logname, badregexes, timeout=1, debug=0)
        logit("STARTING test %d - %s" %   (itercount, test.__name__))
        os.system('logger -s "Load Avg: $(cat /proc/loadavg)"')
        os.system('logger -s "$(grep MemFree: /proc/meminfo)"')
        badwatch.setwatch()
        if test.__name__ == 'DiscoverService':
            testobj = test(store, logname, sysenv, debug=debug
            ,       service='bind9', monitorname='named')
        else:
            testobj = test(store, logname, sysenv, debug=debug)
        ret = testobj.run()
        match = badwatch.look()
        if match is not None:
            logit('BAD MESSAGE from Test %d %s: %s' % (itercount, test.__name__, match))
            testobj.replace_result(AssimSysTest.FAIL)
            ret = AssimSysTest.FAIL
        if ret == AssimSysTest.SUCCESS:
            logit('Test %d %s succeeded!' % (itercount, test.__name__))
            itercount += 1
        elif ret == AssimSysTest.FAIL:
            logit('Test %d %s FAILED :-(' % (itercount, test.__name__))
            itercount += 1
        elif ret == AssimSysTest.SKIPPED:
            logit('Test %d %s skipped' % (itercount, test.__name__))
        else:
            logit('Test %d %s RETURNED SOMETHING REALLY WEIRD [%s]'
            %   (itercount, test.__name__, str(ret)))
            testobj.replace_result(AssimSysTest.FAIL)
        print ''
        if itercount > itermax:
            break
    return summarize_tests()

def summarize_tests():
    '''Summarize the results of the tests - to syslog and stderr
    We return the number of failures.
    '''
    testnames = AssimSysTest.testnames.keys()
    testnames.sort()
    maxlen = max([len(name) for name in testnames])
    totals = {AssimSysTest.SUCCESS:0, AssimSysTest.FAIL:0, AssimSysTest.SKIPPED:0}
    logit('%*s %7s %7s %7s' % (maxlen, 'TEST NAME', 'SUCCESS', 'FAIL', 'SKIPPED'))
    for name in testnames:
        logit('%*s %7d %7d %7d' % (maxlen, name
        ,   AssimSysTest.stats[name][AssimSysTest.SUCCESS]
        ,   AssimSysTest.stats[name][AssimSysTest.FAIL]
        ,   AssimSysTest.stats[name][AssimSysTest.SKIPPED]))
        totals[AssimSysTest.SUCCESS]    += AssimSysTest.stats[name][AssimSysTest.SUCCESS]
        totals[AssimSysTest.FAIL]       += AssimSysTest.stats[name][AssimSysTest.FAIL]
        totals[AssimSysTest.SKIPPED]    += AssimSysTest.stats[name][AssimSysTest.SKIPPED]
    logit('%*s %7s %7s %7s' % (maxlen, '_' * maxlen, '_____', '_____', '_____'))
    logit('%*s %7d %7d %7d' % (maxlen, 'TOTALS'
    ,   totals[AssimSysTest.SUCCESS]
    ,   totals[AssimSysTest.FAIL]
    ,   totals[AssimSysTest.SKIPPED]))
    if totals[AssimSysTest.FAIL] == 0:
        logit('%*s' % (maxlen, 'ALL TESTS SUCCEEDED!'))
    else:
        logit('%*s' % (maxlen, ('%d TESTS FAILED :-(' % totals[AssimSysTest.FAIL])))
    return totals[AssimSysTest.FAIL]

def testmain(logname):
    'This is the actual main program for the assimilation tests'
    maxdrones=10
    itercount=30
    testset = []

    parser = optparse.OptionParser(prog='assimtest'
            ,   description='System Test utility for the Assimilation software.'
            ,   usage=
    '''assimtest.py [options] iteration-count [number-of-systems-in-test-environment]
    The number of systems defaults to iteration-count/4.
    The minimum number of nanoprobe-only systems will always be >= 2.
    You must run this as root and have docker.io installed.''')
    parser.add_option('-t', '--testcases'
    ,   action='append'
    ,   default=[]
    ,   dest='testcases'
    ,   choices=AssimSysTest.testnames.keys()
    ,   help='specific test cases to use')

    parser.add_option('-c', '--cmadebug'
    ,   action='store'
    ,   default=0
    ,   dest='cmadebug'
    ,   choices=('0', '1', '2', '3', '4', '5')
    ,   help='CMA debug level [0-5]')

    parser.add_option('-n', '--nanodebug'
    ,   action='store'
    ,   default=0
    ,   dest='nanodebug'
    ,   choices=('0', '1', '2', '3', '4', '5')
    ,   help='Nanoprobe debug level [0-5]')

    parser.add_option('-s', '--seed'
    ,   action='store'
    ,   default=None
    ,   dest='seed'
    ,   help
    =   'Random seed - a comma-separated list of 8 integers between 0 and 255 - from previous run')

    (opts, args) = parser.parse_args()
    opts.cmadebug = int(opts.cmadebug)
    opts.nanodebug = int(opts.nanodebug)

    if len(args) == 1:
        itercount = int(args[0])
        maxdrones = max(int((itercount+2) / 4), 2)
    elif len(args) == 2:
        itercount = int(args[0])
        maxdrones = int(args[1])
    else:
        parser.parse_args(['--help'])
        return 1

    if opts.seed is None:
        # Prepare Random number generator
        f = open("/dev/urandom", "r")
        seed=struct.unpack("BBBBBBBB", f.read(8))
        f.close()
    else:
        seed = tuple([int(elem) for elem in opts.seed.split(',')])
        assert len(seed) == 8
    random.Random().seed(seed) # The hash of those 8 bytes is used as the seed

    print '\n'
    logit('Iteration count: %d / Number of client systems: %d' % (itercount, maxdrones))
    logit("Random Seed:     %s" % str(seed))

    print '\n'

    # Set up specific test cases -- if requested
    if len(opts.testcases) > 0:
        testset = [AssimSysTest.testnames[name] for name in opts.testcases]
    else:
        testset = [test for test in AssimSysTest.testset]

    # Set up the test environment as requested
    env, store = AssimSysTest.initenviron(logname, maxdrones
    ,   (opts.cmadebug > 0 or opts.nanodebug > 0)
    ,   cmadebug=opts.cmadebug, nanodebug=opts.nanodebug)

    logit('CMA:  %s %15s %6d %s' % (env.cma.hostname, env.cma.ipaddr, env.cma.pid, env.cma.name))
    for nano in env.nanoprobes:
        logit('nano: %s %15s %6d %s' % (nano.hostname, nano.ipaddr, nano.pid, nano.name))

    print '\n'
    logit('STARTING %d tests on %d nanoprobes + CMA' % (itercount, maxdrones))
    return perform_tests(testset, env, store, itercount, logname)


sys.stdout = sys.stderr # Get rid of that nasty buffering...
sys.exit(testmain('/var/log/syslog'))

