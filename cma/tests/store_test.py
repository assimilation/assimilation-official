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
from __future__ import print_function
_suites = ['all', 'cma']
import sys
import gc
import logging
import inject
sys.path.extend(['..', '../cma', "/usr/local/lib/python2.7/dist-packages"])
import py2neo
from py2neo import Graph, GraphError
from store import Store
from AssimCclasses import pyNetAddr, dump_c_objects
from AssimCtypes import ADDR_FAMILY_802, proj_class_live_object_count, proj_class_dump_live_objects
from graphnodes import GraphNode, registergraphclass, JSONMapNode
from systemnode import SystemNode
from cmainit import  CMAInjectables, CMAinit
stderr = sys.stderr

DEBUG=False
class FooClass:
    db = None
    log = None
    store = None
    initialized_yet = False
    CheckForDanglingClasses = True
    AssertOnDanglingClasses = True
    WorstDanglingCount = 0

    @staticmethod
    @inject.params(db='py2neo.Graph', log='logging.Logger', store='Store')
    def config_foo(db=None, log=None, store=None):
        # print("config_foo(%s, %s, %s)" % (db, log, store))
        log.warning("config_foo(%s, %s, %s)" % (db, log, store))
        FooClass.db = db
        FooClass.log = log
        FooClass.store = store

    @staticmethod
    def new_transaction():
        FooClass.store.db_transaction = FooClass.store.db.begin(autocommit=False)

if not FooClass.CheckForDanglingClasses:
    print('WARNING: Memory Leak Detection disabled.', file=stderr)
elif not FooClass.AssertOnDanglingClasses:
    print('WARNING: Memory Leak assertions disabled (detection still enabled).', file=stderr)

print('USING PYTHON VERSION %s' % str(sys.version), file=stderr)

def setup_module(module):
    """Setup for this entire file"""

def assert_no_dangling_Cclasses(doassert=None):
    FooClass.store.clean_store()
    sys._clear_type_cache()
    if doassert is None:
        doassert = FooClass.AssertOnDanglingClasses
    CMAinit.uninit()
    gc.collect()    # For good measure...
    count =  proj_class_live_object_count()
    #print("CHECKING FOR DANGLING CLASSES (%d)..." % count, file=stderr)
    # Avoid cluttering the output up with redundant messages...
    if count > FooClass.WorstDanglingCount and FooClass.CheckForDanglingClasses:
        WorstDanglingCount = count
        if doassert:
            print('STARTING OBJECT DUMP', file=stderr)
            print('stdout STARTING OBJECT DUMP')
            dump_c_objects()
            print('OBJECT DUMP COMPLETE', file=stderr)
            print('stdout OBJECT DUMP COMPLETE')
            raise AssertionError("Dangling C-class objects - %d still around" % count)
        else:
            print("*****ERROR: Dangling C-class objects - %d still around" % count, file=stderr)


class TestCase(object):
    def assertEqual(self, a, b):
        assert a == b

    def assertNotEqual(self, a, b):
        assert a != b

    def assertTrue(self, a):
        assert a is True

    def assertFalse(self, a):
        assert a is False

    def assertRaises(self, exception, function, *args, **kw):
        try:
            function(*args, **kw)
            raise Exception('Did not raise exception %s: %s(%s)', exception, function, str(args))
        except exception as e:
            return True

    def teardown_method(self, method):
        # print('__del__ CALL for %s' % str(method))
        assert_no_dangling_Cclasses()


@registergraphclass
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
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        return ['lastname', 'firstname']


@registergraphclass
class aTestSystem(GraphNode):
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
        if isinstance(role, (list, tuple)):
            for arole in role:
                self.addroles(arole)
        elif role not in self.roles:
                self.roles.append(role)
        return self.roles

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        return ['designation', 'domain']

@registergraphclass
class aTestDrone(aTestSystem):
    def __init__(self, designation, domain='global', roles=None):
        aTestSystem.__init__(self, designation=designation)
        if roles is None:
            roles = []
        elif isinstance(roles, str):
            roles = [roles]
        roles.extend(['host', 'Drone'])
        aTestSystem.__init__(self, designation, domain=domain, roles=roles)


@registergraphclass
class aTestIPaddr(GraphNode):
    def __init__(self, ipaddr):
        GraphNode.__init__(self, domain='global')
        if isinstance(ipaddr, str):
            ipaddr = pyNetAddr(ipaddr)
        if isinstance(ipaddr, pyNetAddr):
            ipaddr = ipaddr.toIPv6()
        self.ipaddr = str(ipaddr)

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        return ['ipaddr']

