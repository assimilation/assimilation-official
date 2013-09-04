#!/usr/bin/python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2013 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community - http://assimproj.org
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
import sys  # Only needed for stderr for printing...
import re
import inspect, weakref
#import traceback
from py2neo import neo4j, exceptions
from datetime import datetime
'''
Store module - contains a transactional batch implementation of Nigel Small's
Object-Graph-Mapping API (or something a lot like it)
'''

class Store:
    '''This 'Store' class is a transaction-oriented implementation of Nigel Small's
    OGM (Object-Graph-Mapping) API - with a few extensions and a few things not implemented.

    Unimplemented APIs
    -----------------
    The following member functions aren't provided:
        is_saved() - replaced by the transaction_pending property

    Some interesting extensions:
    ----------------------------
        -   You can tell the Store constructor things about your Classes and Indexes
                makes handling indexes simpler and less error prone. This affects the
                save() method and makes it usable far more often.
        -   All updates are happen in a batch job - as a single transaction.
        -   You never need to call save once an object was created.  We
            track changes to the attributes.

    New methods:
    -----------
        commit          saves all modifications in a single transaction
        load_in_related load objects we're related to by incoming relationships
        separate_in     separate objects we're related to by incoming relationships
        node            returns the neo4j.Node object associated with an object
        id              returns the id of the neo4j.Node associated with an object
        is_uniqueindex  returns True if the given index name is known to be unique
        __str__         formats information about this Store
        transaction_pending -- Property: True means a transaction is pending

    The various save functions do nothing immediately.  Updates are delayed until
    the commit member function is called.

    Restrictions:
    -------------
    You can't delete something in the same transaction that you created it.
    This could probably be fixed, but would take some effort, and seems unlikely
    to be useful.

    Objects associated with Nodes must be subclasses of object

    Caveats, Warnings and so on...
    ------------------------------
    You can delete the same the same relationship or node multiple times in a transaction.

    Attributes beginning with _ are not replicated as Node properties.

    There are various times when a constructor is called to create an object from a
    node.  Those 'constructors' can be factory functions that construct the right kind
    of object for the type of node involved.

    Such constructors are called with the arguments which correspond to the Node 
    properties - but only those which they will legally take (according to python
    introspection).  It is assumed that argument names correspond to attribute
    (Node property) names.

    Any remaining properties not created by the constructor are assigned to the object
    as attributes.  This is likely not what Nigel did, but it seems sensible.

    Probably should have created some new exception type for a few of our cases.
    I'm not compatible with Nigel in terms of exceptions raised. We mostly
    raise ValueError()...

    In particular, it is possible for data in the database to be incompatible with
    object constructors which would be a bad thing worth recognizing -- but I don't
    do anything special for this case at the moment.
    '''
    LUCENE_RE =  re.compile(r'([\-+&\|!\(\)\{\}[\]^"~\*?:\\])')
    LUCENE_RE =  re.compile(r'([:[\]])')
    def __init__(self, db, uniqueindexmap={}, classkeymap={}):
        '''
        Constructor for Transactional Write (Batch) Store objects
        ---------
        Parameters:
        db             - Database to associate with this object
        uniqueindexmap - Dict of indexes, True means its a unique index, False == nonunique
        classkeymap    - Map of classes to index attributes - indexed by Class or Class name
                         Values are another Dict with these values:
                         'index':   name of index
                         'key':     constant key value
                         'kattr':   object attribute for key
                         'value':   constant key 'value'
                         'vattr':   object attribute for key 'value'
        '''
        self.db = db
        self.clients = {}
        self.newrels = []
        self.deletions = []
        self.classes = {}
        self.weaknoderefs = {}
        self.uniqueindexmap = uniqueindexmap
        self.batch = None
        self.batchindex = None
        if len(classkeymap) > 0 and not isinstance(classkeymap.keys()[0], str):
            # Then the map should be indexed by the classes themselves
            newmap = {}
            for cls in classkeymap.keys():
                newmap[cls.__name__] = classkeymap[cls]
            classkeymap = newmap
        self.classkeymap = classkeymap
        self.create_node_count = 0
        self.relate_node_count = 0
        self.index_entry_count = 0
        self.node_update_count = 0
        self.node_deletion_count = 0
        self.node_separate_count = 0

    def __str__(self):
        'Render our Store object as a string for debugging'
        ret = '{\n\tdb: %s'                     %       self.db
        ret += ',\n\tclasses: %s'               %       self.classes
        if self.uniqueindexmap:
            ret += ',\n\tuniqueindexmap: %s'    %       self.uniqueindexmap
        if self.uniqueindexmap:
            ret += ',\n\tclasskeymap: %s'       %       self.classkeymap
        ret += '\n\tbatchindex: %s'             %       self.batchindex
        for attr in ('clients', 'newrels', 'deletions'):
            avalue = getattr(self, attr)
            acomma='['
            s="\n"
            for each in avalue:
                s += ('%s%s' % (acomma, each))
                acomma=', '
            ret += ",\n\t%10s: %s"  % (attr, s)
        ret += '\n\tweaknoderefs: %s'           %       self.weaknoderefs

        ret += '\n\tbatch: %s'                  %       self.batch
        ret += '\n}'
        return ret

    @staticmethod
    def lucene_escape(query):
        'Returns a string with the lucene special characters escaped'
        return Store.LUCENE_RE.sub(r'\\\1', query)

    @staticmethod
    def id(subj):
        'Returns the id of the neo4j.Node associated with the given object'
        return subj.__store_node._id

    @staticmethod
    def has_node(subj):
        return hasattr(subj, '_Store__store_node')

    @staticmethod
    def is_abstract(subj):
        'Returns True if the underlying database node is Abstract'
        if not hasattr(subj, '_Store__store_node'):
            return True
        return subj.__store_node.is_abstract

    def is_uniqueindex(self, index_name):
        'Return True if this index is known to be a unique index'
        if self.uniqueindexmap is not None and index_name in self.uniqueindexmap:
            return self.uniqueindexmap[index_name]
        return False

    # For debugging...
    def dump_clients(self):
        'Dump out all our client objects and their supported attribute values and states'
        for client in self.clients:
            print 'Client %s:' % client
            for attr in Store._safe_attr_names(client):
                if attr in client.__store_dirty_attrs.keys():
                    print '%10s: Dirty - %s' % (attr, client.__dict__[attr])
                else:
                    print '%10s: Clean - %s' % (attr, client.__dict__[attr])

    def save_indexed(self, index_name, key, value, *subj):
        'Save the given (new) object as an indexed node'
        if not isinstance(subj, tuple) and not isinstance(subj, list):
            subj = (subj,)
        if len(subj) > 1 and unique:
            raise ValueError('Cannot make multiple items unique')
        for obj in subj:
            self._register(obj, neo4j.Node.abstract(**Store._safe_attrs(obj))
            ,   index=index_name, key=key, value=value, unique=False)

    def save_unique(self, index_name, key, value, subj):
        'Save the given new object as a uniquely indexed node'
        self.save_indexed(index_name, key, value, subj)
        # Override save_indexed's judgment that it's not unique...
        subj.__store_index_unique = True

    def save(self, subj, node=None):
        '''Save an object:
            - into a new node
            - into an existing node

            It will be indexed if its class is a known indexed class
                not indexed if its class is not a known indexed class

            If the index is known to be a unique index, then it will
            be saved unique - otherwise it won't be unique
        '''
        if node is not None:
            if subj in self.clients:
                raise ValueError('Cannot save existing node into a new node')
            self._register(subj, node=node)
            return

        # Figure out all the indexed stuff...
        cls = subj.__class__
        if not cls.__name__ in self.classkeymap:
            # Not an indexed object...
            if subj not in self.clients:
                self._register(subj, neo4j.Node.abstract(**Store._safe_attrs(subj)))
            return subj
        (index, key, value) = self._get_idx_key_value(cls, subj.__dict__)

        # Now save it...
        if self.is_uniqueindex(index):
            self.save_unique(index, key, value, subj)
        else:
            self.save_indexed(index, key, value, subj)
        return subj

    def delete(self, subj):
        'Delete the saved object and all its relationships from the database'
        if not hasattr(subj, '_Store__store_node'):
            raise ValueError('Object not associated with the Store system')
        node = subj.__store_node
        if node.is_abstract:
            raise ValueError('Node cannot be abstract')
        self.separate(subj)
        self.separate_in(subj)
        self.deletions.append(subj)

    def refresh(self, subj):
        'Refresh the information in the given object from the database'
        node = self.db.node(subj.__store_node._id)
        return self._construct_obj_from_node(node, subj.__class__)


    def load_indexed(self, index_name, key, value, cls):
        '''
        Return the specified set of 'cls' objects from the given index
        ---------
        Parameters:
        index_name - name of index to retrieve objects from
        key        - key value of nodes to be retrieved
        value      - 'value' of nodes to be retrieved
        cls        - a class to construct -- or a function to call
                     which constructs the desired object
        '''

        idx = self.db.get_index(neo4j.Node, index_name)
        nodes = idx.get(key, value)
        #print 'idx["%s",%s].get("%s", "%s") => %s' % (index_name, idx, key, value, nodes)
        ret = []
        for node in nodes:
            ret.append(self._construct_obj_from_node(node, cls))
        #print 'load_indexed: returning %s' % ret[0].__dict__
        return ret

    def load_or_create(self, cls, **clsargs):
        '''Analogous to 'save' - for loading an object or creating it if it
        doesn't exist
        Note that the class arguments ('clsargs') MUST include key and value
        arguments if they (key or value) are not constants.
        '''
        if not cls.__name__ in self.classkeymap:
            #print self.classkeymap
            raise ValueError("Class 'cls'[%s] must be a class with a known index", cls.__name__)
        subj = self._callconstructor(cls, clsargs)
        (index_name, idxkey, idxvalue) = self._get_idx_key_value(cls, clsargs, subj=subj)
        if not self.is_uniqueindex(index_name):
            raise ValueError("Class 'cls' must be a unique indexed class [%s]", cls)

        # See if we can find this node in memory somewhere...
        ret = self._localsearch(cls, idxkey, idxvalue)
        if ret is not None:
            return ret

        node = self.db.get_indexed_node(index_name, idxkey, idxvalue)
        if node is not None:
            return self._construct_obj_from_node(node, cls)
        return self.save(subj)


    def relate(self, subj, rel_type, obj, properties=None):
        '''Define a 'rel_type' relationship subj-[:rel_type]->obj'''
        assert not isinstance(obj, str)
        self.newrels.append({'from':subj, 'to':obj, 'type':rel_type, 'props':properties})

    def relate_new(self, subj, rel_type, obj, properties=None):
        '''Define a 'rel_type' relationship subj-[:rel_type]->obj'''
        subjnode = subj.__store_node
        objnode  = obj.__store_node

        if not objnode.is_abstract and not subjnode.is_abstract:
            rels = [rel for rel in subjnode.match_outgoing(rel_type, objnode)]
            if len(rels) > 0:
                return
        self.relate(subj, rel_type, obj, properties)

    def separate(self, subj, rel_type=None, obj=None):
        'Separate nodes related by the specified relationship type'
        fromnode = subj.__store_node
        if fromnode.is_abstract:
            raise ValueError('Subj Node cannot be abstract')
        if obj is not None:
            obj = obj.__store_node
            if obj.is_abstract:
                raise ValueError('Obj Node cannot be abstract')

        # No errors - give it a shot!
        rels = subj.__store_node.match_outgoing(rel_type, obj)
        for rel in rels:
            print >> sys.stderr, 'DELETING RELATIONSHIP %s of type %s: %s' % (rel._id, rel_type, rel)
            if obj is not None:
                assert rel.end_node._id == obj._id
            self.deletions.append(rel)

    def separate_in(self, subj, rel_type=None, obj=None):
        'Separate nodes related by the specified relationship type'
        fromnode = subj.__store_node
        if fromnode.is_abstract:
            raise ValueError('Node cannot be abstract')
        if obj is not None:
            obj = obj.__store_node
            if obj.is_abstract:
                raise ValueError('Node cannot be abstract')

        # No errors - give it a shot!
        rels = subj.__store_node.match_incoming(rel_type)
        for rel in rels:
            self.deletions.append(rel)

    def load_related(self, subj, rel_type, cls):
        'Load all outgoing-related nodes with the specified relationship type'

        if Store.is_abstract(subj):
            return
            raise ValueError('Node to load related from cannot be abstract')
        #print 'LOAD RELATED Node(%s).match_outgoing("%s")' % (subj.__store_node, rel_type)
        rels = subj.__store_node.match_outgoing(rel_type)
        ret = []
        for rel in rels:
            yield self._construct_obj_from_node(rel.end_node, cls)

    def load_in_related(self, subj, rel_type, cls):
        'Load all incoming-related nodes with the specified relationship type'
        if subj.__store_node.is_abstract:
            raise ValueError('Node to load related from cannot be abstract')
        rels = subj.__store_node.match_incoming(rel_type)
        ret = []
        for rel in rels:
            yield (self._construct_obj_from_node(rel.start_node, cls))

    def load_cypher_nodes(self, query, cls, params={}, max=None):
        '''Execute the given query that returns a single column of nodes
        and return those nodes'''
        count = 0
        for row in query.stream(**params):
            for key in row.__dict__.keys():
                node = getattr(row, key)
                if node is None:
                    continue
                subj = Store._callconstructor(cls, node.get_properties())
                (index_name, idxkey, idxvalue) = self._get_idx_key_value(cls, {}, subj=subj)
                if not self.is_uniqueindex(index_name):
                    raise ValueError("Class 'cls' must be a unique indexed class [%s]", cls)
                local = self._localsearch(cls, idxkey, idxvalue)
                if local is not None:
                    yield local
                else:
                    self._register(subj, node=node)
                    yield subj
            count += 1
            if max is not None and count >= max:
                break
        return

    def load_cypher_node(self, query, cls, params={}):
        nodes = self.load_cypher_nodes(query, cls, params, max=1)
        for node in nodes:
            return node
        return None

    @property
    def transaction_pending(self):
        'Return True if we have pending transaction work that needs flushing out'
        return (len(self.clients) + len(self.newrels) + len(self.deletions)) > 0

    @staticmethod
    def _storesetattr(self, name, value):
        '''
        Does a setattr() - and marks changed attributes "dirty".  This
        permits us to know when attributes change, and automatically
        include them in the next transaction.
        This is a GoodThing.
        '''

        if name[0] != '_':
            if hasattr(self, '_Store__store_dirty_attrs'):
                #print 'Caught %s being set to %s!' % (name, value)
                #traceback.print_stack()
                self.__store_dirty_attrs[name] = True
                self.__store.clients[self] = True
        object.__setattr__(self, name, value)

    @staticmethod
    def _callconstructor(constructor, kwargs):
        'Call a constructor (or function) in a (hopefully) correct way'

        try:
            args, varargs, varkw, defaults = inspect.getargspec(constructor)
        except TypeError:
            args, varargs, varkw, defaults = inspect.getargspec(constructor.__init__)
        newkwargs = {}
        if varkw:
            newkwargs = kwargs
        else:
            for arg in kwargs.keys():
                if arg in args:
                    newkwargs[arg] = kwargs[arg]
        ret = constructor(**newkwargs)

        # Make sure the attributes match the desired values
        for attr in kwargs.keys():
            if not hasattr(ret, attr) or getattr(ret, attr) is None:
                setattr(ret, attr, kwargs[attr])
        return ret


    @staticmethod
    def _safe_attr_names(subj):
        'Return the list of supported attribute names from the given object'
        ret = []
        for attr in subj.__dict__.keys():
            if attr[0] == '_':
                continue
            value = subj.__dict__[attr]
            ret.append(attr)
        return ret

    @staticmethod
    def _safe_attrs(subj):
        'Return a dictionary of supported attributes from the given object'
        ret = {}
        for attr in Store._safe_attr_names(subj):
            ret[attr] = subj.__dict__[attr]
        return ret

    @staticmethod
    def _proper_attr_value(obj, attr):
        value = getattr(obj, attr)
        if isinstance(value, str) or isinstance(value, int) or isinstance(value, float ) \
        or      isinstance(value, unicode) or isinstance(value, list) or isinstance(value, tuple):
            return value
        else:
            raise ValueError("Attr %s of object %s of type %s isn't really acceptable" % (attr, obj, type(value)))

    @staticmethod
    def _update_node_from_obj(subj):
        'Update the node from its paired object'
        node = subj.__store_node
        for attr in subj.__store_dirty_attrs.keys():
            #print >> sys.stderr, 'Setting node["%s"] to %s' % (attr, getattr(subj, attr))
            node[attr] = Store._proper_attr_value(subj, attr)
        subj.__store_dirty_attrs = {}
 

    def _get_idx_key_value(self, cls, attrdict, subj=None):
        'Return the appropriate key/value pair for an object of a particular class'
        kmap = self.classkeymap[cls.__name__]
        index=kmap['index']
        #print >> sys.stderr, 'GET_IDX_KEY_VALUE: attrdict', attrdict
        #if subj is not None:
            #print >> sys.stderr, 'GET_IDX_KEY_VALUE: subj.__dict___', subj.__dict__
        if 'kattr' in kmap:
            kk = kmap['kattr']
            if kk in attrdict:
                #print >> sys.stderr, 'ATTRDICT:%s, kk=%s' % (attrdict, kk)
                key = attrdict[kk]
            else:
                #print >> sys.stderr, 'SUBJ.__dict__:%s, kk=%s' % (subj.__dict__, kk)
                key = getattr(subj, kk)
        else:
            key=kmap['key']
        if 'vattr' in kmap:
            kv = kmap['vattr']
            if kv in attrdict:
                #print >> sys.stderr, 'KV ATTRDICT:%s, kv=%s' % (attrdict, kv)
                value = attrdict[kv]
            else:
                #print >> sys.stderr, 'KV SUBJ.__dict__:%s, kv=%s' % (subj.__dict__, kv)
                value = getattr(subj, kv)
        else:
            value=kmap['value']
        return (self.classkeymap[cls.__name__]['index'], key, value)


    def _localsearch(self, cls, idxkey, idxvalue):
        '''Search the 'client' array and the weaknoderefs to see if we can find
        the requested object before going to the database'''

        classname = cls.__name__
        kmap = self.classkeymap[classname]
        kattr = None
        searchlist = {}
        if 'kattr' in kmap:
            searchlist[kmap['kattr']] = idxkey
        if 'vattr' in kmap:
            searchlist[kmap['vattr']] = idxvalue

        searchset = self.clients.keys()
        # Not 100% sure we searching weaknoderefs helps anything - but it won't hurt much ;-)
        for weakclient in self.weaknoderefs.values():
            client = weakclient()
            if client is not None and client not in self.clients:
                searchset.append(client)

        for client in searchset:
            if client.__class__ != cls:
                continue
            found = True
            for attr in searchlist.keys():
                if not hasattr(client, attr) or getattr(client, attr) != searchlist[attr]:
                    found = False
                    break
            if found:
                assert hasattr(client, '_Store__store_node')
                return client
        return None




    def _update_obj_from_node(self, subj):
        'Update the object from its paired node'
        node = subj.__store_node
        nodeprops = node.get_properties()
        remove_subj = subj not in self.clients
        for attr in nodeprops.keys():
            pattr = nodeprops[attr]
            setattr(subj, attr, pattr)
            # Avoid unnecessary update transaction
            del subj.__store_dirty_attrs[attr]
        if remove_subj and subj in self.clients:
            del self.clients[subj]

        # Make sure everything in the object is in the Node...
        for attr in Store._safe_attr_names(subj):
            if attr not in nodeprops:
                subj.__store_dirty_attrs[attr] = True
                self.clients[subj] = True

    def _construct_obj_from_node(self, node, cls):
        'Construct an object associated with the given node'
        # Do we already have a copy of an object that goes with this node somewhere?
        # If so, we need to update and return it instead of creating a new object
        nodeid = node._id
        if nodeid in self.weaknoderefs:
            subj = self.weaknoderefs[nodeid]()
            if subj is None:
                del self.weaknoderefs[nodeid]
            else:
                # Yes, we have a copy laying around somewhere - update it...
                subj.__store_node = node
                self._update_obj_from_node(subj)
                return subj
        #print 'RETRIEVED NODE PROPERTIES:', node.get_properties()
        retobj = Store._callconstructor(cls, node.get_properties())
        return self._register(retobj, node=node)

    def _register(self, subj, node=None, index=None, unique=None, key=None, value=None):
        'Register this object with a Node, so we can track it for updates, etc.'

        if not isinstance(subj, object):
            raise(ValueError('Instances registered with Store class must be subclasses of object'))
        assert not hasattr(subj, '_Store__store')
        assert subj not in self.clients
        self.clients[subj] = True
        subj.__store = self
        subj.__store_node = node
        subj.__store_batchindex = None
        subj.__store_index = index
        subj.__store_index_key = key
        subj.__store_index_value = value
        subj.__store_index_unique = unique
        subj.__store_dirty_attrs = {}
        if subj.__class__ not in self.classes:
            subj.__class__.__setattr__ = Store._storesetattr
            self.classes[subj.__class__] = True
        if node is not None and not node.is_abstract:
            if node._id in self.weaknoderefs:
                weakling = self.weaknoderefs[node._id]()
                if weakling is None:
                    del self.weaknoderefs[node._id]
                else:
                    print 'OOPS! - already here... self.weaknoderefs', weakling, weakling.__dict__()
            assert not node._id in self.weaknoderefs or self.weaknoderefs[node._id] is None
            self.weaknoderefs[node._id] = weakref.ref(subj)
        if node is not None:
            if 'post_db_init' in dir(subj):
                subj.post_db_init()

        return subj

    def _new_nodes(self):
        'Return the set of newly created nodes for this transaction'
        ret = []
        for client in self.clients:
            node = client.__store_node
            if node.is_abstract:
                ret.append((client, node))
        return ret


    @staticmethod
    def node(subj):
        'Returns the neo4j.Node associated with the given object'
        return subj.__store_node

    #
    #   Except for commit(), all member functions from here on construct the batch job
    #   from previous requests
    #

    def _batch_construct_create_nodes(self):
        'Construct batch commands for all the new objects in this batch'
        for pair in self._new_nodes():
            (subj, node) = pair
            Store._update_node_from_obj(subj)
            subj.__store_batchindex = self.batchindex
            self.batchindex += 1
            #print >> sys.stderr, 'Performing batch.create(%s) - for a new node' % node
            self.create_node_count += 1
            self.batch.create(node)

    def _batch_construct_relate_nodes(self):
        'Construct the batch commands to create the requested relationships'
        for rel in self.newrels:
            fromobj=rel['from']
            toobj=rel['to']
            fromnode=fromobj.__store_node
            tonode=toobj.__store_node
            reltype=rel['type']
            props=rel['props']
            if fromnode.is_abstract:
                fromnode=fromobj.__store_batchindex
            if tonode.is_abstract:
                tonode=toobj.__store_batchindex
            if props is None:
                absrel = neo4j.Relationship.abstract(fromnode, reltype, tonode)
            else:
                absrel = neo4j.Relationship.abstract(fromnode, reltype, tonode, **props)
            # Record where this relationship will show up in batch output
            # No harm in remembering this until transaction end...
            rel['seqno'] = self.batchindex
            rel['abstract'] = absrel
            self.batchindex += 1
            #print >> sys.stderr, 'Performing batch.create(%s) - for node relationships' % absrel
            self.relate_node_count += 1
            #print >> sys.stderr, 'ADDING rel %s' % absrel
            self.batch.create(absrel)

    def _batch_construct_deletions(self):
        'Construct batch commands for removing relationships or nodes'
        delrels = {}
        delnodes = {}
        for relorobj in self.deletions:
            if isinstance(relorobj, neo4j.Relationship):
                relid = relorobj._id
                if relid not in delrels:
                    print >> sys.stderr, 'DELETING rel %d: %s' % (relorobj._id, relorobj)
                    self.node_separate_count += 1
                    self.batch.delete(relorobj)
                    delrels[relid] = True
            else:
                # Then it must be a node-related object...
                node = relorobj.__store_node
                nodeid = node._id
                if nodeid in delnodes:
                    continue
                if nodeid in self.weaknoderefs:
                    del self.weaknoderefs[nodeid]
                # disconnect it from the database
                for attr in relorobj.__dict__.keys():
                    if attr.startswith('_Store__store'):
                        delattr(relorobj, attr)
                #print >> sys.stderr, 'DELETING node %s' % node
                self.node_deletion_count += 1
                self.batch.delete(node)
                delnodes[relid] = True


    def _batch_construct_new_index_entries(self):
        'Construct batch commands for adding newly created nodes to the indexes'
        for pair in self._new_nodes():
            (subj, node) = pair
            if subj.__store_index is not None:
                idx = self.db.get_index(neo4j.Node, subj.__store_index)
                key = subj.__store_index_key
                value = subj.__store_index_value
                self.index_entry_count += 1
                if subj.__store_index_unique:
                    #print >> sys.stderr, ('Adding node or fail: node %s to index %s("%s","%s")' %\
                        #(subj.__store_batchindex, idx, key, value))
                    self.batch.add_to_index_or_fail(neo4j.Node, idx, key, value
                    ,   subj.__store_batchindex)
                else:
                    #print >> sys.stderr, ('add_to_index: node %s added to index %s(%s,%s)' %
                        #(subj.__store_batchindex, idx, key, value))
                    self.batch.add_to_index(neo4j.Node, idx, key, value
                    ,   subj.__store_batchindex)

    def _batch_construct_node_updates(self):
        'Construct batch commands for updating attributes on "old" nodes'
        clientset = {}
        for subj in self.clients:
            if subj in clientset:
                print >> sys.stderr, 'DUPS in clients: %s IS IN %s' % (subj, clientset.keys())
                print >> sys.stderr, 'DIRTY fields:', subj.__store_dirty_attrs.keys()
                print >> sys.stderr, 'Client array:', self.clients
            assert not subj in clientset
            clientset[subj] = True
            node = subj.__store_node
            if node.is_abstract:
                continue
            for attr in subj.__store_dirty_attrs.keys():
                # Each of these items will return None in the HTTP stream...
                #print >> sys.stderr, 'Setting property %s to %s' % (attr, getattr(subj, attr))
                self.node_update_count += 1
                self.batch.set_property(node, attr, Store._proper_attr_value(subj, attr))

    def abort(self):
        self.batch.clear()
        self.clients = {}
        self.newrels = []
        self.deletions = []
        # Clean out dead node references
        for nodeid in self.weaknoderefs.keys():
            subj = self.weaknoderefs[nodeid]()
            if subj is None or not hasattr(subj, '_Store__store_node'):
                del self.weaknoderefs[nodeid]
    def commit(self):
        '''Commit all the changes we've created since our last transaction'''
        print >> sys.stderr, 'COMMITTING THIS THING:', self
        if self.batch is None:
            self.batch = neo4j.WriteBatch(self.db)
        self.batchindex = 0
        self._batch_construct_create_nodes()        # These return new nodes
        self._batch_construct_relate_nodes()        # These return new relationships
        self._batch_construct_new_index_entries()   # These return the objects indexed
        self._batch_construct_node_updates()        # These return None
        self._batch_construct_deletions()           # These return None
        #print >> sys.stderr, 'Committed THIS THING:', self
        start=datetime.now()
        submit_results = self.batch.submit()
        end=datetime.now()
        print >> sys.stderr, ('DATABASE UPDATE COMPLETED IN %s seconds' % (end-start))
        if self.create_node_count > 0:
            print >> sys.stderr, 'Nodes Created:      %d' % self.create_node_count
        if self.relate_node_count > 0:
            print >> sys.stderr, 'Nodes Related:      %d' % self.relate_node_count
        if self.index_entry_count > 0:
            print >> sys.stderr, 'Nodes Indexed:      %d' % self.index_entry_count
        if self.node_update_count > 0:
            print >> sys.stderr, 'Attributes Updated: %d' % self.node_update_count
        if self.node_deletion_count > 0:
            print >> sys.stderr, 'Nodes Deleted:      %d' % self.node_deletion_count
        if self.node_separate_count > 0:
            print >> sys.stderr, 'Nodes Separated:    %d' % self.node_separate_count
        self.create_node_count = 0
        self.relate_node_count = 0
        self.index_entry_count = 0
        self.node_update_count = 0
        self.node_deletion_count = 0
        self.node_separate_count = 0

        # Save away (update) any newly created nodes...
        for pair in self._new_nodes():
            (subj, node) = pair
            index = subj.__store_batchindex
            newnode = submit_results[index]
            # This 'subj' used to have an abstract node, now it's concrete
            subj.__store_node = newnode
            self.weaknoderefs[newnode._id] = weakref.ref(subj)
            for attr in newnode.get_properties():
                if not hasattr(subj, attr):
                    print "OOPS - we're missing attribute %s" % attr
                elif getattr(subj, attr) != newnode[attr]:
                    print "OOPS - attribute %s is %s and should be %s" \
                    %   (attr, getattr(subj, attr), newnode[attr])
        for subj in self.clients:
            subj.__store_dirty_attrs = {}
        self.abort()
        return submit_results

