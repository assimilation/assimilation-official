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
_suites = ['all', 'external']
import sys, os, subprocess, time, datetime, re
from testify import *


pingcount=30

placestolook = ('.', '..', 'testcode', '../testcode', '../../testcode'
,   '../bin/testcode', '../../bin/testcode', 'src/testcode', '../src/testcode'
,   'root_of_binary_tree/testcode', '../root_of_binary_tree/testcode'
,   '../../root_of_binary_tree/testcode')

def findcmd(argv):
    arg0 = argv[0]
    if arg0.startswith('/'):
        return argv
    for prefix in placestolook:
        fullpath = os.path.join(prefix, arg0)
        if os.access(fullpath, os.X_OK):
            argv[0] = fullpath
            return argv
    raise IOError('Cannot locate file %s' % arg0)
    

sudocmd = '/usr/bin/sudo'
gtestdir = None
class TestExternal(TestCase):
    '''
    Run all the tests that don't run natively under testify
    '''
    gtestdir = None
    gtestpattern = re.compile('gtest[0-9]+$')   # pattern of names of all our gtest tests...

    @class_setup
    def setUp(self):
        '''This function is designed to Fail right away and make sure the other
        tests don't bother running if we can't find an example test.
        Turns out to be handy to know where that command is anyway...
        '''
        cmd=['gtest01',]
        findcmd(cmd)
        TestExternal.gtestdir = os.path.dirname(cmd[0])



    def runacommand(self, argv, sudo=False):
        print '\n******RUNNING TEST COMMAND %s' % str(argv)
        findcmd(argv)
        if sudo and os.geteuid() != 0:
            argv.insert(0, sudocmd)
            print 'ARGV: %s' %  str(argv)
        start = datetime.datetime.now()
        subprocess.check_call(argv)    # Will raise an exception if it exits non-zero
        end = datetime.datetime.now()
        diff = end - start
        print '\nSUCCESS: %s exited with return code 0 in %s' % (str(argv), diff)
        pass

    def  test_valgrind(self):
        self.runacommand(['grind.sh',], sudo=True)

    def  test_gtest_cases(self):
        files = os.listdir(TestExternal.gtestdir)
        files.sort()
        for f in files:
            if TestExternal.gtestpattern.match(f):
                self.runacommand([f,], sudo=True)

    def  test_pinger(self):
        self.runacommand(['grindping.sh',],sudo=False)

    def  test_discovery_tests(self):
        self.runacommand(['test_discovery.sh',],sudo=False)

    @class_teardown
    def tearDown(self):
        pass


if __name__ == "__main__":
    run()