@registergraphclass
class aTestNIC(GraphNode):
    def __init__(self, MACaddr):
        GraphNode.__init__(self, domain='global')
        mac = pyNetAddr(MACaddr)
        if mac is None or mac.addrtype() != ADDR_FAMILY_802:
            raise ValueError('Not a legal MAC address [%s // %s]: %s (%s)'
            %       (MACaddr, str(mac), str(mac.addrtype()), mac.addrlen()))
        self.MACaddr = str(mac)

    @staticmethod
    def meta_key_attributes():
        'Return our key attributes in order of significance'
        return ['MACaddr']


Classes = [Person, aTestSystem, aTestDrone, aTestIPaddr, aTestNIC, SystemNode]


##mys = Store(db)
##
##fred = System('Fred')
##fred.addroles('server')
##fred.addroles(['server', 'switch'])
##print(fred.designation)
##print(fred.roles)
##
##Annika = Person('Annika', 'Hansen')
##print(seven.designation)
##print(seven.roles)
##print(Annika.firstname, Annika.lastname)


def initstore():
    if not FooClass.initialized_yet:
        inject.configure_once(CMAInjectables.test_config_injection)
        FooClass.config_foo()
        print('USING NEO4J VERSION %s' % str(FooClass.db.neo4j_version), file=stderr)
        print('USING py2neo VERSION %s' % str(py2neo.__version__), file=stderr)
        FooClass.initialized_yet = True
    if FooClass.store.db_transaction and not FooClass.store.db_transaction.finished():
        FooClass.store.db_transaction.finish()
    FooClass.db.delete_all()
    FooClass.store.clean_store()
    FooClass.new_transaction()
    CMAinit(None)
    FooClass.new_transaction()
    return FooClass.store

class TestCreateOps(TestCase):
    def test_drone(self):
        store = initstore()
        seven = store.load_or_create(aTestDrone, designation='SevenOfNine', roles='Borg')
        self.assertTrue('host' in seven.roles)
        self.assertTrue('Drone' in seven.roles)
        self.assertTrue('Borg' in seven.roles)
        store.commit()
        self.assertTrue('host' in seven.roles)
        self.assertTrue('Drone' in seven.roles)
        self.assertTrue('Borg' in seven.roles)
        self.assertTrue(isinstance(seven, aTestSystem))
        self.assertEqual(seven.designation, 'sevenofnine')

    def test_person(self):
        store = initstore()
        # store.debug = True
        Annika = store.load_or_create(Person, firstname='Annika', lastname='Hansen')
        store.commit()
        FooClass.new_transaction()
        whoami = store.load_or_create(Person, firstname='Annika', lastname='Hansen')
        self.assertTrue(whoami is Annika)
        self.assertEqual(Annika.firstname, 'Annika')
        self.assertEqual(Annika.lastname, 'Hansen')

    def test_system(self):
        store = initstore()
        # a pyNetAddr is kind of a stupid value for role, but it makes a good test case ;-)
        fredsys = store.load_or_create(aTestSystem, designation='Fred', roles=['bridge', 'router', pyNetAddr('1.2.3.4')])
        self.assertTrue('bridge' in fredsys.roles)
        self.assertTrue('router' in fredsys.roles)
        self.assertFalse('host' in fredsys.roles)
        self.assertFalse('drone' in fredsys.roles)
        store.commit()
        self.assertEqual(fredsys.designation, 'fred')

    def test_nic(self):
        store = initstore()
        freddiemac = store.load_or_create(aTestNIC, MACaddr='AA-BB-CC-DD-EE-FF')
        self.assertEqual(freddiemac.MACaddr, 'aa-bb-cc-dd-ee-ff')
        sys64 = store.load_or_create(aTestNIC, MACaddr='00-11-CC-DD-EE-FF:AA:BB')
        self.assertEqual(sys64.MACaddr, '00-11-cc-dd-ee-ff-aa-bb')
        self.assertRaises(ValueError, store.load_or_create, aTestNIC, MACaddr='AA-BB-CC-DD-EE-FF:')
        self.assertRaises(ValueError, store.load_or_create, aTestNIC, MACaddr='AA-BB-CC-DD-EE-FF:00')
        self.assertRaises(ValueError, store.load_or_create, aTestNIC, MACaddr='AA-BB-CC-DD-EE-FF-')
        self.assertRaises(ValueError, store.load_or_create, aTestNIC, MACaddr='10.10.10.5')
        store.commit()
        self.assertEqual(freddiemac.MACaddr, 'aa-bb-cc-dd-ee-ff')
        self.assertEqual(sys64.MACaddr, '00-11-cc-dd-ee-ff-aa-bb')


