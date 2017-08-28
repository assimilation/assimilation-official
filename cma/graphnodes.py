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
''' This module defines the classes for most of our CMA nodes ...  '''
# Pylint is nuts here...
# pylint: disable=C0411
import sys, re, time, hashlib, netaddr, socket, logging, inject
import py2neo
from consts import CMAconsts
from store import Store
from cmadb import CMAdb
from AssimCtypes import ADDR_FAMILY_IPV4, ADDR_FAMILY_IPV6, ADDR_FAMILY_802
from AssimCclasses import pyNetAddr, pyConfigContext
from store_association import StoreAssociation


def nodeconstructor(**properties):
    '''A generic class-like constructor that knows our class name is stored as nodetype
    It's a form of "factory" for our database classes
    '''
    #print >> sys.stderr, 'Calling nodeconstructor with properties: %s' % (str(properties))
    realcls = GraphNode.classmap[str(properties['nodetype'])]
    # callconstructor is kinda cool - it figures out how to correctly call the constructor
    # with the values in 'properties' as arguments
    return Store.callconstructor(realcls, properties)


def RegisterGraphClass(classtoregister):
    '''Register the given class as being a Graph class so we can
    map the class name to the class object.
    This is intended to be used as a decorator.
    '''
    GraphNode.classmap[classtoregister.__name__] = classtoregister
    return classtoregister


