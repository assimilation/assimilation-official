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
"""
store_association module - associations between objects, py2neo.Nodes and Stores

"""
from __future__ import print_function
# import inject
from AssimCclasses import pyNetAddr


class StoreAssociation(object):
    """
    Class to represent the association between an object and a Neo4j Node
    """
    VARIABLE_NAME_PATTERN = 'var_%d'
    last_variable_id = 0

    def __init__(self, obj, node=None, node_id=None, store=None):
        """
        Associate the given object with the given node

        :param obj: object: object to associate with the Store
        :param node: py2neo.node: node that goes with it (if any)
        :param store: Store; the Store that we are associated with
        """
        self.transaction_name = None
        self.dirty_attributes = {}
        self.obj = obj
        self.key_attributes = obj.__class__.meta_key_attributes()
        self.node = node
        self._node_id = node_id
        self.variable_name = self._new_variable_name()
        for attr in self.key_attributes:
            if not hasattr(obj, attr):
                raise ValueError("Key attribute %s not present in object type %s [%s]"
                                 % (attr, type(obj), obj))
        store.register(obj, node, self)

    @staticmethod
    def _new_variable_name():
        """
        Return a unique variable name for use in Cypher queries
        :return: str: unique, legal Cypher variable name
        """
        StoreAssociation.last_variable_id += 1
        return StoreAssociation.VARIABLE_NAME_PATTERN % StoreAssociation.last_variable_id

    def set_node_id(self, node_id):
        """
        Set the node id of this node in Neo4j. This makes for efficient queries
        NOTE: they cannot be considered to be persistent.
        :param node_id: int: id to associate with the node
        :return: None
        """
        assert self.node is not None
        self._node_id = node_id

    @property
    def node_id(self):
        """
        Return the node id of the associated Neo4j node
        :return: int: Node id
        """
        return self._node_id

    @property
    def is_abstract(self):
        """
        Return True if the associated node is abstract (not yet real)
        :return: bool: as noted
        """
        return self.node_id is not None

    @property
    def default_labels(self):
        """
        Return the default set of labels for this object

        :return: [str]
        """
        return self.obj.__class__.meta_labels()

    @staticmethod
    def cypher_str_repr(cypher_string):
        """
        Return a string representation suitable for putting into a Cypher query as-is
        We quote it using ' - because the Cypher examples tend to do that.

        :param cypher_string: str: string to provide a Cypher representation of
        :return: str: fully escaped representation suitable for Cypher
        """
        return "'%s'" % cypher_string.replace('\\', '\\\\').replace("'", "\\'")

    def cypher_scalar_repr(self, scalar):
        """
        Return the representation of a scalar item in Cypher-style

        :param scalar: object: scalar object to use as input
        :return: str: representation of this scalar suitable for Cypher
        """
        if isinstance(scalar, (str, unicode, pyNetAddr)):
            if isinstance(scalar, pyNetAddr):
                scalar = str(scalar)
            scalar_str = self.cypher_str_repr(scalar)
        elif isinstance(scalar, (bool, int, float)):
            scalar_str = str(scalar)
        else:
            raise ValueError('Inappropriate Neo4j value: "%s" (type %s)'
                             % (scalar, type(scalar)))
        return scalar_str

    def cypher_array_repr(self, array):
        """
        Return the cypher representation of an array/list/tuple of items
        :return: str: Cypher representation of the list

        :param array: [object]: array of scalar items
        :return: str: Cypher representation
        """
        result = ''
        delimiter = ''
        for element in array:
            result += '%s%s' % (delimiter, self.cypher_scalar_repr(element))
            delimiter = ', '
        return '[%s]' % result

    def cypher_repr(self, thing):
        """
        Return the representation of 'thing' Cypher-style
        We only handle things that can be stored in Neo4j attributes

        :param thing: object: an array, tuple, or scalar of some kind
        :return: str: representation of 'thing' in Cypher-style
        """
        if isinstance(thing, (tuple, list)):
            return self.cypher_array_repr(thing)
        return self.cypher_scalar_repr(thing)

    def cypher_find_match_clause(self):
        """
        Construct a cypher match clause which will uniquely find this object if it exists
        It constructs a query which uses this object's key attributes to find the
        py2neo (Neo4j) node that goes with it in the database.
        We only construct the match clause - not the whole query...

        :return: str: query to return (id, node) tuple from Cypher
        """
        var_name = self.variable_name
        if self.node_id is not None:
            return 'MATCH (%s) WHERE ID(%s) = %d' % (var_name, var_name, self.node_id)
        else:
            label = 'Class_%s' % self.obj.nodetype
            result = 'MATCH (%s:%s) WHERE %s.nodetype = "%s"' % (var_name, label, var_name, self.obj.nodetype)
            for attr in self.key_attributes:
                result += (' AND %s.%s = %s' % (var_name, attr,
                                                self.cypher_repr(getattr(self.obj, attr))))
        return result

    def cypher_find_query(self):
        """
        Construct a cypher query which will uniquely return this object and its id if it exists

        :return: str: Cypher query as described above...
        """
        result = self.cypher_find_match_clause()
        result += ' RETURN ID(%s), %s' % (self.variable_name, self.variable_name)
        return result

    def cypher_update_clause(self, attributes):
        """
        Create a query to update the given attributes
        :param attributes: [str]: attribute names to update
        :return: None
        """
        result = self.cypher_find_match_clause()
        result += ' SET '
        delimiter = ''
        for attr in attributes:
            result += ('%s%s.%s = %s' % (delimiter, self.variable_name, attr,
                                         self.cypher_repr(getattr(self.obj, attr))))
            delimiter = ', '
        return result

    def cypher_create_node_query(self):
        """
        Create a Cypher query to create a new graph node.
        It will look like this:
            CREATE (foo_123:label1:label2 {attr1: value1, attr2: value2})

        :return:str: Cypher query string to create this node
        """
        # assert self.is_abstract
        words = ['CREATE (%s' % self.variable_name]
        words.extend(self.default_labels)
        result = ':'.join(words)
        result += ') {'
        delimiter = ''
        for attr in [a for a in self.obj.__dict__.keys() if not a.startswith('_')]:
            result += ('%s%s: %s' % (delimiter, attr, self.cypher_repr(getattr(self.obj, attr))))
            delimiter = ', '
        return result + '})'

