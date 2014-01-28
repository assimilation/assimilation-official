#!/usr/bin/python
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
This module implements observer classes associated with Events in the Assimilation Project.
The base class of these various classes is the abstract class AssimEventObserver.
'''

from AssimCtypes import NOTIFICATION_SCRIPT_DIR, setpipebuf
from assimevent import AssimEvent
from assimjson import JSONtree
import fcntl
import os

#R0903: 35,0:AssimEventObserver: Too few public methods (1/2)
# pylint: disable=R0903
class AssimEventObserver(object):
    '''This class is an abstract base class which is all about observing AssimEvents.
    Our subclasses presumably know what to do with these events.
    '''

    def __init__(self):
        '''Initializer for AssimEventObserver class.
        '''
        AssimEvent.registerobserver(self)
        
    def notifynewevent(self, event):
        '''We get called when a new AssimEvent has occured that we might want to observe.
        But we are an abstract base class so we error out with NotImplementedError every time!
        '''
        raise NotImplementedError('AssimEventObserver is an abstract base class')

    def passes_constraints(self, event):
        '''Return True if the given event conforms to our constraints

        Parameters:
        -----------
        event: dict
            A dictionary describing our desired events
        '''
        # need to provide a real implementation of this ;-)
        return event is event and self is self

class FIFOEventObserver(AssimEventObserver):
    '''Objects in this class send JSON messages to a FIFO when events they are interested in
    are observed.  Each message encapsulates a single event, and is followed by a single
    NUL (zero) byte.  If the len(JSON) then 101 bytes are written to the
    FIFO, with the last being a single NUL byte (as noted in the previous sentence).
    '''
    def __init__(self, FIFOwritefd, constraints=None):
        '''Initializer for FIFO EventObserver class.

        Parameters:
        -----------
        FIFOwritefd: int
            a UNIX file descriptor pointing to the FIFO where event observers are listening...
        '''
        self.FIFOwritefd = FIFOwritefd
        self.constraints = constraints
        # We want a big buffer in the FIFO between us and our clients - they might be slow
        # 4 MB ought to be enough.  Most events should be smallish...
        pipebufsize = setpipebuf(FIFOwritefd, 4096*1024)
        if pipebufsize < (1024*1024):
            pipebufsize = setpipebuf(FIFOwritefd, 1024*1024)
            # Complain if we don't have at least 1 MB
            if pipebufsize < 1024*1024:
                print ('WARNING: pipe buffer size is only %s bytes' % pipebufsize)
        self.pipebufsize = pipebufsize
        # We don't want to hang around if we can't send out an event
        if hasattr(os, 'O_NDELAY'):
            fcntl.fcntl(fcntl.F_SETFL, os.O_NDELAY)
        elif hasattr(os, 'FNDELAY'):
            # we're avoiding a pylint complaint...
            fcntl.fcntl(fcntl.F_SETFL, getattr(os, 'FNDELAY'))
        AssimEventObserver.__init__(self)

    def notifynewevent(self, event):
        '''We get called when a new AssimEvent has occured that we might want to observe.
        When we get the call, we write a NUL-terminated JSON blob to our FIFO file descriptor
        '''
        if not self.passes_constraints(event):
            return

        json = str(JSONtree(event))
        jsonlen = len(json)
        json += chr(0)  # Will this work in python 3?
        rc = os.write(self.FIFOwritefd, json)
        assert(rc == (jsonlen + 1))


class ForkExecObserver(AssimEventObserver):
    '''Objects in this class execute scripts when events they are interested in
    are observed.
    '''
    def __init__(self, eventtypelist=None, objectclasslist=None, scriptdir=None):
        '''Initializer for ForkExecObserver class.

        Parameters:
        -----------
        eventtypelist: list
            A list of integer event types which we are interested in - or None
            for every event type
        objectclasslist: list
            A list of names of classes (all subclasses of GraphNode) representing the classes
            of objects we are interested in observing.  We require exact class matches
            not 'isinstance' type matches.  None means ever object type is acceptable.
        scriptdir: str
            The directory where our scripts are found.  We execute them all whenever an
            event of the selected type occurs.
        '''
        if scriptdir is None:
            scriptdir = NOTIFICATION_SCRIPT_DIR
        if not os.path.isdir(scriptdir):
            raise ValueError('Script directory [%s] is not a directory' % scriptdir)
        self.eventtypelist = eventtypelist
        self.objectclasslist = objectclasslist
        self.scriptdir = scriptdir
        AssimEventObserver.__init__(self)

    def listscripts(self):
        'Return the list of pathnames which we will execute when we get notified of an event'
        retval = []
        for script in os.listdir(self.scriptdir):
            path = os.path.join(self.scriptdir, script)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                retval.append(path)
        retval.sort()
        return retval

    @staticmethod
    def execscript(event, script):
        '''Execute a script with all the right parameters for this event
        We do not wait for it to complete, or check its return code.
        '''
        # FIXME: This needs to be improved.  We want two things, which will
        # require a little more code
        # (1) guarantee sequential execution - need for first notification to finish before
        #       starting a second one
        # (2)   non-blocking execution -- don't wait around for them to complete...
        # 
        #   At the present time, we have medium-crappy non-blocking execution, and that's all.
        #
        
        obj = event.associatedobject
        objclass = obj.__class__.__name__
        eventtype = AssimEvent.eventtypenames[event.eventtype]
        
        args = [script, eventtype, objclass]
        env = {}
        # TODO add the host name that's reporting the problem if it's a monitor action
        # We have the address the report came from, but it's an IP address, not a host name
        for item in os.environ:
            env[item] = os.environ[item]
        if event.extrainfo is not None:
            for extra in event.extrainfo:
                env['ASSIM_%s' % extra] = str(event.extrainfo[extra])
        for attr in obj.__dict__.keys():
            avalue = getattr(obj, attr)
            if isinstance(avalue, (str, unicode, int, float, long, bool)):
                env['ASSIM_%s' % attr] = str(avalue)
        env['ASSIM_JSONobj'] = str(JSONtree(obj))
        os.spawnve(os.P_NOWAITO, script, args, env)
        
    def notifynewevent(self, event):
        '''We get called when a new AssimEvent has occured that we might want to observe.
        We filter which scripts are executed according to our initial parameters.
        '''
        if self.eventtypelist is not None:
            if event.eventtype not in self.eventtypelist:
                return
        if self.eventtypelist is not None:
            clsname = event.associatedobject.__class__.__name__
            # I suppose we could use the nodetype instead...
            # this is slightly more general - but it probably doesn't matter...
            if clsname not in self.objectclasslist:
                return
        # It's an event we want our scripts to know about...
        # So, let's let them know!
        for script in self.listscripts():
            self.execscript(event, script)
