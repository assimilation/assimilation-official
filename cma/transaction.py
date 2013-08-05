#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2013 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community - http://assimproj.org/
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
This file implements the transaction class - a class which encapsulates a description of a database
transaction and a corresponding set of network operations on nanoprobes.  It is these two things which
constitute the transaction.  These transactions are idempotent - that is, they describe enough of the
update that they can be executed multiple times in a row without any harm to the nanoprobe configuration or the
data in the database.

The be-all-and-end-all of these transactions is JSON - that is, the transactions are described in terms of JSON
and they are ultimately expressed and persisted as JSON before being committed.

How they are persisted is something which has generated a little controversy in the project.  Purists say
(quite rightly) that persisting transactions is what messaging systems are designed for.  More pragmatic
people don't want to bring in a large and complex messaging system for what is a relatively simple job.
Personally, I agree with both of them.

So, initially, we will persist the transactions just to flat files.  If we need messaging for (horizontal) scaling,
or other features of the messaging system, then we will switch to a messaging system.

In either case, this class won't be directly affected - since it only stores and executes transactions - it does
not worry about how they ought to be persisted.
'''
import re
import sys
from AssimCclasses import pyNetAddr, pyConfigContext, pyFrameSet, pyIntFrame, pyCstringFrame, pyIpPortFrame
from frameinfo import FrameSetTypes, FrameTypes

class Transaction:
    '''This class implements database/nanoprobe transactions.

    The nanoprobe portions of the transaction support the following operations:
        Start sending heartbeats
        Stop sending heartbeats
        Start listening for heartbeats
        Stop listening for heartbeats
        Start sending/receiving heartbeats
        Stop sending/receiving heartbeats
        Start a monitoring action
        Stop a monitoring action
        Start a discovery action
        Stop a discovery action

    The database portions of the transaction support the following operations:
        Insert a node possibly including a subtree to be inserted
        Replace a node possibly including owned subtrees to be replaced
        Delete a node and possible owned subtrees

    The semantics of the database updates are worth describing in further detail
        An "owned" subtree means that the node in question has ownership of all nodes
            related to it by the given relationship types, and if the node is deleted
            then all the things it owns should also be deleted

        If it is replaced, then all of its nodes related to it by the given
            relationship types should be replaced by the given nodes described in
            the transaction - and no other nodes related to it by these relationship
            types should exist.  If they do, they need to be deleted.

    Is this too complex?  Should the originator of the request be responsible for knowing what nodes he needs to delete?
            If this is eventually going to be executed by a plugin into the database engine, then the more work
            you leave to the executor of the transaction, the faster this code will run.
            On the other hand, it delays the mess until transaction execution time and makes the code
            for creating the transaction simpler...
            I'm gonna opt for the complexity in execution of the transaction rather than complexity in all
            the places where people might add things to the transaction.
    '''
    REESC=re.compile('\\\\')
    REQUOTE=re.compile('"')
    def __init__(self, json=None):
        'Constructor for a transaction'
        if json is None:
            self.tree = {}
        else:
            self.tree = pyConfigContext(init=str(json))

    def __str__(self):
        'Convert our internal tree to JSON'
        return self._jsonstr(self.tree)

    def _jsonesc(self, stringthing):
        'Escape this string according to JSON string escaping rules'
        Transaction.REESC.sub('\\\\\\\\', stringthing)
        Transaction.REQUOTE.sub('\\\\"', stringthing)
        return stringthing
        
    def _jsonstr(self, thing):
        'Convert ("pickle") this thing into a JSON string' 

        if isinstance(thing, list) or isinstance(thing, tuple):
            ret=''
            comma='['
            for item in thing:
                ret += '%s%s' % (comma,self._jsonstr(item))
                comma=','
            ret += ']'
            return ret

        if isinstance(thing, dict):
            ret=''
            comma='{'
            for key in thing.keys():
                ret+= '%s"%s":%s' % (comma, self._jsonesc(key), self._jsonstr(thing[key]))
                comma=','
            ret += '}'
            return ret

        if isinstance(thing, pyNetAddr):
            return '"%s"' % (str(thing))

        if isinstance(thing, int) or isinstance(thing, float) or isinstance(pyConfigContext):
            return str(thing)

        if isinstance(thing, bool):
            if thing:
                return 'true'
            return 'false'

        if isinstance(thing, unicode):
            return '"%s"' % (self._jsonesc(str(thing)))

        if isinstance(thing, str):
            return '"%s"' % (self._jsonesc(thing))

        raise ValueError("Object [%s] isn't a type we handle" % (thing))
        return 'null'

    def add_packet(self, destaddr, action, frames, frametype=None):
        '''Append a packet to the ConfigContext object for this transaction.
        In effect, this queues the packet for sending when this transaction is committed.
        
        Parameters
        ----------
        destaddr : pyNetAddr
            The address to send this packet to - the address that will get this packet
        action : int
            What action to ask the destaddr to perform on our behalf
        frames : [several possible types]
            A list of frames or (optionally) frame values
        frametype: [int], optional
            If present, it is the frame type for all the frame <i>values</i> in the 'frames' array
        '''

        # Note that we don't do this as a ConfigContext - it doesn't support modifying arrays.
        # Our JSON converts nicely to a ConfigContext - because it converts arrays correctly from JSON

        # Allow 'frames' to be a single frame
        if not isinstance(frames, list) and not isinstance(frames, tuple):
            frames = (frames,)
        # Allow 'frames' to be a list of frame <i>values</i> - if they're all the same frametype
        if frametype is not None:
            newframes = []
            for thing in frames:
                if thing is not None:
                    newframes.append({'frametype': frametype, 'framevalue': thing})
            frames = newframes
        if not 'packets' in self.tree:
            self.tree['packets'] = []
        self.tree['packets'].append({'action': int(action), 'destaddr': destaddr, 'frames': frames})

    def commit_trans(self, io):
        'Commit our transaction'
        if 'packets' in self.tree:
            self._commit_network_trans(io)
        self.tree = {}

    def _commit_network_trans(self, io):
        '''
        Commit the network portion of our transaction - that is, send the packets!
        One interesting thing - we should probably not consider this transaction fully
        completed until we decide one of our destinations is dead, or until
        they are all ACKed.
        @TODO: We don't yet cover with CMA crashing before all packets are received versus sent.
        This argues for doing the network portion of the transaction first.
        '''
        for packet in self.tree['packets']:
            fs = pyFrameSet(packet['action'])
            for frame in packet['frames']:
                ftype = frame['frametype']
                fvalue = frame['framevalue']

                if ftype == FrameTypes.IPPORT:
                    if isinstance(fvalue, str) or isinstance(fvalue, unicode):
                        fvalue = pyNetAddr(fvalue)
                    aframe = pyIpPortFrame(ftype, fvalue)
                    fs.append(aframe)

                elif ftype == FrameTypes.DISCNAME or ftype == FrameTypes.DISCJSON:
                    sframe = pyCstringFrame(ftype)
                    sframe.setvalue(str(fvalue))
                    fs.append(sframe)

                elif ftype == FrameTypes.DISCINTERVAL:
                    nframe = pyIntFrame(ftype, intbytes=4, initval=int(fvalue))
                    fs.append(nframe)
                else:
                    raise ValueError('Unrecognized frame type [%s]: %s' % (ftype, frame))
            # In theory we could optimize multiple FrameSets in a row being sent to the
            # same address, but we can always do that later...
            io.sendreliablefs(packet['destaddr'], (fs,))

if __name__ == '__main__':

    import sys

    trans = Transaction()
    destaddr = pyNetAddr('10.10.10.1:1984')
    addresses = (pyNetAddr('10.10.10.5:1984'),pyNetAddr('10.10.10.6:1984'))
    trans.add_packet(destaddr, FrameSetTypes.SENDEXPECTHB, addresses, frametype=FrameTypes.IPPORT)
    trans.add_packet(pyNetAddr('10.10.10.1:1984')
    ,   FrameSetTypes.SENDEXPECTHB, (pyNetAddr('10.10.10.5:1984'),pyNetAddr('10.10.10.6:1984'))
    ,   frametype=FrameTypes.IPPORT)
    print >> sys.stderr, 'JSON: %s\n' % str(trans)
    print >> sys.stderr, 'JSON: %s\n' % str(pyConfigContext(str(trans)))
    # Of course, this next statement won't work - but it does exercise a lot of code...
    trans.commit_trans(None)
