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
import sys
from assimevent import AssimEvent

DEBUG=False

class Observer:
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
    def test_simple_init_good(self):
        'Perform a few simple AssimEvent good initializations'
        AssimEvent.observers = []
        observer=Observer()
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
        AssimEvent.observers = []
        observer=Observer()
        badobserver=BadObserver()
        AssimEvent.registerobserver(observer)
        self.assertRaises(ValueError, AssimEvent,'first', 999)
        AssimEvent.registerobserver(badobserver)
        self.assertRaises(AttributeError, AssimEvent, 'first', AssimEvent.CREATEOBJ)
