#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100 fileencoding=utf-8
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
from typing import Optional
import time
import collections
import inspect
import weakref

# import traceback
from sys import stderr
from datetime import datetime, timedelta
import inject
import py2neo
from neobolt.exceptions import ServiceUnavailable
from assimevent import AssimEvent
from AssimCclasses import pyNetAddr


# R0902: Too many instance attributes (17/10) // R0904: Too many public methods (27/20)
# pylint: disable=R0902,R0904
class Store(object):
    """This 'Store' class is a transaction-oriented implementation of Nigel Small's
    OGM (Object-Graph-Mapping) API - with a few extensions and a few things not implemented.

    Some interesting extensions:
    ----------------------------
        -   You can tell the Store constructor things about your Classes and Indexes
                makes handling indexes simpler and less error prone. This affects the
                save() method and makes it usable far more often.
        -   All updates are happen in a batch job - as a single transaction.

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

    debug = True
    log = None

    # @inject.params(db='py2neo.Graph', log='logging.Logger')
    def __init__(self, db, log, readonly=False, factory_constructor=None):
        """
        Constructor for Transactional Write (Batch) Store objects
        ---------
        Parameters:
        db             - Database to associate with this object
        """
        from graphnodes import GraphNode

        self.graph_node = GraphNode
        self.db = db
        self._log = log
        # print("LOG STUFF", type(self._log), self._log, log)
        assert not isinstance(log, dict)
        assert log is not None
        self.readonly = readonly
        self.stats = {}
        self.reset_stats()
        self.clients = list()
        self.classes = {}
        # self.weaknoderefs = weakref.WeakValueDictionary()
        self.weaknoderefs = {}
        self.factory = factory_constructor if factory_constructor else GraphNode.factory
        self.db_transaction = None
        # print("RETURNING class %s" % self.__class__.__name__)
        return

    def __str__(self):
        """

        :return: str: Store object as a string for debugging
        """
        ret = "{\n\tdb: %s" % self.db
        ret += ",\n\tclasses: %s" % self.classes
        for attr in ("clients",):
            avalue = getattr(self, attr)
            acomma = "["
            s = "\n"
            for each in avalue:
                s += "%s%s" % (acomma, each)
                acomma = ", "
            ret += ",\n\t%10s: %s" % (attr, s)
        ret += "\n%s\n" % self.fmt_dirty_attrs()
        # ret += "\n\tweaknoderefs: %s" % self.weaknoderefs

        ret += "\n\tstats: %s" % self.stats
        ret += "\n}"
        return ret

    # For debugging...
    def dump_clients(self, title=None, outfile=stderr):
        """
        Dump out all our client objects and their supported attribute values and states

        :return: None
        """
        if title:
            print(title, file=outfile)
        print("CURRENT CLIENTS (%s:%d):" % (self, len(self.clients)), file=outfile)
        for client in self.clients:
            print(
                "Client %s [%s]:" % (client.association.variable_name, client.association.node_id),
                file=outfile,
            )
            for attr in Store._safe_attr_names(client):
                dirty = "dirty" if attr in client.association.dirty_attrs else "clean"
                print("%10s: %s - %s" % (attr, dirty, getattr(client, attr)), file=outfile)
            print(
                "%10s: %s: %s" % ("node_id", client.association.node_id, object.__str__(client)),
                file=outfile,
            )

        for obj in self.weaknoderefs.values():
            obj = obj()
            if obj and obj not in self.clients:
                print("WEAK: %s" % obj, file=outfile)
                self._log.debug("WEAK: %s" % obj)
        # self._audit_weaknodes_clients()

    def fmt_dirty_attrs(self):
        """
        Format dirty attributes of our client objects and their modified attribute values and states
        :return: str: dirty attribute info
        """
        result = '"Dirty Attrs": {'
        for client in self.clients:
            namedyet = False
            for attr in Store._safe_attr_names(client):
                if not hasattr(client, "__store_dirty_attrs"):
                    continue
                if attr in client.association.dirty_attrs():
                    if not namedyet:
                        result += "Client %s:%s: {" % (client, client.association.node_id)
                        namedyet = True
                    result += "%10s: %s," % (attr, getattr(client, attr))
            if namedyet:
                result += "}\n"
        result += "}"
        return result

    def delete(self, subj):
        """
        Delete the object and all its relationships from the database

        :param subj: GraphNode: associated with a Neo4j node
        :return: None
        """
        if self.readonly:
            raise RuntimeError("Attempt to delete an object from a read-only store")
        cypher = subj.association.cypher_delete_node_query()
        if self.debug:
            print("DELETE cypher:", cypher, file=stderr)
        self.db_transaction.run(cypher).forward()
        node_id = subj.association.node_id
        subj._association = None
        if subj in self.clients:
            self.clients.remove(subj)
        if node_id in self.weaknoderefs:
            del self.weaknoderefs[node_id]

    @staticmethod
    def _get_key_values(clsobj, clsargs=None, subj=None):
        """
        Return a dict of key names and values
        :param clsobj: classtype: resulting class
        :param clsargs: constructor arguments to class
        :param subj: object possibly from a constructor...
        :return: dict: key name/value pairs
        """
        result = {}
        for attr in clsobj.meta_key_attributes():
            if hasattr(subj, attr):
                result[attr] = getattr(subj, attr)
            elif attr in clsargs:
                result[attr] = clsargs[attr]
            else:
                print(f"get_key_values: {clsobj}:{dir(clsobj)}: {clsargs}", file=stderr)
                print(f"get_key_values: EXPECTED {attr}", file=stderr)
        return result

    @staticmethod
    def neo_node_id(node):
        """
        Return the Neo4j node ID from the node
        :param node: py2neo.Node
        :return: int: node id
        """
        return node.identity if node else None

    def add_labels(self, subj, labels):
        """
        Add these labels to our 'subj' node...
        :param subj: GraphNode: Node to add labels to
        :param labels: (str,)
        :return: None
        """
        label_cypher = subj.association.cypher_add_labels_clause(labels)
        if label_cypher == "":
            return
        cypher = subj.association.cypher_find_match_clause() + "\n" + label_cypher
        if self.debug:
            print('ADD_LABELS:"%s"' % cypher, file=stderr)
        self.db_transaction.run(cypher).forward()

    def delete_labels(self, subj, labels):
        """
        Delete these labels from our 'subj' node...
        :param subj: GraphNode: Node to add labels to
        :param labels: (str,)
        :return: None
        """
        label_cypher = subj.association.cypher_delete_labels_clause(labels)
        if label_cypher == "":
            return
        cypher = subj.association.cypher_find_match_clause() + "\n" + label_cypher
        if self.debug:
            print("DELETE_LABELS(%s)" % cypher, file=stderr)
        self.db_transaction.run(cypher).forward()

    #
    # functions that return nodes, typically from the database
    #
    def load(self, cls, **clsargs):
        """
        Load a pre-existing object from its constructor arguments.

        :param cls: class of the resulting object
        :param clsargs: arguments to the class
        :return: object
        """
        # print('LOAD: %s' % (str(clsargs)))
        self._audit_weaknodes_clients()
        subj = self.callconstructor(cls, clsargs)
        # print('LOAD class %s: constructed obj: %s' % (cls.__name__, object.__str__(subj)),
        #       file=stderr)
        self._audit_weaknodes_clients()
        key_values = self._get_key_values(cls, subj=subj)
        # print('LOAD class %s: clsargs: %s' % (cls.__name__, str(clsargs)), file=stderr)
        # self._log.debug('LOAD class %s: clsargs: %s' % (cls.__name__, str(clsargs)))
        # print('LOAD class %s: key values: %s' % (cls.__name__, str(key_values)), file=stderr)
        # self._log.debug('LOAD class %s: key values: %s' % (cls.__name__, str(key_values)))

        # See if we can find this node in memory somewhere...
        result = self._localsearch(cls, key_values)
        self._audit_weaknodes_clients()
        if result:
            # print("FOUND IN LOCALSEARCH - returning %s/%s" % (object.__str__(result), result),
            #       file=stderr)
            self._audit_weaknodes_clients()
            return result

        try:
            query = subj.association.cypher_find_query()
            # print('LOAD class %s: query: %s' % (cls.__name__, query), file=stderr)
            # self._log.debug('LOAD class %s: query: %s' % (cls.__name__, query))
            node = self.db.evaluate(query)
            # print('QUERY RETURNED node %s' % node)
        except py2neo.GraphError as oops:
            self._log.warning("QUERY RETURNED GraphError %s" % oops)
            return None
        self._audit_weaknodes_clients()
        result = self._construct_obj_from_node(node) if node else None
        # print('LOAD class %s: result: %s' % (cls.__name__, object.__str__(result)), file=stderr)
        # print("NOT FOUND IN LOCALSEARCH - returning %s/%s" % (object.__str__(result), result))
        self._audit_weaknodes_clients()
        return result

    def load_or_create(self, cls, **clsargs):
        """
        Load this object from the database if it exists, or create it if it doesn't
        doesn't exist

        :param cls: class of resulting object
        :param clsargs: arguments to the class constructor
        :return: object: as created by the 'cls' constructor
        """
        self.debug = True
        if self.debug:
            print("LOAD OR CREATE: %s" % (str(clsargs)), file=stderr)
            self._log.debug("LOAD OR CREATE: %s" % (str(clsargs)))
        obj = self.load(cls, **clsargs)
        print(f"LOAD/CREATE OBJECT: {obj}")
        if obj is not None:
            if self.debug:
                print("LOADED node[%s]: %s" % (str(clsargs), str(obj)))
            return obj
        print('NOT LOADED node[%s]: %s' % (str(clsargs), str(obj)))
        subj = self.callconstructor(cls, clsargs)
        assert subj is not None
        self._audit_weaknodes_clients()
        print(f"LOAD clsargs WERE {clsargs}")
        self.register(subj)
        self._audit_weaknodes_clients()
        if AssimEvent.event_observation_enabled:
            AssimEvent(subj, AssimEvent.CREATEOBJ)
        return subj

    def load_related(self, subj, rel_type, obj=None, direction="forward", attrs=None):
        """
        Return nodes related to this one by the given 'rel_type'
        :param subj: GraphNode: from node
        :param rel_type:
        :param obj: GraphNode: to node
        :param direction: which direction should the relationship go?
        :param attrs: properties/attributes to set on the new relationship
        :return: generator yielding related nodes
        """
        other_association = obj.association if obj is not None else None
        query = subj.association.cypher_return_related_nodes(
            rel_type, direction=direction, other_node=other_association, attrs=attrs
        )
        # print("load_related: %s" % query, file=stderr)
        if self.debug:
            print("load_related cypher:", query, file=stderr)
        cursor = self.db.run(query)
        print(f"load_related cypher: {cursor}")
        while cursor.forward():
            print(f"Yielding node : {cursor.current[0]}")
            yield self._construct_obj_from_node(cursor.current[0])
        print("returning from load_related_cypher")

    def load_in_related(self, subj, rel_type, obj=None, attrs=None):
        """
        Load all incoming-related nodes with the specified relationship type
        It would be really nice to be able to filter on relationship properties
        All it would take would be to write a little Cypher query
        Of course, that still leaves the recently-created case unhandled...

        :param subj: node to search for related nodes from
        :param rel_type: type of relationship
        :param obj: node to search for related nodes to
        :param attrs: dict(str, str): properties of the desired relationships
        :return: generator(object): all the related objects
        """
        return self.load_related(subj, rel_type, obj, direction="reverse", attrs=attrs)

    def load_cypher_nodes(self, querystr, params=None, maxcount=None, debug=False):
        """
        Execute the given query that yields a single column of nodes
        all of the same Class (cls) and yield each of those Objects in turn
        through an iterator (generator)

        :param querystr: str: Cypher query string
        :param params: {str,str}:  parameters for the query
        :param maxcount: int: maximum number of nodes to yield (or None)
        :param debug: bool: True if you want debug output
        :return: generator(object): all the objects from the query
        """
        count = 0
        if params is None:
            params = {}
        if self.debug or debug:
            print("load_cypher_nodes: Starting query %s(%s)" % (querystr, params), file=stderr)
        cursor = self.db.run(querystr, params)
        print("db.run complete.", file=stderr)
        while cursor.forward():
            print("cursor.forward complete.", file=stderr)
            item = self._construct_obj_from_node(cursor.current[0])
            print("construct_obj_from_node complete.", file=stderr)
            if self.debug or debug:
                print(f"YIELDING result: {item}", file=stderr)
            yield item
            count += 1
            if maxcount is not None and count >= maxcount:
                if debug:
                    print("quitting on maxcount (%d)" % count, file=stderr)
                break
        if self.debug or debug:
            print("quitting on end of query output (%d)" % count, file=stderr)
        return

    def load_cypher_node(self, query, params=None):
        """
        Load a single node as a result of a Cypher query
        :param query: str: Cypher query
        :param params: {str,str}:  parameters for the query
        :return: object: first node resulting form the query
        """
        if params is None:
            params = {}
        for node in self.load_cypher_nodes(query, params, maxcount=1):
            return node
        return None

    def load_cypher_query(self, querystr, params=None, maxcount=None):
        """
        Iterator returning results from a query translated into classes, and so on
        Each iteration returns a namedtuple with node fields as classes, etc.
        Note that 'clsfact' _must_ be a class "factory" capable of translating any
        type of node encountered into the corresponding objects.
        Return result is a generator.

        :param querystr: str: Cypher query string
        :param params: {str,str}:  parameters for the query
        :param maxcount: int: maximum number of nodes to yield (or None)
        :return: generator(object): all the objects from the query
        """
        count = 0
        if params is None:
            params = {}
        if self.debug:
            print("load_cypher_query: %s" % querystr, file=stderr)
        cursor = self.db.run(querystr, params)
        print(f"Cypher cursor: {cursor}", file=stderr)
        tuple_class = None
        while cursor.forward():
            print(f"Cypher cursor forward... {cursor}", file=stderr)
            yieldval = []
            current = cursor.current
            print(f"Cypher cursor current... {current}", file=stderr)
            # print('CURRENT.keys[%s]: cursor.current.keys(): %s'
            #       % (type(current), str(current.keys())))
            for elem in current:
                yieldval.append(self._yielded_value(elem))
            if tuple_class is None:
                tuple_class = collections.namedtuple("CypherQueryResult", " ".join(current.keys()))
            print(f"Cypher yielding... {yieldval}", file=stderr)
            yield tuple_class(*yieldval)
            # yield yieldval
            count += 1
            if maxcount is not None and count >= maxcount:
                print(f"Cypher returning on maxcount...", file=stderr)
                return
        print(f"Cypher returning...", file=stderr)

    def _yielded_value(self, value):
        """
        Translate 'raw' query return to an appropriate object in our world
        :param value: object: Node, relationship, path, list, tuple, scalar value
        :return: object: appropriate value in our world
        """
        if isinstance(value, py2neo.Node):
            return self._construct_obj_from_node(value)
        elif isinstance(value, py2neo.Relationship):
            from graphnodes import NeoRelationship

            return NeoRelationship(value)
        elif isinstance(value, py2neo.Path):
            return "Sorry, Path values not yet supported"
        elif isinstance(value, (list, tuple)):
            result = []
            for elem in value:
                result.append(self._yielded_value(elem))
            return result
        else:
            # Integers, strings, None, etc.
            return value

    def labels(self, subj):
        """
        Return the labels associated with this object
        :param subj:
        :return:
        """
        query = (
            subj.association.cypher_find_match_clause()
            + "\n RETURN labels(%s) as labels" % subj.association.variable_name
        )
        # print('LABEL QUERY: %s' % query, file=stderr)
        for row in self.load_cypher_query(query):
            # print('ROW: %s' % str(row), file=stderr)
            return row[0]
        return []

    def relate(self, subj, rel_type, obj, attrs=None):
        """
        Define a 'rel_type' relationship subj-[:rel_type]->obj

        :param subj: from-node in relationship
        :param rel_type: type of relationship
        :param obj: to-node in relationship
        :param attrs: relationship properties
        :return: None
        """
        assert not isinstance(obj, str)
        if self.readonly:
            raise RuntimeError("Attempt to relate objects in a read-only store")
        if self.debug:
            print("NEW RELATIONSHIP FROM %s to %s" % (subj, obj), file=stderr)
            print("FROM id is %s" % subj.association.node_id, file=stderr)
            print("TO id is %s" % obj.association.node_id, file=stderr)

        cypher = subj.association.cypher_find_match2_clause(obj.association) + "\n"
        cypher += subj.association.cypher_relate_node(rel_type, obj.association, attrs=attrs)
        # print('ADDREL Cypher:', cypher, file=stderr)
        if self.debug:
            print("relate(%s)" % cypher, file=stderr)
        self.db_transaction.run(cypher).forward()

    def relate_new(self, subj, rel_type, obj, attrs=None):
        """
        Define a 'rel_type' relationship subj-[:rel_type]->obj but guaranteed that there
        is only one of this type between these nodes
        NOTE: 'attrs' is not used in the search for pre-existing relationships

        :param subj: from-node
        :param rel_type: relationship type
        :param obj: to-node
        :param attrs: relationship properties
        :return: None
        """

        # Check for pre-existing relationships
        # TODO: NEEDS MORE WORK
        for other in self.load_related(subj, rel_type, obj):
            if other is not None:
                # print('RELATIONSHIP from %s to %s already exists' % (subj, other), file=stderr)
                return
        self.relate(subj, rel_type, obj, attrs)

    def separate(self, subj, rel_type=None, obj=None, direction="forward", attrs=None):
        """
        Separate nodes related by the specified relationship type
            subj-[:rel_type]->obj -- obj can be None

        :param subj: GraphNode: from-node
        :param rel_type: relationship type
        :param obj: GraphNode: to-node
        :param direction: str: direction of relationship: forward, reverse, bidirectional
        :param attrs: {str:str} - attributes of relationship to delete
        :return: None
        """
        if self.readonly:
            raise RuntimeError("Attempt to separate() an object from a read-only store")
        cypher = ""
        if subj:
            cypher += subj.association.cypher_find_match_clause() + "\n"
        if obj and subj is not obj:
            cypher += obj.association.cypher_find_match_clause() + "\n"
        cypher += subj.association.cypher_unrelate_node(
            rel_type, to_association=obj, direction=direction, attrs=attrs
        )
        if self.debug:
            print("delrel(%s)" % cypher, file=stderr)
        self.db_transaction.run(cypher).forward()

    def separate_in(self, subj, rel_type=None, obj=None):
        """
        Separate nodes related by the specified relationship type
            subj<-[:rel_type]-obj -- obj can be none

        :param subj:
        :param rel_type:
        :param obj:
        :return:
        """
        self.separate(subj=subj, rel_type=rel_type, obj=obj, direction="reverse")

    @staticmethod
    def callconstructor(constructor, kwargs):
        """
        Call a constructor (or function) in a (hopefully) correct way

        :param constructor: class or callable: thing that constructs the object
        :param kwargs: keyword arguments to the constructor function
        :return: object: whatever the constructor/function gives us
        """
        if Store.debug:
            print("CALLING CONSTRUCTOR: %s(%s)" % (constructor.__name__, str(kwargs)), file=stderr)
        try:
            argspec_tuple = inspect.getfullargspec(constructor)
        except TypeError:
            argspec_tuple = inspect.getfullargspec(constructor.__init__)
        args = argspec_tuple.args
        varkw = argspec_tuple.varkw

        newkwargs = {}
        extraattrs = {}
        if varkw:  # Allows any keyword arguments
            newkwargs = kwargs
            # print('OUR KWARGS:', kwargs)
        else:  # Only allows some keyword arguments
            for arg in kwargs:
                if arg in args:
                    newkwargs[arg] = kwargs[arg]
                else:
                    extraattrs[arg] = kwargs[arg]
        # print("NEWKWARGS:", newkwargs)
        # self._audit_weaknodes_clients()
        ret = constructor(**newkwargs)
        # self._audit_weaknodes_clients()
        # assert isinstance(ret, self.graph_node)

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
                # TODO: I wonder if that is really right - in spite of the comments above ;-)
                object.__setattr__(ret, attr, kwa)
        # self._audit_weaknodes_clients()
        ret.association.dirty_attrs = set()
        # self._audit_weaknodes_clients()
        return ret

    @staticmethod
    def _safe_attr_names(subj):
        """
         'Return the list of supported attribute names from the given object'

        :param subj: object: the object of interest
        :return: [str]: attribute names
        """
        ret = []
        for attr in subj.__dict__.keys():
            if attr[0] == "_" or attr == "association":
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
        if isinstance(value, (str, bytes, float, int)):
            return value
        if isinstance(value, (list, tuple)):
            ret = []
            for elem in value:
                ret.append(Store._fixup_attr_value(obj, attr, elem))
            if len(ret) < 1:
                print("Attr %s of object %s cannot be an empty list" % (attr, obj), file=stderr)
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
            print(
                "Attr %s of object %s of type %s isn't acceptable" % (attr, obj, type(value)),
                file=stderr,
            )
            raise ValueError(
                "Attr %s of object %s of type %s isn't acceptable" % (attr, obj, type(value))
            )

    def _update_obj_from_node(self, subj, node):
        """
        'Update an object from its paired node - preserving "dirty" attributes'

        :param subj: object: thing to be updated
        :return: None
        """
        assert isinstance(subj, self.graph_node)
        assert self.neo_node_id(node) is not None
        if subj.association.node_id is None:
            assert self.neo_node_id(node) is not None
            subj.association.node_id = self.neo_node_id(node)
        else:
            assert subj.association.node_id == self.neo_node_id(node)
        nodeprops = dict(node)
        remove_subj = subj not in self.clients
        for attr in nodeprops.keys():
            pattr = nodeprops[attr]
            if attr in subj.association.dirty_attrs:
                remove_subj = False
                continue
            # print(('Setting obj["%s"] to %s' % (attr, pattr), file=stderr)
            # Avoid getting it marked as dirty...
            object.__setattr__(subj, attr, pattr)
            if attr in subj.association.dirty_attrs:
                # print('ATTRIBUTE %s NOW CLEAN' % attr, file=stderr)
                subj.association.dirty_attrs.remove(attr)

        # Make sure everything in the object is in the Node...
        for attr in Store._safe_attr_names(subj):
            if attr not in nodeprops:
                # print('ATTRIBUTE %s missing from node' % attr, file=stderr)
                subj.association.dirty_attrs.add(attr)
                assert subj.association.node_id is not None
                self._audit_weaknodes_clients()
                if subj not in self.clients:
                    self.clients.append(subj)
                self._audit_weaknodes_clients()
                remove_subj = False
        if remove_subj and subj in self.clients:
            self.clients.remove(subj)
        assert self.neo_node_id(node) is not None
        subj.association.node_id = self.neo_node_id(node)
        return subj

    def reset_stats(self):
        """
        Reset all our statistical counters and timers

        :return: None
        """
        self.stats = {}
        for statname in (
            "nodecreate",
            "relate",
            "separate",
            "index",
            "attrupdate",
            "index",
            "nodedelete",
            "addlabels",
            "dellabels",
            "commit",
        ):
            self.stats[statname] = 0
        self.stats["lastcommit"] = None
        self.stats["totaltime"] = timedelta()

    def _bump_stat(self, statname, increment=1):
        """
        Increment the given statistic by the given increment - default increment is 1

        :param statname:
        :param increment:
        :return:
        """
        self.stats[statname] += increment

    def _localsearch(self, cls, key_values, need_node=False):
        """
        Search the 'client' array and the weaknoderefs to see if we can find
        the requested object before going to the database
        We strongly prefer finding them in the pre-existing nodes
        idxkey, idxvalue uniquely determine which object we're after
                they're effectively key values

        :param cls: class: class of object
        :param key_values: dict(str, str): key values for this object
        :return: GraphNode or None
        """

        # print('SEARCHING FOR class %s with %s' % (cls, key_values), file=stderr)
        # self._log.debug('LOCALSEARCH: SEARCHING FOR class %s with %s' % (cls, key_values))
        result = self._weaknodes_search(cls, key_values=key_values, need_node=need_node)
        if result:
            return result
        return self._find_keys_in_iterable(cls, key_values, self.clients, need_node=need_node)

    def _weaknodes_search(self, cls, key_values, need_node=False):
        """
        Search for a node matching certain (unique) key values already laying around...
        :return: GraphNode: or None
        """
        searchset = []
        missing_keys = []
        for node_id, client in self.weaknoderefs.items():
            # client = self.weaknoderefs[node_id]
            client = client()
            if client:
                # print('Weaknodes: node_id: %s Client: %s'
                #       % (node_id, object.__str__(client)), file=stderr)
                # self._log.debug('Weaknodes: node_id: %s Client: %s'
                #                 % (client.association.node_id, object.__str__(client)))
                searchset.append(client)
            else:
                self._log.debug("WEAKNODES: Node ID %s IS missing!" % node_id)
                missing_keys.append(node_id)
        for item in missing_keys:
            # self._log.debug('WEAKNODES: Deleting missing Node ID %s' % item)
            del self.weaknoderefs[item]
        # print('Weaknodes: key_values: %s' % str(key_values), file=stderr)
        # self._log.debug('Weaknodes: key_values: %s' % str(key_values))
        # self._log.debug('Weaknode_search set: %s' % str(searchset))
        result = self._find_keys_in_iterable(cls, key_values, searchset, need_node=need_node)
        # if result:
        #     print('Found client %s in weaknoderefs %s'
        #           % (object.__str__(result), key_values), file=stderr)
        return result

    @staticmethod
    def _find_keys_in_iterable(clsobj, key_values, searchset, need_node=False):
        """
        Search the iterable for a set of keys that matches 'key_values'

        :param key_values:
        :param searchset: iterable(GraphNode)
        :param need_node: bool: True if we only want results with node affiliations
        :return: GraphNode
        """
        class_name = clsobj.__name__
        for client in searchset:
            if client.__class__.__name__ != class_name:
                # print('LOOKING: %s is NOT %s'
                #       % (client.association.variable_name, class_name), file=stderr)
                continue
            if need_node and client.association.node_id is None:
                continue
            found = True
            for attr, value in key_values.items():
                if not hasattr(client, attr) or getattr(client, attr) != value:
                    found = False
                    break
            if found:
                return client
        return None

    @staticmethod
    def _node_to_dict(node):
        """
        Convert all the attributes in a node to a dict
        :param node:
        :return: dict(str, object): attribute dict
        """
        # TODO: return dict(node) ??
        result = {}
        assert isinstance(node, py2neo.Node)
        # print('VIEWKEYS:', node.viewkeys())
        for attribute in node.keys():
            result[attribute] = node[attribute]
        return result

    def _search_for_same_node(self, node):
        """
        See if we already have this node around somewhere...
        Every node that's still around is _supposed to be_ in 'weaknoderefs'
        But there's some evidence that uncollected objects disappear from weaknoderefs...
        :param node:
        :return:
        """
        from graphnodes import GraphNode

        node_id = self.neo_node_id(node)
        assert node_id is not None
        # Weaknoderefs loses items(!)
        if node_id in self.weaknoderefs:
            return self.weaknoderefs[node_id]()

        nodeclass = GraphNode.node_to_class(node)
        key_values = self._get_key_values(nodeclass, dict(node))
        if self.debug:
            print("DOING LOCALSEARCH WITH %s" % key_values, file=stderr)
            self._log.debug("DOING LOCALSEARCH WITH %s" % key_values)
        return self._localsearch(nodeclass, key_values)

    def _construct_obj_from_node(self, node, clsargs=None):
        """
        Construct an object associated with the given node
        and register it in our current node-associated object registry

        :param node: Neoj4.node: Node to construct object from
        :param clsargs: dict(str, object): arguments to the constructor
        :return: object
        """
        assert isinstance(node, py2neo.Node)
        assert self.neo_node_id(node) is not None
        # print("CONSTRUCT OBJ FROM NODE: %s" % node)
        clsargs = [] if clsargs is None else clsargs
        # Do we already have a copy of an object that goes with this node somewhere?
        # If so, we need to update and return it instead of creating a new object
        current_obj = self._search_for_same_node(node)
        if current_obj is not None:
            # FIXME: I think I should just return the current object...(??)
            return self._update_obj_from_node(current_obj, node)

        node_id = self.neo_node_id(node)
        if node_id in self.weaknoderefs:
            weaknode = self.weaknoderefs[node_id]()
            assert weaknode is None
        retobj = Store.callconstructor(self.factory, self._node_to_dict(node))
        for attr in clsargs:
            if not hasattr(retobj, attr) or getattr(retobj, attr) is None:
                # None isn't a legal value for Neo4j to store in the database
                setattr(retobj, attr, clsargs[attr])
        self.register(retobj, node=node)
        return retobj

    def _audit_weaknodes_clients(self):
        """

        :return:
        """
        # self._log.debug('WEAK CLIENTS: %s' % str(self.weaknoderefs.keys()))
        # print("In audit_weaknodes_clients", file=stderr)
        for client in self.clients:
            # print(f"audit_weaknodes_clients: {type(client)}", file=stderr)
            if client.association.node_id is not None:
                # self._log.debug('NODE ID for other: %s' % client.association.node_id)
                # print(f"client.association: {client.association}", file=stderr)
                # print(f"client.association.node_id: {client.association.node_id}", file=stderr)
                if client.association.node_id in self.weaknoderefs:
                    # print(f"found client.association.node_id: {client.association.node_id}",
                    #       file=stderr)
                    other = self.weaknoderefs[client.association.node_id]()
                    assert other is client
                else:
                    # print(f"CLIENT {client.association.node_id} IS MISSING FROM WEAK",
                    # file=stderr)
                    # This seems to happen - even though it shouldn't...
                    # self._log.critical('CLIENT %s MISSING FROM WEAKNODES!!'
                    #                    % client.association.node_id)
                    pass

        complete_set = self.clients
        # print(f"COMPLETE SET {complete_set}", file=stderr)
        for node_id, subj in self.weaknoderefs.items():
            subj = subj()
            if subj is not None and subj not in complete_set:
                complete_set.append(subj)
        complete_list = list(complete_set)
        for j in range(len(complete_list) - 1):
            sublist = complete_list[j + 1:]
            comparison = complete_list[j]
            cls = comparison.__class__
            key_values = self._get_key_values(cls, subj=comparison)
            other = self._find_keys_in_iterable(cls, key_values, sublist)
            if other is not None:
                print(
                    "OOPS: Comparison: %s vs %s"
                    % (object.__str__(comparison), object.__str__(other)),
                    file=stderr,
                )
                self._log.critical(
                    "OOPS: Comparison: %s vs %s"
                    % (object.__str__(comparison), object.__str__(other))
                )
                print("OOPS: Comparison: %s vs %s" % (comparison, other), file=stderr)
                self._log.critical("OOPS: Comparison: %s vs %s" % (comparison, other))
                print("j=%d: %s" % (j, complete_list), file=stderr)
            # assert other is None

    def register(self, subj, node=None):
        """
        Register this object with a Node, so we can track it for updates, etc.

        :param subj:object: object to register
        :param node: neo4j.Node: node to associate it with
        :return: object: subj - the original object - now decorated
        """
        assert isinstance(subj, self.graph_node)
        # print('REGISTERING in store %s transaction %s / %s' % (object.__str__(self),
        #                                                        self.db_transaction,
        #                                                        object.__str__(
        #                                                                     self.db_transaction)),
        #       file=stderr)
        # print('REGISTERING class %s: %s / %s' % (subj.__class__, object.__str__(subj), str(subj)),
        #       file=stderr)
        key_values = self._get_key_values(subj.__class__, subj=subj)
        print ('DOING LOCALSEARCH WITH %s' % key_values, file=stderr)
        self._log.debug('DOING LOCALSEARCH WITH %s' % key_values)
        other = self._localsearch(subj.__class__, key_values)
        if other is subj:
            return
        if other and other is not subj:
            raise RuntimeError("Equivalent Object %s already exists: %s" % (subj, other))
        self._audit_weaknodes_clients()
        # subj.association.node_id = self.neo_node_id(node)
        if self.debug:
            print("STORE._log:", self._log)
            self._log.debug(
                "register-ing [%s] with node %s [node id:%s], %s"
                % (type(subj), node, self.neo_node_id(node), type(node))
            )
            print(
                "register-ing [%s] with node %s [node id:%s], %s"
                % (type(subj), node, self.neo_node_id(node), type(node)),
                file=stderr
            )
            # self._log.debug("Clients of %s include: %s" % (self, str(self.clients)))
            # print("Clients of %s include: %s" % (self, str(self.clients)), file=stderr)

        if node is None:
            print(f"CREATING NODE {str(node)[:100]}", file=stderr)
            self.execute_create_node(subj)
            node_id = subj.association.node_id
            print(f"CREATED NODE {subj} with node id {node_id}", file=stderr)
        else:
            node_id = self.neo_node_id(node)
            subj.association.node_id = node_id

        assert node_id is not None
        weakling = self.weaknoderefs[node_id]() if node_id in self.weaknoderefs else None
        if weakling:
            print(
                "OOPS! - already here... self.weaknoderefs",
                weakling,
                weakling.__dict__,
                file=stderr,
            )
            print(f"NODE ATTEMPTING REGISTRATION: {type(subj)}: {subj}")
            print("Calling audit_weaknodes_clients", file=stderr)
            self._audit_weaknodes_clients()
            raise ValueError("Node id %s already registered" % node_id)
        else:
            if self.debug:
                print(
                    "Registering node %s with node id %d [%s]"
                    % (object.__str__(subj), node_id, subj),
                    file=stderr,
                )
                self._log.debug(
                    "Registering node %s with node id %d [%s]"
                    % (object.__str__(subj), node_id, subj)
                )
            self.weaknoderefs[node_id] = weakref.ref(subj)

            assert self.weaknoderefs[node_id]() == subj
            self._audit_weaknodes_clients()
        if node is None and hasattr(subj, "post_db_init"):
            print('POST_DB_INIT...[%s' % type(subj), file=stderr)
            subj.post_db_init()
        return subj

    def execute_create_node(self, subj):
        """
        Create a node and capture the new node's node id

        :param subj:
        :return: None
        """
        print(f"IN execute_create_node {subj}")
        assert isinstance(subj, self.graph_node)
        cypher = subj.association.cypher_create_node_query()
        cypher += "\n RETURN ID(%s)" % subj.association.variable_name
        if True or self.debug:
            print("CREATE CYPHER: %s" % cypher, file=stderr)
            self._log.info("CREATE CYPHER: %s" % cypher)
        # Let's work around a weird random failure in Neo4j
        retry_times = 5
        node_id = None
        for j in range(retry_times):
            try:
                node_id = self.db_transaction.evaluate(cypher)
                break
            except AssertionError as failure:
                if j == (retry_times - 1):
                    raise failure
                print(f"CRITICAL: Retrying Neo4j create on AssertionError: {j}")
                time.sleep(0.5)
        assert node_id is not None
        # print('NODE_ID:', node_id, file=stderr)
        subj.association.node_id = node_id

    def batch_execute_node_updates(self):
        """
        Construct and execute batch commands for updating attributes on nodes

        :return: None
        """
        for subj in self.clients:
            if not subj.association.dirty_attrs:
                continue
            cypher = subj.association.cypher_find_match_clause() + "\n"
            cypher += subj.association.cypher_update_clause()  # Defaults to dirty attributes
            if self.debug:
                print("batch_execute_node_updates:%s" % cypher, file=stderr)
            self.db_transaction.run(cypher).forward()

    def begin(self, autocommit=False):
        """

        :param autocommit:
        :return:
        """
        save_oops: Optional[Exception] = None
        for _ in range(20):
            try:
                self.db_transaction = self.db.begin(autocommit=autocommit)
                break
            except ServiceUnavailable as oops:
                save_oops = oops
                time.sleep(.5)
        if save_oops is not None:
            raise save_oops
        return self.db_transaction

    def commit(self):
        """
        Commit all the changes we've created since our last transaction
        This is only needed for testing - the production code has a 'with' statement
        that takes care of committing the transaction.

        :return: None
        """
        # print ("COMMIT CLIENTS: %s" % self.clients)
        start = datetime.now()
        self.batch_execute_node_updates()
        self.db_transaction.commit()
        end = datetime.now()
        self.stats["lastcommit"] = end
        self.stats["totaltime"] += end - start

        if self.debug:
            print("DB TRANSACTION COMPLETED SUCCESSFULLY", file=stderr)
            self.abort()

    def abort(self):
        """
        Clear out any currently pending transaction work - start fresh'

        :param self:
        :return:
        """
        for subj in self.clients:
            assert isinstance(subj, self.graph_node)
            # print('CLIENT/subj: %s' % subj, file=stderr)
            if subj.association is not None:
                subj.association.dirty_attrs = set()
        self.clients = list()

    def clean_store(self):
        """
        Clean out all the objects we used to have in our store - afterwards we
        have none associated with this Store. Very useful for testing when
        trying to verify that all our 'C' objects were freed...
        But should only be used in testing situations...

        :return: None
        """
        # print('PERFORMING CLEAN_STORE! (for testing only)', file=stderr)
        for obj in self.weaknoderefs.values():
            obj = obj()
            if obj is not None:
                obj.association.obj = None
                obj._association = None
        # self.weaknoderefs = weakref.WeakValueDictionary()
        self.weaknoderefs = {}
        self.abort()


if __name__ == "__main__":
    # pylint: disable=C0413
    from cmainit import CMAInjectables

    inject.configure_once(CMAInjectables.test_config_injection)

    # I'm not too concerned about this test code...
    # R0914:923,4:testme: Too many local variables (17/15)
    # pylint: disable=R0914

    @inject.params(store="Store", ourdb="py2neo.Graph")
    def testme(store=None, ourdb=None):
        """
        'A little test code...'
        :return: None
        """

        print("NAME: %s" % store.__class__.__name__)
        # Must be a subclass of 'GraphNode'...
        # pylint: disable=R0903
        from graphnodes import GraphNode

        @GraphNode.register
        class Drone(GraphNode):
            """
            This is a Class docstring
            """

            def __init__(self, a=None, b=None, name=None):
                """This is a doc string"""
                GraphNode.__init__(self, domain="global")
                self.a = a
                self.b = b
                self.name = name
                assert self.nodetype == self.__class__.__name__

            def foo_is_blacklisted(self):
                """This is a doc string too"""
                return "a=%s b=%s name=%s" % (self.a, self.b, self.name)

            @classmethod
            def meta_key_attributes(cls):
                """key attributes"""
                return ["domain", "name"]

        # Clean out the database
        qstring = "match (n) optional match (n)-[r]-() delete n,r"
        for _ in range(10):
            try:
                ourdb.run(qstring)
            except ServiceUnavailable:
                time.sleep(1)

        drone = "Drone121"

        # Construct an initial Drone
        #   fred = Drone(a=1,b=2,name=drone)
        #   store.save(fred)    # Drone is a 'known' type, so we know which fields are index key(s)
        #
        #   load_or_create() is the preferred way to create an object...
        #
        store.db_transaction = store.db.begin(autocommit=False)
        fred = store.load_or_create(Drone, a=1, b=2, name=drone)
        print("TEST1: clients of %s: %s" % (store, store.clients), file=stderr)

        assert fred.a == 1
        assert fred.b == 2
        assert fred.name == drone
        assert not hasattr(fred, "c")
        # Modify some fields -- add some...
        fred.a = 52
        fred.c = 3.14159
        assert fred.a == 52
        assert fred.b == 2
        assert fred.name == drone
        assert 3.14158 < fred.c < 3.146
        # Create some relationships...
        rellist = ["ISA", "WASA", "WILLBEA"]
        print("TEST2: clients: %s" % store.clients, file=stderr)
        for rel in rellist:
            store.relate(fred, rel, fred)
        # These should have no effect - but let's make sure...
        print("TEST3: clients: %s" % store.clients, file=stderr)
        for rel in rellist:
            store.relate_new(fred, rel, fred)
        print("TEST4: clients: %s" % store.clients, file=stderr)
        store.commit()  # The updates have been captured...
        print("Statistics:", store.stats, file=stderr)

        assert fred.a == 52
        assert fred.b == 2
        assert fred.name == drone
        assert 3.14158 < fred.c < 3.146

        # See if the relationships 'stuck'...
        for rel in rellist:
            ret = store.load_related(fred, rel)
            print("RET2: %s" % ret)
            ret = [elem for elem in ret]
            print("RET2: %s" % ret)
            assert len(ret) == 1 and ret[0] is fred
        for rel in rellist:
            ret = store.load_in_related(fred, rel)
            ret = [elem for elem in ret]
            assert len(ret) == 1 and ret[0] is fred
        assert fred.a == 52
        assert fred.b == 2
        assert fred.name == drone
        assert 3.14158 < fred.c < 3.146
        print(store, file=stderr)
        store.dump_clients()
        store.db_transaction = store.db.begin(autocommit=False)

        # Add another new field
        fred.x = "malcolm"
        store.dump_clients()
        print("store:", store, file=stderr)
        store.commit()
        print("Statistics:", store.stats, file=stderr)
        assert fred.a == 52
        assert fred.b == 2
        assert fred.name == drone
        assert 3.14158 < fred.c < 3.146
        assert fred.x == "malcolm"

        store.db_transaction = store.db.begin(autocommit=False)
        # Check out load()...
        store._audit_weaknodes_clients()
        newnode = store.load(Drone, name=fred.name, a=fred.a, b=fred.b)
        store._audit_weaknodes_clients()
        print(
            "Load NewNode: %s::%s %s"
            % (object.__str__(newnode), newnode, store.safe_attrs(newnode)),
            file=stderr,
        )
        # It's dangerous to have two separate objects which are the same thing be distinct
        # so we if we fetch a node, and one we already have, we get the original one...
        print("FRED: %s" % object.__str__(fred), file=stderr)
        print("NEWNODE: %s" % object.__str__(newnode), file=stderr)
        assert fred is newnode
        assert newnode.association.node_id is not None
        store._audit_weaknodes_clients()
        assert newnode.a == 52
        assert newnode.b == 2
        assert newnode.x == "malcolm"
        store.db_transaction = store.db.begin(autocommit=False)
        store.separate(fred, "WILLBEA")
        store.commit()
        print("Statistics:", store.stats, file=stderr)

        # Test a simple cypher query...
        qstr = "MATCH(d:Class_Drone) RETURN d"
        qnode = store.load_cypher_node(qstr)  # Returns a single node
        store.dump_clients()
        print("qnode=%s" % qnode, file=stderr)
        assert qnode is fred
        qnodes = store.load_cypher_nodes(qstr)  # Returns iterable
        qnodes = [qnode for qnode in qnodes]
        assert len(qnodes) == 1
        assert qnode is fred

        # See if the now-separated relationship went away...
        rels = store.load_related(fred, "WILLBEA")
        rels = [rel for rel in rels]
        print("REMAINING RELS: %s" % rels, file=stderr)
        assert len(rels) == 0
        store.db_transaction = store.db.begin(autocommit=False)
        store.delete(fred)
        store.commit()

        # When we delete an object from the database, the  python object
        # is disconnected from the database...
        assert fred.association is None
        store.db_transaction = store.db.begin(autocommit=False)
        notfred = store.load(Drone, name=fred.name, a=fred.a, b=fred.b)
        assert notfred is None
        store.commit()

        print("Statistics:", store.stats, file=stderr)
        print("Final returned values look good!", file=stderr)

    # Store.debug = True
    testme()