class TestRelateOps(TestCase):

    def test_relate1(self):
        store = initstore()
        Annika = store.load_or_create(Person, firstname='Annika', lastname='Hansen')
        seven = store.load_or_create(aTestDrone, designation='SevenOfNine', roles='Borg')
        store.relate(seven, 'formerly', Annika)
        # Borg Drones need 64 bit MAC addresses ;-) (or maybe more)
        sevennic = store.load_or_create(aTestNIC, MACaddr='ff-ff:7-0f-9:7-0f-9')
        store.relate(seven, 'nicowner', sevennic)
        self.assertEqual(str(sevennic.MACaddr), 'ff-ff-07-0f-09-07-0f-09')
        self.assertTrue(isinstance(seven, aTestSystem))
        self.assertTrue(isinstance(seven, aTestDrone))
        self.assertTrue(isinstance(seven, GraphNode))
        self.assertTrue(isinstance(Annika, Person))
        self.assertTrue(isinstance(Annika, GraphNode))
        self.assertTrue(isinstance(sevennic, aTestNIC))
        self.assertTrue(isinstance(sevennic, GraphNode))

        # It would be nice if the following tests would work even before committing...
        store.commit()
        count=0
        for node in store.load_related(seven, 'formerly'):
            self.assertTrue(node is Annika)
            count += 1
        self.assertEqual(count, 1)
        count=0
        for node in store.load_in_related(Annika, 'formerly'):
            self.assertTrue(node is seven)
            count += 1
        self.assertEqual(count, 1)
        count=0
        for node in store.load_related(seven, 'nicowner'):
            self.assertTrue(node is sevennic)
            count += 1
        self.assertEqual(count, 1)

    def test_relate2(self):
        store = initstore()
        seven = store.load_or_create(aTestDrone, designation='SevenOfNine', roles='Borg')
        sevennic1 = store.load_or_create(aTestNIC, MACaddr='ff-ff:7-0f-9:7-0f-9')
        sevennic2 = store.load_or_create(aTestNIC, MACaddr='00-00:7-0f-9:7-0f-9')
        ipaddr1 = store.load_or_create(aTestIPaddr, ipaddr='10.10.10.1')
        ipaddr2 = store.load_or_create(aTestIPaddr, ipaddr='10.10.10.2')
        store.relate(seven, 'nicowner', sevennic1)
        store.relate(seven, 'nicowner', sevennic2)
        store.relate(sevennic1, 'ipowner', ipaddr1)
        store.relate(sevennic2, 'ipowner', ipaddr2)
        store.commit()

        prevnode = None
        count=0
        for nic in store.load_related(seven, 'nicowner'):
            self.assertTrue((nic is sevennic1 or nic is sevennic2) and nic is not prevnode)
            prevnode = nic
            count += 1
            ipcount=0
            # print('NIC IS %s' % nic, file=stderr)
            for ip in store.load_related(nic, 'ipowner'):
                # print('IPaddr is IS %s' % ip, file=stderr)
                if nic is sevennic1:
                    # print('IP IS %s NOT ipaddr1' % ip, file=stderr)
                    self.assertTrue(ip is ipaddr1)
                else:
                    self.assertTrue(ip is ipaddr2)
                ipcount += 1
            self.assertTrue(ipcount == 1)
        self.assertEqual(count, 2)

    def test_separate1(self):
        store = initstore()
        seven = store.load_or_create(aTestDrone, designation='SevenOfNine', roles='Borg')
        sevennic1 = store.load_or_create(aTestNIC, MACaddr='ff-ff:7-0f-9:7-0f-9')
        sevennic2 = store.load_or_create(aTestNIC, MACaddr='00-00:7-0f-9:7-0f-9')
        ipaddr1 = store.load_or_create(aTestIPaddr, ipaddr='10.10.10.1')
        ipaddr2 = store.load_or_create(aTestIPaddr, ipaddr='10.10.10.2')
        store.relate(seven, 'nicowner', sevennic1)
        store.relate(seven, 'nicowner', sevennic2)
        store.relate(sevennic1, 'ipowner', ipaddr1)
        store.relate(sevennic2, 'ipowner', ipaddr2)
        store.commit()
        FooClass.new_transaction()
        store.separate(sevennic2, 'ipowner')
        store.separate(seven, 'nicowner', sevennic2)
        store.commit()
        count=0
        for node in store.load_related(seven, 'nicowner'):
            self.assertTrue(node is sevennic1)
            count += 1
            ipcount=0
            for ip in store.load_related(node, 'ipowner'):
                self.assertTrue(ip is ipaddr1)
                ipcount += 1
            self.assertTrue(ipcount == 1)
        self.assertEqual(count, 1)