class GraphNode(object):
    '''
    GraphNode is the base class for all our 'normal' graph nodes.
    '''
    REESC = re.compile(r'\\')
    REQUOTE = re.compile(r'"')
    classmap = {}

    @staticmethod
    def register(classtoregister):
        """

        :param classtoregister:
        :return:
        """
        return RegisterGraphClass(classtoregister)

    @staticmethod
    def factory(**kwargs):
        'A factory "constructor" function - acts like a universal constructor for GraphNode types'
        return nodeconstructor(**kwargs)

    @staticmethod
    def clean_graphnodes():
        'Invalidate any persistent objects that might become invalid when resetting the database'
        pass

    @staticmethod
    def str_to_class(class_name):
        """
        Return the class corresponding to this class name
        :param class_name: str: class name
        :return: cls
        """
        print('CLASSMAP', GraphNode.classmap)
        return GraphNode.classmap[str(class_name)]

    @inject.params(store='Store', log='logging.Logger')
    def __init__(self, domain, time_create_ms=None, time_create_iso8601=None, store=None, log=None):
        'Abstract Graph node base class'
        self.domain = domain
        self.nodetype = self.__class__.__name__
        self._baseinitfinished = False
        self._store = store
        self._log = log
        if time_create_ms is None:
            time_create_ms = int(round(time.time()*1000))
        if time_create_iso8601 is None:
            time_create_iso8601 = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        self.time_create_iso8601 = time_create_iso8601
        self.time_create_ms = time_create_ms
        assert hasattr(self, 'nodetype')
        association = StoreAssociation(self, store=store)
        association.dirty_attrs = set()
        self._association = association

    @property
    def association(self):
        """
        :return: StoreAssociation: self._association
        """
        return self._association

    def __setattr__(self, name, value):
        """
        Does a setattr() - and marks changed attributes "dirty".  This
        permits us to know when attributes change, and automatically
        include them in the next transaction.
        This is a GoodThing.

        :param self:
        :param name:
        :param value:
        :return:
        """

        if not hasattr(self, '_association') or self._association is None:
            object.__setattr__(self, name, value)
            return
        if name in ('node_id', 'dirty_attrs'):
            raise(ValueError('Bad attribute name: %s' % name))
        if not name.startswith('_'):
            try:
                if getattr(self, name) == value:
                    # print('Value of %s already set to %s' % (name, value), file=sys.stderr)
                    return
            except AttributeError:
                pass
            if self.association.store.readonly:
                print >> sys.stderr, ('Caught Read-Only %s being set to %s!' % (name, value))
                raise RuntimeError('Attempt to set attribute %s using a read-only store' % name)
            if hasattr(value, '__iter__') and len(value) == 0:
                raise ValueError(
                    'Attempt to set attribute %s to empty array (Neo4j limitation)' % name)
            self.association.dirty_attrs.add(name)
        print>> sys.stderr, ('SETTING %s to %s' % (name, value))
        object.__setattr__(self, name, value)

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        raise NotImplementedError('Abstract base class function meta_key_attributes')

    @classmethod
    def meta_labels(cls):
        'Return the default set of labels which should be put on our objects when created'
        labels = []
        classes = [cls]
        classes.extend(cls.__bases__)
        labels = []
        for c in classes:
            name = c.__name__
            if name == 'GraphNode':
                break
            labels.append('Class_' + name)
        return labels

    @staticmethod
    def cypher_all_label_indexes():
        """
        Create all the label indexes that seem good to make ;-)
        This includes a composite index over all key components and an
        index on each field that's part of that key

        :return:str: Cypher commands to create indexes
        """
        result = ''
        for classname, cls in GraphNode.classmap.viewitems():
            class_label = 'Class_' + classname
            key_attrs = cls.meta_key_attributes()
            for attr in key_attrs:
                result += 'CREATE INDEX ON :%s(%s)\n' % (class_label, attr)
            if len(key_attrs) > 1:
                result += ('CREATE INDEX ON :%s(%s)\n' % (key_attrs, ':'.join(key_attrs)))
        return result

    @staticmethod
    def cypher_all_label_constraints(use_enterprise_features=False):
        """
        Output Cypher to create all the label constraints we can
        - or all that don't require Neo4j enterprise features...

        Most constraints require Neo4j Enterprise features...

        :param use_enterprise_features: bool: True if we want to use enterprise features
        :return: str: Cypher commands to create constraints (or "")
        """
        result = ''
        for classname, cls in GraphNode.classmap.viewitems():
            class_label = 'Class_' + classname
            key_attrs = cls.meta_key_attributes()
            if use_enterprise_features:
                for attr in key_attrs:
                    result += ('CREATE CONSTRAINT ON (n:%s) ASSERT EXISTS(n.%s)\n'
                               % (class_label, attr))
            if len(key_attrs) == 1:
                result += ('CREATE CONSTRAINT ON (n:%s) ASSERT (n.%s) IS UNIQUE\n'
                           % (class_label, key_attrs[0]))
            elif use_enterprise_features:
                result += ('CREATE CONSTRAINT ON (n.%s) ASSERT (n.%s) IS NODE KEY\n'
                           % (class_label, ', n.'.join(key_attrs)))
        return result

    def post_db_init(self):
        '''Set node creation time'''
        if not self._baseinitfinished:
            self._baseinitfinished = True

    def update_attributes(self, other):
        'Update our attributes from another node of the same type'
        if other.nodetype != self.nodetype:
            raise ValueError('Cannot update attributes from incompatible nodes (%s vs %s)'
            %   (self.nodetype, other.nodetype))
        for attr in other.__dict__.keys():
            if not hasattr(self, attr) or getattr(self, attr) != getattr(other, attr):
                setattr(self, attr, getattr(other, attr))
        return self

    def __str__(self):
        'Default routine for printing GraphNodes'
        result = '%s({' % self.__class__.__name__
        comma  = ''
        for attr in Store.safe_attrs(self):
            result += '%s%s = %s'% (comma, attr, str(getattr(self, attr)))
            comma = ",\n    "
        result += '%sobject.__str__ =  "%s"' % (comma, object.__str__(self))
        result += comma + 'HasNode:%s' % self.association.node_id

        result += "\n})"
        return result

    # pylint R0911: Too many return statements
    # pylint: disable=R0911
    def get(self, attrstring, valueifnotfound=None):
        'Implement potentially deep attribute value lookups through JSON strings'
        try:
            (prefix, suffix) = attrstring.split('.', 1)
        except ValueError:
            suffix = None
            prefix = attrstring
        if not hasattr(self, prefix):
            if not prefix.endswith(']'):
                return valueifnotfound
            else:
                # Probably an array index
                # Note that very similar code exists in AssimCclasses for pyConfigContext
                #   deepget member function
                allbutrbracket = prefix[0:len(prefix)-1]
                try:
                    (preprefix, idx) = allbutrbracket.split('[', 1)
                except ValueError:
                    return valueifnotfound
                if not hasattr(self, preprefix):
                    return valueifnotfound
                try:
                    arraypart = getattr(self, preprefix)
                    idx = int(idx) # Possible ValueError
                    arrayvalue = arraypart[idx] # possible IndexError or TypeError
                    if suffix is None:
                        return arrayvalue
                except (TypeError, IndexError, ValueError):
                    return valueifnotfound
                prefixvalue = arrayvalue
        else:
            prefixvalue = getattr(self, prefix)
        if suffix is None:
            return prefixvalue
        # OK.  We're in the more complicated case...
        # Our expectation is that the prefixvalue is JSON...
        jsonstruct = pyConfigContext(init=prefixvalue)
        if jsonstruct is None:
            # Should we throw an exception instead?
            return valueifnotfound
        return jsonstruct.deepget(suffix, valueifnotfound)

    def JSON(self, includemap=None, excludemap=None):
        '''Output this object according to JSON rules. We take advantage
        of the fact that Neo4j restricts what kind of objects we can
        have as Node properties.
        '''

        attrstodump = []
        for attr in Store.safe_attrs(self):
            if includemap is not None and attr not in includemap:
                continue
            if excludemap is not None and attr in excludemap:
                continue
            attrstodump.append(attr)
        ret = '{'
        comma = ''
        for attr in attrstodump.sort():
            ret += '%s"%s": %s' % (comma, attr, GraphNode._JSONelem(getattr(self, attr)))
            comma = ','
        ret += '}'
        return ret

    @staticmethod
    def _JSONelem(value):
        'Return the value of an element suitable for JSON output'
        if isinstance(value, str) or isinstance(value, unicode):
            return '"%s"' % GraphNode._JSONesc(value)
        if isinstance(value, bool):
            if value:
                return 'true'
            return 'false'
        if isinstance(value, list) or isinstance(value, tuple):
            ret = '['
            comma = ''
            for elem in value:
                ret += '%s%s' % (comma, GraphNode._JSONelem(elem))
                comma = ','
            ret += ']'
            return ret
        return str(value)

    @staticmethod
    def _JSONesc(stringthing):
        'Escape this string according to JSON string escaping rules'
        stringthing = GraphNode.REESC.sub(r'\\\\', stringthing)
        stringthing = GraphNode.REQUOTE.sub(r'\"', stringthing)
        return stringthing

    @staticmethod
    def initclasstypeobj(store, nodetype):
        '''Initialize things for our "nodetype"
        This involves
         - Ensuring that there's an index for this class
         - Caching the class that goes with this nodetype
         - setting up all of our IS_A objects, including the root object if necessary,
         - updating the store's uniqueindexmap[nodetype]
         - updating the store's classkeymap[nodetype]
         This should eliminate the need to do any of these things for any class.
        '''
        ourclass = GraphNode.classmap[nodetype]


