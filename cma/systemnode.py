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
from consts import CMAconsts
from store import Store
from cmadb import CMAdb
import sys, time
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
    JSONattrnames =        '''START d=node({droneid})
                           MATCH (d)-[r:jsonattr]->()
                           return r.jsonname as key'''
    JSONsingleattr =      '''START d=node({droneid})
                           MATCH (d)-[r:jsonattr]->(json)
                           WHERE r.jsonname={jsonname}
                           return json'''

    _JSONprocessors = None # This will get updated

    def __init__(self, domain, designation, roles=None):
        GraphNode.__init__(self, domain=domain)
        self.designation = str(designation).lower()
        self.monitors_activated = False
        if roles == None or roles == []:
            # Neo4j can't initialize node properties to empty arrays because
            # it wants to know what kind of array it is...
            roles = ['']
        self.roles = roles

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of significance'
        return ['designation', 'domain']

    def addrole(self, roles):
        'Add a role to our SystemNode'
        self.roles = add_an_array_item(self.roles, roles)
        # Make sure the 'roles' attribute gets marked as dirty...
        Store.mark_dirty(self, 'roles')
        return self.roles

    def delrole(self, roles):
        'Delete a role from our SystemNode'
        self.roles = delete_an_array_item(self.roles, roles)
        Store.mark_dirty(self, 'roles')
        return self.roles

    def logjson(self, origaddr, jsontext):
        'Process and save away JSON discovery data.'
        assert CMAdb.store.has_node(self)
        jsonobj = pyConfigContext(jsontext)
        if 'instance' not in jsonobj or not 'data' in jsonobj:
            CMAdb.log.warning('Invalid JSON discovery packet: %s' % jsontext)
            return
        dtype = jsonobj['instance']
        if not self.json_eq(dtype, jsontext):
            CMAdb.log.debug("Saved discovery type %s [%s] for endpoint %s."
            %       (jsonobj['discovertype'], dtype, self.designation))
            self[dtype] = jsontext # This is stored in separate nodes for performance
        else:
            if not self.monitors_activated and dtype == 'tcpdiscovery':
                # This is because we need to start the monitors anyway...
                if CMAdb.debug:
                    CMAdb.log.debug('Discovery type %s for endpoint %s is unchanged'
                    '. PROCESSING ANYWAY.'
                    %       (dtype, self.designation))
            else:
                if CMAdb.debug:
                    CMAdb.log.debug('Discovery type %s for endpoint %s is unchanged. ignoring'
                    %       (dtype, self.designation))
                return
        self._process_json(origaddr, jsonobj)


    def __iter__(self):
        'Iterate over our child JSON attribute names'
        for tup in CMAdb.store.load_cypher_query(self.JSONattrnames, None,
                                     params={'droneid': Store.id(self)}):
            yield tup.key

    def keys(self):
        'Return the names of all our JSON discovery attributes.'
        return [attr for attr in self]

    def __contains__(self, key):
        'Return True if our object contains the given key (JSON name).'
        return hasattr(self, self.HASH_PREFIX + key)

    def __len__(self):
        'Return the number of JSON items in this SystemNode.'
        return len(self.keys())

    def jsonval(self, jsontype):
        'Construct a python object associated with a particular JSON discovery value.'
        if not hasattr(self, self.HASH_PREFIX + jsontype):
            #print >> sys.stderr, 'DOES NOT HAVE ATTR %s' % jsontype
            #print >> sys.stderr, 'ATTRIBUTES ARE:' , str(self.keys())
            return None
        #print >> sys.stderr, 'LOADING', self.JSONsingleattr, \
        #       {'droneid': Store.id(self), 'jsonname': jsontype}
        node = CMAdb.store.load_cypher_node(self.JSONsingleattr, JSONMapNode,
                                            params={'droneid': Store.id(self),
                                            'jsonname': jsontype}
                                            )
        #assert self.json_eq(jsontype, str(node))
        return node

    def get(self, key, alternative=None):
        '''Return JSON object if the given key exists - 'alternative' if not.'''
        ret = self.deepget(key)
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
                #print >> sys.stderr, 'DELETING ATTRIBUTE', name
                # FIXME: ADD ATTRIBUTE HISTORY (enhancement)
                # This will likely involve *not* doing a 'del' here
                del self[name]
        jsonnode = CMAdb.store.load_or_create(JSONMapNode, json=value)
        setattr(self, self.HASH_PREFIX + name, jsonnode.jhash)
        CMAdb.store.relate(self, CMAconsts.REL_jsonattr, jsonnode,
                           properties={'jsonname':  name,
                                       'time':   long(round(time.time()))
                                       })

    def __delitem__(self, name):
        'Delete the given JSON value from the SystemNode.'
        #print >> sys.stderr, 'ATTRIBUTE DELETION:', name
        jsonnode=self.get(name, None)
        try:
            delattr(self, self.HASH_PREFIX + name)
        except AttributeError:
            raise IndexError('No such JSON attribute [%s].' % name)
        if jsonnode is None:
            CMAdb.log.warning('Missing JSON attribute: %s' % name)
            print >> sys.stderr, ('Missing JSON attribute: %s' % name)
            return
        should_delnode = True
        # See if it has any remaining references...
        for node in CMAdb.store.load_in_related(jsonnode,
                                                CMAconsts.REL_jsonattr,
                                                nodeconstructor):
            if node is not self:
                should_delnode = False
                break
        CMAdb.store.separate(self, CMAconsts.REL_jsonattr, jsonnode)
        if should_delnode:
            # Avoid dangling properties...
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
        #print >> sys.stderr, 'COMPARING %s to %s for value %s' % (oldhash, newhash, key)
        return oldhash == newhash

    def send_frames(self, _framesettype, _frames):
        'Send messages to our parent - or their parent, or their parent...'
        raise ValueError('Cannot send frames to a %s - must be a subclass'
                         %  (str(self.__class__)))

    def request_discovery(self, args): ##< A vector of arguments containing
        '''Send our System a request to perform discovery
        We send a           DISCNAME frame with the instance name
        then an optional    DISCINTERVAL frame with the repeat interval
        then a              DISCJSON frame with the JSON data for the discovery operation.

        Our argument is a vector of pyConfigContext objects with values for
            'instance'  Name of this discovery instance
            'interval'  How often to repeat this discovery action
            'timeout'   How long to wait before considering this discovery failed...
        '''
        #fs = pyFrameSet(FrameSetTypes.DODISCOVER)
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


    def _process_json(self, origaddr, jsonobj):
        'Pass the JSON data along to interested discovery plugins (if any)'
        dtype = jsonobj['discovertype']
        foundone = False
        if CMAdb.debug:
            CMAdb.log.debug('Processing JSON for discovery type [%s]' % dtype)
        for prio in range(0, len(SystemNode._JSONprocessors)):
            if dtype in SystemNode._JSONprocessors[prio]:
                foundone = True
                classes = SystemNode._JSONprocessors[prio][dtype]
                #print >> sys.stderr, 'PROC[%s][%s] = %s' % (prio, dtype, str(classes))
                for cls in classes:
                    proc = cls(CMAdb.io.config, CMAdb.transaction, CMAdb.store
                    ,   CMAdb.log, CMAdb.debug)
                    proc.processpkt(self, origaddr, jsonobj)
        if foundone:
            CMAdb.log.info('Processed %s JSON data from %s into graph.'
            %   (dtype, self.designation))
        else:
            CMAdb.log.info('Stored %s JSON data from %s without processing.'
            %   (dtype, self.designation))

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

