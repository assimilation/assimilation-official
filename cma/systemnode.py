#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
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
''' This module defines the classes for several of our System nodes ...  '''
from __future__ import print_function
import sys, time
from consts import CMAconsts
from store import Store
from cmadb import CMAdb
from AssimCclasses import pyConfigContext
from graphnodes import RegisterGraphClass, GraphNode, JSONMapNode,  \
        add_an_array_item, delete_an_array_item, nodeconstructor
from cmaconfig import ConfigFile
from AssimCtypes import CONFIGNAME_TYPE
from frameinfo import FrameTypes, FrameSetTypes

@RegisterGraphClass
class SystemNode(GraphNode):
    'An object that represents a physical or virtual system (server, switch, etc)'
    HASH_PREFIX = 'JSON__hash__'
    JSONattrnames = '''MATCH (d)-[r:jsonattr]->() WHERE ID(d) = $droneid
                           return r.jsonname as key'''
    JSONsingleattr = '''MATCH (d)-[r:jsonattr]->(json) WHERE r.jsonname={jsonname} AND
                             ID(d) = $droneid
                             RETURN json'''

    _JSONprocessors = None # This will get updated
    debug = False

    def __init__(self, domain, designation, roles=None):
        GraphNode.__init__(self, domain=domain)
        self.designation = str(designation).lower()
        self.monitors_activated = False
        if roles is None or roles == []:
            # Neo4j can't initialize node properties to empty arrays because
            # it wants to know what kind of array it is...
            roles = ['']
        self.roles = roles

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        return ['designation', 'domain']

    def addrole(self, roles):
        'Add a role to our SystemNode'
        self.roles = add_an_array_item(self.roles, roles)
        # Make sure the 'roles' attribute gets marked as dirty...
        self.association.dirty_attrs.add('roles')
        return self.roles

    def delrole(self, roles):
        'Delete a role from our SystemNode'
        self.roles = delete_an_array_item(self.roles, roles)
        self.association.dirty_attrs.add('roles')
        return self.roles

    def logjson(self, origaddr, jsontext):
        'Process and save away JSON discovery data.'
        assert self.association.node_id is not None
        jsonobj = pyConfigContext(jsontext)
        if 'instance' not in jsonobj or 'data' not in jsonobj:
            CMAdb.log.warning('Invalid JSON discovery packet: %s' % jsontext)
            return
        dtype = jsonobj['instance']
        discoverychanged = not self.json_eq(dtype, jsontext)
        if discoverychanged:
            CMAdb.log.debug("Saved discovery type %s [%s] for endpoint %s."
                            % (jsonobj['discovertype'], dtype, self.designation))
        else:
            if CMAdb.debug:
                CMAdb.log.debug('Discovery type %s for endpoint %s is unchanged.'
                                % (dtype, self.designation))
        self._process_json(origaddr, jsonobj, discoverychanged)
        self[dtype] = jsontext # This is stored in separate nodes for performance

    def __iter__(self):
        'Iterate over our child JSON attribute names'
        for tup in CMAdb.store.load_cypher_query(self.JSONattrnames,
                                                 params={'droneid': self.association.node_id}):
            yield str(tup[0])

    def keys(self):
        'Return the names of all our JSON discovery attributes.'
        return [str(attr) for attr in self]

    def __contains__(self, key):
        'Return True if our object contains the given key (JSON name).'
        return hasattr(self, str(self.HASH_PREFIX + key))

    def __len__(self):
        'Return the number of JSON items in this SystemNode.'
        return len(self.keys())

    def jsonval(self, jsontype):
        'Construct a python object associated with a particular JSON discovery value.'
        attrname = unicode(self.HASH_PREFIX+jsontype)
        if not hasattr(self, attrname):
            # self._log.debug('DOES NOT HAVE ATTR "%s"' % attrname)
            # self._log.debug( 'ATTRIBUTES ARE: %s' % str(self.keys()))
            # self._log.debug('ALL attributes: %s' % str(self.__dict__))
            return None
        params = {'droneid': self.association.node_id, 'jsonname': str(jsontype)}
        if self.debug:
            self._log.debug('LOADING %s // %s' % (self.JSONsingleattr, str(params)))
        node = CMAdb.store.load_cypher_node(self.JSONsingleattr, params=params)
        assert self.json_eq(jsontype, str(node))
        return node

    def get(self, key, alternative=None):
        '''Return JSON object if the given key exists - 'alternative' if not.'''
        ret = self.deepget(unicode(key))
        return ret if ret is not None else alternative

    def __getitem__(self, key):
        'Return the given JSON value or raise IndexError.'
        ret = self.jsonval(key)
        if ret is None:
            raise IndexError('No such JSON attribute [%s].' % key)
        return ret

    def deepget(self, key, alternative=None):
        '''Return value if object contains the given *structured* key - 'alternative' if not.'''
        keyparts = key.split('.', 1)
        if len(keyparts) == 1:
            ret = self.jsonval(key)
            return ret if ret is not None else alternative
        jsonmap = self.jsonval(keyparts[0])
        return alternative if jsonmap is None else jsonmap.deepget(keyparts[1], alternative)

    def __setitem__(self, name, value):
        'Set the given JSON value to the given object/string.'
        if name in self:
            if self.json_eq(name, value):
                return
            else:
                # print('DELETING ATTRIBUTE', name, file=stderr)
                # FIXME: ADD ATTRIBUTE HISTORY (enhancement)
                # This will likely involve *not* doing a 'del' here
                del self[name]
        jsonnode = self._store.load_or_create(JSONMapNode, json=value)
        # print('JUST CREATED JSON NODE: %s' % str(jsonnode))
        setattr(self, unicode(self.HASH_PREFIX + name), jsonnode.jhash)
        self._store.relate(self, CMAconsts.REL_jsonattr, jsonnode,
                           attrs={'jsonname':  name,
                                       'time': long(round(time.time()))
                                       })

    def __delitem__(self, name):
        'Delete the given JSON value from the SystemNode.'
        # print('ATTRIBUTE DELETION:', name, file=stderr)
        jsonnode = self.get(name, None)
        try:
            delattr(self, unicode(self.HASH_PREFIX + name))
        except AttributeError:
            raise IndexError('No such JSON attribute [%s].' % name)
        if jsonnode is None:
            CMAdb.log.warning('Missing JSON attribute: %s' % name)
            print('Missing JSON attribute: %s' % name, file=stderr)
            return
        should_delnode = True
        # See if it has any remaining references...
        for node in self._store.load_in_related(jsonnode,
                                                CMAconsts.REL_jsonattr,
                                                nodeconstructor):
            if node is not self:
                should_delnode = False
                break
        self._store.separate(self, CMAconsts.REL_jsonattr, jsonnode)
        if should_delnode:
            # Avoid dangling properties...

            CMAdb.log.warning('Deleting old attribute value: %s [%s]' % (name, str(jsonnode)))
            CMAdb.store.delete(jsonnode)

    def json_eq(self, key, newvalue):
        '''Return True if this new value is equal to the current value for
        the given key (JSON attribute name).

        We do this by comparing hash values. This keeps us from having to
        fetch potentially very large strings (read VERY SLOW) if we can
        compare hash values instead.

        Our hash values are representable in fewer than 60 bytes to maximize Neo4j performance.
        '''
        if key not in self:
            return False
        hashname = self.HASH_PREFIX + key
        oldhash = getattr(self, hashname)
        newhash = JSONMapNode.strhash(str(pyConfigContext(newvalue)))
        # print('COMPARING %s to %s for value %s' % (oldhash, newhash, key), file=stderr)
        return oldhash == newhash

    def send_frames(self, _framesettype, _frames):
        'Send messages to our parent - or their parent, or their parent...'
        raise ValueError('Cannot send frames to a %s - must be a subclass'
                         % (str(self.__class__)))

    def request_discovery(self, args):
        '''Send our System a request to perform discovery
        We send a           DISCNAME frame with the instance name
        then an optional    DISCINTERVAL frame with the repeat interval
        then a              DISCJSON frame with the JSON data for the discovery operation.

        Our argument is a vector of pyConfigContext objects with values for
            'instance'  Name of this discovery instance
            'interval'  How often to repeat this discovery action
            'timeout'   How long to wait before considering this discovery failed...
        '''
        # fs = pyFrameSet(FrameSetTypes.DODISCOVER)
        frames = []
        for arg in args:
            agent_params = ConfigFile.agent_params(CMAdb.io.config, 'discovery',
                                                   arg[CONFIGNAME_TYPE], self.designation)
            for key in ('repeat', 'warn' 'timeout', 'nice'):
                if key in agent_params and key not in arg:
                    arg[key] = agent_params[arg]
            instance = arg['instance']
            frames.append({'frametype': FrameTypes.DISCNAME, 'framevalue': instance})
            if 'repeat' in arg:
                interval = int(arg['repeat'])
                frames.append({'frametype': FrameTypes.DISCINTERVAL, 'framevalue': int(interval)})
            else:
                interval = 0
            frames.append({'frametype': FrameTypes.DISCJSON, 'framevalue': str(arg)})
        self.send_frames(FrameSetTypes.DODISCOVER, frames)

    def _process_json(self, origaddr, jsonobj, discoverychanged):
        'Pass the JSON data along to interested discovery plugins (if any)'
        dtype = jsonobj['discovertype']
        foundone = False
        if CMAdb.debug:
            CMAdb.log.debug('Processing JSON for discovery type [%s]' % dtype)
        for prio in range(0, len(SystemNode._JSONprocessors)):
            if dtype in SystemNode._JSONprocessors[prio]:
                foundone = True
                classes = SystemNode._JSONprocessors[prio][dtype]
                # print('PROC[%s][%s] = %s' % (prio, dtype, str(classes)), file=stderr)
                for cls in classes:
                    proc = cls(CMAdb.io.config, CMAdb.net_transaction, CMAdb.store,
                               CMAdb.log, CMAdb.debug)
                    proc.processpkt(self, origaddr, jsonobj, discoverychanged)
        if foundone:
            CMAdb.log.info('Processed %schanged %s JSON data from %s into graph.'
                           % ('' if discoverychanged else 'un', dtype, self.designation))
        elif discoverychanged:
            CMAdb.log.info('Stored %s JSON data from %s without processing.'
                           % (dtype, self.designation))

    @staticmethod
    def add_json_processor(clstoadd):
        "Register (add) all the json processors we've been given as arguments"

        if SystemNode._JSONprocessors is None:
            SystemNode._JSONprocessors = []
            for _prio in range(0, clstoadd.PRI_LIMIT):
                SystemNode._JSONprocessors.append({})

        priority = clstoadd.priority()
        msgtypes = clstoadd.desiredpackets()

        for msgtype in msgtypes:
            if msgtype not in SystemNode._JSONprocessors[priority]:
                SystemNode._JSONprocessors[priority][msgtype] = []
            if clstoadd not in SystemNode._JSONprocessors[priority][msgtype]:
                SystemNode._JSONprocessors[priority][msgtype].append(clstoadd)

        return clstoadd

