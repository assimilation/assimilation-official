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
transaction and a corresponding set of network operations on nanoprobes.  It is these two things
which constitute the transaction.  These transactions are idempotent - that is, they describe
enough of the update that they can be executed multiple times in a row without any harm to the
nanoprobe configuration or the data in the database.

The be-all-and-end-all of these transactions is JSON - that is, the transactions are described in
terms of JSON and they are ultimately expressed and persisted as JSON before being committed.

How they are persisted is something which has generated a little controversy in the project. 
Purists say (quite rightly) that persisting transactions is what messaging systems are designed
for.  More pragmatic people don't want to bring in a large and complex messaging system for what
    is a relatively simple job.  Personally, I agree with both of them.

So, initially, we will persist the transactions just to flat files.  If we need messaging for
(horizontal) scaling, or other features of the messaging system, then we will switch to a messaging
system.

In either case, this class won't be directly affected - since it only stores and executes
transactions - it does not worry about how they ought to be persisted.
'''
import re
import sys
from AssimCclasses import pyNetAddr, pyConfigContext, pyFrameSet, pyIntFrame, pyCstringFrame, \
        pyIpPortFrame
from frameinfo import FrameSetTypes, FrameTypes
from cmadb import CMAdb
from py2neo import neo4j

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

    Is this too complex?  Should the originator of the request be responsible for knowing what
            nodes he needs to delete?
            If this is eventually going to be executed by a plugin into the database engine, then
            the more work you leave to the executor of the transaction, the faster this code will
            run.  On the other hand, it delays the mess until transaction execution time and makes
            the code for creating the transaction simpler...
            I'm gonna opt for the complexity in execution of the transaction rather than complexity
            in all the places where people might add things to the transaction.


    There seem to be two kinds of hierarchical ownership relationships related to deletion:
        Strong relationships 
        Weak relationships

    If one wishes to delete a node "n", then all things related to it by strong relationships
    <i>must</i> also be deleted.

    When deleting a node "n" which has things related to it by weak relationships, then its
    weak children can be deleted if:
        1) It has no weak relationships
        2) All its weak relationships are to nodes of one of the two types:
            a) nodes which are strongly related any of the parents of "n"
            b) nodes whose only relationships are to the subgraph of things which are
                a) strongly related to the parent of "n" (bidirectionally)
                b) weakly related to "n" as parent

    '''
    REESC=re.compile('\\\\')
    REQUOTE=re.compile('"')

    def __init__(self, json=None):
        'Constructor for a combined database/network transaction.'
        if json is None:
            self.tree = {}
        else:
            self.tree = pyConfigContext(init=str(json))
        self.namespace = {}

    def __str__(self):
        'Convert our internal tree to JSON.'
        return self._jsonstr(self.tree)

    def _jsonesc(self, stringthing):
        'Escape this string according to JSON string escaping rules'
        Transaction.REESC.sub('\\\\\\\\', stringthing)
        Transaction.REQUOTE.sub('\\\\"', stringthing)
        return stringthing
        
    def _jsonstr(self, thing):
        'Recursively convert ("pickle") this thing to JSON' 

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

        if isinstance(thing, int) or isinstance(thing, float) \
                or isinstance(thing, pyConfigContext):
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
        # On the other hand, our JSON converts nicely into a ConfigContext - because it converts
        # arrays correctly from JSON

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

    def check_id(self, item):
        if isinstance(item, dict) or isinstance(item, pyConfigContext):
            if not 'defines' in item:
                raise ValueError('No "defines" in to_id [%s]' % item)
            defname = item['defines']
            self.namespace[defname] = True
            return defname
        elif isinstance(item, str):
            if not item in self.namespace:
                raise ValueError('Unknown symbolic name in item [%s]' % item)
            return self.namespace[item]
        elif isinstance(item, neo4j.Node):
            return item.id
        elif isinstance(item, int):
            return item
        raise ValueError('invalid value type in to_id [%s] type(%s)' % (item, type(item)))

    def add_rels(self, rels):
        '''Add a relationship to our graph transaction.
        @todo  Note that if the given relationship type exists between the two nodes, then 
        this code will add it - hope that's what you wanted!
        '''
        if not isinstance(rels, list) and not isinstance(rels, tuple):
            rels = (rels,)
        if not 'db' in self.tree:
            self.tree['db'] = []
        db = self.tree['db']

        item = {'AddRel': []}

        for rel in rels:
            fromid = rel['from']
            toid = rel['to']
            fromid = self.check_id(fromid)
            toid = self.check_id(toid)
            rtype = rel['type']
            if 'attrs' in rel:
                item['AddRel'].append({'from':fromid, 'to':toid, 'type':rtype
                ,   'attrs':rel['attrs']})
            else:
                item['AddRel'].append({'from':fromid, 'to':toid, 'type':rtype})
        db.append(item)

    def del_rels(self, rels):
        'Delete a relationship as part of our graph transaction'
        if not isinstance(rels, list) and not isinstance(rels, tuple):
            rels = (rels,)
        if not 'db' in self.tree:
            self.tree['db'] = []
        db = self.tree['db']

        item = {'DelRel': []}
        for rel in rels:
            item['DelRel'].append(rel)
        db.append(item)


    def commit_trans(self, io):
        'Commit our transaction'
        if 'packets' in self.tree:
            self._commit_network_trans(io)
        if 'db' in self.tree:
            self._commit_db_trans(io)
        self.tree = {}

    def _commit_db_trans(self, io):
        '''
        Commit the database portion of our transaction - that is, actually do the work.
        We do all this as a batch job - which makes it a single transaction, and hopefully faster.
        '''
        batch = neo4j.WriteBatch(CMAdb.cdb.db)
        #print >> sys.stderr, "BATCH UPDATE: >>%s<<" % self.tree['db']
        for item in self.tree['db']:
            for key in item.keys():
                if key == 'DelRel':
                    for drel in item['DelRel']:
                        #drel is a relationship id
                        batch.delete_relationship(CMAdb.cdb.get_relationship(drel))
                if key == 'AddRel':
                    for addrel in item['AddRel']:
                        fromid = addrel['from']
                        toid = addrel['to']
                        if isinstance(fromid, str):
                            fromnode = self.namespace[fromid]
                        else:
                            fromnode = CMAdb.cdb.nodefromid(fromid)
                        if isinstance(toid, str):
                            tonode = self.namespace[toid]
                        else:
                            tonode = CMAdb.cdb.nodefromid(toid)
                        attrs = None
                        if 'attrs' in addrel:
                            attrs = addrel['attrs']
                        batch.create(neo4j._rel(fromnode, addrel['type'], tonode, *attrs))
        batch.submit()

    def _commit_network_trans(self, io):
        '''
        Commit the network portion of our transaction - that is, send the packets!
        One interesting thing - we should probably not consider this transaction fully
        completed until we decide each destination is dead, or until its packets are all ACKed.

        @TODO: We don't yet cover with CMA crashing before all packets are received versus sent --
        That is, if they get lost between sending by the CMA and receiving by the nanoprobes.
        This argues for doing the network portion of the transaction first - presuming we do the
        db and network portions sequentially --  Of course, no transaction can start until
        the previous one is finished.
        '''
        #print >> sys.stderr, "PACKET JSON IS >>>%s<<<" % self.tree['packets']
        for packet in self.tree['packets']:
            fs = pyFrameSet(packet['action'])
            for frame in packet['frames']:
                ftype = frame['frametype']
                fvalue = frame['framevalue']
                # The number of cases below will have to grow over time.
                # but this code is pretty simple so far...

                if ftype == FrameTypes.IPPORT:
                    if isinstance(fvalue, str) or isinstance(fvalue, unicode):
                        fvalue = pyNetAddr(fvalue)
                    aframe = pyIpPortFrame(ftype, fvalue)
                    fs.append(aframe)

                elif ftype == FrameTypes.DISCNAME or ftype == FrameTypes.DISCJSON \
                        or ftype == FrameTypes.CONFIGJSON:
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
    from AssimCtypes import CONFIGNAME_OUTSIG
    from AssimCclasses import pyReliableUDP, pyPacketDecoder, pySignFrame

    config = pyConfigContext(init={CONFIGNAME_OUTSIG: pySignFrame(1)})
    io = pyReliableUDP(config, pyPacketDecoder())
    CMAdb.initglobal(io, debug=True)
    trans = Transaction()
    node0 = CMAdb.cdb.nodefromid(0)
    destaddr = pyNetAddr('10.10.10.1:1984')
    addresses = (pyNetAddr('10.10.10.5:1984'),pyNetAddr('10.10.10.6:1984'))
    trans.add_packet(destaddr, FrameSetTypes.SENDEXPECTHB, addresses, frametype=FrameTypes.IPPORT)
    trans.add_packet(pyNetAddr('10.10.10.1:1984')
    ,   FrameSetTypes.SENDEXPECTHB, (pyNetAddr('10.10.10.5:1984'),pyNetAddr('10.10.10.6:1984'))
    ,   frametype=FrameTypes.IPPORT)

    trans.add_rels([{'from': node0, 'to': 0, 'type': 'Frobisher', 'attrs': {'color': 'Red'}}
    ,   {'from': 0, 'to': node0, 'type': 'Framistat', 'attrs': {'color': 'Black'}}])
    print >> sys.stderr, 'JSON: %s\n' % str(trans)
    print >> sys.stderr, 'JSON: %s\n' % str(pyConfigContext(str(trans)))
    # Of course, this next statement won't work - but it does exercise a lot of code...
    trans.commit_trans(io)