class ChildSystem(SystemNode):
    'A class representing a Child System (like a VM or a container)'

    DiscoveryPath = None

    # pylint R0913: too many arguments - needed because of the way we retrieve from the database
    # and we never call the constructor directly - we call it via "childfactory" or the
    # database calls it with args
    # pylint: disable=R0913
    def __init__(self, designation, parentsystem=None, domain=None, roles=None, selfjson=None,
                 uniqueid=None, childpath=None):
        if domain is None:
            domain=parentsystem.domain
        SystemNode.__init__(self, domain=domain, designation=designation, roles=roles)
        self.selfjson = selfjson
        if uniqueid is None:
            uniqueid = ChildSystem.compute_uniqueid(designation, parentsystem, domain)
        self.uniqueid = uniqueid
        if childpath is None:
            if hasattr(parentsystem, 'childpath'):
                childpath = '%s/%s:%s' % (self.__class__.DiscoveryPath, designation,
                                          parentsystem.childpath)
            else:
                childpath = '%s/%s' % (self.__class__.DiscoveryPath, designation)
        self.childpath = childpath
        if parentsystem is not None:
            self._parentsystem = parentsystem
        else:
            store = Store.getstore(self)
            for node in store.load_related(self, CMAconsts.REL_parentsys, nodeconstructor):
                self._parentsystem = node
                break
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
        return ('%s::%s::%s' %(designation, parentsystem.designation, domain))

    @staticmethod
    def childfactory(parentsystem, childtype, designation, jsonobj, roles=None, domain=None):
        'We construct an appropriate ChildSystem subclass object - or find it in the database'
        store = Store.getstore(parentsystem)
        childtype = jsonobj['discoverytype']
        if childtype == 'docker':
            cls = DockerSystem
        elif childtype == 'vagrant':
            cls = VagrantSystem
        else:
            raise ValueError('Unknown ChildSystem type(%s)' % childtype)
        uniqueid = ChildSystem.compute_uniqueid(designation, parentsystem, domain)
        return store.load_or_create(cls, designation=designation, parentsystem=parentsystem,
                                    selfjson=str(jsonobj), roles=roles, uniqueid=uniqueid)

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of significance'
        return ['uniqueid']

class DockerSystem(ChildSystem):
    'A class representing a Docker container'
    DiscoveryPath='docker'

class VagrantSystem(ChildSystem):
    'A class representing a Vagrant VM'
    DiscoveryPath='vagrant'


if __name__ == '__main__':
    def maintest():
        'test main program'
        return 0

    sys.exit(maintest())