if __name__ == '__main__':
    class BaseGraph(object):
        """
        Base class for all graph things...
        """
        @staticmethod
        def meta_labels():
            """
            :return:
            """
            return []

        @staticmethod
        def meta_key_attributes():
            """
            :return:
            """
            return []


    class Humanoid(BaseGraph):
        """
        Humanoid...
        """
        def __init__(self, name):
            BaseGraph.__init__(self)
            self.name = name

        @staticmethod
        def meta_labels():
            """
            :return:
            """
            return ['Class_Humanoid']

        @staticmethod
        def meta_key_attributes():
            """
            :return:
            """
            return ['name']

    class Hobbit(Humanoid):
        """
        Hobbit...
        """
        def __init__(self, name, hobbithole):
            """
            :param name:
            :param hobbithole:
            """
            Humanoid.__init__(self, name)
            self.hobbithole = hobbithole
            self.forty_two = 42

        @staticmethod
        def meta_labels():
            """
            :return:
            """
            return ['Class_Humanoid', 'Class_Hobbit']

        @staticmethod
        def meta_key_attributes():
            """
            :return:
            """
            return ['name', 'hobbithole']

        @property
        def nodetype(self):
            """
            :return:
            """
            return self.__class__.__name__

    class Store(object):
        """
        Store pass...
        """
        @staticmethod
        def register(*_):
            """
            :param _:
            :return:
            """
            pass

    def test_main():
        """
        :return: None
        """
        store = Store()
        frodo = Hobbit('Frodo', 'Shire')
        frodo_association = StoreAssociation(frodo, store=store)
        samwise = Hobbit('Samwise', 'Shire-too')
        sam_association = StoreAssociation(samwise, store=store, node_id=13)
        for association in (frodo_association, sam_association):
            for fun in ('cypher_create_node_query',
                        'cypher_find_match_clause',
                        'cypher_find_query'):

                print(getattr(association, fun)())
            print(association.cypher_update_clause(['name']))
            print(association.cypher_update_clause(['name', 'hobbithole']))
            print(association.cypher_update_clause(['name', 'hobbithole', 'forty_two']))

    test_main()
