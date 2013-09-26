# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
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
_suites = ['all', 'cma']
import sys
import os
sys.path.extend(['..', '../cma', "/usr/local/lib/python2.7/dist-packages"])
from py2neo import neo4j
from testify import *
from store import Store
from AssimCclasses import pyNetAddr
from AssimCtypes import ADDR_FAMILY_802
from graphnodes import GraphNode, RegisterGraphClass

DEBUG=False

def CreateIndexes(indexlist):
    'Create Indexes(indexlist) - a list of strings for Node indexes to create'
    for index in indexlist:
        db.get_or_create_index(neo4j.Node, index, None)
     

@RegisterGraphClass
class Person(GraphNode):
    'A Person - or at least an electronic representation of one'
    def __init__(self, firstname, lastname, dateofbirth=None):
        GraphNode.__init__(self, domain='global')
        self.firstname = firstname
        self.lastname = lastname
        if dateofbirth is not None:
            self.dateofbirth = dateofbirth
        else:
            self.dateofbirth='unknown'
            
    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of significance'
        return ['lastname', 'firstname']


@RegisterGraphClass
class System(GraphNode):
    'Some kind of semi-intelligent system'
    def __init__(self, designation, domain='global', roles=None):
        GraphNode.__init__(self, domain)
        self.designation = designation.lower()
        if roles == None:
            roles = ['']
        self.roles = roles
        if domain is None:
            domain='global'
        self.domain = domain
            
    def addroles(self, role):
        if self.roles[0] == '':
            del self.roles[0]
        if isinstance(role, list):
            for arole in role:
                self.addroles(arole)
        elif role not in self.roles:
                self.roles.append(role)
        return self.roles

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of significance'
        return ['designation', 'domain']
    
@RegisterGraphClass
class Drone(System):
    def __init__(self, designation, domain='global', roles=None):
        System.__init__(self, designation=designation)
        if roles is None:
            roles = []
        elif isinstance(roles, str):
            roles = [roles]
        roles.extend(['host', 'Drone'])
        System.__init__(self, designation, domain=domain, roles=roles)

        
@RegisterGraphClass
class IPaddr(GraphNode):
    def __init__(self, ipaddr):
        GraphNode.__init__(self, domain='global')
        if isinstance(ipaddr, str):
            ipaddr = pyNetAddr(ipaddr)
        if isinstance(ipaddr, pyNetAddr):
            ipaddr = ipaddr.toIPv6()
        self.ipaddr = str(ipaddr)

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of significance'
        return ['ipaddr']

@RegisterGraphClass
class NIC(GraphNode):
    def __init__(self, MACaddr):
        GraphNode.__init__(self, domain='global')
        mac = pyNetAddr(MACaddr)
        if mac is None or mac.addrtype() != ADDR_FAMILY_802:
            raise ValueError('Not a legal MAC address [%s // %s]: %s (%s)' 
            %       (MACaddr, str(mac), str(mac.addrtype()), mac.addrlen()))
        self.MACaddr = str(mac)

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of significance'
        return ['MACaddr']

     
Classes = [Person, System, Drone, IPaddr, NIC]

keymap = {'Person': {'index':'Person','kattr': 'lastname', 'vattr': 'firstname'},
          'System': {'index':'System','kattr': 'designation', 'value': 'global'},
          'Drone':  {'index':'Drone','kattr': 'designation', 'value': 'global'},
          'IPaddr': {'index':'IPaddr','kattr': 'ipaddr', 'value': 'global'},
          'NIC':    {'index':'NIC','kattr': 'MACaddr', 'value': 'global'}
          }
uniqueindexes = {}
for key in keymap:
    uniqueindexes[key] = True


##mys = Store(db, uniqueindexmap=uniqueindexes, classkeymap=keymap)
##
##fred = System('Fred')
##fred.addroles('server')
##fred.addroles(['server', 'switch'])
##print fred.designation
##print fred.roles
##
##Annika = Person('Annika', 'Hansen')
##print seven.designation
##print seven.roles
##print Annika.firstname, Annika.lastname
db = neo4j.GraphDatabaseService(None)
db.clear()
OurStore = None
CreateIndexes([cls.__name__ for cls in Classes])

def initstore():
    global OurStore
    GraphNode.clean_graphnodes()
    if OurStore is not None:
        OurStore.clean_store()
    db.clear()
    OurStore = Store(db, uniqueindexmap=uniqueindexes, classkeymap=keymap)
    return OurStore