def add_an_array_item(currarray, itemtoadd):
    'Function to add an item to an array of strings (like for roles)'
    if currarray is not None and len(currarray) == 1 and currarray[0] == '':
        currarray = []
    if isinstance(itemtoadd, (tuple, list)):
        for item in itemtoadd:
            currarray = add_an_array_item(currarray, item)
        return currarray
    assert isinstance(itemtoadd, (str, unicode))
    if currarray is None:
        currarray = [itemtoadd]
    elif currarray not in currarray:
        currarray.append(itemtoadd)
    return currarray

def delete_an_array_item(currarray, itemtodel):
    'Function to delete an item from an array of strings (like for roles)'
    if isinstance(itemtodel, (tuple, list)):
        for item in itemtodel:
            currarray = delete_an_array_item(currarray, item)
        return currarray
    assert isinstance(itemtodel, (str, unicode))
    if itemtodel is not None and itemtodel in currarray:
        currarray = currarray.remove(itemtodel)
    if len(currarray) == 0:
        currarray = ['']    # Limitation of Neo4j
    return currarray


@RegisterGraphClass
class BPRules(GraphNode):
    '''Class defining best practice rules'''

    def __init__(self, bp_class, json, rulesetname):
        GraphNode.__init__(self, domain='metadata')
        self.bp_class = bp_class
        self.rulesetname = rulesetname
        self.json = json
        self._jsonobj = pyConfigContext(json)

    def jsonobj(self):
        'Return the JSON object corresponding to our rules'
        return self._jsonobj

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        return ['bp_class', 'rulesetname']

