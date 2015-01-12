
#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
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
from consts import CMAconsts
from store import Store
import sys, re, time
from AssimCtypes import ADDR_FAMILY_IPV4, ADDR_FAMILY_IPV6, ADDR_FAMILY_802
from AssimCclasses import pyNetAddr, pyConfigContext
from py2neo import neo4j


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
    classtypeobjs = {}

    @staticmethod
    def factory(**kwargs):
        'A factory "constructor" function - acts like a universal constructor for GraphNode types'
        return nodeconstructor(**kwargs)

    @staticmethod
    def clean_graphnodes():
        'Invalidate any persistent objects that might become invalid when resetting the database'
        GraphNode.classtypeobjs = {}

    def __init__(self, domain, time_create_ms=None, time_create_iso8601=None):
        'Abstract Graph node base class'
        self.domain = domain
        self.nodetype = self.__class__.__name__
        self._baseinitfinished = False
        self.time_create_iso8601 = time_create_iso8601
        self.time_create_ms = time_create_ms

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of significance'
        raise NotImplementedError('Abstract base class function __meta_keyattrs__')

    @classmethod
    def __meta_labels__(cls):
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

    def post_db_init(self):
        '''Create IS_A relationship to our 'class' node in the database, and set creation time'''
        if not self._baseinitfinished:
            self._baseinitfinished = True
            if Store.is_abstract(self) and self.nodetype != CMAconsts.NODE_nodetype:
                store = Store.getstore(self)
                if self.nodetype not in GraphNode.classtypeobjs:
                    GraphNode.initclasstypeobj(store, self.nodetype)
                store.relate(self, CMAconsts.REL_isa, GraphNode.classtypeobjs[self.nodetype])
                assert GraphNode.classtypeobjs[self.nodetype].name == self.nodetype
                self.time_create_ms = int(round(time.time()*1000))
                self.time_create_iso8601  = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())


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
        if Store.has_node(self):
            if Store.is_abstract(self):
                result += comma + 'HasNode = "abstract"'
            else:
                result += (comma + 'HasNode = %d' %Store.id(self))

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
        '''Initialize GraphNode.classtypeobjs for our "nodetype"
        This involves
         - Ensuring that there's an index for this class, and the NODE_nodetype class
         - Caching the class that goes with this nodetype
         - setting up all of our IS_A objects, including the root object if necessary,
         - updating the store's uniqueindexmap[nodetype]
         - updating the store's classkeymap[nodetype]
         - updating GraphNode.classtypeobjs[nodetype]
         This should eliminate the need to do any of these things for any class.
        '''
        if nodetype != CMAconsts.NODE_nodetype and CMAconsts.NODE_nodetype not in store.classkeymap:
            # Have to make sure our root type node exists and is set up properly
            GraphNode.initclasstypeobj(store, CMAconsts.NODE_nodetype)
        ourclass = GraphNode.classmap[nodetype]
        rootclass = GraphNode.classmap[CMAconsts.NODE_nodetype]
        if nodetype not in store.classkeymap:
            store.uniqueindexmap[nodetype] = True
            keys = ourclass.__meta_keyattrs__()
            ckm_entry = {'kattr': keys[0], 'index': nodetype}
            if len(keys) > 1:
                ckm_entry['vattr'] = keys[1]
            else:
                ckm_entry['value'] = 'None'
            store.classkeymap[nodetype] = ckm_entry
        store.db.get_or_create_index(neo4j.Node, nodetype)
        ourtypeobj = store.load_or_create(rootclass, name=nodetype)
        assert ourtypeobj.name == nodetype
        if Store.is_abstract(ourtypeobj) and nodetype != CMAconsts.NODE_nodetype:
            roottype = store.load_or_create(rootclass, name=CMAconsts.NODE_nodetype)
            store.relate(ourtypeobj, CMAconsts.REL_isa, roottype)
        GraphNode.classtypeobjs[nodetype] = ourtypeobj



# R0903: Too few public methods (0/2)
# pylint: disable=R0903
@RegisterGraphClass
class CMAclass(GraphNode):
    '''Class defining the relationships of our CMA classes to each other'''

    def __init__(self, name):
        GraphNode.__init__(self, domain='metadata')
        self.name = name
        self.domain = CMAconsts.metadomain
        self.nodetype = CMAconsts.NODE_nodetype
        assert str(self.name) == str(name)

    def __str__(self):
        'Default routine for printing CMAclass objects'
        result = '%s({' % self.__class__.__name__
        comma  = ''
        for attr in Store.safe_attrs(self):
            result += '%s%s = %s'% (comma, attr, str(getattr(self, attr)))
            comma = ",\n    "
        if Store.has_node(self):
            if Store.is_abstract(self):
                result += comma + 'HasNode = "abstract"'
            else:
                result += (comma + 'HasNode = %d' %Store.id(self))

        result += "\n})"
        return result

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of significance'
        return ['name']

@RegisterGraphClass
class SystemNode(GraphNode):
    'An object that represents a physical or virtual system (server, switch, etc)'
    # We really ought to figure out how to make Drone a subclass of SystemNode
    def __init__(self, domain, designation, roles=None):
        GraphNode.__init__(self, domain=domain)
        self.designation = str(designation).lower()
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
        'Add a role to our GraphNode'
        if self.roles is not None and len(self.roles) > 0 and self.roles[0] == '':
            self.delrole('')
        if isinstance(roles, tuple) or isinstance(roles, list):
            for role in roles:
                self.addrole(role)
            return self.roles
        assert isinstance(roles, str) or isinstance(roles, unicode)
        if self.roles is None:
            self.roles = [roles]
        elif not roles in self.roles:
            self.roles.append(roles)
        return self.roles

    def delrole(self, roles):
        'Delete a role from our GraphNode'
        if isinstance(roles, tuple) or isinstance(roles, list):
            for role in roles:
                self.delrole(role)
            return self.roles
        assert isinstance(roles, str) or isinstance(roles, unicode)
        if roles in self.roles:
            self.roles.remove(roles)
        return self.roles



