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
import inspect, traceback
from AssimCclasses import pyNetAddr, pyConfigContext, pyFrameSet, pyIntFrame, pyCstringFrame, \
        pyIpPortFrame
from frameinfo import FrameSetTypes, FrameTypes
from cmadb import CMAdb
import py2neo
from py2neo import neo4j

def dumpargs(*args, **kwargs):
    result="CALLING %s(" % args[0]
    comma=''
    for j in range(1,len(args)-1):
        result += ("%s%s" % (comma, str(args[j])))
        comma=', '
    for key in kwargs.keys():
        result += ', %s=%s' % (key, kwargs[key])
    result += ')'
    print >> sys.stderr, result
    for j in range(1,len(args)-1):
        print >> sys.stderr, ("ARG%d type : %s" % (j-1, type(args[j])))
        print >> sys.stderr, ("ARG%d value: %s" % (j-1, str(args[j])))

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
            If this is eventually going to be executed by a plugin into the database engine,
            then the more work you leave to the executor of the transaction, the faster this
            code will run.  On the other hand, it delays the mess until transaction execution
            time and makes the code for creating the transaction simpler...
            I'm gonna opt for the complexity in processing of the transaction rather than
            complexity in all the places where people might add things to the transaction.


    @NOTE AND WARNING: 
    Transactions need to be somehow repeatable...  This means if this transaction
    was committed, we need to <i>not</i> repeat it - or make sure it's idempotent.
    Neither of those is true at the moment.
    '''
    REESC=re.compile('\\\\')
    REQUOTE=re.compile('"')

    def __init__(self, json=None):
        'Constructor for a combined database/network transaction.'
        if json is None:
            self.tree = {'db': [], 'packets': []}
        else:
            self.tree = pyConfigContext(init=str(json))
            if not 'db' in self.tree or not 'packets' in self.tree:
                raise ValueError('Incoming JSON is malformed: >>%s<<' % json)
        print >> sys.stderr, 'RESETTING NAMESPACE (1)'
        self.namespace = {}
        self.created = []
        self.sequence=None

    def __str__(self):
        'Convert our internal tree to JSON.'
        return self._jsonstr(self.tree)

    def _jsonesc(self, stringthing):
        'Escape this string according to JSON string escaping rules'
        stringthing = Transaction.REESC.sub('\\\\\\\\', stringthing)
        stringthing = Transaction.REQUOTE.sub('\\\\"', stringthing)
        return stringthing
        
    def _jsonstr(self, thing):
        'Recursively convert ("pickle") this thing to JSON' 

        #print >> sys.stderr, "CONVERTING", thing
        if isinstance(thing, list) or isinstance(thing, tuple):
            ret=''
            comma='['
            if len(thing) == 0:
                ret+= '['
            for item in thing:
                ret += '%s%s' % (comma,self._jsonstr(item))
                comma=','
            ret += ']'
            return ret

        if isinstance(thing, dict):
            ret=''
            comma='{'
            if len(thing) == 0:
                ret+= '{'
            for key in thing.keys():
                value = thing[key]
                ret+= '%s"%s":%s' % (comma, self._jsonesc(key), self._jsonstr(value))
                comma=','
            ret += '}'
            return ret

        if isinstance(thing, pyNetAddr):
            return '"%s"' % (str(thing))

        if isinstance(thing, bool):
            if thing:
                return 'true'
            return 'false'
        if isinstance(thing, int) or isinstance(thing, float) \
                or isinstance(thing, pyConfigContext):
            return str(thing)

        if isinstance(thing, unicode):
            return '"%s"' % (self._jsonesc(str(thing)))

        if isinstance(thing, str):
            return '"%s"' % (self._jsonesc(thing))

        raise ValueError("Object [%s] [type %s]isn't a type we handle" % (thing, type(thing)))
        return 'null'
###################################################################################################
#
#   This collection of member functions accumulate work to be done for our Transaction
#
###################################################################################################

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
        self.tree['packets'].append({'action': int(action), 'destaddr': destaddr, 'frames': frames})

    def _check_id(self, item, notbool=False):
        '''Return the Node ID associated with the given item.
        The items must be one of the following types:
            - An integer (meaning a node id) - just return it
            - A string - meaning a symbolic node id - we return it from our 'symbol table'
            - A neo4j.node - meaning a database node object - we return the 'id' of the node
            - One of our Node-derived classes (Drone, etc) - we return the node id of its node
        If it's not one of these types, then we raise a ValueError.
        If it has a 'node' field, but not a 'node.id' field, then we raise an AttributeError.
        '''
        print >> sys.stderr, 'CHECKING ID ON %s' % item
        if isinstance(item, dict) or isinstance(item, pyConfigContext):
            if not 'defines' in item:
                raise ValueError('No "defines" in to_id [%s]' % item)
            defname = item['defines']
            print >> sys.stderr, 'DEFINING %s' % defname
            self.namespace[defname] = True
            return defname
        elif isinstance(item, str):
            if not item in self.namespace:
                print >> sys.stderr, 'NAMESPACE:', self.namespace
                raise ValueError('Unknown symbolic name in item [%s]' % item)
            ret = self.namespace[item]
            if notbool:
                assert not isinstance(ret, bool)
            if not isinstance(ret, bool):
                print >> sys.stderr, 'RETURNING %s' % ret
                return ret
            else:
                print >> sys.stderr, 'RETURNING %s' % item
                return item
        elif isinstance(item, neo4j.Node):
            print >> sys.stderr, 'FOUND NODE [%s]' % (item)
            if hasattr(item, 'LABELID'):
                print >> sys.stderr, 'FOUND LABELID [%s]' % (item.LABELID)
                print >> sys.stderr, 'Checking %s recursively' % (item.LABELID)
                return self._check_id(item.LABELID, notbool)
            print >> sys.stderr, 'NODE HAS NO LABELID [%s, %s]' % (item, item.id)
            print >> sys.stderr, 'RETURNING %s' % item.id
            return item.id
        elif isinstance(item, int):
            return item
        elif hasattr(item, 'node'):
            print >> sys.stderr, 'FOUND ITEM WITH NODE ATTR [%s] => %s' % (item, item.node)
            return self._check_id(item.node, notbool)
        raise ValueError('invalid value type in to_id [%s] type(%s)' % (item, type(item)))

    def add_rels(self, rels):
        '''Add a relationship to our graph transaction.
        @todo  Note that if the given relationship type already exists between the two nodes,
        then this code will add it <i>again</i> - hope that's what you wanted!
        '''
        print >> sys.stderr, 'ADDREL(%s)' % rels
        if not isinstance(rels, list) and not isinstance(rels, tuple):
            rels = (rels,)
        db = self.tree['db']

        stack = traceback.extract_stack(inspect.currentframe(), 8)
        item = {'AddRel': [], 'caller': stack}

        for rel in rels:
            fromid = rel['from']
            toid = rel['to']
            fromid = self._check_id(fromid)
            toid = self._check_id(toid)
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
        db = self.tree['db']

        stack = traceback.extract_stack(inspect.currentframe(), 8)
        item = {'DelRel': [], 'caller': stack}
        for rel in rels:
            if isinstance(rel, neo4j.Relationship):
                print 'DELETING RELATIONSHIP [%s] [%d]' % (rel, rel.id)
                item['DelRel'].append(int(rel.id))
            else:
                print 'DELETING RELATIONSHIP [%d]' % ( rel)
                item['DelRel'].append(int(rel))
        db.append(item)

    def add_nodes(self, nodes):
        db = self.tree['db']
        if not isinstance(nodes, list) and not isinstance(nodes, tuple):
            nodes = (nodes,)
        stack = traceback.extract_stack(inspect.currentframe(), 8)
        db.append({'AddNode': nodes, 'caller': stack})
        print >> sys.stderr, ('ADDING NODE FROM: %s' % traceback.format_list(stack))
        for node in nodes:
            if 'defines' in node:
                print >> sys.stderr, 'DEFINING %s as True' % node['defines']
                self.namespace[node['defines']] = True
                print >> sys.stderr, 'UPDATED NAMESPACE: ', self.namespace

    def update_node_attrs(self, nodes):
        db = self.tree['db']
        if not isinstance(nodes, list) and not isinstance(nodes, tuple):
            nodes = (nodes,)
        stack = traceback.extract_stack(inspect.currentframe(), 8)
        db.append({'UpdateAttrs': nodes, 'caller': stack})
        print >> sys.stderr, ('ADDING ATTRS FROM: %s' % traceback.format_list(stack))


###################################################################################################
#
#   Code from here to the end has to do with committing our transactions...
#
###################################################################################################

    def _commit_node_add(self, batch, nodes):
        '''We commit a node addition to the database.
        '''
        print >> sys.stderr, 'COMMIT_NODE_ADD'
        for node in nodes:
            nodetype = node['type']
            name = str(node['name'])
            props = node['attributes']
            newprops = {}
            for key in props.keys():
                pkey = props[key]
                if isinstance(pkey, pyNetAddr):
                    pkey = str(pkey)
                newprops[key] = pkey
            props = newprops
            props['nodetype'] = nodetype
            props['name'] = name
            unique = False
            if nodetype in CMAdb.uniqueindexes and CMAdb.uniqueindexes[nodetype]:
                unique = True
            indexed = False
            if nodetype in CMAdb.is_indexed and CMAdb.is_indexed[nodetype]:
                indexed = True

            print >> sys.stderr, ('ADDING %s (%s) with unique=%s and index=%s' 
            %           (name, nodetype, unique, indexed))
            if indexed:
                # We default to unique indexes
                if unique:
                    idx = CMAdb.cdb.indextbl[nodetype]
                    print >> sys.stderr, "INDEX TYPE:", type(idx)
                    dumpargs('batch.create_indexed_node_or_fail',idx, nodetype, name
                    ,   properties=props)
                    #batch.create_indexed_node_or_fail(idx, nodetype, name, properties=props)
                    dnode = CMAdb.cdb.db.get_or_create_indexed_node(nodetype, nodetype, name, properties=props)
                else:
                    dumpargs('batch.add_indexed_node', idx, nodetype, name, properties=props)
                    #batch.add_indexed_node(idx, nodetype, name, properties=props)
                    dnode = CMAdb.cdb.db.create_indexed_node(nodetype, nodetype, name, properties=props)
                print >> sys.stderr, 'CREATE RETURNED %s' % dnode
            else:
                # No index
                print >>sys.stderr, 'CREATING: %s(%s)'% ('batch.create', py2neo.node(*props))
                dumpargs('batch.create', py2neo.node(*props))
                #batch.create(py2neo.node(*props))
                dnode = CMAdb.cdb.db.create(py2neo.node(*props))
            if 'defines' in node:
                print >> sys.stderr, 'DEFINING %s as %s' % (node['defines'], dnode)
                self.namespace[node['defines']] = dnode
                #self.namespace[node['defines']] = self.sequence
                #self.sequence += 1
            print >> sys.stderr, 'CREATE RETURNING %s' % dnode
            return dnode

    def _commit_rel_additions(self, batch):
        '''Commit our relationship additions'''
        for item in self.tree['db']:
            for key in item.keys():
                if key == 'AddRel':
                    for addrel in item['AddRel']:
                        fromid = addrel['from']
                        toid = addrel['to']
                        print >> sys.stderr, ('ORIGINAL FROMID %s TOID %s' % (fromid, toid))
                        if (isinstance(fromid, str)):
                            fromnode = self._check_id(fromid, notbool=True)
                        else:
                            fromnode = CMAdb.cdb.nodefromid(fromid)
                            print >> sys.stderr, ('FROMNODE %s' % (fromnode))
                        if (isinstance(toid, str)):
                            tonode = self._check_id(toid, notbool=True)
                        else:
                            tonode = CMAdb.cdb.nodefromid(toid)
                            print >> sys.stderr, ('TONODE %s' % (tonode))
                        print >> sys.stderr, ('FROMID %s TOID %s' % (fromid, toid))
                        print >> sys.stderr, ('FROMNODE %s TONODE %s' % (fromnode, tonode))
                        attrs = None
                        if 'attrs' in addrel:
                            attrs = addrel['attrs']
                            print >> sys.stderr, ('RELATIONSHIP(%s, %s, %s, attrs=%s)' 
                            %       (fromnode, addrel['type'], tonode, attrs))
                            print >>sys.stderr, 'CALLING batch.create(%s)' % (py2neo.rel(fromnode, addrel['type'], tonode, *attrs))
                            batch.create(py2neo.rel(fromnode, addrel['type'], tonode, *attrs))
                        else:
                            print >> sys.stderr, ('RELATIONSHIP FROM %s' % fromnode)
                            print >> sys.stderr, ('RELATIONSHIP TO %s' % tonode)
                            print >> sys.stderr, ('RELATIONSHIP(%s, %s, %s)' 
                            %       (fromnode, addrel['type'], tonode))
                            print >>sys.stderr, 'CALLING batch.create(%s)' % (py2neo.rel(fromnode, addrel['type'], tonode ))
                            batch.create(py2neo.rel(fromnode, addrel['type'], tonode))

    def _commit_node_del(self, batch, nodes):
        '''We commit a node deletion to the database'''
        pass


    def _commit_db_deletions(self, batch):
        '''We commit a node deletion to the database - this may be recursive'''
        for item in self.tree['db']:
            for key in item.keys():
                if key == 'DelRel':
                    for drel in item['DelRel']:
                        #drel is a relationship id (i.e, an 'int')
                        print >> sys.stderr, 'batch.delete_relationship(type) %s' % type(drel)
                        dumpargs('batch.delete_relationship(int)', drel)
                        dumpargs('batch.delete_relationship',CMAdb.cdb.db.relationship(drel))
                        batch.delete_relationship(CMAdb.cdb.db.relationship(drel))

    def _commit_db_changes(self, batch):
        pass

    def _commit_node_additions(self, batch):
        '''We commit all our database additions to the database'''
        self.sequence=0
        self.namespace = {}
        for item in self.tree['db']:
            for key in item.keys():
                if key == 'AddNode':
                    self._commit_node_add(batch, item['AddNode'])



    def _commit_db_trans(self):
        '''
        Commit the database portion of our transaction - that is, actually do the work.
        We do all this as a batch job - which makes it a single transaction, and hopefully faster.
        '''
        print >> sys.stderr, 'BEFORE UPDATE:'
        CMAdb.dump_nodes()
        CMAdb.dump_nodes(nodetype=CMAdb.NODE_NIC)
        CMAdb.dump_nodes(nodetype=CMAdb.NODE_ipaddr)
        CMAdb.dump_nodes(nodetype=CMAdb.NODE_ring)
        batch = neo4j.WriteBatch(CMAdb.cdb.db)
        #print >> sys.stderr, "BATCH UPDATE: >>%s<<" % self.tree['db']
        self._commit_db_changes(batch)
        self._commit_db_deletions(batch)
        self._commit_node_additions(batch)
        self._commit_rel_additions(batch)
        dumpargs('batch.submit')
        batch.submit()
        print >> sys.stderr, 'AFTER UPDATE:'
        CMAdb.dump_nodes()
        CMAdb.dump_nodes(nodetype=CMAdb.NODE_NIC)
        CMAdb.dump_nodes(nodetype=CMAdb.NODE_ipaddr)
        CMAdb.dump_nodes(nodetype=CMAdb.NODE_ring)
        batch = neo4j.WriteBatch(CMAdb.cdb.db)
        self.created = []

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

    def commit_trans(self, io):
        'Commit our transaction'
        # This is just to test that our tree serializes successfully - before we
        # persist it on disk later.  Once we're doing that, this will be
        # unnecessary...
        print >> sys.stderr, "HERE IS OUR TREE:"
        print >> sys.stderr, str(self)
        print >> sys.stderr, "CONVERTING BACK TO TREE"
        self.tree = pyConfigContext(str(self))
        if len(self.tree['packets']) > 0:
            self._commit_network_trans(io)
        if len(self.tree['db']) > 0:
            self._commit_db_trans()
        self.tree = {'db': [], 'packets': []}
        print >> sys.stderr, 'RESETTING NAMESPACE'
        self.namespace = {}
        CMAdb.Transaction = Transaction()

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
    trans.commit_trans(io)
