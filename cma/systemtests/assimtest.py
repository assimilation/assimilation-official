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

def perform_tests(testset, sysenv, store, itercount, logname, debug=False):
    'Actually perform the given set of tests the given number of times, etc'
    badregex=' (ERROR|CRIT|CRITICAL): '
    badcount = 0
    for j in range(1, itercount+1):
        test = random.choice(testset)
        badwatch = LogWatcher(logname, (badregex,), timeout=0, returnonlymatch=False)
        logit("STARTING test %d - %s" %   (j, test.__name__))
        badwatch.setwatch()
        if test.__name__ == 'DiscoverService':
            ret = test(store, logname, sysenv, debug=debug
            ,       service='bind9', monitorname='named').run()
        else:
            ret = test(store, logname, sysenv, debug=debug).run()
        if ret == AssimSysTest.SUCCESS:
            logit('Test %s succeeded!' % test.__name__)
        elif ret == AssimSysTest.FAIL:
            logit('Test %s FAILED :-(' % test.__name__)
            badcount += 1
        elif ret == AssimSysTest.SKIPPED:
            logit('Test %s skipped' % test.__name__)
        else:
            logit('Test %s RETURNED SOMETHING REALLY WEIRD [%s]' % (test.__name__, str(ret)))
        print ''
    if badcount == 0:
        logit('ALL TESTS SUCCEEDED!')
    else:
        logit("%d tests failed :-(" % badcount)
    return badcount


def testmain(logname):
    'This is the actual main program for the assimilation tests'
    maxdrones=10
    itercount=30
    testset = []
    usagestring = (
    '''assimtest.py [options] iteration-count [number-of-systems-in-test-environment]
    The number of systems defaults to iteration-count/4.
    The minimum number of nanoprobe-only systems will always be >= 2.
    You must run this as root and have to have docker.io installed.''')

    parser = optparse.OptionParser(prog='assimtest'
            ,   description='System Test utility for the Assimilation software.'
            ,   usage=usagestring)
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

    # Prepare Random number generator
    f = open("/dev/urandom", "r")
    seed=struct.unpack("BBBBBBBB", f.read(8))
    f.close()
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
    ,   cmadebug=0, nanodebug=0)

    logit('CMA:  %s %15s %6d' % (env.cma.hostname, env.cma.ipaddr, env.cma.pid))
    for nano in env.nanoprobes:
        logit('nano: %s %15s %6d' % (nano.hostname, nano.ipaddr, nano.pid))

    print '\n'
    logit('STARTING %d tests on %d nanoprobes + CMA' % (itercount, maxdrones))
    return perform_tests(testset, env, store, itercount, logname)


sys.exit(testmain('/var/log/syslog'))

