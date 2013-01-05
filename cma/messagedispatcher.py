#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
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

from cmadb import CMAdb
from dispatchtarget import DispatchTarget
from hbring import HbRing
from frameinfo import FrameSetTypes
import os, sys, traceback

class MessageDispatcher:
    'We dispatch incoming messages where they need to go.'
    def __init__(self, dispatchtable):
        'Constructor for MessageDispatcher - requires a dispatch table as a parameter'
        self.dispatchtable = dispatchtable
        self.default = DispatchTarget()

    def dispatch(self, origaddr, frameset):
        'Dispatch a Frameset where it will get handled.'
        fstype = frameset.get_framesettype()
        #print >>sys.stderr, 'Got frameset of type %s [%s]' % (fstype, frameset)
        #
        # Eventually handling incoming packets needs to be transactional in nature.
        #
        # Once that happens, this is a reasonable place to implement transactions.
        # Need to think medium-hard about how to deal with doing this in a queueing system
        # where a single packet might trigger a transaction on several systems for a node
        # which appears on several rings.
        #
        try:
            # May eventually begin a transaction here
            # Of course, this transaction needs to span both the database and the network
            if fstype in self.dispatchtable:
                self.dispatchtable[fstype].dispatch(origaddr, frameset)
            else:
                self.default.dispatch(origaddr, frameset)
        except Exception as e:
            # Darn!  Got an exception - let's try and put everything useful into the logs in legible way
            (etype, evalue, trace) = sys.exc_info()
            tblist=traceback.extract_tb(trace, 20)
            fstypename = FrameSetTypes.get(fstype)[0]

            print >>sys.stderr, ('MessageDispatcher %s exception [%s] occurred while handling [%s] FrameSetFrameset from %s' 
            %           (etype, e, fstypename, origaddr))
            CMAdb.log.critical('MessageDispatcher exception [%s] occurred while handling [%s] FrameSet from %s'
            %           (e, fstypename, origaddr))
            lines=str(frameset).splitlines()
            CMAdb.log.info('FrameSet Contents follows (%d lines):' % len(lines))
            for line in lines:
                CMAdb.log.info(line.expandtabs())
            CMAdb.log.info('======== Begin %s Message %s Exception Traceback ========' % (fstypename, e))
            for tb in tblist:
                (filename, line, funcname, text) = tb
                filename = os.path.basename(filename)
                CMAdb.log.info('%s.%s:%s: %s'% (filename, line, funcname, text))
            CMAdb.log.info('======== End %s Message %s Exception Traceback ========' % (fstypename, e))
            # @todo Eventually will want to abort the transaction here
        else:
            # @todo Eventually will want to commit the transaction here
            pass
        # @todo This will eventually need to be part of the transaction
        self.io.ackmessage(origaddr, frameset)


    def setconfig(self, io, config):
        'Save our configuration away.  We need it before we can do anything.'
        self.io = io
        self.default.setconfig(io, config)
        for msgtype in self.dispatchtable.keys():
            self.dispatchtable[msgtype].setconfig(io, config)