@RegisterGraphClass
class NICNode(GraphNode):
    'An object that represents a NIC - characterized by its MAC address'
    def __init__(self, domain, macaddr, ifname=None):
        GraphNode.__init__(self, domain=domain)
        mac = pyNetAddr(macaddr)
        if mac is None or mac.addrtype() != ADDR_FAMILY_802:
            raise ValueError('Not a legal MAC address [%s]' % macaddr)
        self.macaddr = str(mac)
        if ifname is not None:
            self.ifname = ifname

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in decreasing order of significance'
        return ['macaddr', 'domain']


@RegisterGraphClass
class IPaddrNode(GraphNode):
    '''An object that represents a v4 or v6 IP address without a port - characterized by its
    IP address. They are always represented in the database in ipv6 format.
    '''
    def __init__(self, domain, ipaddr, cidrmask='unknown'):
        'Construct an IPaddrNode - validating our parameters'
        GraphNode.__init__(self, domain=domain)
        if isinstance(ipaddr, str) or isinstance(ipaddr, unicode):
            ipaddr = pyNetAddr(str(ipaddr))
        if isinstance(ipaddr, pyNetAddr):
            addrtype = ipaddr.addrtype()
            if addrtype == ADDR_FAMILY_IPV4:
                ipaddr = ipaddr.toIPv6()
            elif addrtype != ADDR_FAMILY_IPV6:
                raise ValueError('Invalid network address type for IPaddrNode constructor: %s'
                %   str(ipaddr))
            ipaddr.setport(0)
            ipaddr = unicode(str(ipaddr))
        else:
            raise ValueError('Invalid address type for IPaddrNode constructor: %s type(%s)'
            %   (str(ipaddr), type(ipaddr)))
        self.ipaddr = ipaddr
        self.cidrmask = cidrmask

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of significance'
        return ['ipaddr', 'domain']

@RegisterGraphClass
class IPtcpportNode(GraphNode):
    'An object that represents an IP:port combination characterized by the pair'
    def __init__(self, domain, ipaddr, port=None, protocol='tcp'):
        'Construct an IPtcpportNode - validating our parameters'
        GraphNode.__init__(self, domain=domain)
        if isinstance(ipaddr, str) or isinstance(ipaddr, unicode):
            ipaddr = pyNetAddr(str(ipaddr))
        if isinstance(ipaddr, pyNetAddr):
            if port is None:
                port = ipaddr.port()
            if port <= 0 or port >= 65536:
                raise ValueError('Invalid port for constructor: %s' % str(port))
            addrtype = ipaddr.addrtype()
            if addrtype == ADDR_FAMILY_IPV4:
                ipaddr = ipaddr.toIPv6()
            elif addrtype != ADDR_FAMILY_IPV6:
                raise ValueError('Invalid network address type [%s] for constructor: %s'
                %  (addrtype, str(ipaddr)))
            ipaddr.setport(0)
            ipaddr = unicode(str(ipaddr))
        else:
            raise ValueError('Invalid address type for constructor: %s type(%s)'
            %   (str(ipaddr), type(ipaddr)))
        self.ipaddr = ipaddr
        self.port = port
        self.protocol = protocol
        self.ipport = self.format_ipport()

    @staticmethod
    def __meta_keyattrs__():
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
    def __init__(self, domain, processname, host, pathname, argv, uid, gid, cwd, roles=None):
        GraphNode.__init__(self, domain=domain)
        self.host = host
        self.pathname   = pathname
        self.argv       = argv
        self.uid        = uid
        self.gid        = gid
        self.cwd        = cwd
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
        'Add a role to our GraphNode'
        if self.roles is not None and len(self.roles) > 0 and self.roles[0] == '':
            self.delrole('')
        if isinstance(roles, tuple) or isinstance(roles, list):
            for role in roles:
                self.addrole(role)
            return self.roles
        assert isinstance(roles, str) or isinstance(roles, unicode)
        if self.roles is None:
            self.roles = [roles]
        elif not roles in self.roles:
            self.roles.append(roles)
        return self.roles

    def delrole(self, roles):
        'Delete a role from our GraphNode'
        if isinstance(roles, tuple) or isinstance(roles, list):
            for role in roles:
                self.delrole(role)
            return self.roles
        assert isinstance(roles, str) or isinstance(roles, unicode)
        if roles in self.roles:
            self.roles.remove(roles)
        return self.roles

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of significance'
        return ['processname', 'domain']

if __name__ == '__main__':
    from cmainit import CMAinit
    from cmadb import CMAdb
    print >> sys.stderr, 'Starting'
    CMAinit(None, cleanoutdb=True, debug=True)
    if CMAdb.store.transaction_pending:
        print 'Transaction pending in:', CMAdb.store
        print 'Results:', CMAdb.store.commit()
    print CMAclass.__meta_labels__()
    print ProcessNode.__meta_labels__()
    print SystemNode.__meta_labels__()
    from droneinfo import Drone
    print Drone.__meta_labels__()
    print 'keys:', Drone.__meta_keyattrs__()
    print >> sys.stderr, 'Init done'