@RegisterGraphClass
class ChildSystem(SystemNode):
    'A class representing a Child System (like a VM or a container)'

    DiscoveryPath = None

    # pylint R0913: too many arguments - needed because of the way we retrieve from the database
    # and we never call the constructor directly - we call it via "childfactory" or the
    # database calls it with args
    # pylint: disable=R0913
    def __init__(self, designation, _parentsystem=None, domain=None, roles=None, _selfjson=None,
                 uniqueid=None, childpath=None):
        # print('CONSTRUCTING CHILD NODE!====================: %s' % str(designation), file=stderr)
        if domain is None:
            domain=_parentsystem.domain
        SystemNode.__init__(self, domain=domain, designation=designation, roles=roles)
        self._selfjson = _selfjson
        if uniqueid is None:
            uniqueid = ChildSystem.compute_uniqueid(designation, _parentsystem, domain)
        self.uniqueid = uniqueid
        if childpath is None:
            if hasattr(_parentsystem, 'childpath'):
                childpath = '%s/%s:%s' % (self.__class__.DiscoveryPath, designation,
                                          _parentsystem.childpath)
            else:
                childpath = '%s/%s' % (self.__class__.DiscoveryPath, designation)
        self.childpath = childpath
        self.runas_user = None
        self.runas_group = None
        if _parentsystem is not None:
            self._parentsystem = _parentsystem
        # print('YAY GOT A CHILD NODE!=====================: %s' % str(self), file=stderr)

    def post_db_init(self):
        '''Do post-constructor database updates'''
        if not hasattr(self, '_parentsystem'):
            for node in CMAdb.store.load_related(self, CMAconsts.REL_parentsys, nodeconstructor):
                self._parentsystem = node
                break
        if self._selfjson is not None:
            self['selfjson'] = self._selfjson
        if not hasattr(self, '_parentsystem'):
            raise RuntimeError('Cannot find parent system for %s (%s)' % (type(self), self))
        if self._parentsystem.__class__ is SystemNode:
            raise ValueError('Parent system cannot be a base "SystemNode" object')

    def send_frames(self, framesettype, frames):
        'Send messages to our parent - or their parent, or their parent...'
        self._parentsystem.send_frames(framesettype, frames)

    @staticmethod
    def compute_uniqueid(designation, parentsystem, domain=None):
        'We compute the unique id we use to find this in the database'
        if domain is None:
            domain = parentsystem.domain
        if hasattr(parentsystem, 'uniqueid'):
            return getattr(parentsystem, 'uniqueid') + '::' + designation
        return '%s::%s::%s' % (designation, parentsystem.designation, domain)

    @staticmethod
    def childfactory(parentsystem, childtype, designation, jsonobj, roles=None, domain=None):
        'We construct an appropriate ChildSystem subclass object - or find it in the database'
        store = parentsystem.association.store
        if childtype == 'docker':
            cls = DockerSystem
        elif childtype == 'vagrant':
            cls = VagrantSystem
        else:
            raise ValueError('Unknown ChildSystem type(%s)' % childtype)
        uniqueid = ChildSystem.compute_uniqueid(designation, parentsystem, domain)
        return store.load_or_create(cls, designation=designation, _selfjson=str(jsonobj),
                                    _parentsystem=parentsystem, roles=roles, uniqueid=uniqueid)

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        return ['uniqueid']


@RegisterGraphClass
class DockerSystem(ChildSystem):
    'A class representing a Docker container'
    DiscoveryPath='docker'

    def post_db_init(self):
        ChildSystem.post_db_init(self)
        self.runas_user = 'nobody'
        self.runas_group = 'docker'


@RegisterGraphClass
class VagrantSystem(ChildSystem):
    'A class representing a Vagrant VM'
    DiscoveryPath='vagrant'

    def post_db_init(self):
        ChildSystem.post_db_init(self)
        if not hasattr(self, 'runas_user'):
            jsonobj = pyConfigContext(self._selfjson)
            self.runas_user  = jsonobj['user']
            self.runas_group = jsonobj['group']

if __name__ == '__main__':
    def maintest():
        'test main program'
        return 0

    sys.exit(maintest())
