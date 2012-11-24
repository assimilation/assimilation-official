#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab
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
#
#
#

from AssimCclasses import pyNetIOudp, pyPacketDecoder, pyNetAddr
import time
import sys
from cmadb import CMAdb

class PacketListener:
    'Listen for packets and get them dispatched as any good packet ought to be.'
    def __init__(self, config, dispatch, io=None):
        self.config = config
        if io is None:
            self.io = pyNetIOudp(config, pyPacketDecoder())
        else:
            self.io = io
        dispatch.setconfig(self.io, config)

        if not self.io.bindaddr(config['cmainit']):
            raise NameError('Cannot bind to address %s' % (str(config['cmainit'])))
        if not self.io.mcastjoin(pyNetAddr('224.0.2.5:1984')):
            print >>sys.stderr, 'Failed to join multicast at 224.0.2.5'
        self.io.setblockio(True)
        #print "IO[socket=%d,maxpacket=%d] created." \
        #%  (self.io.getfd(), self.io.getmaxpktsize())
        self.dispatcher = dispatch
        
    def listen(self):
      'Listen for packets.  Get them dispatched.'
      while True:
        (fromaddr, framesetlist) = self.io.recvframesets()
        if fromaddr is None:
            # BROKEN! ought to be able to set blocking mode on the socket...
            #print "Failed to get a packet - sleeping."
            time.sleep(0.5)
        else:
            fromstr = repr(fromaddr)
            if CMAdb.debug: CMAdb.log.debug("Received packet from [%s]" % (fromstr))

            for frameset in framesetlist:
                self.dispatcher.dispatch(fromaddr, frameset)