class TestGeneralQuery(TestCase):

    def test_multicolumn_query(self):
        store = initstore()
        Annika = store.load_or_create(Person, firstname='Annika', lastname='Hansen')
        seven = store.load_or_create(aTestDrone, designation='SevenOfNine', roles='Borg')
        store.relate(seven, 'formerly', Annika)
        sevennic1 = store.load_or_create(aTestNIC, MACaddr='ff-ff:7-0f-9:7-0f-9')
        sevennic2 = store.load_or_create(aTestNIC, MACaddr='00-00:7-0f-9:7-0f-9')
        ipaddr1 = store.load_or_create(aTestIPaddr, ipaddr='10.10.10.1')
        ipaddr2 = store.load_or_create(aTestIPaddr, ipaddr='10.10.10.2')
        store.relate(seven, 'nicowner', sevennic1)
        store.relate(seven, 'nicowner', sevennic2)
        store.relate(sevennic1, 'ipowner', ipaddr1)
        store.relate(sevennic2, 'ipowner', ipaddr2)
        store.commit()
        # Now we have something to test queries against...
        # seven-[:formerly]->Annika
        # seven-[:nicowner]-> sevennic1-[:ipowner]->10.10.10.1
        # seven-[:nicowner]-> sevennic2-[:ipowner]->10.10.10.2

        Qstr='''
        MATCH (person:Class_Person)<-[:formerly]-(drone:Class_aTestDrone)-[:nicowner]->(nic)-[:ipowner]->(ipaddr)
        WHERE person.firstname = 'Annika' and person.lastname = 'Hansen'
        RETURN person, drone, nic, ipaddr'''
        iterator = store.load_cypher_query(Qstr)
        rowcount = 0
        foundaddr1 = False
        foundaddr2 = False
        for row in iterator:
            # print('>>>>>>>>>>>>>>>>>>ROW.NIC.IPADDR: %s' % row.ipaddr.ipaddr, file=stderr)
            # print('>>>>>>>>>>>>>>>>>>ROW.NIC.MACADDR: %s' % row.nic.MACaddr, file=stderr)
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
        # print('ROWCOUNT: %s', rowcount, file=stderr)
        self.assertEqual(rowcount, 2)
        self.assertTrue(foundaddr1)
        self.assertTrue(foundaddr2)

