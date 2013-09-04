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
import os, sys, traceback
from hbring import HbRing

class MessageDispatcher:
    'We dispatch incoming messages where they need to go.'
    def __init__(self, dispatchtable):
        'Constructor for MessageDispatcher - requires a dispatch table as a parameter'
        self.dispatchtable = dispatchtable
        self.default = DispatchTarget()
        self.io = None

    #pylint: disable=R0914
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
        CMAdb.transaction = Transaction()
        # W0703 == Too general exception catching...
        # pylint: disable=W0703 
        try:
            if fstype in self.dispatchtable:
                self.dispatchtable[fstype].dispatch(origaddr, frameset)
            else:
                self.default.dispatch(origaddr, frameset)
            # Commit the transaction here
            CMAdb.transaction.commit_trans(CMAdb.io)
            if CMAdb.store.transaction_pending:
                CMAdb.store.commit()
                CMAdb.TheOneRing.AUDIT()
            else:
                if CMAdb.debug:
                    print >> sys.stderr, 'No database changes this time'
                CMAdb.store.abort()
            if CMAdb.debug:
                print >> sys.stderr, ''
        except Exception as e:
            # Darn!  Got an exception - let's try and put everything useful into the
            #   logs in a legible way
            (etype, evalue, trace) = sys.exc_info()
            evalue = evalue # make pylint happy
            tblist = traceback.extract_tb(trace, 20)
            fstypename = FrameSetTypes.get(fstype)[0]

            print >> sys.stderr, ('MessageDispatcher %s exception [%s] occurred while' 
            ' handling [%s] FrameSetFrameset from %s' % (etype, e, fstypename, origaddr))
            CMAdb.log.critical('MessageDispatcher exception [%s] occurred while'
            ' handling [%s] FrameSet from %s' % (e, fstypename, origaddr))
            lines = str(frameset).splitlines()
            CMAdb.log.info('FrameSet Contents follows (%d lines):' % len(lines))
            for line in lines:
                CMAdb.log.info(line.expandtabs())
            CMAdb.log.info('======== Begin %s Message %s Exception Traceback ========'
            %   (fstypename, e))
            print >> sys.stderr, ('======== Begin %s Message %s Exception Traceback ========'
            %   (fstypename, e))
            for tb in tblist:
                (filename, line, funcname, text) = tb
                filename = os.path.basename(filename)
                CMAdb.log.info('%s.%s:%s: %s'% (filename, line, funcname, text))
                print >> sys.stderr, ('%s.%s:%s: %s'% (filename, line, funcname, text))
            CMAdb.log.info('======== End %s Message %s Exception Traceback ========'
            %   (fstypename, e))
            if CMAdb.store is not None:
                CMAdb.log.critical("Aborting Neo4j transaction %s" % CMAdb.store)
                CMAdb.store.abort()
            if CMAdb.transaction is not None:
                CMAdb.log.critical("Aborting network transaction %s" % CMAdb.transaction.tree)
                CMAdb.transaction = None
            print >> sys.stderr, 'EXITING!!'
            os._exit(1)
            
        # We want to do this even in the failed case - retries are unlikely to help
        # and we're far more likely to get stuck in a loop retrying it forever...
        self.io.ackmessage(origaddr, frameset)


    def setconfig(self, io, config):
        'Save our configuration away.  We need it before we can do anything.'
        self.io = io
        self.default.setconfig(io, config)
        for msgtype in self.dispatchtable.keys():
            self.dispatchtable[msgtype].setconfig(io, config)

