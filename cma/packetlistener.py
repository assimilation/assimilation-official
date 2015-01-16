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

from AssimCclasses import pyReliableUDP, pyPacketDecoder, pyNetAddr, pyCryptFrame
from AssimCtypes import CMAADDR, CONFIGNAME_CMAINIT
from frameinfo import FrameSetTypes
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
import sys

# R0903 is too few public methods
#pylint: disable=R0903
class PacketListener(object):
    'Listen for packets and get them dispatched as any good packet ought to be.'
    PRIO_ZERO   = 0
    PRIO_ONE    = 1
    PRIO_TWO    = 2
    PRIO_THREE  = 3

    DEFAULT_PRIO = PRIO_THREE
    LOWEST_PRIO = PRIO_THREE

    prio_map = {    # Our map of packet type priorities
        FrameSetTypes.CONNSHUT:     PRIO_ZERO,  # High priority and cheap
        FrameSetTypes.HBSHUTDOWN:   PRIO_ZERO,
        FrameSetTypes.HBDEAD:       PRIO_ZERO,
        FrameSetTypes.PING:         PRIO_ZERO,
        FrameSetTypes.PONG:         PRIO_ZERO,
        FrameSetTypes.RSCOPREPLY:   PRIO_ZERO,

        FrameSetTypes.STARTUP:      PRIO_ONE,   # High priority but sometimes expensive

        FrameSetTypes.SWDISCOVER:   PRIO_TWO,   # Not priority, often expensive
        FrameSetTypes.JSDISCOVERY:  PRIO_TWO,

        FrameSetTypes.HBLATE:       PRIO_THREE, # Not terribly important
        FrameSetTypes.HBBACKALIVE:  PRIO_THREE,
        FrameSetTypes.HBMARTIAN:    PRIO_THREE,
    }

    unencrypted_fstypes = {
        FrameSetTypes.STARTUP
    }

    def __init__(self, config, dispatch, io=None, encryption_required=True):
        self.config = config
        self.encryption_required=encryption_required
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
        # W0612: unused variable j
        # pylint: disable=W0612
        self.prio_queues = [[] for j in range(PacketListener.LOWEST_PRIO+1)]
        self.queue_addrs = {} # Indexed by IP addresses - which queue is this IP in?

    @staticmethod
    def frameset_prio(frameset):
        'Return the priority of a frameset'
        fstype = frameset.get_framesettype()
        return PacketListener.prio_map.get(fstype, PacketListener.DEFAULT_PRIO)

    def enqueue_frameset(self, frameset, fromaddr):
        '''Enqueue (read in) a frameset to our frameset queue system
        This queue system has a queue of frameset queues - one per priority level
        Each frameset queue consists of three elements:
            'addr'  the IP address of the far-end
            'Q'     a queue of framesets from address 'addr'
            'prio'  the priority of the highest priority packet in the queue
        Every frameset in a given frameset queue came from the same address...

        When we read in a new packet, we append it to the appropriate frameset
        queue - creating it if need be.  If the new packet raises the priority
        of the queue, then we move that frameset queue to the appropriate priority queue

        We keep a separate hash table (queue_addrs) which associates frameset queues with
        the corresponding IP addresses.
        '''
        prio = self.frameset_prio(frameset)
        if fromaddr not in self.queue_addrs:
            # Then we need to create a new frameset queue for it
            queue = {'addr': fromaddr, 'Q': [frameset,], 'prio': prio}
            self.queue_addrs[fromaddr] = queue
            self.prio_queues[prio].append(queue)
        else:
            # The frameset queue exists.  Append our frameset to the queue
            queue = self.queue_addrs[fromaddr]
            queue['Q'].append(frameset)
            oldprio = queue['prio']
            # Do we need to move the frameset queue to a different priority queue?
            if prio < oldprio:
                queue['prio'] = prio
                self.prio_queues[oldprio].remove(queue)
                self.prio_queues[prio].append(queue)

    def dequeue_a_frameset(self):
        '''Read a frameset from our frameset queue system in priority order
        We read from the highest priority queues first, moving down the
        priority scheme if there are no higher priority queues with packets to read.
        '''
        for prio_queue in self.prio_queues:
            if len(prio_queue) == 0:
                continue
            frameset_queue = prio_queue.pop(0)
            frameset = frameset_queue['Q'].pop(0)
            fromaddr = frameset_queue['addr']
            # Was that the last packet from this address?
            if len(frameset_queue['Q']) > 0:
                # Nope.  We still have more to read.
                newprio = min([self.frameset_prio(fs) for fs in frameset_queue['Q']])
                # Appending the frameset queue to the end => fairness under load
                self.prio_queues[newprio].append(frameset_queue)
                frameset_queue['prio'] = newprio
            else:
                # Frameset queue is now empty
                del self.queue_addrs[fromaddr]
            print >> sys.stderr, ('dequeue_a_frameset: RETURNING (%s, %s)' % (fromaddr, str(frameset)[:80]))
            CMAdb.log.debug('dequeue_a_frameset: RETURNING (%s, %s)' % (fromaddr, str(frameset)[:80]))
            return fromaddr, frameset
        CMAdb.log.debug('dequeue_a_frameset: RETURNING (None, None)')
        return None, None



    @staticmethod
    def mainloop_callback(unusedsource, cb_condition, listener):
        'Function to be called back by the Python Glib mainloop hooks'
        #make pylint happy
        unusedsource = unusedsource
        if cb_condition == glib.IO_IN or cb_condition == glib.IO_PRI:
            #print >> sys.stderr, ('Calling %s.listenonce' %  listener), type(listener)
            #listener.listenonce() ##OLD CODE
            listener.queueanddispatch()
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
                    CMAdb.log.debug("listenonce: Received FrameSets from str([%s], [%s])" \
                    %       (str(fromaddr), fromstr))
                #print >> sys.stderr, ("Received FrameSet from str([%s], [%s])" \
                #%       (str(fromaddr), fromstr))

            for frameset in framesetlist:
                if CMAdb.debug:
                    CMAdb.log.debug("listenonce: FrameSet Gotten ([%s]: [%s])" \
                    %       (str(fromaddr), frameset))
                self.dispatcher.dispatch(fromaddr, frameset)
    def _read_all_available(self):
        'Read All available framesets into our queue system'
        while True:
            (fromaddr, framesetlist) = self.io.recvframesets()
            if fromaddr is None:
                break
            else:
                fromstr = repr(fromaddr)
                if CMAdb.debug:
                    CMAdb.log.debug("_read_all_available: Received FrameSet from str([%s], [%s])" \
                    %       (str(fromaddr), fromstr))
                #print >> sys.stderr, ("Received FrameSet from str([%s], [%s])" \
                #%       (str(fromaddr), fromstr))

            for frameset in framesetlist:
                if CMAdb.debug:
                    CMAdb.log.debug("FrameSet Gotten ([%s]: [%s])" \
                    %       (str(fromaddr), frameset))
                self.enqueue_frameset(frameset, fromaddr)

    def queueanddispatch(self):
        'Queue and dispatch all available framesets in priority order'
        while True:
            CMA.log.warning('CALLING read_all_available')
            self._read_all_available()
            CMA.log.warning('read_all_available returned')
            CMA.log.warning('CALLING dequeue_a_frameset')
            fromaddr, frameset = self.dequeue_a_frameset()
            CMA.log.warning('RETURNED FROM dequeue_a_frameset')
            CMA.log.warning('FROMADDR IS %s, FRAMESET IS %s' % (fromaddr, frameset))
            CMA.log.debug('FROMADDR IS %s, FRAMESET IS %s' % (fromaddr, frameset))
            if fromaddr is None:
                return
            fstype = frameset.get_framesettype()
            key_id=frameset.sender_key_id()
            if key_id is not None:
                if CMAdb.debug:
                    CMAdb.log.debug('SETTING KEY(%s, %s) from fstype %s'
                    %   (fromaddr, key_id, frameset.fstypestr()))
                pyCryptFrame.dest_set_key_id(fromaddr, key_id)
            elif (self.encryption_required and
                fstype not in PacketListener.unencrypted_fstypes):
                raise ValueError('Unencrypted %s frameset received from %s'
                %       (frameset.fstypestr(), fromaddr))
            CMA.log.debug('Dispatching FRAMESET from %s' % (fromaddr))
            self.dispatcher.dispatch(fromaddr, frameset)
