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
This module implements observer classes associated with Events in the Assimilation Project.
The base class of these various classes is the abstract class AssimEventObserver.
'''

from AssimCtypes import NOTIFICATION_SCRIPT_DIR, setpipebuf
from AssimCclasses import pyConfigContext
from assimevent import AssimEvent
from assimjson import JSONtree
import fcntl
import os, signal
import sys

DEBUG = True
DEBUG = False

#R0903: 35,0:AssimEventObserver: Too few public methods (1/2)
# pylint: disable=R0903
class AssimEventObserver(object):
    '''This class is an abstract base class which is all about observing AssimEvents.
    Our subclasses presumably know what to do with these events.
    '''

    def __init__(self, constraints):
        '''Initializer for AssimEventObserver class.

        Parameters:
        -----------
        constraints: dict
            A dict describing our desired events. The constraints in the dict are
            effectively ANDed together.  Each key is an attribute name in either
            the event itself or its associated object.  The value associated with
            each attribute is either a list or a scalar value.  A list implies that
            any one of those values is acceptable.  A scalar value implies that it
            *must* have that value.

            This should be able to constrain the type of event we're looking at, the
            type of event-object we're looking at, and the domain of the event-object -
            and lots of other potentially useful things.

            See the "is_interesting" method below for implementation details...
        '''
        self.constraints = constraints
        AssimEvent.registerobserver(self)

    def notifynewevent(self, event):
        '''We get called when a new AssimEvent has occured that we might want to observe.
        But we are an abstract base class so we error out with NotImplementedError every time!
        '''
        raise NotImplementedError('AssimEventObserver is an abstract base class')

    def is_interesting(self, event):
        '''Return True if the given event conforms to our constraints.  That is, would it
        be interesting to our observers.

        Parameters:
        -----------
        event: AssimEvent
            The event we're evaluating to see if our listeners want to hear about it.
        '''
        if self.constraints is None:
            return True
        for attr in self.constraints:
            value = AssimEventObserver.getvalue(event, attr)
            if value is None:
                # @FIXME: Is this the right treatment of no-such-value (None)?
                continue
            constraint = self.constraints[attr]
            if isinstance(constraint, (list, dict)):
                if value not in constraint:
                    return False
            if value != constraint:
                return False
        return True

    @staticmethod
    def getvalue(event, attr):
        'Helper function to return a the value of a constraint expression'
        value = None
        if hasattr(event, attr):
            value = getattr(event, attr)
        else:
            try:
                value = event.associatedobject.get(attr)
            except AttributeError:
                if hasattr(event.associatedobject, attr):
                    value = getattr(event.associatedobject, attr)
        return value


class FIFOEventObserver(AssimEventObserver):
    '''Objects in this class send JSON messages to a FIFO when events they are interested in
    are observed.  Each message encapsulates a single event, and is followed by a single
    NUL (zero) byte.  If the len(JSON) is 100, then 101 bytes are written to the
    FIFO, with the last being a single NUL byte (as noted in the previous sentence).
    '''

    NULstr = chr(0) # Will this work in python 3?

    def __init__(self, FIFOwritefd, constraints=None, maxerrcount=None):
        '''Initializer for FIFO EventObserver class.

        Parameters:
        -----------
        FIFOwritefd: int
            a UNIX file descriptor pointing to the FIFO where event observers are listening...
        '''
        self.FIFOwritefd = FIFOwritefd
        self.constraints = constraints
        self.errcount = 0
        self.maxerrcount = maxerrcount
        # We want a big buffer in the FIFO between us and our clients - they might be slow
        # 4 MB ought to be plenty.  Most events are only a few hundred bytes...
        pipebufsize = setpipebuf(FIFOwritefd, 4096*1024)
        if pipebufsize < (1024*1024):
            pipebufsize = setpipebuf(FIFOwritefd, 1024*1024)
            # Complain if we don't have at least 1 MB
            if pipebufsize < 1024*1024:
                print ('WARNING: pipe buffer size is only %s bytes' % pipebufsize)
        self.pipebufsize = pipebufsize
        # We don't want to hang around if we can't send out an event
        if hasattr(os, 'O_NDELAY'):
            fcntl.fcntl(FIFOwritefd, fcntl.F_SETFL, os.O_NDELAY)
        elif hasattr(os, 'FNDELAY'):
            # Using getattr avoids a pylint complaint...
            fcntl.fcntl(FIFOwritefd, fcntl.F_SETFL, getattr(os, 'FNDELAY'))
        AssimEventObserver.__init__(self, constraints)

    def notifynewevent(self, event):
        '''We get called when a new AssimEvent has occured that we might want to observe.
        When we get the call, we write a NUL-terminated JSON blob to our FIFO file descriptor
        '''
        # @TODO add the host name that's reporting the problem if it's a monitor action
        # We have the address the report came from, but it's an IP address, not a host name
        if not self.is_interesting(event):
            return

        json = str(JSONtree(event))
        jsonlen = len(json)
        json += FIFOEventObserver.NULstr
        try:
            if DEBUG:
                print >> sys.stderr, '*************SENDING EVENT (%d bytes)' % (jsonlen+1)
            os.write(self.FIFOwritefd, json)
            self.errcount = 0
            if DEBUG:
                print >> sys.stderr, '*************EVENT SENT (%d bytes)' % (jsonlen+1)
        except OSError, e:
            if DEBUG:
                print >> sys.stderr, '+++++++++++++++++FIFO write error: %s' % str(e)
            self.errcount += 1
            self.ioerror(event)

    def ioerror(self, unusedevent):
        '''This function gets called when we get an I/O error writing to the FIFO.
        This is likely an EPIPE (broken pipe) error.
        '''
        unusedevent = unusedevent # Make pylint happy...
        if self.maxerrcount is not None and self.errcount > self.maxerrcount:
            AssimEvent.unregisterobserver(self)

class ForkExecObserver(FIFOEventObserver):
    '''Objects in this class execute scripts when events they are interested in
    are observed.  Note that these events come to us through a pipe
    that we create, but is written to by our base class FIFOEventObserver...
    '''
    def __init__(self, constraints=None, scriptdir=None):
        '''Initializer for ForkExecObserver class.

        Parameters:
        -----------
        constraints: dict
            Same as AssimEventObserver's constraints parameter.
        scriptdir: str
            The directory where our scripts are found.  We execute them all whenever an
            event of the selected type occurs.
        '''
        if scriptdir is None:
            scriptdir = NOTIFICATION_SCRIPT_DIR
        if not os.path.isdir(scriptdir):
            raise ValueError('Script directory [%s] is not a directory' % scriptdir)
        self.scriptdir = scriptdir
        pipefds = os.pipe()
        self.FIFOreadfd = pipefds[0]
        FIFOEventObserver.__init__(self, pipefds[1], constraints)
        self.childpid = os.fork()
        if self.childpid == 0:
            self.listenforevents()
        else:
            os.close(self.FIFOreadfd)
            self.FIFOreadfd = -1

    def ioerror(self, event):
        '''Re-initialize (respawn) our child in response to an I/O error'''

        if DEBUG:
            print >> sys.stderr, '**********Reinitializing child process'
        if self.childpid > 0:
            os.kill(self.childpid, signal.SIGKILL)
            self.childpid = 0
        if self.FIFOwritefd >= 0:
            os.close(self.FIFOwritefd)
            self.FIFOwritefd = -1
        self.__init__(self.constraints, self.scriptdir)

        if self.errcount < 2:
            # Try to keep from losing this event
            self.notifynewevent(event)
        else:
            print >> sys.stderr, 'Reinitialization of ForkExecObserver may have failed.'

    def __del__(self):
        if self.childpid > 0:
            os.close(self.FIFOwritefd)
            os.kill(self.childpid, signal.SIGTERM)
            self.childpid = 0


    def listenforevents(self):
        'Listen for JSON events terminated by a FIFOEventObserver.NULstr'
        os.close(self.FIFOwritefd)
        fcntl.fcntl(self.FIFOreadfd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
        for fd in range(3, 1024):
            try:
                fcntl.fcntl(fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
            except IOError:
                pass
        currentbuf = ''
        while True:
            try:
                if DEBUG:
                    print >> sys.stderr, 'ISSUING READ...'
                currentbuf += os.read(self.FIFOreadfd, 4096)
                if DEBUG:
                    print >> sys.stderr, 'READ returned %d bytes' % (len(currentbuf))
                if len(currentbuf) == 0:
                    # We don't want any kind of python cleanup going on here...
                    # so we access the 'protected' member _exit of os, and irritate pylint
                    # pylint: disable=W0212
                    os._exit(0)
                while True:
                    if FIFOEventObserver.NULstr in currentbuf:
                        (currentbuf, additional) = currentbuf.split(FIFOEventObserver.NULstr, 1)
                        self.processJSONevent(currentbuf)
                        currentbuf = additional
                    else:
                        break
            # W0703: catching too general exception Exception
            # pylint: disable=W0703
            except Exception as e:
                print >> sys.stderr, ('ForkExecObserver Got exception in child process: %s'
                %   str(e))
                currentbuf = ''
            except KeyboardInterrupt as e:
                sys.exit(0)


    def processJSONevent(self, jsonstr):
        'Process a single JSON event from out input stream'
        eventobj = pyConfigContext(jsonstr)
        aobj = eventobj['associatedobject']
        aobjclass = aobj['nodetype']
        eventtype = AssimEvent.eventtypenames[eventobj['eventtype']]
        env = {}

        # Initialize the child environment with our current environment
        for item in os.environ:
            env[item] = os.environ[item]
        # Add in things in 'extrainfo' (if any)
        if 'extrainfo' in eventobj and eventobj['extrainfo'] is not None:
            extrastuff = eventobj['extrainfo']
            for extra in extrastuff.keys():
                evextra = extrastuff[extra]
                env['ASSIM_%s' % extra] = str(evextra)
        # Add all the scalars in the associated object
        for attr in aobj.keys():
            avalue = aobj[attr]
            if isinstance(avalue, (str, unicode, int, float, long, bool)):
                env['ASSIM_%s' % attr] = str(avalue)
        env['ASSIM_JSONobj'] = str(jsonstr)

        # It's an event we want our scripts to know about...
        # So, let them know!
        if DEBUG:
            print >> sys.stderr, 'TO RUN: %s' % (str(self.listscripts()))
        for script in self.listscripts():
            args = [script, eventtype, aobjclass]
            if DEBUG:
                print >> sys.stderr, 'STARTING SCRIPT: %s' % (str(args))
            os.spawnve(os.P_WAIT, script, args, env)
            if DEBUG:
                print >> sys.stderr, 'SCRIPT %s IS NOW DONE' % (str(args))

    def listscripts(self):
        'Return the list of pathnames which we will execute when we get notified of an event'
        retval = []
        for script in os.listdir(self.scriptdir):
            path = os.path.join(self.scriptdir, script)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                retval.append(path)
        retval.sort()
        return retval