class TestDatabaseWrites(TestCase):
    mac1 = 'ff-ff:7-0f-9:7-0f-9'
    mac2 = '00-00:7-0f-9:7-0f-9'
    ip1 = '10.10.10.1'
    ip2 = '10.10.10.2'

    def create_stuff(self, store):
        FooClass.new_transaction()
        seven = store.load_or_create(aTestDrone, designation='SevenOfNine', roles='Borg')
        Annika = store.load_or_create(Person, firstname='Annika', lastname='Hansen')
        store.relate(seven, 'formerly', Annika)
        sevennic1 = store.load_or_create(aTestNIC, MACaddr=TestDatabaseWrites.mac1)
        sevennic2 = store.load_or_create(aTestNIC, MACaddr=TestDatabaseWrites.mac2)
        ipaddr1 = store.load_or_create(aTestIPaddr,   ipaddr=TestDatabaseWrites.ip1)
        ipaddr2 = store.load_or_create(aTestIPaddr,   ipaddr=TestDatabaseWrites.ip2)
        store.relate(seven, 'nicowner', sevennic1)
        store.relate(seven, 'nicowner', sevennic2)
        store.relate(sevennic1, 'ipowner', ipaddr1)
        store.relate(sevennic2, 'ipowner', ipaddr2)
        store.commit()
        # Now we have something to test queries against...
        # seven-[:formerly]->Annika
        # seven-[:nicowner]-> sevennic1-[:ipowner]->10.10.10.1
        # seven-[:nicowner]-> sevennic2-[:ipowner]->10.10.10.2
        # When we return, we should not have anything in our cache
        FooClass.new_transaction()

    def test_create_and_query(self):
        """
        The main point of this test is to verify that things actually go into the
        database correctly.

        :return: None
        """
        Qstr='''
        MATCH (person:Class_Person)<-[:formerly]-(drone:Class_aTestDrone)-[:nicowner]->(nic)-[:ipowner]->(ipaddr)
        WHERE person.firstname = "Annika" AND person.lastname="Hansen"
        RETURN person, drone, nic, ipaddr
        '''
        store = initstore()
        #print('RUNNING create_stuff', file=stderr)
        self.create_stuff(store)    # Everything has gone out of scope
                                    # so nothing is cached any more
        #print('RUNNING test_create_and_query', file=stderr)
        iterator = store.load_cypher_query(Qstr)
        rowcount = 0
        foundaddr1 = False
        foundaddr2 = False
        for row in iterator:
            rowcount += 1
            # fields are person, drone, nic and ipaddr
            self.assertEqual(row.person.firstname, 'Annika')
            self.assertEqual(row.person.lastname, 'Hansen')
            self.assertEqual(row.drone.designation, 'SevenOfNine'.lower())
            for role in ('host', 'Drone', 'Borg'):
                self.assertTrue(role in row.drone.roles)
            # print('>>>>>>>>>>>>>>>>>>ROW.NIC.IPADDR: %s' % row.ipaddr.ipaddr, file=stderr)
            # print('>>>>>>>>>>>>>>>>>>ROW.NIC.MACADDR: %s' % row.nic.MACaddr), file=stderr)
            # print('MAC1:', TestDatabaseWrites.mac1, file=stderr)
            # print('MAC2:', TestDatabaseWrites.mac2, file=stderr)
            if pyNetAddr(row.nic.MACaddr) == pyNetAddr(TestDatabaseWrites.mac1):
                self.assertEqual(pyNetAddr(row.ipaddr.ipaddr), pyNetAddr(TestDatabaseWrites.ip1))
                foundaddr1 = True
            else:
                self.assertEqual(pyNetAddr(row.ipaddr.ipaddr), pyNetAddr(TestDatabaseWrites.ip2))
                self.assertEqual(pyNetAddr(row.nic.MACaddr), pyNetAddr(TestDatabaseWrites.mac2))
                foundaddr2 = True
            # print('GOT A ROW: %s' % str(row), file=stderr)
        # print("ROWCOUNT = %s" % rowcount, file=stderr)
        self.assertEqual(rowcount, 2)
        self.assertTrue(foundaddr1)
        self.assertTrue(foundaddr2)
        FooClass.store.db_transaction.finish()


class TestSystemNode(TestCase):
    def test_systemnode_json(self):
        """Test that our SystemNode JSON "dict" works like it should"""
        from cmadb import CMAdb
        store = initstore()
        CMAdb.store = store
        # Store.debug = True
        designation="SystemNodeUno"
        sysnode = store.load_or_create(SystemNode, domain="global", designation=designation, roles=['Server', 'Switch'])
        sysnode['FunkyAttributeab'] = '''{"a": "b"}'''
        sysnode['FunkyAttributecd'] = '''{"c": "d"}'''
        store.commit()
        Store.debug = False
        sysnode = None
        # print("COMMIT done", file=stderr)
        query_string='''MATCH(sys:Class_SystemNode) WHERE sys.nodetype='SystemNode' AND sys.designation=toLower({desig}) RETURN sys'''
        qnode = store.load_cypher_node(query_string, params={'desig': designation})
        assert qnode is not None
        # print("Qnode: %s" % (qnode.__dict__.keys()))
        # print(qnode.keys())
        assert str(qnode['FunkyAttributeab']) == '''{"a":"b"}'''
        assert str(qnode['FunkyAttributecd']) == '''{"c":"d"}'''
        # print('JSONMAP NODE CLASS attributes: %s' % JSONMapNode.__dict__)



# Other things that ought to have tests:
#   node deletion
#   Searching for nodes we just added (I forgot which ones work that way)
#   Filtered queries - note that fields have to be filtered out in the JSON
#   they can't be reliably filtered out of the nodes
#   other things?
 
if __name__ == "__main__":
    import inspect
    test_count = 0
    test_classes = []
    for name, obj in dict(globals()).viewitems():
        if inspect.isclass(obj) and name.startswith('Test'):
            test_classes.append((name, obj))
    test_classes.sort()
    for name, cls in test_classes:
        obj = cls()
        if hasattr(cls, 'setup_method'):
            obj.setup_method()
        for item, fun in dict(cls.__dict__).viewitems():
            if item.lower().startswith('test_') and callable(fun):
                print('===================RUNNING TEST %s.%s' % (name, item), file=stderr)
                # print('====================RUNNING TEST %s.%s' % (name, item))
                fun(obj)
                test_count += 1
        if hasattr(cls, 'teardown_method'):
            obj.teardown_method(name)
    print('Completed %d tests.' % test_count)
