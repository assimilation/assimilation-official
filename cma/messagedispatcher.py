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
'''
This is the overall message dispatcher - it receives incoming messages as they arrive
then call dispatch it so it will get handled.
'''

from cmadb import CMAdb
from transaction import Transaction
from dispatchtarget import DispatchTarget
from frameinfo import FrameSetTypes
from AssimCtypes import proj_class_live_object_count, proj_class_max_object_count
from AssimCclasses import pyAssimObj, dump_c_objects
import os, sys, traceback
import gc

class MessageDispatcher:
    'We dispatch incoming messages where they need to go.'
    def __init__(self, dispatchtable):
        'Constructor for MessageDispatcher - requires a dispatch table as a parameter'
        self.dispatchtable = dispatchtable
        self.default = DispatchTarget()
        self.io = None
        self.dispatchcount = 0

    #pylint: disable=R0914
    def dispatch(self, origaddr, frameset):
        'Dispatch a Frameset where it will get handled.'
        fstype = frameset.get_framesettype()
        #print >>sys.stderr, 'Got frameset of type %s [%s]' % (fstype, frameset)
        self.dispatchcount += 1
        CMAdb.transaction = Transaction()
        # W0703 == Too general exception catching...
        # pylint: disable=W0703 
        try:
            if fstype in self.dispatchtable:
                self.dispatchtable[fstype].dispatch(origaddr, frameset)
            else:
                self.default.dispatch(origaddr, frameset)
            # Commit the network transaction here
            CMAdb.transaction.commit_trans(CMAdb.io)
            if CMAdb.store.transaction_pending:
                result = CMAdb.store.commit()
                if CMAdb.debug:
                    resultlines = str(result).splitlines()
                    CMAdb.log.debug('Commit results follow:')
                    for line in resultlines:
                        CMAdb.log.debug(line.expandtabs())
                    CMAdb.log.debug('end of commit results.')
                    # This is a VERY expensive call...
                    # Good thing we only do it when debug is enabled...
                    CMAdb.TheOneRing.AUDIT()
            else:
                if CMAdb.debug:
                    CMAdb.log.debug('No database changes this time')
                CMAdb.store.abort()
            if (self.dispatchcount % 100) == 1:
                gccount = gc.get_count()
                gctotal = 0
                for elem in gccount:
                    gctotal += elem
                CMAdb.log.info('Total allocated Objects: %s. gc levels: %s'
                %   (gctotal, str(gccount)))
                cobjcount = proj_class_live_object_count()
                CMAdb.log.info('Total/max allocated C-Objects: %s/%s'
                %   (cobjcount, proj_class_max_object_count()))
                if gctotal < 20 and cobjcount > 100:
                        dump_c_objects()
                
                if CMAdb.debug:
                    # Another very expensive set of debug-only calls
                    assimcount = 0
                    for obj in gc.get_objects():
                        if isinstance(obj, (pyAssimObj)):
                            assimcount += 1
                    CMAdb.log.info('Total allocated C-Objects: %s' % assimcount)
        except Exception as e:
            # Darn!  Got an exception - let's try and put everything useful into the
            #   logs in a legible way
            (etype, evalue, trace) = sys.exc_info()
            evalue = evalue # make pylint happy
            tblist = traceback.extract_tb(trace, 20)
            fstypename = FrameSetTypes.get(fstype)[0]

            CMAdb.log.critical('MessageDispatcher exception [%s] occurred while'
            ' handling [%s] FrameSet from %s' % (e, fstypename, origaddr))
            lines = str(frameset).splitlines()
            CMAdb.log.info('FrameSet Contents follows (%d lines):' % len(lines))
            for line in lines:
                CMAdb.log.info(line.expandtabs())
            CMAdb.log.info('======== Begin %s Message %s Exception Traceback ========'
            %   (fstypename, e))
            for tb in tblist:
                (filename, line, funcname, text) = tb
                filename = os.path.basename(filename)
                CMAdb.log.info('%s.%s:%s: %s'% (filename, line, funcname, text))
            CMAdb.log.info('======== End %s Message %s Exception Traceback ========'
            %   (fstypename, e))
            if CMAdb.store is not None:
                CMAdb.log.critical("Aborting Neo4j transaction %s" % CMAdb.store)
                CMAdb.store.abort()
            if CMAdb.transaction is not None:
                CMAdb.log.critical("Aborting network transaction %s" % CMAdb.transaction.tree)
                CMAdb.transaction = None
            
        # We want to ack the packet even in the failed case - retries are unlikely to help
        # and we need to avoid getting stuck in a loop retrying it forever...
        self.io.ackmessage(origaddr, frameset)


    def setconfig(self, io, config):
        'Save our configuration away.  We need it before we can do anything.'
        self.io = io
        self.default.setconfig(io, config)
        for msgtype in self.dispatchtable.keys():
            self.dispatchtable[msgtype].setconfig(io, config)