if __name__ == "__main__":

    # Must be a subclass of 'object'...
    class Drone(object):
        def __init__(self, a=None, b=None, name=None):
            self.a = a
            self.b = b
            self.name = name
        def foo(self):
            return 'a=%s b=%s name=%s' % (a, b, name)

    db = neo4j.GraphDatabaseService()
    db.get_or_create_index(neo4j.Node, 'Drone')
    query = neo4j.CypherQuery(db, 'start n=node(*) match n-[r?]-() where id(n) <> 0 delete n,r')
    query.run()
    # Which indexes are unique?
    uniqueindexmap={'Drone': True}
    # Which fields of which types are used for indexing
    classkeymap = {
        Drone:   # this is for the Drone class
            {'index': 'Drone',  # The index name for this class is 'Drone'
            'key': 'Drone',     # The key field is a constant - 'Drone'
            'vattr': 'name'     # The value field is an attribute - 'name'
            }
    }
    # uniqueindexmap and classkeymap are optional, but make save() work

    store = Store(db, uniqueindexmap={'Drone': True}, classkeymap=classkeymap)
    DRONE='Drone121'
    fred = Drone(a=1,b=2,name=DRONE)
    store.save(fred)    # Drone is a 'known' type, so we know which fields are index key(s)
    assert fred.a == 1
    assert fred.b == 2
    assert fred.name == DRONE
    assert not hasattr(fred, 'c')
    fred.a = 52
    fred.c = 3.14159
    assert fred.a == 52
    assert fred.b == 2
    assert fred.name == DRONE
    assert fred.c > 3.14158 and fred.c < 3.146
    rellist = ['ISA', 'WASA', 'WILLBEA']
    for rel in rellist:
        store.relate(fred, rel, fred)
    store.commit()  # The updates have been captured...
    assert fred.a == 52
    assert fred.b == 2
    assert fred.name == DRONE
    assert fred.c > 3.14158 and fred.c < 3.146

    for rel in rellist:
        ret = store.load_related(fred, rel, Drone)
        ret = [elem for elem in ret]
        assert len(ret) == 1 and ret[0] is fred
    for rel in rellist:
        ret = store.load_in_related(fred, rel, Drone)
        ret = [elem for elem in ret]
        assert len(ret) == 1 and ret[0] is fred
    assert fred.a == 52
    assert fred.b == 2
    assert fred.name == DRONE
    assert fred.c > 3.14158 and fred.c < 3.146
    print store
    assert not store.transaction_pending

    fred.x='malcolm'
    store.dump_clients()
    print 'store:', store
    assert store.transaction_pending
    store.commit() 
    assert not store.transaction_pending
    assert fred.a == 52
    assert fred.b == 2
    assert fred.name == DRONE
    assert fred.c > 3.14158 and fred.c < 3.146
    assert fred.x == 'malcolm'
    newnode = store.load_indexed('Drone', 'Drone', fred.name, Drone)[0]
    print 'LoadIndexed NewNode:', newnode, store._safe_attrs(newnode)
    # It's dangerous to have two separate objects which are the same thing be distinct
    # so we if we fetch a node, and one we already have, we get the original one...
    assert fred is newnode
    if store.transaction_pending:
        print 'UhOh, we have a transaction pending.'
        store.dump_clients()
        assert not store.transaction_pending
    assert newnode.a == 52
    assert newnode.b == 2
    assert newnode.x == 'malcolm'
    store.separate(fred, 'WILLBEA')
    assert store.transaction_pending
    store.commit() 
    rels = store.load_related(fred, 'WILLBEA', Drone)
    rels = [rel for rel in rels]
    assert len(rels) == 0
    store.refresh(fred)
    store.delete(fred)
    assert store.transaction_pending
    store.commit() 
    assert not hasattr(fred, '_Store__store_node')
    assert not store.transaction_pending
    print 'Final returned values look good!'
