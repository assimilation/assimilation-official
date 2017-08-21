#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
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
# W0212 -- access to a protected member of a client class (we do this a lot)
# pylint: disable=W0212
"""
Store module - contains a transactional batch implementation of Nigel Small's
Object-Graph-Mapping API (or something a lot like it)

Here are some more things I need:
    An object association class with all the properties but one
        of the existing __Store_foobar attributes.

    Add the class factory constructor to the Store constructor

    Remove the cls (class) arguments from all the various constructor-like things


"""
from __future__ import print_function
import re, inspect, weakref
from collections import namedtuple
#import traceback
import sys # only for stderr
from datetime import datetime, timedelta
import logging
import inject
import py2neo
from py2neo import Node,Relationship, GraphError
from assimevent import AssimEvent
from AssimCclasses import pyNetAddr


# R0902: Too many instance attributes (17/10) // R0904: Too many public methods (27/20)
# pylint: disable=R0902,R0904
class Store(object):
    """This 'Store' class is a transaction-oriented implementation of Nigel Small's
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
        load_cypher_nodes generator which yields a vector of sametype nodes from a cypher query
        load_cypher_node return a single object from a cypher query
        load_cypher_query return iterator with objects for fields
        separate_in     separate objects we're related to by incoming relationships
        node            returns the neo4j.Node object associated with an object
        id              returns the id of the neo4j.Node associated with an object
        is_uniqueindex  returns True if the given index name is known to be unique
        __str__         formats information about this Store
        transaction_pending -- Property: True means a transaction is pending
        stats           a data member containing statistics in a dict
        reset_stats     Reset statistics counters and timers

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
    """
    LUCENE_RE = re.compile(r'([\-+&\|!\(\)\{\}[\]^"~\*?:\\])')
    LUCENE_RE = re.compile(r'([:[\]])')

    debug = True
    log = None

    @inject.params(db=neo4j.Graph, log=logging.Logger)
    def __init__(self, db=None, log=None, readonly=False):
        """
        Constructor for Transactional Write (Batch) Store objects
        ---------
        Parameters:
        db             - Database to associate with this object
        """
        from graphnodes import GraphNode
        self.db = db
        self._log = log
        assert not isinstance(log, dict)
        self.readonly = readonly
        self.stats = {}
        self.reset_stats()
        self.clients = {}
        self.newrels = []
        self.deletions = []
        self.classes = {}
        self.weaknoderefs = {}
        self._transaction_create_map = {}
        self._transaction_variables_defined = set()
        self.batch = None
        self.create_node_count = 0
        self.relate_node_count = 0
        self.index_entry_count = 0
        self.node_update_count = 0
        self.node_deletion_count = 0
        self.node_separate_count = 0
        self.cypher = ''

    def __str__(self):
        """

        :return: str: Store object as a string for debugging
        """
        ret = '{\n\tdb: %s' % self.db
        ret += ',\n\tclasses: %s' % self.classes
        if False and self.uniqueindexmap:
            ret += ',\n\tuniqueindexmap: %s' % self.uniqueindexmap
        if False and self.uniqueindexmap:
            ret += ',\n\tclasskeymap: %s' % self.classkeymap
        for attr in ('clients', 'newrels', 'deletions'):
            avalue = getattr(self, attr)
            acomma = '['
            s = "\n"
            for each in avalue:
                s += ('%s%s' % (acomma, each))
                acomma = ', '
            ret += ",\n\t%10s: %s" % (attr, s)
        ret += '\n%s\n' % self.fmt_dirty_attrs()
        ret += '\n\tweaknoderefs: %s' % self.weaknoderefs

        ret += '\n\tstats: %s' % self.stats
        ret += '\n\tbatch: %s' % self.batch
        ret += '\n}'
        return ret


    # For debugging...
    def dump_clients(self):
        """
        Dump out all our client objects and their supported attribute values and states

        :return: None
        """
        print ("CURRENT CLIENTS (%s:%d):" % (self, len(self.clients)), file=sys.stderr)
        for client in self.clients:
            print('Client %s:' % client, file=sys.stderr)
            for attr in Store._safe_attr_names(client):
                dirty = 'dirty' if attr in client.__store_dirty_attrs.keys() else 'clean'
                print('%10s: %s - %s' % (attr, dirty, client.__dict__[attr]), file=sys.stderr)

    def fmt_dirty_attrs(self):
        """
        Format dirty attributes of our client objects and their modified attribute values and states
        :return: str: dirty attribute info
        """
        result = '"Dirty Attrs": {'
        for client in self.clients:
            namedyet = False
            for attr in Store._safe_attr_names(client):
                if not hasattr(client, '__store_dirty_attrs'):
                    continue
                if attr in client.__store_dirty_attrs.keys():
                    if not namedyet:
                        result += ('Client %s:%s: {' % (client, Store.id(client)))
                        namedyet = True
                    result += ('%10s: %s,' % (attr, client.__dict__[attr]))
            if namedyet:
                result += '}\n'
        result += '}'
        return result


    def delete(self, subj):
        """
        Delete the saved object and all its relationships from the database

        :param subj: object: associated with a Neo4j node
        :return: None
        """
        if not hasattr(subj, '_Store__store_node'):
            raise ValueError('Object not associated with the Store system')
        if self.readonly:
            raise RuntimeError('Attempt to delete an object from a read-only store')
        node = subj.__store_node
        if not node.bound:
            raise ValueError('Node cannot be abstract')
        self.separate(subj)
        self.separate_in(subj)
        self.deletions.append(subj)


    def load(self, cls, **clsargs):
        """
        Load a pre-existing object from its constructor arguments.

        :param cls: class of the resulting object
        :param clsargs: arguments to the class
        :return:
        """
        if cls.__name__ not in self.classkeymap:
            print (self.classkeymap, file=sys.stderr)
            raise ValueError("Class [%s] does not have a known index [%s]"
                             % (cls.__name__, self.classkeymap))
        try:
            (index_name, idxkey, idxvalue) = self._get_idx_key_value(cls, clsargs, subj=clsargs)
        except KeyError:
            # On rare occasions, constructors create some default "unique" values
            # which don't appear as arguments, then the call above fails with KeyError.
            # The rest of the time, just using subj=clsargs is cheaper...
            # There are no cases where it produces different results.
            # If we're called by load_or_save() it will call the constructor again,
            # so it seems good to avoid that.
            subj = self.save(self.callconstructor(cls, clsargs))
            (index_name, idxkey, idxvalue) = self._get_idx_key_value(cls, clsargs, subj=subj)
        if not self.is_uniqueindex(index_name):
            raise ValueError("Class [%s] is not a unique indexed class" % cls)

        # See if we can find this node in memory somewhere...
        ret = self._localsearch(cls, idxkey, idxvalue)
        if ret is not None:
            return ret

        try:
            node = self.db.legacy.get_indexed_node(index_name, idxkey, idxvalue)
        except GraphError:
            return None
        return self._construct_obj_from_node(node, cls, clsargs) if node is not None else None

    def load_or_create(self, cls, **clsargs):
        """
        Analogous to 'save' - for loading an object or creating it if it
        doesn't exist

        :param cls: class of resulting object
        :param clsargs: arguments to the class constructor
        :return: object: as created by the 'cls' constructor
        """
        obj = self.load(cls, **clsargs)
        if obj is not None:
            if Store.debug:
                print('LOADED node[%s]: %s' % (str(clsargs), str(obj)), file=sys.stderr)
            return obj
        return self.save(self.callconstructor(cls, clsargs))

    def relate(self, subj, rel_type, obj, properties=None):
        """
        Define a 'rel_type' relationship subj-[:rel_type]->obj

        :param subj: from-node in relationship
        :param rel_type: type of relationship
        :param obj: to-node in relationship
        :param properties: relationship properties
        :return: None
        """
        assert not isinstance(obj, str)
        if self.readonly:
            raise RuntimeError('Attempt to relate objects in a read-only store')
        self.newrels.append({'from': subj, 'to': obj, 'type': rel_type, 'props': properties})
        if Store.debug:
            print ('NEW RELATIONSHIP FROM %s to %s' % (subj, obj), file=sys.stderr)
            if not Store.is_abstract(subj):
                print('FROM id is %s' % Store.id(subj), file=sys.stderr)
            if not Store.is_abstract(obj):
                print('TO id is %s' % Store.id(obj), file=sys.stderr)

    def relate_new(self, subj, rel_type, obj, properties=None):
        """
        Define a 'rel_type' relationship subj-[:rel_type]->obj but guaranteed that there
        is only one of this type between these nodes

        :param subj: from-node
        :param rel_type: relationship type
        :param obj: to-node
        :param properties: relationship properties
        :return: None
        """
        subjnode = subj.__store_node
        objnode = obj.__store_node

        # Check for relationships created in this transaction...
        for rel in self.newrels:
            if rel['from'] is subj and rel['to'] is obj and rel['type'] == rel_type:
                return
        # Check for pre-existing relationships
        if objnode.bound and subjnode.bound:
            rels = [rel for rel in subjnode.match_outgoing(rel_type, objnode)]
            if len(rels) > 0:
                return
        self.relate(subj, rel_type, obj, properties)

    def separate(self, subj, rel_type=None, obj=None):
        """
        Separate nodes related by the specified relationship type
            subj-[:rel_type]->obj -- obj can be None

        :param subj: from-node
        :param rel_type: relationship type
        :param obj: to-node
        :return: None
        """
        fromnode = subj.__store_node
        if not fromnode.bound:
            raise ValueError('Subj Node cannot be abstract')
        if obj is not None:
            obj = obj.__store_node
            if not obj.bound:
                raise ValueError('Obj Node cannot be abstract')

        # No errors - give it a shot!
        rels = subj.__store_node.match_outgoing(rel_type, obj)
        for rel in rels:
            if Store.debug:
                print ('DELETING RELATIONSHIP %s of type %s: %s' % (rel._id, rel_type, rel))
            if obj is not None:
                assert rel.end_node._id == obj._id
            self.deletions.append(rel)

    def separate_in(self, subj, rel_type=None, obj=None):
        """
        Separate nodes related by the specified relationship type
            subj<-[:rel_type]-obj -- obj can be none

        :param subj:
        :param rel_type:
        :param obj:
        :return:
        """
        fromnode = subj.__store_node
        if not fromnode.bound:
            raise ValueError('Node cannot be abstract')
        if obj is not None:
            obj = obj.__store_node
            if not obj.bound:
                raise ValueError('Node cannot be abstract')

        # No errors - give it a shot!
        rels = subj.__store_node.match_incoming(rel_type)
        for rel in rels:
            self.deletions.append(rel)

    def load_related(self, subj, rel_type, cls):
        """
        Load all outgoing-related nodes with the specified relationship type
        It would be really nice to be able to filter on relationship properties
        All it would take would be to write a little Cypher query
        Of course, that still leaves the recently-created case unhandled...

        :param subj: node subject of this query
        :param rel_type: type of relationship
        :param cls: class or general constructor function
        :return: generator(object): all the related objects
        """

        if Store.is_abstract(subj):
            # @TODO Should search recently created relationships...
            raise ValueError('Node to load_related from cannot be abstract')
        rels = subj.__store_node.match_outgoing(rel_type)
        for rel in rels:
            yield self._construct_obj_from_node(rel.end_node, cls)

    def load_in_related(self, subj, rel_type, cls):
        """
        Load all incoming-related nodes with the specified relationship type
        It would be really nice to be able to filter on relationship properties
        All it would take would be to write a little Cypher query
        Of course, that still leaves the recently-created case unhandled...

        :param subj: node to search for related nodes from
        :param rel_type: type of relationship
        :param cls: class or general constructor function
        :return: generator(object): all the related objects
        """
        if not subj.__store_node.bound:
            # @TODO Should search recently created relationships...
            raise ValueError('Node to load related from cannot be abstract')
        rels = subj.__store_node.match_incoming(rel_type)
        for rel in rels:
            yield (self._construct_obj_from_node(rel.start_node, cls))

    def load_cypher_nodes(self, querystr, cls, params=None, maxcount=None, debug=False):
        """
        Execute the given query that yields a single column of nodes
        all of the same Class (cls) and yield each of those Objects in turn
        through an iterator (generator)

        :param querystr: str: Cypher query string
        :param cls: class or general constructor function
        :param params: {str,str}:  parameters for the query
        :param maxcount: int: maximum number of nodes to yield (or None)
        :param debug: bool: True if you want debug output
        :return: generator(object): all the objects from the query
        """
        count = 0
        if params is None:
            params = {}
        if debug:
            print('Starting query %s(%s)' % (querystr, params), file=sys.stderr)
        for row in self.db.cypher.stream(querystr, params):
            if debug:
                print('Received Row from stream: %s' % row, file=sys.stderr)
            for key in row.__producer__.columns:
                if debug:
                    print('looking for column %s' % key, file=sys.stderr)
                node = getattr(row, key)
                if node is None:
                    if debug:
                        print('getattr(%s) failed' % key, file=sys.stderr)
                    continue
                yval = self.constructobj(cls, node)
                if debug:
                    print('yielding row %d (%s)' % (count, yval), file=sys.stderr)
                yield yval
            count += 1
            if maxcount is not None and count >= maxcount:
                if debug:
                    print('quitting on maxcount (%d)' % count, file=sys.stderr)
                break
        if debug:
            print('quitting on end of query output (%d)' % count, file=sys.stderr)
        return

    def load_cypher_node(self, query, cls, params=None):
        """
        :param query: str: Cypher query
        :param cls: class or general constructor function
        :param params: {str,str}:  parameters for the query
        :return: object: first node resulting form the query
        """
        'Load a single node as a result of a Cypher query'
        if params is None:
            params = {}
        for node in self.load_cypher_nodes(query, cls, params, maxcount=1):
            return node
        return None

    def load_cypher_query(self, querystr, clsfact, params=None, maxcount=None):
        """
        Iterator returning results from a query translated into classes, and so on
        Each iteration returns a namedtuple with node fields as classes, etc.
        Note that 'clsfact' _must_ be a class "factory" capable of translating any
        type of node encountered into the corresponding objects.
        Return result is a generator.

        :param querystr: str: Cypher query string
        :param clsfact: general constructor (factory) function
        :param params: {str,str}:  parameters for the query
        :param maxcount: int: maximum number of nodes to yield (or None)
        :return: generator(object): all the objects from the query
        """
        count = 0
        if params is None:
            params = {}
        rowfields = None
        rowclass = None
        for row in self.db.cypher.stream(querystr, **params):
            if rowfields is None:
                rowfields = row.__producer__.columns
                rowclass = namedtuple('FilteredRecord', rowfields)
            yieldval = []
            for attr in rowfields:
                yieldval.append(self._yielded_value(getattr(row, attr), clsfact))
            count += 1
            if maxcount is not None and count > maxcount:
                return
            yield rowclass._make(yieldval)

    def _yielded_value(self, value, clsfact):
        """
        Translate 'raw' query return to an appropriate object in our world
        :param value: object: Node, relationship, path, list, tuple, scalar value
        :param clsfact: general constructor (factory) function
        :return: object: appropriate value in our world
        """
        if isinstance(value, neo4j.Node):
            obj = self.constructobj(clsfact, value)
            return obj
        elif isinstance(value, neo4j.Relationship):
            from graphnodes import NeoRelationship
            return NeoRelationship(value)
        elif isinstance(value, neo4j.Path):
            return '''Sorry, Path values aren't yet supported'''
        elif isinstance(value, (list, tuple)):
            ret = []
            for elem in value:
                ret.append(self._yielded_value(elem, clsfact))
            return ret
        else:
            # Integers, strings, None, etc.
            return value


    @property
    def transaction_pending(self):
        """
        Return True if we have pending transaction work that needs flushing out

        :return: bool: as noted
        """
        return (len(self.clients) + len(self.newrels) + len(self.deletions)) > 0

    @staticmethod
    def callconstructor(constructor, kwargs):
        """
        Call a constructor (or function) in a (hopefully) correct way

        :param constructor: class or callable: thing that constructs the object
        :param kwargs: keyword arguments to the constructor function
        :return: object: whatever the constructor/function gives us
        """
        if Store.debug:
             print("CALLING CONSTRUCTOR: %s(%s)" % (constructor.__name__, str(kwargs)))
        try:
             args, _unusedvarargs, varkw, _unuseddefaults = inspect.getargspec(constructor)
        except TypeError:
             args, _unusedvarargs, varkw, _unuseddefaults = inspect.getargspec(constructor.__init__)
        newkwargs = {}
        extraattrs = {}
        if varkw: # Allows any keyword arguments
             newkwargs = kwargs
        else: # Only allows some keyword arguments
             for arg in kwargs:
                 if arg in args:
                     newkwargs[arg] = kwargs[arg]
                 else:
                     extraattrs[arg] = kwargs[arg]
        ret = constructor(**newkwargs)


         # Make sure the attributes match the desired values
        for attr in kwargs:
             kwa = kwargs[attr]
             if attr in extraattrs:
                 if not hasattr(ret, attr) or getattr(ret, attr) != kwa:
                     object.__setattr__(ret, attr, kwa)
             elif not hasattr(ret, attr) or getattr(ret, attr) is None:
                 # If the constructor set this attribute to a value, but it doesn't match the db
                 # then we let it stay as the constructor set it
                 # We gave this value to the constructor as a keyword argument.
                 # Sometimes constructors need to do that...
                 object.__setattr__(ret, attr, kwa)
        return ret

    def constructobj(self, constructor, node):
        """
        Create/construct an object from a Graph node

        :param constructor: Constructor for this object
        :param node: Neo4j.Node: graph node
        :return: object: constructed object
        """
        kwargs = node.get_properties()
        #print >> sys.stderr, 'constructobj NODE PROPERTIES', kwargs
        subj = Store.callconstructor(constructor, kwargs)
        #print >> sys.stderr, 'constructobj CONSTRUCTED NODE ', subj
        cls = subj.__class__
        (index_name, idxkey, idxvalue) = self._get_idx_key_value(cls,  {}, subj=subj)
        if not self.is_uniqueindex(index_name):
            raise ValueError("Class 'cls' must be a unique indexed class [%s]", cls)
        local = self._localsearch(cls, idxkey, idxvalue)
        if local is not None:
            return local
        else:
            self.register(subj, node=node)
            return subj

    @staticmethod
    def _safe_attr_names(subj):
        """
         'Return the list of supported attribute names from the given object'

        :param subj: object: the object of interest
        :return: [str]: attribute names
        """
        ret = []
        for attr in subj.__dict__.keys():
            if attr[0] == '_':
                continue
            ret.append(attr)
        return ret

    @staticmethod
    def safe_attrs(subj):
        """
        Return a dictionary of supported attributes and values from the given object

        :param subj: object: object of interest
        :return: dict(str, object): object converted to a dict
        """
        ret = {}
        for attr in Store._safe_attr_names(subj):
            ret[attr] = getattr(subj, attr)
        return ret

    @staticmethod
    def _proper_attr_value(obj, attr):
        """
        Return the value of the given attribute

        :param obj: object: object of interest
        :param attr: str: attribute name
        :return: object: whatever value that attribute has in the given object
        """
        return getattr(obj, attr)

    @staticmethod
    def _neo4j_safe_attrs(subj):
        """
        Return a dict of supported attributes from the given object,
        modified so that they're safe for Neo4j

        :param subj: object: object of interest
        :return: dict(str, object): object as dict
        """
        ret = {}
        for attr in Store._safe_attr_names(subj):
            ret[attr] = Store._neo4j_attr_value(subj, attr)
        return ret

    @staticmethod
    def _neo4j_attr_value(obj, attr):
        """
        Return a neo4j-safe version of attribute of an object

        :param obj: object: object of interest
        :param attr: str: attribute name
        :return: object: whatever value goes with this - sanitized for neo4j
        """
        value = getattr(obj, attr)
        return Store._fixup_attr_value(obj, attr, value)


    @staticmethod
    def _fixup_attr_value(obj, attr, value):
        """
        Validate and fix up the value so it can be stored in the Neo4j database
        (recursive)

        :param obj: object: object of interest
        :param attr: str: attribute name for messages only
        :param value: object: value to be fixed up
        :return: object: safe for Neo4j
        :raises ValueError: if the value can't be made acceptable
        """
        if isinstance(value, (str, unicode, float, int)):
            return value
        if isinstance(value, (list, tuple)):
            ret = []
            for elem in value:
                ret.append(Store._fixup_attr_value(obj, attr, elem))
            if len(ret) < 1:
                print("Attr %s of object %s cannot be an empty list"
                      % (attr, obj), file=sys.stderr)
                raise ValueError("Attr %s of object %s cannot be an empty list" % (attr, obj))
            # We don't check that all array elements are of the same type - Neo4j requirement
            # Elements also can't be a list or tuple...
            # In theory, one could simply make all array elements to be strings and that would
            # take care of the cases we know of - but that's probably not a good choice...
            return ret
        if isinstance(value, pyNetAddr):
            # These convert to perfectly wonderful strings - and we know what to do with them later.
            return str(value)
        else:
            print("Attr %s of object %s of type %s isn't acceptable"
            %   (attr, obj, type(value)), file=sys.stderr)
            raise ValueError("Attr %s of object %s of type %s isn't acceptable"
            %   (attr, obj, type(value)))

    @staticmethod
    def mark_dirty(objself, attr):
        """
        Mark the given attribute as dirty in our store

        :param objself: object: Object of interest
        :param attr: str: attribute name in objself
        :return: None
        """
        if hasattr(objself, '_Store__store_dirty_attrs'):
            objself.__store_dirty_attrs[attr] = True
            objself.__store.clients[objself] = True

    @staticmethod
    def _storesetattr(objself, name, value):
        """
        Does a setattr() - and marks changed attributes "dirty".  This
        permits us to know when attributes change, and automatically
        include them in the next transaction.
        This is a GoodThing.

        :param objself:
        :param name:
        :param value:
        :return:
        """

        if name[0] != '_':
            if hasattr(objself, '_Store__store_dirty_attrs'):
                try:
                     if getattr(objself, name) == value:
                         # print('Value of %s already set to %s' % (name, value), file=sys.stderr)
                         return
                except AttributeError:
                    pass
                if objself.__store.readonly:
                    print('Caught %s being set to %s!' % (name, value), file=sys.stderr)
                    raise RuntimeError('Attempt to set attribute %s using a read-only store' % name)
                if hasattr(value, '__iter__') and len(value) == 0:
                    raise ValueError(
                        'Attempt to set attribute %s to empty array (Neo4j limitation)' % name)
                objself.__store_dirty_attrs[name] = True
                objself.__store.clients[objself] = True
        object.__setattr__(objself, name, value)

    @staticmethod
    def _update_node_from_obj(subj):
        """
        Update the node from its paired object - _clearing_ dirty attributes

        :param subj: object: object to be used to update node from
        :return: None
        """
        node = subj.__store_node
        attrlist = subj.__store_dirty_attrs.keys()
        for attr in attrlist:
            node[attr] = Store._neo4j_attr_value(subj, attr)
            # print('SETTING node["%s"] to %s' %
            #                      (attr, Store.__attr_value(subj, attr)), file=sys.stderr)
        subj.__store_dirty_attrs = {}

    def _update_obj_from_node(self, subj):
        """
        'Update an object from its paired node - preserving "dirty" attributes'

        :param subj: object: thing to be updated
        :return: None
        """
        node = subj.__store_node
        nodeprops = node.get_properties()
        remove_subj = subj not in self.clients
        for attr in nodeprops.keys():
            pattr = nodeprops[attr]
            if attr in subj.__store_dirty_attrs:
                remove_subj = False
                continue
            #print >> sys.stderr, ('Setting obj["%s"] to %s' % (attr, pattr))
            # Avoid getting it marked as dirty...
            object.__setattr__(subj, attr, pattr)
        if remove_subj and subj in self.clients:
            del self.clients[subj]

        # Make sure everything in the object is in the Node...
        for attr in Store._safe_attr_names(subj):
            if attr not in nodeprops:
                subj.__store_dirty_attrs[attr] = True
                self.clients[subj] = True

    def reset_stats(self):
        """
        Reset all our statistical counters and timers

        :return: None
        """
        self.stats = {}
        for statname in ('nodecreate', 'relate', 'separate', 'index', 'attrupdate',
                         'index', 'nodedelete', 'addlabels'):
            self.stats[statname] = 0
        self.stats['lastcommit'] = None
        self.stats['totaltime'] = timedelta()

    def _bump_stat(self, statname, increment=1):
        """
        Increment the given statistic by the given increment - default increment is 1

        :param statname:
        :param increment:
        :return:
        """
        self.stats[statname] += increment


    def _localsearch(self, cls, idxkey, idxvalue):
        """
        Search the 'client' array and the weaknoderefs to see if we can find
        the requested object before going to the database
        idxkey, idxvalue uniquely determine which object we're after
                they're effectively key values

        TODO: This needs to be completely redesigned, and rewritten
              Needs new API

        :param cls: class: class of object
        :param idxkey: str: index key
        :param idxvalue: str: value
        :return: object or None
        """

        classname = cls.__name__
        kmap = self.classkeymap[classname]
        searchlist = {}
        if 'kattr' in kmap:
            searchlist[kmap['kattr']] = idxkey
        if 'vattr' in kmap:
            searchlist[kmap['vattr']] = idxvalue

        searchset = self.clients.keys()
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

    def _construct_obj_from_node(self, node, cls, clsargs=None):
        """
        Construct an object associated with the given node
        and register it in our current node-associated object registry

        :param node: Neoj4.node: Node to construct object from
        :param cls: cls: class of the object - or factory constructor
        :param clsargs: dict(str, object): arguments to the constructor
        :return: object
        """
        clsargs = [] if clsargs is None else clsargs
        # Do we already have a copy of an object that goes with this node somewhere?
        # If so, we need to update and return it instead of creating a new object
        nodeid = node._id
        if nodeid in self.weaknoderefs:
            subj = self.weaknoderefs[nodeid]()
            if subj is None:
                del self.weaknoderefs[nodeid]
            else:
                # Yes, we have a copy laying around somewhere - update it...
                # print >> sys.stderr, ('WE HAVE NODE LAYING AROUND...', node.get_properties())
                self._update_obj_from_node(subj)
                return subj
        # print('NODE ID: %d, node = %s' % (node._node_id, str(node)), file=sys.stderr)
        retobj = Store.callconstructor(cls, node.get_properties())
        for attr in clsargs:
            if not hasattr(retobj, attr) or getattr(retobj, attr) is None:
                # None isn't a legal value for Neo4j to store in the database
                setattr(retobj, attr, clsargs[attr])
        return self.register(retobj, node=node)

    def register(self, subj, node=None, index=None, unique=None, key=None, value=None):
        """
        Register this object with a Node, so we can track it for updates, etc.

        :param subj:object: object to register
        :param node: neo4j.Node: node to associate it with
        :param index: str: index name to store it in
        :param unique: bool: Always True
        :param key: key value for index
        :param value: value value for index
        :return: object: subj - the original object - now decorated
        """
        # todo: API and code needs redesign

        if not isinstance(subj, object):
            raise(ValueError('Instances registered with Store class must be subclasses of object'))
        assert not hasattr(subj, '_Store__store')
        assert subj not in self.clients
        self.clients[subj] = True
        if Store.debug:
            self._log.debug("register-ing %s[%s] with node %s [abstract? %s], %s"
                            % (subj, type(subj), node, Store.is_abstract(node), type(node)))
            self._log.debug("Clients include: %s" % str(self.clients.keys()))

        # todo: this is way too many attributes
        # We don't really need attributes, we can look things up in a table anyway...
        # This might be slightly faster, but dicts in python are very fast
        subj.__store = self
        subj.__store_node = node
        subj.__store_index = index
        subj.__store_index_key = key
        subj.__store_index_value = value
        subj.__store_index_unique = unique
        subj.__store_dirty_attrs = {}
        if subj.__class__ not in self.classes:
            subj.__class__.__setattr__ = Store._storesetattr
            self.classes[subj.__class__] = True
        if node is not None and node.bound:
            if node._id in self.weaknoderefs:
                weakling = self.weaknoderefs[node._id]()
                if weakling is None:
                    del self.weaknoderefs[node._id]
                else:
                    print('OOPS! - already here... self.weaknoderefs',
                          weakling, weakling.__dict__, file=sys.stderr)
            assert node._id not in self.weaknoderefs or self.weaknoderefs[node._id] is None
            self.weaknoderefs[node._id] = weakref.ref(subj)
        if node is not None:
            if 'post_db_init' in dir(subj):
                subj.post_db_init()
            if not node.bound:
                # Create an event to commemorate the creation of the new database object
                if AssimEvent.event_observation_enabled:
                    AssimEvent(subj, AssimEvent.CREATEOBJ)

        if Store.debug:
            self.dump_clients()
        return subj

    def _newly_created_nodes(self):
        """
        Return the set of newly created nodes for this transaction

        :return: [(object, neo4j.Node)]
        """
        return [client for client in self.clients if client.is_abstract]


    @staticmethod
    def node(subj):
        """
        Returns the neo4j.Node associated with the given object

        :param subj: object: object of interest
        :return: neo4j.Node: associated node
        """
        return subj.association.node

     #
     #   Except for commit() and abort(), all member functions from here on
     #   construct the batch job from previous requests
     #

    def _batch_construct_create_nodes(self):
         'Construct batch commands for all the new objects in this batch'
         # todo: needs complete redesign to create Cypher statements
         for subj in self._newly_created_nodes():
             assert isinstance(subj, GraphNode)
             if Store.debug:
                 print ('====== Performing batch.create(%s: %s) - for new node'
                 %   (subj.association.variable_name, str(subj)), file=sys.stderr)

             self.cypher += subj.association.cypher_create_node_query()
             self._transaction_create_map[subj.association.variable_name] = subj
             self._transaction_variables_defined.add(subj.association.variable_name)
             self._bump_stat('nodecreate')

    def _batch_define_if_undefined(self, subj):
        """
        Define a previously undefined variable by searching the database for it
        Or do nothing if it's been previously defined...
        :return: None
        """
        variable_name = subj.association.variable_name
        if variable_name not in self._transaction_variables_defined:
            self.cypher += subj.association.cypher_find_match_clause()
            self._transaction_variables_defined.add(variable_name)

    def _batch_construct_add_labels(self):
        """
        Construct batch commands for all the labels to be added for this batch
        Note that we add "default" labels from class membership for objects automatically

        :return: None
        """
        # todo: needs complete redesign to create Cypher statements
        pass

    def _batch_construct_relate_nodes(self):
        """
        Construct the batch commands to create the requested relationships
        return: None
        """
        for rel in self.newrels:
            fromobj = rel['from']
            toobj = rel['to']
            self._batch_define_if_undefined(fromobj)
            self._batch_define_if_undefined(toobj)
            self._bump_stat('relate')
            if Store.debug:
                print('ADDING rel %s' % rel, file=sys.stderr)
            self.cypher += fromobj.association.cypher_relate_node(rel['type'],
                                                                  toobj,
                                                                  attrs=rel['props'])

    def _batch_construct_deletions(self):
        """
         'Construct batch commands for removing relationships or nodes'

        :return: None
        """
         # todo: needs complete redesign to create Cypher statements
         delrels = {}
         delnodes = {}
         for relorobj in self.deletions:
             if isinstance(relorobj, neo4j.Relationship):
                 relid = relorobj._id
                 if relid not in delrels:
                     if Store.debug and Store.log:
                         Store.log.debug('DELETING rel %d: %s' % (relorobj._id, relorobj))
                     self._bump_stat('separate')
                     self.batch.delete(relorobj)
                     delrels[relid] = True
             else:
                 # Then it must be a node-related object...
                 if Store.debug and Store.log:
                     Store.log.debug('DELETING NODE %s: %s' %
                                     (str(relorobj.__dict__.keys()), relorobj))
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
                 if Store.debug and Store.log:
                     Store.log.debug('DELETING node %s' % node)
                 self._bump_stat('nodedelete')
                 self.batch.delete(node)
                 delnodes[relid] = True

    def _batch_construct_node_updates(self):
         'Construct batch commands for updating attributes on "old" nodes'
         # todo: needs complete redesign to create Cypher statements
         clientset = {}
         for subj in self.clients:
             assert subj not in clientset
             clientset[subj] = True
             node = subj.__store_node
             if not node.bound:
                 continue
             for attr in subj.__store_dirty_attrs.keys():
                 # Each of these items will return None in the HTTP stream...
                 self.node_update_count += 1
                 self._bump_stat('attrupdate')
                 setattr(node, attr, Store._neo4j_attr_value(subj, attr))
                 if Store.debug:
                     print >> sys.stderr, ('Setting property %s of node %d to %s' % (attr
                     ,       node._id, Store._proper_attr_value(subj, attr)))
                     if Store.log:
                         Store.log.debug('Setting property %s of %d to %s' % (attr
                         ,       node._id, Store._proper_attr_value(subj, attr)))
                 self.batch.set_property(node, attr, Store._proper_attr_value(subj, attr))

    def abort(self):
         'Clear out any currently pending transaction work - start fresh'
         if self.batch is not None:
             self.batch = None
         for subj in self.clients:
             subj.__store_dirty_attrs = {}  # should probably be a set...
         self.clients = {}  # should also be a set...
         self.newrels = []
         self.deletions = []
         # Clean out dead node references
         for nodeid in self.weaknoderefs.keys():
             subj = self.weaknoderefs[nodeid]()
             if subj is None or not hasattr(subj, '_Store__store_node'):
                 del self.weaknoderefs[nodeid]

    def commit(self):
         '''Commit all the changes we've created since our last transaction'''
         if Store.debug:
             print >> sys.stderr, ('COMMITTING THIS THING:', str(self))
         self.batch = self.batch if self.batch is not None \
                      else py2neo.legacy.LegacyWriteBatch(self.db)
         self._batch_construct_create_nodes()        # These return new nodes in batch return result
         self._batch_construct_relate_nodes()        # These return new relationships
         self._batch_construct_new_index_entries()   # These return the objects indexed
         self._batch_construct_node_updates()        # These return None
         self._batch_construct_add_labels()          # Not sure what these return
         self._batch_construct_deletions()           # These return None
         if Store.debug:
             print >> sys.stderr, ('Batch Updates constructed: Committing THIS THING:', str(self))
             if Store.log:
                 Store.log.debug('Batch Updates constructed: Committing THIS THING: %s'
                 %   str(self))
         start = datetime.now()
         try:
             submit_results = self.batch.submit()
         except GraphError as e:
             print >> sys.stderr, ('FAILED TO COMMIT THIS THING:', str(self))
             print >> sys.stderr, self
             print >> sys.stderr, ('BatchError: %s' % e)
             raise e
         if Store.debug:
             print >> sys.stderr, 'SUBMIT RESULTS FOLLOW:'
             for result in submit_results:
                 print >> sys.stderr, 'SUBMITRESULT:', type(result), result
         end = datetime.now()
         diff = end - start
         self.stats['lastcommit'] = diff
         self.stats['totaltime'] += diff

         # Save away (update) any newly created nodes...
         for subj in self._newly_created_nodes():
             # TODO: REWRITE THIS...
             newnode = submit_results[index]
             if Store.debug:
                 print('LOOKING at new node with batch index %d' % index, file=sys.stderr)
                 print('NEW NODE looks like %s' % str(newnode), file=sys.stderr)
                 print('SUBJ (our copy) looks like %s' % str(subj), file=sys.stderr)
                 print('NEONODE (their copy) looks like %d, %s'
                 %       (newnode._id, str(newnode.get_properties())), file=sys.stderr)
             # This 'subj' used to have an abstract node, now it's concrete
             subj.__store_node = newnode
             self.weaknoderefs[newnode._id] = weakref.ref(subj)
             for attr in newnode.get_properties():
                 if not hasattr(subj, attr):
                     print ("OOPS - we're missing attribute %s" % attr, file=sys.stderr)
                 elif getattr(subj, attr) != newnode[attr]:
                     print ("OOPS - attribute %s is %s and should be %s"
                     %   (attr, getattr(subj, attr), newnode[attr]), file=sys.stderr)
                     #self.dump_clients()
         self.abort()
         if Store.debug:
             print('DB TRANSACTION COMPLETED SUCCESSFULLY', file=sys.stderr)
         return submit_results

    def clean_store(self):
         '''Clean out all the objects we used to have in our store - afterwards we
         have none associated with this Store'''
         for nodeid in self.weaknoderefs:
             obj = self.weaknoderefs[nodeid]()
             if obj is not None:
                 for attr in obj.__dict__.keys():
                     if attr.startswith('_Store__store'):
                         delattr(obj, attr)
         self.weaknoderefs = {}
         self.abort()

 if __name__ == "__main__":
     from cmainit import CMAInjectables
     # pylint: disable=C0413
     from cmainit import Neo4jCreds
     # I'm not too concerned about this test code...
     # R0914:923,4:testme: Too many local variables (17/15)
     # pylint: disable=R0914
     inject.configure_once(CMAInjectables.test_config_injection)


     def testme():
         'A little test code...'

         # Must be a subclass of 'object'...
         # pylint: disable=R0903
         class Drone(object):
             'This is a Class docstring'
             def __init__(self, a=None, b=None, name=None):
                 'This is a doc string'
                 self.a = a
                 self.b = b
                 self.name = name
             def foo_is_blacklisted(self):
                 'This is a doc string too'
                 return 'a=%s b=%s name=%s' % (self.a, self.b, self.name)

             @classmethod
             def __meta_labels__(cls):
                 return ['Class_%s' % cls.__name__]

         Neo4jCreds().authenticate()
         ourdb = neo4j.Graph()
         ourdb.legacy.get_or_create_index(neo4j.Node, 'Drone')
         dbvers = ourdb.neo4j_version
         # Clean out the database
         if dbvers[0] >= 2:
             qstring = 'match (n) optional match (n)-[r]-() delete n,r'
         else:
             qstring = 'start n=node(*) match n-[r?]-() delete n,r'
         ourdb.cypher.run(qstring)
         # Which fields of which types are used for indexing
         classkeymap = {
             Drone:   # this is for the Drone class
                 {'index':   'Drone',    # The index name for this class is 'Drone'
                 'key':      'Drone',    # The key field is a constant - 'Drone'
                 'vattr':    'name'      # The value field is an attribute - 'name'
                 }
         }
         # uniqueindexmap and classkeymap are optional, but make save() much more convenient

         store = Store(ourdb, uniqueindexmap={'Drone': True}, classkeymap=classkeymap)
         DRONE = 'Drone121'

         # Construct an initial Drone
         #   fred = Drone(a=1,b=2,name=DRONE)
         #   store.save(fred)    # Drone is a 'known' type, so we know which fields are index key(s)
         #
         #   load_or_create() is the preferred way to create an object...
         #
         fred = store.load_or_create(Drone, a=1, b=2, name=DRONE)

         assert fred.a == 1
         assert fred.b == 2
         assert fred.name == DRONE
         assert not hasattr(fred, 'c')
         # Modify some fields -- add some...
         fred.a = 52
         fred.c = 3.14159
         assert fred.a == 52
         assert fred.b == 2
         assert fred.name == DRONE
         assert fred.c > 3.14158 and fred.c < 3.146
         # Create some relationships...
         rellist = ['ISA', 'WASA', 'WILLBEA']
         for rel in rellist:
             store.relate(fred, rel, fred)
         # These should have no effect - but let's make sure...
         for rel in rellist:
             store.relate_new(fred, rel, fred)
         store.commit()  # The updates have been captured...
         print >> sys.stderr, ('Statistics:', store.stats)

         assert fred.a == 52
         assert fred.b == 2
         assert fred.name == DRONE
         assert fred.c > 3.14158 and fred.c < 3.146

         #See if the relationships 'stuck'...
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
         print >> sys.stderr, (store)
         assert not store.transaction_pending

         #Add another new field
         fred.x = 'malcolm'
         store.dump_clients()
         print >> sys.stderr, ('store:', store)
         assert store.transaction_pending
         store.commit()
         print >> sys.stderr, ('Statistics:', store.stats)
         assert not store.transaction_pending
         assert fred.a == 52
         assert fred.b == 2
         assert fred.name == DRONE
         assert fred.c > 3.14158 and fred.c < 3.146
         assert fred.x == 'malcolm'

         # Check out load_indexed...
         newnode = store.load_indexed('Drone', 'Drone', fred.name, Drone)[0]
         print >> sys.stderr, ('LoadIndexed NewNode: %s %s' % (newnode, store.safe_attrs(newnode)))
         # It's dangerous to have two separate objects which are the same thing be distinct
         # so we if we fetch a node, and one we already have, we get the original one...
         assert fred is newnode
         if store.transaction_pending:
             print >> sys.stderr, ('UhOh, we have a transaction pending.')
             store.dump_clients()
             assert not store.transaction_pending
         assert newnode.a == 52
         assert newnode.b == 2
         assert newnode.x == 'malcolm'
         store.separate(fred, 'WILLBEA')
         assert store.transaction_pending
         store.commit()
         print >> sys.stderr, ('Statistics:', store.stats)

         # Test a simple cypher query...
         qstr = "START d=node:Drone('*:*') RETURN d"
         qnode = store.load_cypher_node(qstr, Drone) # Returns a single node
         print >> sys.stderr, ('qnode=%s' % qnode)
         assert qnode is fred
         qnodes = store.load_cypher_nodes(qstr, Drone) # Returns iterable
         qnodes = [qnode for qnode in qnodes]
         assert len(qnodes) == 1
         assert qnode is fred

         # See if the now-separated relationship went away...
         rels = store.load_related(fred, 'WILLBEA', Drone)
         rels = [rel for rel in rels]
         assert len(rels) == 0
         store.delete(fred)
         assert store.transaction_pending
         store.commit()

         # When we delete an object from the database, the  python object
         # is disconnected from the database...
         assert not hasattr(fred, '_Store__store_node')
         assert not store.transaction_pending

         print >> sys.stderr, ('Statistics:', store.stats)
         print >> sys.stderr, ('Final returned values look good!')


     Store.debug = False
     testme()
