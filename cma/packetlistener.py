#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2011, 2012, 2013 - Alan Robertson <alanr@unix.sh>
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

'''
This implements the PacketListener class - which listens to packets then
dispatches them.
'''

from AssimCclasses import pyReliableUDP, pyPacketDecoder, pyNetAddr
from AssimCtypes import CMAADDR, CONFIGNAME_CMAINIT
from cmadb import CMAdb
#try:
    #gi.repository confuses pylint...
    #pylint: disable=E0611
    #from gi.repository import GLib as glib
#except ImportError:
    #pylint: disable=F0401
    #import gobject as glib
import glib # We've replaced gi.repository and gobject with our own 'glib' module

import time
#import sys

# R0903 is too few public methods
#pylint: disable=R0903
class PacketListener(object):
    'Listen for packets and get them dispatched as any good packet ought to be.'
    def __init__(self, config, dispatch, io=None):
        self.config = config
        if io is None:
            self.io = pyReliableUDP(config, pyPacketDecoder())
        else:
            self.io = io
        dispatch.setconfig(self.io, config)

        if not self.io.bindaddr(config[CONFIGNAME_CMAINIT]):
            raise NameError('Cannot bind to address %s' % (str(config[CONFIGNAME_CMAINIT])))
        if not self.io.mcastjoin(pyNetAddr(CMAADDR)):
            CMAdb.log.warning('Failed to join multicast at %s' % CMAADDR)
        self.io.setblockio(False)
        #print "IO[socket=%d,maxpacket=%d] created." \
        #%  (self.io.fileno(), self.io.getmaxpktsize())
        self.dispatcher = dispatch
        self.source = None
        self.mainloop = glib.MainLoop()

    @staticmethod
    def mainloop_callback(unusedsource, cb_condition, listener):
        'Function to be called back by the Python Glib mainloop hooks'
        #make pylint happy
        unusedsource = unusedsource
        if cb_condition == glib.IO_IN or cb_condition == glib.IO_PRI:
            #print >> sys.stderr, ('Calling %s.listenonce' %  listener), type(listener)
            listener.listenonce()
        else:
            if cb_condition == glib.IO_ERR:
                cond = 'IO_ERR'
            elif cb_condition == glib.IO_OUT:
                cond = 'IO_OUT'
            elif cb_condition == glib.IO_HUP:
                cond = 'IO_HUP'
            else:
                cond = '(%s?)' % (str(cb_condition))
            CMAdb.log.warning('PacketListener::mainloop_callback(cb_condition=%s)' % (cond))
            listener.mainloop.quit()
        #print >> sys.stderr, 'RETURNING True'
        return True

    def listen(self):
        'Listen for packets.  Get them dispatched.'
        self.source = glib.io_add_watch(self.io.fileno(), glib.IO_IN | glib.IO_PRI
        ,   PacketListener.mainloop_callback, self)
        self.mainloop.run()

        # Clean up before returning [if we ever do ;-)]
        glib.source_remove(self.source)
        self.source = None
        self.mainloop = None

    def OLDlisten(self):
        'Listen for packets.  Get them dispatched.'
        while True:
            self.listenonce()
            time.sleep(0.5)

    def listenonce(self):
        'Process framesets received as a single packet'
        while True:
            (fromaddr, framesetlist) = self.io.recvframesets()
            if fromaddr is None:
                # Must have read an ACK or something...
                return
            else:
                fromstr = repr(fromaddr)
                if CMAdb.debug:
                    CMAdb.log.debug("Received FrameSet from str([%s], [%s])" \
                    %       (str(fromaddr), fromstr))
                #print >> sys.stderr, ("Received FrameSet from str([%s], [%s])" \
                #%       (str(fromaddr), fromstr))

            for frameset in framesetlist:
                if CMAdb.debug:
                    CMAdb.log.debug("FrameSet Gotten ([%s]: [%s])" \
                    %       (str(fromaddr), frameset))
                self.dispatcher.dispatch(fromaddr, frameset)
