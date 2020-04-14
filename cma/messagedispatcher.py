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
"""
This is the overall message dispatcher - it receives incoming messages as they arrive
then call dispatch it so it will get handled.
"""

from __future__ import print_function
import os
import sys
import traceback
import gc
from datetime import datetime
import inject
from cmadb import CMAdb
from transaction import NetTransaction
from dispatchtarget import DispatchTarget
from frameinfo import FrameSetTypes
from AssimCtypes import proj_class_live_object_count, proj_class_max_object_count
from AssimCclasses import pyAssimObj, dump_c_objects


class MessageDispatcher(object):
    "We dispatch incoming messages where they need to go."

    @inject.params(store="Store")
    def __init__(self, dispatchtable, store=None, logtimes=False, encryption_required=True):
        "Constructor for MessageDispatcher - requires a dispatch table as a parameter"
        self.dispatchtable = dispatchtable
        self.default = DispatchTarget()
        self.io = None
        self.store = store
        self.dispatchcount = 0
        self.logtimes = logtimes or CMAdb.debug
        self.encryption_required = encryption_required

    def dispatch(self, origaddr, frameset):
        """
        Dispatch a Frameset where it will get handled.
        This is where all the work associated with processing an incoming packet gets done.

        :param origaddr: pyNetAddr: Origination address for the packet
        :param frameset: pyFrameSet: FrameSet to act on (process)
        :return: None
        """
        self.dispatchcount += 1
        assert self.io is not None

        try:
            # The __enter__ functions are called in the order given, but the exits are called in the
            # opposite order they're listed. The exits are what commit the transactions...
            # As a result, the idempotent NetTransaction is committed first...
            with self.store.db.begin(autocommit=False) as self.store.db_transaction, NetTransaction(
                self.io, encryption_required=self.encryption_required
            ) as CMAdb.net_transaction:
                self._try_dispatch_action(origaddr, frameset)
            if (self.dispatchcount % 100) == 1:
                self._check_memory_usage()
        # W0703 == Too general exception catching...
        # pylint: disable=W0703
        except Exception as e:
            CMAdb.log.critical("Got an exception of type %s: %s" % (type(e), e))
            self._process_exception(e, origaddr, frameset)
            try:
                if "response 404" in str(e):
                    # Let's at least try it again once and see what happens...
                    # FIXME: This should probably result in some higher-level recovery action
                    # We utterly rely on database updates working...
                    CMAdb.log.info("Retrying 404 database transaction.")
                    self.store.db_transaction.commit()
            # pylint: disable=W0703
            except Exception as e2:
                CMAdb.log.critical("Database transaction retry failed: %s" % str(e2))
        # print('TRANSACTIONs COMMITTED!', file=sys.stderr)
        if CMAdb.debug:
            fstypename = FrameSetTypes.get(frameset.get_framesettype())[0]
            CMAdb.log.debug(
                "MessageDispatcher - ACKing %s message from %s" % (fstypename, origaddr)
            )
        # We want to ack the packet even in the failed case - retries are unlikely to help
        # and we need to avoid getting stuck in a loop retrying it forever...
        self.io.ackmessage(origaddr, frameset)
        if not self.store.db_transaction.finished:
            CMAdb.log.critical("MessageDispatcher: DB transaction NOT committed!")
            self.store.db_transaction.finish()

    # [R0912:MessageDispatcher._try_dispatch_action] Too many branches (13/12)
    # pylint: disable=R0912
    def _try_dispatch_action(self, origaddr, frameset):
        """Core code to actually dispatch the Frameset.
        It should be run inside a try/except construct so that anything
        we barf up won't cause the CMA to die.
        """
        # print('Got Frameset:', frameset, file=stderr)
        fstype = frameset.get_framesettype()
        # print('Got frameset of type %s [%s]' % (fstype, frameset), file=sys.stderr)
        dispatchstart = datetime.now()
        if fstype in self.dispatchtable:
            self.dispatchtable[fstype].dispatch(origaddr, frameset)
        else:
            self.default.dispatch(origaddr, frameset)
        dispatchend = datetime.now()
        if self.logtimes:
            CMAdb.log.info(
                "Initial dispatch time for %s frameset: %s" % (fstype, dispatchend - dispatchstart)
            )
        if CMAdb.debug:
            # This is a VERY expensive call...
            # Good thing we only do it when debug is enabled...
            CMAdb.TheOneRing.AUDIT()
        for pkttype in CMAdb.net_transaction.post_transaction_packets:
            CMAdb.net_transaction.add_packet(origaddr, pkttype, [])
        if len(CMAdb.net_transaction.post_transaction_packets) > 0:
            CMAdb.net_transaction.commit_trans()
            CMAdb.post_transaction_packets = []
        dispatchend = datetime.now()
        if self.logtimes or CMAdb.debug:
            CMAdb.log.info(
                "Total dispatch time for %s frameset: %s" % (fstype, dispatchend - dispatchstart)
            )

    @staticmethod
    def _process_exception(e, origaddr, frameset):
        "Handle an exception from our message dispatcher"
        # Darn!  Got an exception - let's try and put everything useful into the
        #   logs in a legible way
        trace = sys.exc_info()[2]
        # we ignore the etype and evalue returns from sys.exc_info
        tblist = traceback.extract_tb(trace, 20)
        fstype = frameset.get_framesettype()
        fstypename = FrameSetTypes.get(fstype)[0]

        sys.stdout.flush()
        print("MessageDispatcher exception [%s] occurred" % e, file=sys.stderr)
        CMAdb.log.exception(
            "MessageDispatcher exception [%s] occurred while"
            " handling [%s] FrameSet from %s" % (e, fstypename, origaddr)
        )
        lines = str(frameset).splitlines()
        CMAdb.log.info("FrameSet Contents follows (%d lines):" % len(lines))
        for line in lines:
            CMAdb.log.info(line.expandtabs())
        CMAdb.log.info(
            "======== Begin %s Message %s Exception Traceback ========" % (fstypename, e)
        )
        for tb in tblist:
            (filename, line, funcname, text) = tb
            filename = os.path.basename(filename)
            CMAdb.log.info("%s.%s:%s: %s" % (filename, line, funcname, text))
        CMAdb.log.info("======== End %s Message %s Exception Traceback ========" % (fstypename, e))
        if CMAdb.store is not None:
            CMAdb.log.critical("Aborting Neo4j transaction %s" % CMAdb.store)
            CMAdb.store.abort()
        if CMAdb.net_transaction is not None:
            CMAdb.log.critical("Aborting network transaction %s" % CMAdb.net_transaction.tree)
            CMAdb.net_transaction = None

    @staticmethod
    def _check_memory_usage():
        "Check to see if we have too many objects outstanding right now"
        gccount = gc.get_count()
        gctotal = 0
        for elem in gccount:
            gctotal += elem
        CMAdb.log.info("Total allocated Objects: %s. gc levels: %s" % (gctotal, str(gccount)))
        cobjcount = proj_class_live_object_count()
        CMAdb.log.info(
            "Total/max allocated C-Objects: %s/%s" % (cobjcount, proj_class_max_object_count())
        )
        if gctotal < 20 and cobjcount > 5000:
            dump_c_objects()

        if CMAdb.debug:
            # Another very expensive set of debug-only calls
            assimcount = 0
            for obj in gc.get_objects():
                if isinstance(obj, pyAssimObj):
                    assimcount += 1
            CMAdb.log.info("Total allocated C-Objects: %s" % assimcount)

    def setconfig(self, io, config):
        "Save our configuration away.  We need it before we can do anything."
        self.io = io
        self.default.setconfig(io, config)
        for msgtype in self.dispatchtable.keys():
            self.dispatchtable[msgtype].setconfig(io, config)
