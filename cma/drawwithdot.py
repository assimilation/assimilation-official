#!/usr/bin/env python
#
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=80
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2015 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community
#   - http://assimproj.org
# Paid support is available from Assimilation Systems Limited
#   - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.
# If not, see http://www.gnu.org/licenses/
#
'''

Drawwithdot: Sample program to draw Assimilation graphs using Dot

The core part of this program is pretty simple.
The complicated part is getting the 'dot' diagram to look pretty
This is accomplished by fancy format strings.

When we format nodes, the following variables are available:
    id: An idname suitable for matching up in relationship (see below)
    If the GraphNode supports __getitem__ (mainly Drones) then any
        item that __getitem__ might return
    Any attributes of the GraphNode

We only format nodes when we have a format string for its nodetype

When we format relationships, the following variables are available:
    from: the idname of the from node in the relationship
    to: the idname of the to node in the relationship
    type: the relationship type
    Any other attributes of the relationship

    In other words, this relationship looks like this in Cypher notation:
        from-[:type]->to

    We only output relationships when we've formatted (selected) both the
    from and the to node in the relationship, AND we have a format
    string for that relationship type.


This is a very flexible and powerful graph drawing method, for which
the code is simple and common - and the formats are more complicated.
'''

from __future__ import print_function, unicode_literals
from graphnodes import GraphNode
from assimcli import dbsetup
import sys

#pylint complaint: too few public methods. It's OK - it's a utility class ;-)
#pylint: disable=R0903
class DictObj(object):
    '''This is a class that allows us to see the objects below us as a
    dict-like object - both for any dict-like characteristics and for its
    attributes.  This is for formatting them with the "usual" Python formatting
    rules.
    '''

    def __init__(self, obj, kw=None):
        '''Initialization'''
        self.obj = obj
        if kw is None:
            kw = {}
        self.kw = kw

    def __contains__(self, name):
        try:
            if name in self.kw or name in self.obj:
                return True
        except TypeError:
            pass
        return hasattr(self.obj, name)

    def __getitem__(self, name):
        if name in self.kw:
            return self.kw[name]
        try:
            return self.obj[name]
        except (IndexError, KeyError, TypeError):
            pass
        return getattr(self.obj, name)

class DotGraph(object):
    '''Class to format Assimilation graphs as 'dot' graphs'''
    def __init__(self, formatdict, dburl=None, nodequery=None,
            nodequeryparams=None, relquery=None, relqueryparams=None):
        '''Initialization'''
        self.formatdict = formatdict
        self.store = dbsetup(readonly=True, url=dburl)
        self.nodeids = None
        if nodequery is None:
            nodequery = 'START n=node(*) RETURN n'
        self.nodequery = nodequery
        self.nodequeryparams = nodequeryparams
        if relquery is None:
            relquery = '''START fromnode=node(*) MATCH fromnode-[rel]->tonode
            RETURN rel
            '''
        self.relquery = relquery
        self.relqueryparams = relqueryparams

    @staticmethod
    def idname(nodeid):
        'Format a node id so dot will like it (not numeric)'
        return 'node_%d' % nodeid

    def _outnodes(self):
        '''Output our nodes, formatted for 'dot'
        '''
        self.nodeids = set()
        nodeiter = self.store.load_cypher_nodes(self.nodequery, GraphNode.factory,
               self.nodequeryparams)
        nodeformats = self.formatdict['nodes']
        try:
            for node in nodeiter:
                if node.nodetype not in nodeformats:
                    continue
                self.nodeids.add(self.store.id(node))
                dictobj = DictObj(node,
                        {'id': DotGraph.idname(self.store.id(node))})
                yield nodeformats[node.nodetype] % dictobj
        except KeyError as e:
            print('Bad node type: %s' %  e, file=sys.stderr)

    def _outrels(self):
        '''Yield relationships, formatted for 'dot'
        '''
        relformats = self.formatdict['relationships']
        reliter = self.store.db.cypher.stream(self.relquery,
                self.relqueryparams)
        for result in reliter:
            rel = result[0]
            # We really need the id. The API calls it _id. Sorry about that...
            # pylint: disable=W0212
            if (rel.end_node._id not in self.nodeids
                or rel.start_node._id not in self.nodeids
                or rel.type not in relformats):
                continue
            dictobj = DictObj(rel, {'from': DotGraph.idname(rel.start_node._id),
                'to': DotGraph.idname(rel.end_node._id)})
            yield relformats[rel.type] % dictobj

    def __iter__(self):
        '''Yield 'dot' strings for our nodes and relationships'''
        yield 'Digraph G {\n'
        for line in self._outnodes():
            yield line.strip() + '\n'
        for line in self._outrels():
            yield line.strip() + '\n'
        yield '}\n'

    def out(self, outfile=sys.stdout):
        '''Output nodes and relationships to the 'outfile'.'''
        outfile.writelines(self.__iter__())

    def __str__(self):
        '''Output nodes and relationships in a string.'''
        ret = ''
        for line in self.__iter__():
            ret += '%s\n' % line
        return ret

if __name__ == '__main__':
    ipmaconly = {
        'nodes': {
            'IPaddrNode':
            '''
            %(id)s [shape=box color=blue label="%(ipaddr)s"] ''',
            'NICNode':
            '''
            %(id)s [shape=ellipse color=red label="%(macaddr)s"]''',
            'Drone':
            '''
            %(id)s [shape=house color=orange label="%(designation)s"] ''',
            },

        'relationships': {
            'ipowner':
            '''
            %(from)s->%(to)s [color=hotpink]''',
            'nicowner':
            ''' %(from)s->%(to)s [color=black]''',
        }
    }

    dot = DotGraph(ipmaconly)
    dot.out()
