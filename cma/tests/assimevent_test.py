#!/usr/bin/python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2013 - Assimilation Systems Limited
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
_suites = ['all', 'events']
import sys
sys.path.append("../cma")
sys.path.append("/usr/local/lib/python2.7/dist-packages")
from testify import *
import os, sys, tempfile, time, signal
from assimevent import AssimEvent
from assimeventobserver import ForkExecObserver

DEBUG=False

AssimEvent.enable_all_observers()

def makescript(createdscriptname, outfile):
    'Create the requested script - outputting to requested file'
    script='''#!/bin/sh
    # Simple script to test external event interfaces
    (   echo "====START===="
        j=1
        for arg
        do
            echo "ARG${j}=$arg"
            j=$(expr $j + 1)
        done
        env |  grep '^ASSIM_' | LC_ALL=C sort
        echo "==== JSON START ===="
        cat
        printf '\n==== JSON END ====\n'
        echo "====END===="
    ) >> %s 2>&1
'''
    f = open(createdscriptname, 'w')
    f.write(script % outfile)
    f.close()
    os.chmod(createdscriptname, 0755)

class ClientClass:
    def __init__(self):
        self.nodetype = 'ClientClass'
        pass


class DummyObserver:
    'An observer class for testing AssimEvents - we just keep a list of notifications'
    def __init__(self):
        self.events = []
        pass

    def notifynewevent(self, event):
        self.events.append(event)
        

class BadObserver:
    "An un-observer class for testing AssimEvent failures - doesn't do anything"
    def __init__(self):
        pass


class TestAssimEvent(TestCase):
    'Class for basic AssimEvent testing'

    @staticmethod
    def waitfor(pathname, expectedcontent, timeout=20):
        for j in range(0, timeout):
            f=open(pathname, 'r')
            content=f.read()
            f.close()
            if content == expectedcontent:
                return
            time.sleep(0.1)
        return

    def test_simple_init_good(self):
        'Perform a few simple AssimEvent good initializations'
        AssimEvent.enable_all_observers()
        AssimEvent.observers = []
        observer=DummyObserver()
        AssimEvent.registerobserver(observer)
        event1 = AssimEvent('first', AssimEvent.CREATEOBJ)
        self.assertEqual(len(observer.events), 1)
        self.assertTrue(observer.events[0], event1)
        self.assertEqual(AssimEvent.unregisterobserver(observer), True)
        event2 = AssimEvent('second', AssimEvent.CREATEOBJ)
        self.assertEqual(len(observer.events), 1)
        self.assertTrue(observer.events[0], event1)
        AssimEvent.registerobserver(observer)
        event3 = AssimEvent('third', AssimEvent.CREATEOBJ)
        self.assertEqual(len(observer.events), 2)
        self.assertTrue(observer.events[0], event3)

    def test_simple_init_bad(self):
        'Perform a few simple AssimEvent bad initializations'
        AssimEvent.enable_all_observers()
        AssimEvent.observers = []
        observer=DummyObserver()
        badobserver=BadObserver()
        AssimEvent.registerobserver(observer)
        self.assertRaises(ValueError, AssimEvent, 'first', 999)
        self.assertRaises(AttributeError, AssimEvent.registerobserver, badobserver)

    def test_fork_exec_event(self):
        '''This test will create a fork/exec event observer script
        and then test to see if its getting invoked properly...
        '''
        AssimEvent.enable_all_observers()
        tmpdir = tempfile.mkdtemp('.d', 'testexec_')
        (fd, pathname) = tempfile.mkstemp('.out.txt')
        execscript = os.path.join(tmpdir, 'observer.sh')
        makescript(execscript, pathname)
        AssimEvent.observers = []
        observer=ForkExecObserver(scriptdir=tmpdir)
        dummyclient = ClientClass()
        dummyclient.fred='fred'
        dummyclient.sevenofnine='Annika'
        dummyclient.foo = {'foo': 'bar'}

        self.assertEqual(observer.listscripts(), [execscript,])
        AssimEvent.registerobserver(observer)
        AssimEvent(dummyclient, AssimEvent.CREATEOBJ)
        AssimEvent(dummyclient, AssimEvent.OBJUP, extrainfo={'origaddr': '10.10.10.254'})
        os.close(fd)
        expectedcontent=\
'''====START====
ARG1=create
ARG2=ClientClass
ASSIM_fred=fred
ASSIM_nodetype=ClientClass
ASSIM_sevenofnine=Annika
==== JSON START ====
{"associatedobject":{"foo":{"foo":"bar"},"fred":"fred","nodetype":"ClientClass","sevenofnine":"Annika"},"eventtype":0,"extrainfo":null}
==== JSON END ====
====END====
====START====
ARG1=up
ARG2=ClientClass
ASSIM_fred=fred
ASSIM_nodetype=ClientClass
ASSIM_origaddr=10.10.10.254
ASSIM_sevenofnine=Annika
==== JSON START ====
{"associatedobject":{"foo":{"foo":"bar"},"fred":"fred","nodetype":"ClientClass","sevenofnine":"Annika"},"eventtype":1,"extrainfo":{"origaddr":"10.10.10.254"}}
==== JSON END ====
====END====
'''
        TestAssimEvent.waitfor(pathname, expectedcontent)
        f=open(pathname, 'r')
        content=f.read()
        f.close()
        self.assertEqual(content, expectedcontent)
        os.unlink(execscript)
        os.unlink(pathname)
        os.rmdir(tmpdir)

    def test_fork_exec_killchild(self):
        '''This test will create a fork/exec event observer script
        and then kill the child listener and verify that it is handled
        correctly.
        '''
        AssimEvent.enable_all_observers()
        tmpdir = tempfile.mkdtemp('.d', 'testexec_')
        (fd, pathname) = tempfile.mkstemp('.out.txt')
        execscript = os.path.join(tmpdir, 'observer.sh')
        makescript(execscript, pathname)
        AssimEvent.observers = []
        observer=ForkExecObserver(scriptdir=tmpdir)
        dummyclient = ClientClass()
        dummyclient.fred='fred'
        dummyclient.sevenofnine='Annika'
        dummyclient.foo = {'foo': 'bar'}
        AssimEvent.registerobserver(observer)
        try:
            os.kill(observer.childpid, signal.SIGKILL)
        except OSError:
            # "docker build" doesn't let us kill processes...
            # so we give up on this test and call it good...
            os.unlink(execscript)
            os.unlink(pathname)
            os.rmdir(tmpdir)
            return
        time.sleep(0.1)
        AssimEvent(dummyclient, AssimEvent.CREATEOBJ)
        # Death of our FIFO child will cause it to get respawned, and
        # message sent to new child.  No messages should be lost.
        expectedcontent=\
'''====START====
ARG1=create
ARG2=ClientClass
ASSIM_fred=fred
ASSIM_nodetype=ClientClass
ASSIM_sevenofnine=Annika
==== JSON START ====
{"associatedobject":{"foo":{"foo":"bar"},"fred":"fred","nodetype":"ClientClass","sevenofnine":"Annika"},"eventtype":0,"extrainfo":null}
==== JSON END ====
====END====
'''
        TestAssimEvent.waitfor(pathname, expectedcontent)
        f=open(pathname, 'r')
        content=f.read()
        f.close()
        self.assertEqual(content, expectedcontent)
        os.close(fd)
        os.unlink(execscript)
        os.unlink(pathname)
        os.rmdir(tmpdir)