@RegisterGraphClass
class BPRuleSet(GraphNode):
    '''Class defining best practice rule sets'''
    def __init__(self, rulesetname, basisrules=None):
        GraphNode.__init__(self, domain='metadata')
        self.rulesetname = rulesetname
        self.basisrules = basisrules
        if self.basisrules is None or not Store.is_abstract(self):
            return
        query = CMAconsts.QUERY_RULESET_RULES
        parent = CMAdb.store.load_cypher_node(query, BPRuleSet, params={'name': basisrules})
        CMAdb.store.relate_new(self, CMAconsts.REL_basedon, parent)

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        return ['rulesetname']

@RegisterGraphClass
class NICNode(GraphNode):
    'An object that represents a NIC - characterized by its MAC address'
    def __init__(self, domain, macaddr, ifname=None, json=None):
        GraphNode.__init__(self, domain=domain)
        mac = pyNetAddr(macaddr)
        if mac is None or mac.addrtype() != ADDR_FAMILY_802:
            raise ValueError('Not a legal MAC address [%s]' % macaddr)
        self.macaddr = str(mac)
        if ifname is not None:
            self.ifname = ifname
        if json is not None:
            self.json = json
            self._json = pyConfigContext(json)
            for attr in ('carrier', 'duplex', 'MTU', 'operstate', 'speed'):
                if attr in self._json:
                    setattr(self, attr, self._json[attr])
        if not hasattr(self, 'OUI'):
            oui = self.mac_to_oui(self.macaddr)
            if oui is not None:
                self.OUI = oui

    @staticmethod
    def mac_to_oui(macaddr):
        'Convert a MAC address to an OUI organization string - or raise KeyError'
        try:
            # Pylint is confused about the netaddr.EUI.oui.registration return result...
            # pylint: disable=E1101
            return str(netaddr.EUI(macaddr).oui.registration().org)
        except netaddr.NotRegisteredError:
            prefix = str(macaddr)[0:8]
            return CMAdb.io.config['OUI'][prefix] if prefix in CMAdb.io.config['OUI'] else None

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in decreasing order of significance'
        return ['macaddr', 'domain']


@RegisterGraphClass
class IPaddrNode(GraphNode):
    '''An object that represents a v4 or v6 IP address without a port - characterized by its
    IP address. They are always represented in the database in ipv6 format.
    '''
    StoreHostNames = True
    def __init__(self, domain, ipaddr, cidrmask='unknown'):
        'Construct an IPaddrNode - validating our parameters'
        GraphNode.__init__(self, domain=domain)
        if isinstance(ipaddr, str) or isinstance(ipaddr, unicode):
            ipaddrout = pyNetAddr(str(ipaddr))
        else:
            ipaddrout = ipaddr
        if isinstance(ipaddrout, pyNetAddr):
            addrtype = ipaddrout.addrtype()
            if addrtype == ADDR_FAMILY_IPV4:
                ipaddrout = ipaddrout.toIPv6()
            elif addrtype != ADDR_FAMILY_IPV6:
                raise ValueError('Invalid network address type for IPaddrNode constructor: %s'
                %   str(ipaddrout))
            ipaddrout.setport(0)
        else:
            raise ValueError('Invalid address type for IPaddrNode constructor: %s type(%s)'
            %   (str(ipaddr), type(ipaddr)))
        self.ipaddr = unicode(str(ipaddrout))
        self.cidrmask = cidrmask
        if IPaddrNode.StoreHostNames and not hasattr(self, 'hostname'):
            ip = repr(pyNetAddr(ipaddr))
            try:
                self.hostname = socket.gethostbyaddr(ip)[0]
            except socket.herror:
                return

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        return ['ipaddr', 'domain']

