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
import py2neo


class StoreAssociation(object):
    """
    Class to represent the association between an object and a Neo4j Node

    Each object is given a unique variable name to use in the Cypher which will be consistent
    within a transaction. You can read it in early in the transaction, and later on trust
    that that variable name is the same later on in the transaction.

    The "variable_name" field is the field for the variable name. It is created by
    the _new_variable_name function. No guarantee that the same Cypher Node will have the same
    variable name from one transaction to the next. Only if the object lasts from one
    transaction to the next would this be true. This shouldn't happen often - if at all.

    """
    VARIABLE_NAME_PATTERN = '%s%d'
    last_variable_id = 0

    def __init__(self, obj, node=None, store=None):
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
        self.variable_name = self._new_variable_name()
        for attr in self.key_attributes:
            if not hasattr(obj, attr):
                raise ValueError("Key attribute %s not present in object type %s [%s]"
                                 % (attr, type(obj), obj))
        store.register(obj, node, self)

    def _new_variable_name(self):
        """
        Return a unique variable name for use in Cypher queries
        :return: str: unique, legal Cypher variable name
        """
        StoreAssociation.last_variable_id += 1
        return (StoreAssociation.VARIABLE_NAME_PATTERN
                % (self.obj.__class__.__name__, self.last_variable_id))

    @property
    def node_id(self):
        """
        Return the node id of the associated Neo4j node
        :return: int: Node id
        """
        try:  # getattr avoids complaints from various tools about accessing the _id attribute
            return getattr(py2neo.remote(self.node), '_id')
        except AttributeError:
            return None

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

    def attribute_string(self, attributes):
        """
        Return the Cypher representation of a bunch of attributes
        :param attributes: dict: attributes as a dict
        :return: str: Cypher attributes
        """
        result = ''
        delimiter=''
        if attributes is None:
            return ''
        for key, item in attributes.viewitems():
            if key.startswith('_'):
                continue
            result += '%s%s: %s' % (delimiter, key, self.cypher_repr(item))
            delimiter = ', '
        return result

    @staticmethod
    def find_store_association(obj):
        """
        Find the StoreAssociation associated with this object
        :param obj: object: the object of interest
        :return: the associated StoreAssociation object
        """
        if not hasattr(obj, '_Store__store_association'):
            raise ValueError('%s is not associated with a Store.' % obj)
        return getattr(obj, '_Store__store_association')

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
            result = 'MATCH (%s:%s) WHERE %s.nodetype = %s' % (var_name, label, var_name,
                                                               self.cypher_repr(self.obj.nodetype))
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
        return ':'.join(words) + ' { ' + self.attribute_string(self.obj.__dict__) + ' })'

    def cypher_relate_node(self, relationship_type, to_object, rel_attrs=None):
        """
        Relate the current node to the 'to_obj' with the arrow pointing from self->to_obj

        NOTE: if the objects have not been "read in" yet, they may need to be read in first.

        :param relationship_type: str: relationship type
        :param to_object: object: object to relate to
        :param rel_attrs: dict: attributes of this relationship
        :return: str: Cypher query string
        """
        to_association = self.find_store_association(to_object)
        return ('CREATE (%s)-[:%s { %s }]->(%s)' % (self.variable_name,
                                                    relationship_type,
                                                    self.attribute_string(rel_attrs),
                                                    to_association.variable_name))


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
            self.nodetype = self.__class__.__name__

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
            self.nodetype = 'Hobbit'

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
        import json
        saved_output = {}
        expected_output = {
            'cypher_find_match_clauseFrodo': 'MATCH (Hobbit1:Class_Hobbit) WHERE Hobbit1.nodetype '
                                             '= \'Hobbit\' AND Hobbit1.name = \'Frodo\' AND '
                                             'Hobbit1.hobbithole = \'Shire\'',
            'update:name:hobbitholeSamwise': 'MATCH (Hobbit2:Class_Hobbit) WHERE Hobbit2.nodetype '
                                             '= \'Hobbit\' AND Hobbit2.name = \'Samwise\' AND '
                                             'Hobbit2.hobbithole = \'Shire-too\' SET Hobbit2.name '
                                             '= \'Samwise\', Hobbit2.hobbithole = \'Shire-too\'',
            'cypher_create_node_queryFrodo': "CREATE (Hobbit1:Class_Humanoid:Class_Hobbit { "
                                             "hobbithole: 'Shire', forty_two: 42, nodetype: "
                                             "'Hobbit', name: 'Frodo' })",
            'cypher_find_match_clauseSamwise': 'MATCH (Hobbit2:Class_Hobbit) WHERE '
                                               'Hobbit2.nodetype = \'Hobbit\' AND Hobbit2.name = '
                                               '\'Samwise\' AND Hobbit2.hobbithole = '
                                               '\'Shire-too\'',
            'update:name:hobbithole:42Samwise': 'MATCH (Hobbit2:Class_Hobbit) WHERE '
                                                'Hobbit2.nodetype = \'Hobbit\' AND Hobbit2.name = '
                                                '\'Samwise\' AND Hobbit2.hobbithole = '
                                                '\'Shire-too\' SET Hobbit2.name = \'Samwise\', '
                                                'Hobbit2.hobbithole = \'Shire-too\', '
                                                'Hobbit2.forty_two = 42',
            'update:name:hobbitholeFrodo': 'MATCH (Hobbit1:Class_Hobbit) WHERE Hobbit1.nodetype = '
                                           '\'Hobbit\' AND Hobbit1.name = \'Frodo\' AND '
                                           'Hobbit1.hobbithole = \'Shire\' SET Hobbit1.name = '
                                           '\'Frodo\', Hobbit1.hobbithole = \'Shire\'',
            'cypher_create_node_querySamwise': "CREATE (Hobbit2:Class_Humanoid:Class_Hobbit { "
                                               "hobbithole: 'Shire-too', forty_two: 42, nodetype:"
                                               " 'Hobbit', name: 'Samwise' })",
            'cypher_find_querySamwise': 'MATCH (Hobbit2:Class_Hobbit) WHERE Hobbit2.nodetype = '
                                        '\'Hobbit\' AND Hobbit2.name = \'Samwise\' AND '
                                        'Hobbit2.hobbithole = \'Shire-too\' RETURN ID(Hobbit2), '
                                        'Hobbit2',
            'update:nameFrodo': 'MATCH (Hobbit1:Class_Hobbit) WHERE Hobbit1.nodetype = \'Hobbit\' '
                                'AND Hobbit1.name = \'Frodo\' AND Hobbit1.hobbithole = \'Shire\' '
                                'SET Hobbit1.name = \'Frodo\'',
            'update:name:hobbithole:42Frodo': 'MATCH (Hobbit1:Class_Hobbit) WHERE '
                                              'Hobbit1.nodetype = \'Hobbit\' AND Hobbit1.name = '
                                              '\'Frodo\' AND Hobbit1.hobbithole = \'Shire\' SET '
                                              'Hobbit1.name = \'Frodo\', Hobbit1.hobbithole = '
                                              '\'Shire\', Hobbit1.forty_two = 42',
            'update:nameSamwise': 'MATCH (Hobbit2:Class_Hobbit) WHERE Hobbit2.nodetype = \'Hobbit\' '
                                  'AND Hobbit2.name = \'Samwise\' AND Hobbit2.hobbithole = '
                                  '\'Shire-too\' SET Hobbit2.name = \'Samwise\'',
            'cypher_find_queryFrodo': 'MATCH (Hobbit1:Class_Hobbit) WHERE Hobbit1.nodetype = '
                                      '\'Hobbit\' AND Hobbit1.name = \'Frodo\' AND '
                                      'Hobbit1.hobbithole = \'Shire\' RETURN ID(Hobbit1), Hobbit1'
        }

        store = Store()
        frodo = Hobbit('Frodo', 'Shire')
        frodo_association = StoreAssociation(frodo, store=store)
        samwise = Hobbit('Samwise', 'Shire-too')
        sam_association = StoreAssociation(samwise, store=store)
        for association in (frodo_association, sam_association):
            for fun in ('cypher_create_node_query',
                        'cypher_find_match_clause',
                        'cypher_find_query'):

                saved_output[(fun + association.obj.name)] = getattr(association, fun)()

            saved_output['update:name' + association.obj.name] = \
                association.cypher_update_clause(['name'])
            saved_output['update:name:hobbithole' + association.obj.name] = \
                association.cypher_update_clause(['name', 'hobbithole'])
            saved_output['update:name:hobbithole:42' + association.obj.name] = \
                association.cypher_update_clause(['name', 'hobbithole', 'forty_two'])

        failcount = 0
        testcount = 0
        for key in expected_output:
            testcount += 1
            if expected_output[key] != saved_output[key]:
                print("Key: %s" % key)
                print("    %s" % expected_output[key])
                print("    %s" % saved_output[key])
                failcount += 1
        print("%d tests completed. %d failed." % (testcount, failcount))
        if failcount == 0:
            keys = saved_output.keys()
            keys.sort()
            for key in keys:
                print(saved_output[key])
        #print(saved_output)
    test_main()
