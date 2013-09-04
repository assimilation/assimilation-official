
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
from consts import CMAconsts
from cmadb import CMAdb, CMAclass
from store import Store
from os import path
from hashlib import md5
import sys
'''
This module defines the classes for all our CMA nodes ...
'''

def nodeconstructor(**properties):
    'A class-like constructor that knows our class name is stored as nodetype'
    realcls = eval(properties['nodetype'])
    return Store._callconstructor(realcls, properties)

class GraphNode(object):
    def __init__(self, domain, roles=[]):
        'Abstract Graph node base class'
        self.domain = domain
        self.nodetype = self.__class__.__name__
        self._baseinitfinished=False
        if roles == []:
            # Neo4j can't initialize node properties to empty arrays because
            # it wants to know what kind of array it is...
            roles = ['']
        self.roles = roles

    def addrole(self, *roles):
        if len(self.roles) > 0 and self.roles[0] == '':
            self.delrole('')
        for role in roles:
            assert isinstance(role, str)
            if self.roles is None:
                self.roles=[role]
            elif not role in self.roles:
                self.roles.append(role)
        return self.roles

    def delrole(self, roles):
        if not isinstance(self, tuple) and not isinstance(self, list):
            roles=(roles,)
        for role in roles:
            for j in range(0,len(self.roles)):
                if self.roles[j] == role:
                    del self.roles[j]
                    break
        return self.roles


    def post_db_init(self):
        '''Create IS_A relationship to our 'class' node in the database'''
        if not self._baseinitfinished:
            self._baseinitfinished = True
            if Store.is_abstract(self):
                CMAdb.store.relate(self, CMAconsts.REL_isa, CMAdb.cdb.nodetypetbl[self.nodetype])

    def update_attributes(self, other):
        'Update our attributes from another node of the same type'
        if other.nodetype != self.nodetype:
            raise ValueError('Cannot update attributes from incompatible nodes (%s vs %s)'
            %   (self.nodetype, other.nodetype))
        for attr in other.__dict__.keys():
            if not hasattr(self, attr) or getattr(self, attr) != getattr(other, attr):
                self.attr = other.attr
        return self

    def __str__(self):
        'Default routine for printing GraphNodes'
        result = '%s({' % self.__class__.__name__
        comma  = ''
        for attr in Store._safe_attrs(self):
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
    def dump_nodes(nodetype='Drone', stream=sys.stderr):
        'Dump all our drones out to the given stream (defaults to sys.stderr)'
        idx = CMAdb.cdb.indextbl[nodetype]
        query= '*:*'
        #print >> stream, 'QUERY against %s IS: "%s"' % (idx, query)
        dronelist = idx.query(query)
        dronelist = [drone for drone in dronelist]
        print >> stream, 'List of %ss: %s' % (nodetype, dronelist)
        for drone in dronelist:
            print >> stream, ('DRONE %s (%s id=%s)' % (nodetype
            ,   str(drone.get_properties()), drone._id))
            for rel in drone.match():
                start=rel.start_node
                end=rel.end_node
                if start._id == drone._id:
                    print >> stream, '    (%s)-[%s]->(%s:%s,%s)' \
                    %       (drone['designation'], rel.type, end['nodetype'], end['designation'], end._id)
                else:
                    print >> stream, '    (%s:%s,%s)-[%s]->(%s)' \
                    %       (start['designation'], start['nodetype'], start._id, rel.type, drone['designation'])
                if start._id == end._id:
                    print >> stream, 'SELF-REFERENCE to %s' % start._id


class SystemNode(GraphNode):
    'A node that represents a physical or virtual system (server, switch, etc)'
    def __init__(self, domain, name, roles=[]):
        GraphNode.__init__(self, domain=domain, roles=roles)
        self.name=name

class NICNode(GraphNode):
    def __init__(self, domain, macaddr, ifname='unknown'):
        GraphNode.__init__(self, domain=domain)
        self.macaddr=macaddr
        self.ifname=ifname

class IPaddrNode(GraphNode):
    def __init__(self, domain, ipaddr, cidrmask='unknown'):
        GraphNode.__init__(self, domain=domain)
        self.ipaddr=ipaddr
        self.cidrmask=cidrmask
        

class IPtcpportNode(GraphNode):
    def __init__(self, domain, ipaddr, port):
        GraphNode.__init__(self, domain=domain)
        self.ipaddr=ipaddr
        self.port=port
        self.ipport = self.make_ipport(ipaddr, port)

    def make_ipport(self, ipaddr, port):
        return '%s_%s' % (port, ipaddr)
        

class ProcessNode(GraphNode):
    def __init__(self, domain, host, pathname, arglist, uid, gid, cwd, roles=[]):
        GraphNode.__init__(self, domain=domain, roles=roles)
        self.host=host
        self.pathname=pathname
        self.arglist=arglist
        self.uid=uid
        self.gid=gid
        self.cwd=cwd
        #self.processname='%s|%s|%s|%s:%s|%s' \
        #%       (path.basename(pathname), path.dirname(pathname), host, uid, gid, str(arglist))
        sum=md5()
        procstring='%s|%s|%s:%s|%s' \
        %       (path.dirname(pathname), host, uid, gid, str(arglist))
        sum.update(procstring)
        self.processname='%s_%s' % (path.basename(pathname), sum.hexdigest())

if __name__ == '__main__':
    print >> sys.stderr, 'Starting'
    CMAinit(None, cleanoutdb=True, debug=True)
    if CMAdb.store.transaction_pending:
        print 'Transaction pending in:', CMAdb.store
        print 'Results:', CMAdb.store.commit()
    print >> sys.stderr, 'Init done'