@RegisterGraphClass
class IPtcpportNode(GraphNode):
    'An object that represents an IP:port combination characterized by the pair'
    def __init__(self, domain, ipaddr, port=None, protocol='tcp'):
        'Construct an IPtcpportNode - validating our parameters'
        GraphNode.__init__(self, domain=domain)
        if isinstance(ipaddr, (str, unicode)):
            ipaddr = pyNetAddr(str(ipaddr))
        if isinstance(ipaddr, pyNetAddr):
            if port is None:
                port = ipaddr.port()
            else:
                ipaddr.setport(port)
            self._repr = repr(ipaddr)
            if port <= 0 or port >= 65536:
                raise ValueError('Invalid port for constructor: %s' % str(port))
            addrtype = ipaddr.addrtype()
            if addrtype == ADDR_FAMILY_IPV4:
                ipaddr = ipaddr.toIPv6()
            elif addrtype != ADDR_FAMILY_IPV6:
                raise ValueError('Invalid network address type [%s] for constructor: %s'
                %  (addrtype, str(ipaddr)))
            ipaddr.setport(0)
        else:
            raise ValueError('Invalid initial value for IPtcpportNode constructor: %s type(%s)'
            %   (str(ipaddr), type(ipaddr)))
        self.ipaddr = unicode(str(ipaddr))
        self.port = port
        self.protocol = protocol
        self.ipport = self.format_ipport()

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        return ['ipport', 'domain']

    def format_ipport(self):
        '''Format the ip and port into our key field
        Note that we make the port the most significant part of the key - which
        should allow some more interesting queries.
        '''
        return '%s_%s_%s' % (self.port, self.protocol, self.ipaddr)


@RegisterGraphClass
class ProcessNode(GraphNode):
    'A node representing a running process in a host'
    # R0913: Too many arguments (9/7)
    # pylint: disable=R0913
    def __init__(self, domain, processname, host, pathname, argv, uid, gid, cwd, roles=None,
            is_monitored=False):
        GraphNode.__init__(self, domain=domain)
        self.host = host
        self.pathname       = pathname
        self.argv           = argv
        self.uid            = uid
        self.gid            = gid
        self.cwd            = cwd
        self.is_monitored   = is_monitored
        if roles is None:
            self.roles = ['']
        else:
            self.roles = None
            self.addrole(roles)
        #self.processname='%s|%s|%s|%s:%s|%s' \
        #%       (path.basename(pathname), path.dirname(pathname), host, uid, gid, str(argv))
        #procstring = '%s|%s|%s:%s|%s' \
        #%       (str(path.dirname(pathname)), str(host), str(uid), str(gid), str(argv))
        #hashsum = hashlib.sha1()
        # E1101: Instance of 'sha1' has no 'update' member (but it does!)
        # pylint: disable=E1101
        #hashsum.update(procstring)
        #self.processname = '%s::%s' % (path.basename(pathname), hashsum.hexdigest())
        self.processname = processname


    def addrole(self, roles):
        'Add a role to our ProcessNode'
        self.roles = add_an_array_item(self.roles, roles)
        # Make sure the Processnode 'roles' attribute gets marked as dirty...
        Store.mark_dirty(self, 'roles')
        # TODO: Add role-based label
        return self.roles

    def delrole(self, roles):
        'Delete a role from our ProcessNode'
        self.roles = delete_an_array_item(self.roles, roles)
        # Mark our Processnode 'roles' attribute dirty...
        Store.mark_dirty(self, 'roles')
        # TODO: Delete role-based label
        return self.roles

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        return ['processname', 'domain']