class TestCreateOps(TestCase):
    def test_drone(self):
        store = initstore()
        seven = store.load_or_create(Drone, designation='SevenOfNine', roles='Borg')
        self.assertTrue('host' in seven.roles)
        self.assertTrue('Drone' in seven.roles)
        self.assertTrue('Borg' in seven.roles)
        self.assertTrue(store.is_abstract(seven))
        store.commit()
        self.assertTrue('host' in seven.roles)
        self.assertTrue('Drone' in seven.roles)
        self.assertTrue('Borg' in seven.roles)
        self.assertTrue(not store.is_abstract(seven))
        self.assertTrue(isinstance(seven, System))
        self.assertEqual(seven.designation, 'sevenofnine')
        self.assertFalse(store.is_abstract(seven))

    def test_person(self):
        store = initstore()
        Annika = Person('Annika', 'Hansen')
        store.save(Annika)
        store.commit()
        whoami = store.load_or_create(Person, firstname='Annika', lastname='Hansen')
        self.assertTrue(whoami is Annika)
        self.assertEqual(Annika.firstname, 'Annika')
        self.assertEqual(Annika.lastname, 'Hansen')

    def test_system(self):
        store = initstore()
        fredsys = store.load_or_create(System, designation='Fred', roles=['bridge', 'router'])
        self.assertTrue('bridge' in fredsys.roles)
        self.assertTrue('router' in fredsys.roles)
        self.assertFalse('host' in fredsys.roles)
        self.assertFalse('drone' in fredsys.roles)
        self.assertTrue(store.is_abstract(fredsys))
        store.commit()
        self.assertFalse(store.is_abstract(fredsys))
        self.assertEqual(fredsys.designation, 'fred')

    def test_nic(self):
        store = initstore()
        freddiemac = store.load_or_create(NIC, MACaddr='AA-BB-CC-DD-EE-FF')
        self.assertEqual(freddiemac.MACaddr, 'aa-bb-cc-dd-ee-ff')
        sys64 = store.load_or_create(NIC, MACaddr='00-11-CC-DD-EE-FF:AA:BB')
        self.assertEqual(sys64.MACaddr, '00-11-cc-dd-ee-ff-aa-bb')
        self.assertRaises(ValueError, store.load_or_create, NIC, MACaddr='AA-BB-CC-DD-EE-FF:')
        self.assertRaises(ValueError, store.load_or_create, NIC, MACaddr='AA-BB-CC-DD-EE-FF:00')
        self.assertRaises(ValueError, store.load_or_create, NIC, MACaddr='AA-BB-CC-DD-EE-FF-')
        self.assertRaises(ValueError, store.load_or_create, NIC, MACaddr='10.10.10.5')
        self.assertTrue(store.is_abstract(freddiemac))
        store.commit()
        self.assertEqual(freddiemac.MACaddr, 'aa-bb-cc-dd-ee-ff')
        self.assertEqual(sys64.MACaddr, '00-11-cc-dd-ee-ff-aa-bb')
        self.assertTrue(not store.is_abstract(freddiemac))