@RegisterGraphClass
class JSONMapNode(GraphNode):
    '''A node representing a map object encoded as a JSON string
    This has everything to do with performance in Neo4j.
    They don't support maps, and they do a poor (*very* slow) job of supporting large strings.
    The only way I know of to support our JSON-based maps in Neo4j is as large strings.
    These used to be stored in the Drone nodes themselves, but that meant that every time
    a Drone was transferred to the python code, it transferred *all* of its attributes,
    which means transferring lots and lots of very slow and rarely needed string data.

    Although these are transmitted in UDP packets, they are compressed, and JSON compresses very
    well, and in some cases extremely well. I've actually seen 3M of (unusually verbose)
    JSON discovery data compress down to less than 40K of binary.
    XML blobs are typically more compressible than the average JSON blob.
    '''

    def __init__(self, json, jhash=None):
        GraphNode.__init__(self, domain='metadata')
        self._map = pyConfigContext(json)
        self.json = str(self._map)
        # We use sha224 to keep the length under 60 characters (56 to be specific)
        # This is a performance consideration for the current (2.3) verison of Neo4j
        if jhash is None:
            jhash = self.strhash(self.json)
        self.jhash = jhash

    @staticmethod
    def strhash(string):
        'Return our canonical hash value (< 60 chars long)'
        return hashlib.sha224(string).hexdigest()

    def __str__(self):
        'Convert to string - returning the JSON string itself'
        return self.json

    def hash(self):
        'Return the (sha224) hash of this JSON string'
        return self.jhash

    def map(self):
        'Return the map (pyConfigContext) that corresponds to our JSON string'
        return self._map

    def keys(self):
        'Return the keys that go with our map'
        return self.map().keys()

    def get(self, key, alternative=None):
        '''Return value if object contains the given *structured* key - 'alternative' if not.'''
        return self.map().deepget(key, alternative)

    def deepget(self, key, alternative=None):
        '''Return value if object contains the given *structured* key - 'alternative' if not.'''
        return self.map().deepget(key, alternative)

    def __getitem__(self, key):
        return self.map()[key]

    def __iter__(self):
        'Iterate over self.keys() - giving the names of all our *top level* attributes.'
        for key in self.keys():
            yield key

    def __contains__(self, key):
        return key in self.map()

    def __len__(self):
        return len(self.map())

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        return  ['jhash']

# pylint  W0212: we need to get the value of the _node_id fields...
# pylint  R0903: too few public methods. Not appropriate here...
# pylint: disable=W0212,R0903
class NeoRelationship(object):
    '''Our encapsulation of a Neo4j Relationship - good for displaying them '''
    def __init__(self, relationship):
        '''Constructor for our Relationship proxy
        Relationship should be a neo4j.Relationship
        '''
        self._relationship = relationship
        self._id = relationship._id
        self.type = relationship.type
        self.start_node = relationship.start_node._id
        self.end_node = relationship.end_node._id
        self.properties = relationship.properties

if __name__ == '__main__':
    def maintest():
        'test main program'
        from cmainit import CMAinit
        from droneinfo import Drone
        from systemnode import SystemNode
        print >> sys.stderr, 'Starting'
        CMAinit(None, cleanoutdb=True, debug=True)
        if CMAdb.store.transaction_pending:
            print 'Transaction pending in:', CMAdb.store
            print 'Results:', CMAdb.store.commit()
        print ProcessNode.meta_labels()
        print SystemNode.meta_labels()
        print Drone.meta_labels()
        print 'keys:', Drone.meta_key_attributes()
        print >> sys.stderr, 'Init done'
        return 0

    sys.exit(maintest())