class TestRelateOps(TestCase):

    def test_relate1(self):
        store = initstore()
        Annika = store.load_or_create(Person, firstname='Annika', lastname='Hansen')
        seven = store.load_or_create(Drone, designation='SevenOfNine', roles='Borg')
        store.relate(seven, 'formerly', Annika)
        # Borg Drones need 64 bit MAC addresses ;-) (or maybe more)
        sevennic = store.load_or_create(NIC, MACaddr='ff-ff:7-0f-9:7-0f-9')
        store.relate(seven, 'nicowner', sevennic)
        self.assertTrue(sevennic.MACaddr, 'ff:ff:07:0f:09:07:0f:09')
        self.assertTrue(isinstance(seven, System))
        self.assertTrue(isinstance(seven, Drone))
        self.assertTrue(isinstance(seven, GraphNode))
        self.assertTrue(isinstance(Annika, Person))
        self.assertTrue(isinstance(Annika, GraphNode))
        self.assertTrue(isinstance(sevennic, NIC))
        self.assertTrue(isinstance(sevennic, GraphNode))

        # It would be nice if the following tests would work even before committing...
        store.commit()
        count=0
        for node in store.load_related(seven, 'formerly', Person):
            self.assertTrue(node is Annika)
            count += 1
        self.assertEqual(count, 1)
        count=0
        for node in store.load_in_related(Annika, 'formerly', Drone):
            self.assertTrue(node is seven)
            count += 1
        self.assertEqual(count, 1)
        count=0
        for node in store.load_related(seven, 'nicowner', NIC):
            self.assertTrue(node is sevennic)
            count += 1
        self.assertEqual(count, 1)

    def test_relate2(self):
        store = initstore()
        seven = store.load_or_create(Drone, designation='SevenOfNine', roles='Borg')
        sevennic1 = store.load_or_create(NIC, MACaddr='ff-ff:7-0f-9:7-0f-9')
        sevennic2 = store.load_or_create(NIC, MACaddr='00-00:7-0f-9:7-0f-9')
        ipaddr1=store.load_or_create(IPaddr, ipaddr='10.10.10.1')
        ipaddr2=store.load_or_create(IPaddr, ipaddr='10.10.10.2')
        store.relate(seven, 'nicowner', sevennic1)
        store.relate(seven, 'nicowner', sevennic2)
        store.relate(sevennic1, 'ipowner', ipaddr1)
        store.relate(sevennic2, 'ipowner', ipaddr2)
        store.commit()

        prevnode = None
        count=0
        for node in store.load_related(seven, 'nicowner', NIC):
            self.assertTrue((node is sevennic1 or node is sevennic2) and node is not prevnode)
            prevnode = node
            count += 1
            ipcount=0
            for ip in store.load_related(node, 'ipowner', IPaddr):
                if node is sevennic1:
                    self.assertTrue(ip is ipaddr1)
                else:
                    self.assertTrue(ip is ipaddr2)
                ipcount += 1
            self.assertTrue(ipcount == 1)
        self.assertEqual(count, 2)

    def test_separate1(self):
        store = initstore()
        seven = store.load_or_create(Drone, designation='SevenOfNine', roles='Borg')
        sevennic1 = store.load_or_create(NIC, MACaddr='ff-ff:7-0f-9:7-0f-9')
        sevennic2 = store.load_or_create(NIC, MACaddr='00-00:7-0f-9:7-0f-9')
        ipaddr1=store.load_or_create(IPaddr, ipaddr='10.10.10.1')
        ipaddr2=store.load_or_create(IPaddr, ipaddr='10.10.10.2')
        store.relate(seven, 'nicowner', sevennic1)
        store.relate(seven, 'nicowner', sevennic2)
        store.relate(sevennic1, 'ipowner', ipaddr1)
        store.relate(sevennic2, 'ipowner', ipaddr2)
        store.commit()
        store.separate(sevennic2, 'ipowner')
        store.separate(seven, 'nicowner', sevennic2)
        store.commit()
        count=0
        for node in store.load_related(seven, 'nicowner', NIC):
            self.assertTrue(node is sevennic1)
            count += 1
            ipcount=0
            for ip in store.load_related(node, 'ipowner', IPaddr):
                self.assertTrue(ip is ipaddr1)
                ipcount += 1
            self.assertTrue(ipcount == 1)
        self.assertEqual(count, 1)

class TestGeneralQuery(TestCase):

    def test_multicolumn_query(self):
        store = initstore()
        Annika = store.load_or_create(Person, firstname='Annika', lastname='Hansen')
        seven = store.load_or_create(Drone, designation='SevenOfNine', roles='Borg')
        store.relate(seven, 'formerly', Annika)
        sevennic1 = store.load_or_create(NIC, MACaddr='ff-ff:7-0f-9:7-0f-9')
        sevennic2 = store.load_or_create(NIC, MACaddr='00-00:7-0f-9:7-0f-9')
        ipaddr1=store.load_or_create(IPaddr, ipaddr='10.10.10.1')
        ipaddr2=store.load_or_create(IPaddr, ipaddr='10.10.10.2')
        store.relate(seven, 'nicowner', sevennic1)
        store.relate(seven, 'nicowner', sevennic2)
        store.relate(sevennic1, 'ipowner', ipaddr1)
        store.relate(sevennic2, 'ipowner', ipaddr2)
        store.commit()
        # Now we have something to test queries against...
        # seven-[:formerly]->Annika
        # seven-[:nicowner]-> sevennic1-[:ipowner]->10.10.10.1
        # seven-[:nicowner]-> sevennic2-[:ipowner]->10.10.10.2

        Qstr='''START drone=node:Drone('sevenofnine:*')
        MATCH person<-[:formerly]-drone-[:nicowner]->nic-[:ipowner]->ipaddr
        RETURN person, drone, nic, ipaddr'''
        Query = neo4j.CypherQuery(store.db, Qstr)
        iter = store.load_cypher_query(Query, GraphNode.factory)
        rowcount = 0
        foundaddr1=False
        foundaddr2=False
        for row in iter:
            rowcount += 1
            # fields are person, drone, nic and ipaddr
            self.assertTrue(row.person is Annika)
            self.assertTrue(row.drone is seven)
            if row.nic is sevennic1:
                self.assertTrue(row.ipaddr is ipaddr1)
                foundaddr1 = True
            else:
                self.assertTrue(row.nic is sevennic2)
                self.assertTrue(row.ipaddr is ipaddr2)
                foundaddr2 = True
        self.assertTrue(foundaddr1)
        self.assertTrue(foundaddr2)
        print >> sys.stderr, 'It all looks great!'

# Other things that ought to have tests:
#   node deletion
#   Searching for nodes we just added (I forgot which ones work that way)
#   Filtered queries - note that fields have to be filtered out in the JSON
#   they can't be reliably filtered out of the nodes
#   other things?
    
if __name__ == "__main__":
    run()

