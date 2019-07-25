#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100 fileencoding=utf-8
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
""" This module defines the classes for most of our CMA nodes ...  """
# Pylint is nuts here...
# pylint: disable=C0411
from __future__ import print_function
import re
import time
import hashlib
import netaddr
import socket
import inject
from sys import stderr
import uuid
from consts import CMAconsts
from store import Store
from cmadb import CMAdb
from AssimCtypes import ADDR_FAMILY_IPV4, ADDR_FAMILY_IPV6, ADDR_FAMILY_802
from AssimCclasses import pyNetAddr, pyConfigContext
from store_association import StoreAssociation


def nodeconstructor(**properties):
    """
    A generic class-like constructor that knows our class name is stored as nodetype
    It's a form of "factory" for our database classes
    """
    # print('Calling nodeconstructor with properties: %s' % (str(properties)), file=stderr)
    realcls = GraphNode.classmap[str(properties["nodetype"])]
    # callconstructor is kinda cool - it figures out how to correctly call the constructor
    # with the values in 'properties' as arguments
    return Store.callconstructor(realcls, properties)


def registergraphclass(classtoregister):
    """
    Register the given class as being a Graph class so we can
    map the class name to the class object.
    This is intended to be used as a decorator.
    """
    GraphNode.classmap[classtoregister.__name__] = classtoregister
    return classtoregister


class GraphNode(object):
    """
    GraphNode is the base class for all our 'normal' graph nodes.
    """

    REESC = re.compile(r"\\")
    REQUOTE = re.compile(r'"')
    classmap = {}

    @staticmethod
    def register(classtoregister):
        """

        :param classtoregister:
        :return:
        """
        return registergraphclass(classtoregister)

    @staticmethod
    def factory(**kwargs):
        """
        A factory "constructor" function - acts like a universal constructor for GraphNode types
        """
        return nodeconstructor(**kwargs)

    @staticmethod
    def clean_graphnodes():
        """
        Invalidate any persistent objects that might become invalid when resetting the database
        """
        pass

    @staticmethod
    def str_to_class(class_name):
        """
        Return the class corresponding to this class name
        :param class_name: str: class name
        :return: cls
        """
        return GraphNode.classmap[str(class_name)]

    @staticmethod
    def node_to_class(neo_node):
        """
        Return the class that corresponds to this Py2neo Neo4j Node object

        :param neo_node: py2neo.Neo4j.node
        :return:
        """
        return GraphNode.str_to_class(str(neo_node["nodetype"]))

    @inject.params(store="Store", log="logging.Logger")
    def __init__(self, domain, time_create_ms=None, time_create_iso8601=None, store=None, log=None):
        """Abstract Graph node base class"""
        self.domain = domain
        self.nodetype = self.__class__.__name__
        self._baseinitfinished = False
        self._store = store
        self._log = log
        if time_create_ms is None:
            time_create_ms = int(round(time.time() * 1000))
        if time_create_iso8601 is None:
            time_create_iso8601 = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        self.time_create_iso8601 = time_create_iso8601
        self.time_create_ms = time_create_ms
        association = StoreAssociation(self, store=store)
        association.dirty_attrs = set()
        self._association = association
        store._audit_weaknodes_clients()

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

        if not hasattr(self, "_association") or self._association is None:
            object.__setattr__(self, name, value)
            return
        if name in ("node_id", "dirty_attrs"):
            raise (ValueError("Bad attribute name: %s" % name))
        if not name.startswith("_") and name != "association":
            try:
                if getattr(self, name) == value:
                    # print('Value of %s already set to %s' % (name, value), file=stderr)
                    return
            except AttributeError:
                pass
            if self.association.store.readonly:
                print("Caught Read-Only %s being set to %s!" % (name, value), file=stderr)
                raise RuntimeError("Attempt to set attribute %s using a read-only store" % name)
            if hasattr(value, "__iter__") and len(value) == 0:
                raise ValueError(
                    "Attempt to set attribute %s to empty array (Neo4j limitation)" % name
                )
            self.association.dirty_attrs.add(name)
        # print('SETTING %s to %s' % (name, value), file=stderr)
        object.__setattr__(self, name, value)

    @classmethod
    def meta_key_attributes(cls):
        """Return our key attributes in order of significance"""
        raise NotImplementedError(
            "Abstract base class method meta_key_attributes for %s" % cls.__name__
        )

    @classmethod
    def meta_labels(cls):
        """Return the default set of labels which should be put on our objects when created"""
        classes = [cls]
        classes.extend(cls.__bases__)
        labels = []
        for c in classes:
            name = c.__name__
            if name == "GraphNode":
                break
            labels.append("Class_" + name)
        return labels

    @staticmethod
    def cypher_all_label_indexes():
        """
        Create all the label indexes that seem good to make ;-)
        This includes a composite index over all key components and an
        index on each field that's part of that key

        :return:str: Cypher commands to create indexes
        """
        result = ""
        for classname, cls in GraphNode.classmap.viewitems():
            class_label = "Class_" + classname
            key_attrs = cls.meta_key_attributes()
            for attr in key_attrs:
                result += "CREATE INDEX ON :%s(%s)\n" % (class_label, attr)
            if len(key_attrs) > 1:
                result += "CREATE INDEX ON :%s(%s)\n" % (key_attrs, ":".join(key_attrs))
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
        result = ""
        for classname, cls in GraphNode.classmap.viewitems():
            class_label = "Class_" + classname
            key_attrs = cls.meta_key_attributes()
            if use_enterprise_features:
                for attr in key_attrs:
                    result += "CREATE CONSTRAINT ON (n:%s) ASSERT EXISTS(n.%s)\n" % (
                        class_label,
                        attr,
                    )
            if len(key_attrs) == 1:
                result += "CREATE CONSTRAINT ON (n:%s) ASSERT (n.%s) IS UNIQUE\n" % (
                    class_label,
                    key_attrs[0],
                )
            elif use_enterprise_features:
                result += "CREATE CONSTRAINT ON (n.%s) ASSERT (n.%s) IS NODE KEY\n" % (
                    class_label,
                    ", n.".join(key_attrs),
                )
        return result

    def post_db_init(self):
        """Set node creation time"""
        if not self._baseinitfinished:
            self._baseinitfinished = True
            self.association.store.add_labels(self, self.meta_labels())

    def update_attributes(self, other):
        """Update our attributes from another node of the same type"""
        if other.nodetype != self.nodetype:
            raise ValueError(
                "Cannot update attributes from incompatible nodes (%s vs %s)"
                % (self.nodetype, other.nodetype)
            )
        for attr in other.__dict__.keys():
            if not hasattr(self, attr) or getattr(self, attr) != getattr(other, attr):
                setattr(self, attr, getattr(other, attr))
        return self

    def __str__(self):
        """Default routine for printing GraphNodes"""
        result = "%s({" % self.__class__.__name__
        comma = ""
        for attr in Store.safe_attrs(self):
            result += "%s%s = %s" % (comma, attr, str(getattr(self, attr)))
            comma = ",\n    "
        result += '%sobject.__str__ =  "%s"' % (comma, object.__str__(self))
        node_id = self.association.node_id if self.association is not None else "None(0)"
        result += comma + "HasNode:%s" % node_id

        result += "\n})"
        return result

    # pylint R0911: Too many return statements
    # pylint: disable=R0911
    def get(self, attrstring, valueifnotfound=None):
        """Implement potentially deep attribute value lookups through JSON strings"""
        try:
            (prefix, suffix) = attrstring.split(".", 1)
        except ValueError:
            suffix = None
            prefix = attrstring
        if not hasattr(self, prefix):
            if not prefix.endswith("]"):
                return valueifnotfound
            else:
                # Probably an array index
                # Note that very similar code exists in AssimCclasses for pyConfigContext
                #   deepget member function
                allbutrbracket = prefix[0 : len(prefix) - 1]
                try:
                    (preprefix, idx) = allbutrbracket.split("[", 1)
                except ValueError:
                    return valueifnotfound
                if not hasattr(self, preprefix):
                    return valueifnotfound
                try:
                    arraypart = getattr(self, preprefix)
                    idx = int(idx)  # Possible ValueError
                    arrayvalue = arraypart[idx]  # possible IndexError or TypeError
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

    def json(self, includemap=None, excludemap=None):
        """Output this object according to JSON rules. We take advantage
        of the fact that Neo4j restricts what kind of objects we can
        have as Node properties.
        """

        attrstodump = []
        for attr in Store.safe_attrs(self):
            if includemap is not None and attr not in includemap:
                continue
            if excludemap is not None and attr in excludemap:
                continue
            attrstodump.append(attr)
        ret = "{"
        comma = ""
        attrstodump.sort()
        for attr in attrstodump:
            ret += '%s"%s": %s' % (comma, attr, GraphNode._json_elem(getattr(self, attr)))
            comma = ","
        ret += "}"
        return ret

    @staticmethod
    def _json_elem(value):
        """Return the value of an element suitable for JSON output"""
        if isinstance(value, str) or isinstance(value, unicode):
            return '"%s"' % GraphNode._json_escape(value)
        if isinstance(value, bool):
            if value:
                return "true"
            return "false"
        if isinstance(value, list) or isinstance(value, tuple):
            ret = "["
            comma = ""
            for elem in value:
                ret += "%s%s" % (comma, GraphNode._json_elem(elem))
                comma = ","
            ret += "]"
            return ret
        return str(value)

    @staticmethod
    def _json_escape(stringthing):
        """Escape this string according to JSON string escaping rules"""
        stringthing = GraphNode.REESC.sub(r"\\\\", stringthing)
        stringthing = GraphNode.REQUOTE.sub(r"\"", stringthing)
        return stringthing


def add_an_array_item(currarray, itemtoadd):
    """Function to add an item to an array of strings (like for roles)"""
    if currarray is not None and len(currarray) == 1 and currarray[0] == "":
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
    """Function to delete an item from an array of strings (like for roles)"""
    if isinstance(itemtodel, (tuple, list)):
        for item in itemtodel:
            currarray = delete_an_array_item(currarray, item)
        return currarray
    assert isinstance(itemtodel, (str, unicode))
    if itemtodel is not None and itemtodel in currarray:
        currarray = currarray.remove(itemtodel)
    if len(currarray) == 0:
        currarray = [""]  # Limitation of Neo4j
    return currarray


@registergraphclass
class BPRules(GraphNode):
    """Class defining best practice rules"""

    def __init__(self, bp_class, json, rulesetname):
        GraphNode.__init__(self, domain="metadata")
        self.bp_class = bp_class
        self.rulesetname = rulesetname
        self.json = json
        self._jsonobj = pyConfigContext(json)

    def jsonobj(self):
        """Return the JSON object corresponding to our rules"""
        return self._jsonobj

    @classmethod
    def meta_key_attributes(cls):
        """Return our key attributes in order of significance"""
        return ["bp_class", "rulesetname"]


@registergraphclass
class BPRuleSet(GraphNode):
    """Class defining best practice rule sets"""

    def __init__(self, rulesetname, basisrules=None):
        GraphNode.__init__(self, domain="metadata")
        self.rulesetname = rulesetname
        self.basisrules = basisrules
        if self.basisrules is None:
            return
        query = CMAconsts.QUERY_RULESET_RULES
        parent = CMAdb.store.load_cypher_node(query, BPRuleSet, params={"name": basisrules})
        CMAdb.store.relate_new(self, CMAconsts.REL_basedon, parent)

    @classmethod
    def meta_key_attributes(cls):
        """Return our key attributes in order of significance"""
        return ["rulesetname"]


@registergraphclass
class NICNode(GraphNode):
    """
    An object that represents a NIC - characterized by its MAC address
    We handily ignore the fact that a single NIC can have multiple MAC addresses...

    One of the problematic issues about NICs is that in fact, they can be duplicated.
    Theory says otherwise "mostly" but obvious examples are the loopback device and
    virtual NICs. There is no mechanism to insure that virtual NICs aren't duplicated
    within an enterprise. So the practical matter is that they can show up multiple times,
    and the same NIC can show up in mulitple contexts - confusing the issue.

    And what is the issue?  The issue is that we want each NIC (real or virtual) to appear exactly
    once in our database.

    There are currently three different contexts in which we might find a NIC:

        a)  It might be a NIC attached to one of our Drones. It might be real, or it might
            be virtual. It might have associated IP addresses, or it might not. If it has
            an IP address, which in turn is associated with a subnet.

        b)  It might be discovered by our ARP listeners. In this case, it might be real,
            or it could be virtual. But it always has an associated IP address, which
            has an associated subnet.

        c)  It might be a NIC attached to a switch which we've discovered - currently only by LLDP
            but it could eventually be through SNMP or other types of discovery. Most of these
            are real, but it's not obvious what some of them are (virtual spanned??).
            Some will have associated IP addresses, but most will not.

    The issue here is that some NICs discovered by (b) might also have been discovered previously
    by method (a) or (c). Conversely, some discovered by (a) or (c) might have previously been
    discovered by method (b).

    100% of the confusion comes from category (b). But in category (b) there is something
    interesting going on - the MACs have associated IPv4 IPs. There's a pretty simple query which
    will find any similar pairs in this particular domain - or for that matter in the
    entire database.

    But in cases (a) and (c) the NICs need to be owned by this particular SystemNode.
    Here's an algorithm that might work:
        for case (b) - always look for the IP/MAC pair (in this domain?)
                       if you find it, then that's your NIC/MAC.
                       if not, then create it.
                       You need something to ensure that this is unique.
                       So, use the subnet it's on to ensure uniqueness.
        for cases (a) and (c) if it exists - then you're done - return that NICNode
        If it doesn't exist and it doesn't have a non-local IP, then create it - you're done.
        If it doesn't exist but has an associated non-local IP, then you search for
        all the IPs associated with this MAC in your domain. If any of them match your IPs
        then return that NICNode.

    To make things a bit more complicated - it's possible for a given ethernet broadcast domain to
    cover multiple subnets. This only comes up for case (b).

    Do we need to represent broadcast domains as well as subnets?  How do we identify broadcast
    domains? How to name them?


    Either a NIC is associated with an IP address or a host.  NICs which aren't associated with
    either one can't be seen.

    IP addresses can either be associated with a subnet (like found through the 'ip' command)
    or they are associated with a network segment via an ARP.

    The key thing I still don't understand is how to name a network segment particularly before we
    know which subnets are associated with that network segment. We always know one of the subnets
    that's associated with it. And the set of subnets may change over time - especially if one
    or more of them was due to a mistake ;-)

    For the case where I'm doing a netconfig discovery:

    That data is organized by NICs. Each NIC is potentially its own network segment.

    When I'm processing an ARP packet, I can query the NICs for a network segment attribute, and
    assign that network segment to my NIC and all the other NICs I heard about in the ARP packet.
    If the query returns no NICs with an assigned network segment attribute, then I'll construct
    a network segment UUID - and use that for creating all the NICs.

    The question is how will I make sure I don't get a different NIC with the same MAC address?
    The only way to know for sure is if we can hear ARPs, and figure out which MACs go together.

    I think the bigger question is when I create a MAC address from the get-go from Drone
    discovery, whether that particular MAC address has been seen before...

    When creating a MAC address from netconfig, it should probably be enough to say "We found the
    same IP/MAC pair in the database for the same domain - if we did then that's ours.
    We may need to update the IP to have

    Conversely, when we hear IP/MACs

    We assume that IPs that we hear from in tcpdiscovery are global.

    There are two ways we discover MAC addresses:
    1) netconfig
    2) ARP caches

    IP addresses add one more way - tcpdiscovery

    The key thing seems to be that we can make mistakes here. There doesn't seem to be any
    perfect way to guarantee that we discover things and assign the correct network segments
    to them without accidentally merging them together, or having them be separate...

    Only in the presence of complete understanding of all the virtual plumbing and all the
    routing information can we really understand what is connected where. On systems where
    ARPs are filtered (like clouds), it becomes impossible to really know what's going on.
    On the other hand, in clouds, it's also possible to get insight into routing that might
    be more difficult than in a conventional architecture.

    So, we plunge ahead making the best guesses we can - when in fact we don't know as much
    as we'd like...

    """

    def __init__(self, domain, macaddr, scope, ifname=None, json=None, net_segment=None):
        """
        Construct a NICNode object from our parameters
        :param domain: str: domain of this object - which customer is it?
        :param macaddr: str: MAC address in one of the standard formats
        :param scope: str: the scope of this MAC address - part of its fully qualified name
        :param ifname: str: interface name if known
        :param json: str: JSON string from netconfig discovery
        :param net_segment: str: UUID of our network segment - or None
                                 We only know the network segment when we are dealing with ARP
                                 caches. It's None otherwise...
        """
        GraphNode.__init__(self, domain=domain)
        mac = pyNetAddr(macaddr)
        if mac is None or mac.addrtype() != ADDR_FAMILY_802:
            raise ValueError("Not a legal MAC address [%s]" % macaddr)
        self.macaddr = str(mac)
        self.ifname = ifname  # If it's none it doesn't go into the database...
        if json is not None:
            self.json = json
            self._json = pyConfigContext(json)
            for attr in (
                "carrier",
                "duplex",
                "MTU",
                "operstate",
                "speed",
                "virtual",
                "type" "bridge_id",
                "brport_bridge",
            ):
                if attr in self._json:
                    setattr(self, attr, self._json[attr])
        if not hasattr(self, "OUI"):
            oui = self.mac_to_oui(self.macaddr)
            if oui is not None:
                self.OUI = oui
        self.scope = scope
        self.net_segment = net_segment

    def set_net_segment(self, net_segment):
        """
        Set the network segment once we've discovered it...
        :param net_segment: str: network segment name (UUID)
        :return: None
        """
        self.net_segment = net_segment

    @staticmethod
    def find_this_macaddr(store, domain, macaddr, system=None, net_segment=None):
        """
        Locate this MAC address taking into account that it might not be unique...
        Please pass the related 'system' if known...

        :param store: Store: Our store
        :param domain: str: Domain for the NIC
        :param macaddr: str: MAC address
        :param system: SystemNode: The associated SystemNode if known
        :param net_segment: str or None: our network segment or None
        :return: NICNode or None
        """
        if system is None:
            query = "MATCH(nic:Class_NicNode) WHERE nic.domain = $domain and nic.macaddr = $macaddr"
        else:
            query = """
            MATCH(nic:Class_NicNode)-[:nicowner]->(system:Class_SystemNode)
            WHERE nic.domain = $domain and nic.macaddr = $macaddr AND ID(system) = $system_id
            """
        if net_segment is not None:
            query += " AND nic.net_segment = $net_segment"
        parameters = {
            "domain": domain,
            "macaddr": str(macaddr),
            "net_segment": str(net_segment),
            "system_id": system.association.node_id if system is not None else None,
        }
        query += " RETURN nic"
        mac = store.load_cypher_node(query, parameters)
        if mac or system is None:  # Can't improve our answer...
            return mac
        query = """
        MATCH(nic:Class_NicNode)
        WHERE nic.domain = $domain and nic.macaddr = $macaddr AND NOT (nic)-[:nicowner]->()
        """
        if net_segment is not None:
            query += " AND nic.net_segment = $net_segment"
        query += " RETURN nic"
        return store.load_cypher_node(query, parameters)

    @staticmethod
    def mac_to_oui(macaddr):
        """Convert a MAC address to an OUI organization string - or return None"""
        try:
            # Pylint is confused about the netaddr.EUI.oui.registration return result...
            # pylint: disable=E1101
            return str(netaddr.EUI(macaddr).oui.registration().org)
        except netaddr.NotRegisteredError:
            prefix = str(macaddr)[0:8]
            return CMAdb.config["OUI"][prefix] if prefix in CMAdb.config["OUI"] else None

    @classmethod
    def meta_key_attributes(cls):
        """
        Return our key attributes in decreasing order of significance
        :return:  [str]
        """
        return ["macaddr", "scope", "domain"]

    def post_db_init(self):
        """Set up the labels on the graph"""
        GraphNode.post_db_init(self)


@registergraphclass
class IPaddrNode(GraphNode):
    """An object that represents a v4 or v6 IP address without a port - characterized by its
    IP address. They are always represented in the database in ipv6 format.
    It is must be unique within the 'subnet' passed as a parameter
    """

    StoreHostNames = True

    def __init__(self, ipaddr, domain, subnet):
        """
        Construct an IPaddrNode - validating our parameters

        :param ipaddr: Union(str, pyIPaddr): the IP address for this node
        :param subnet: Subnet: The subnet this IP address is on...
        """
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
                raise ValueError(
                    "Invalid network address type for IPaddrNode constructor: %s" % str(ipaddrout)
                )
            ipaddrout.setport(0)
        else:
            raise ValueError(
                "Invalid address type for IPaddrNode constructor: %s type(%s)"
                % (str(ipaddr), type(ipaddr))
            )
        # self.ipaddr = unicode(str(ipaddrout))
        self.ipaddr = str(ipaddrout)
        self._ipaddr = ipaddrout
        if subnet is not None:
            if not isinstance(subnet, (str, unicode)):
                if not subnet.belongs_on_this_subnet(ipaddrout):
                    raise ValueError(
                        "IP address %s does not belong on subnet %s" % (ipaddrout, subnet)
                    )
                subnet = subnet.name
        self.subnet = subnet

        if IPaddrNode.StoreHostNames and not hasattr(self, "hostname"):
            ip = repr(pyNetAddr(ipaddr))
            try:
                self.hostname = socket.gethostbyaddr(ip)[0]
            except socket.herror:
                pass

    @classmethod
    def meta_key_attributes(cls):
        """
        Return our key attributes in order of significance
        Not sure what it means to have an optional value listed as a potential key value
        :return: [str]
        """
        return ["ipaddr", "subnet", "domain"]

    def post_db_init(self):
        """Set up the labels on the graph"""
        GraphNode.post_db_init(self)
        # print >> stderr, ('POST_DB_INIT: Adding labels: %s' % Subnet.name_to_label(self.subnet))
        self.association.store.add_labels(self, (Subnet.name_to_label(self.subnet),))


SUBNET_GLOBAL = "_GLOBAL_"


@registergraphclass
class Subnet(GraphNode):
    """
    A class representing a subnet

    A key feature that's a bit hard to deal with here is that we need to give it a
    unique name. Ideally one that's generated from the things we know...

    As it stands, there's a chance that we will connect several different NICs on the
    same subnet with different subnets. We would need to repair that later if we do.
    Or is it better to consider them as being globally unique, and splitting them out later
    once (and if) we figure out which network segments they're part of...

    On the other hand, a reasonable approach might be to call anything on a virtual NIC as
    a local subnet, and anything on a real NIC as global...
    Three cases for context:
        real NIC: None
        bridge: host:bridge
        virtual NIC attached to a bridge: host:bridge
        other virtual: host:ifname
    If it's a bridge, then it should be the host+bridge name

    """

    def __init__(self, domain, ipaddr, cidrmask=None, context=SUBNET_GLOBAL, net_segment=None):
        """
        A class defining a subnet. Like every other part of the system, we really only
        believe in IPv6 addresses. We convert IPV4 to IPv6

        :param domain: Domain of this Subnet
        :param ipaddr: pyNetAddr or str: either IPv4 or IPv6 format
        :param cidrmask: int: subnet mask in CIDR format (just a single int)
                         If ipaddr is a string and contains a /, the part after the '
                         is considered to be the 'cidrmask'
        :param context: str: Further context system name, etc.
        """
        GraphNode.__init__(self, domain=domain)
        self._ipaddr, self.cidrmask = self.str_to_ip_cidr(ipaddr, cidrmask)
        self.ipaddr = str(self._ipaddr)
        self.domain = domain
        self.context = context
        self.net_segment = net_segment
        self.name = str(self)
        if self.cidrmask > 128:
            raise ValueError("Illigal CIDR mask")
        # print('Subnet(domain=%s, ipaddr=%s, cidrmask=%s, context=%s, net_segment=%s) => %s'
        #       % (domain, ipaddr, cidrmask, context, net_segment, str(self)), file=stderr)
        assert context is None or isinstance(context, (str, unicode))
        assert not str(self).startswith("::/")

    @staticmethod
    def str_to_ip_cidr(ipaddr, cidrmask):
        """
        Convert a string to a subnet with CIDR-style mask (bit count)
        :param ipaddr:
        :param cidrmask:
        :return:
        """
        if isinstance(ipaddr, str) and "/" in ipaddr:
            ipaddr, cidrmask = ipaddr.split("/", 1)
        ipaddr = pyNetAddr(str(ipaddr))
        ipaddr.setport(0)
        try:
            cidrmask = int(cidrmask)
            if ipaddr.addrtype() == ADDR_FAMILY_IPV4:
                ipaddr = ipaddr.toIPv6()
                cidrmask += 96  # a.k.a. 128-32
        except ValueError:
            # Maybe it's an old-style IPv4 netmask??
            cidrmask = Subnet.v4_netmask_to_cidr(cidrmask)
            ipaddr = ipaddr.toIPv6()
            cidrmask += 96  # a.k.a. 128-32
        ipaddr.and_with_cidr(cidrmask)
        return ipaddr, cidrmask

    @property
    def base_address(self):
        """
        Return the base address as a pyNetAddr
        :return: pyNetAddr
        """
        return self._ipaddr

    @staticmethod
    def v4_netmask_to_cidr(mask):
        """
        Convert a old-style IPV4 netmask to CIDR notation (e.g., '255.255.255.0' => 24)
        :param mask: str: old-style netmask
        :return: int: CIDR integer equivalent
        """
        powers = {255: 8, 254: 7, 252: 6, 248: 5, 240: 4, 224: 3, 192: 2, 128: 1, 0: 0}
        bit_count = 0
        elems = [elem for elem in mask.split(".")]
        if len(elems) != 4:
            raise ValueError("Invalid old-style netmask [%s]" % mask)
        elem = None
        try:
            for elem in elems:
                bit_count += powers[int(elem)]
        except (KeyError, ValueError):
            raise ValueError("Invalid element [%s] in old-style netmask [%s]" % (elem, mask))
        return bit_count

    def __str__(self):
        return "%s/%d_%s_%s" % (self.ipaddr, self.cidrmask, self.domain, self.context)

    @property
    def subnet_label(self):
        """
        For IP addresses things are associated with this subnet, label them with this label.
        :return: str: subnet label
        """
        return self.name_to_label(str(self))

    @staticmethod
    def name_to_label(name):
        """
        Convert this subnet name to a subnet label
        :param name: str: subnet name
        :return: str: subnet label
        """
        return "Subnet_" + str(name).replace(".", "_").replace(":", "_").replace("-", "_").replace(
            "/", "_"
        )

    @staticmethod
    def find_matching_subnets(store, domain, ipaddr, contexts):
        """
        Yield each matching subnet in turn. Might be zero or one - could be more
        This is slow if you have lots of subnets to search
        :param store: Store: store to search
        :param domain: str: domain to search - could be None
        :param ipaddr: str: IP address
        :param contexts: [str] or None: Contexts that interest us - or None
        :return: generator(Subnet)
        """
        query = "MATCH(subnet:Class_Subnet) WHERE "
        if domain is not None:
            query += "subnet.domain = $domain "
        if contexts is not None:
            if domain is not None:
                query += "AND "
            query += "subnet.context in $contexts "
        query += "RETURN subnet"

        for subnet in store.load_cypher_nodes(query, {"domain": domain, "contexts": contexts}):
            if subnet.belongs_on_this_subnet(ipaddr):
                yield subnet

    @staticmethod
    def normalize_subnet_set(subnet_set):
        """
        Groom out duplicate subnets - choosing which ones we're going to keep if there are
        duplicates or overlaps. We remove ones that seem redundant.
        Although this is an N^2 operation, normally there is only one element in the set
        and in the worst cases, only a handful...
        :param subnet_set: set(Subnet)
        :return: set(Subnet)
        """
        subnets = [s for s in subnet_set]
        removed = set()
        # pylint: disable=C0200
        for j, subnet in enumerate(subnets):
            if j in removed:
                continue
            subnet = subnets[j]
            for k in range(j + 1, len(subnets)):
                if k in removed:
                    continue
                other = subnets[k]
                if subnet.equivalent(other):
                    if subnet.context != SUBNET_GLOBAL and other.context == SUBNET_GLOBAL:
                        removed.add(j)
                        subnet_set.remove(subnet)
                    else:
                        removed.add(k)
                        subnet_set.remove(other)
                # These last two really shouldn't happen...
                # They are indicative of a network misconfiguration
                elif subnet.subsumes(other):
                    removed.add(k)
                    subnet_set.remove(other)
                elif other.subsumes(subnet):
                    removed.add(j)
                    subnet_set.remove(subnet)

    def members(self, cls=None):
        """
        Return the objects that are associated with this subnet
        :param cls: ClassType: Desired class of associated objects = or None for any
        :return: Generator(GraphNode): Generator yielding the desired objects
        """
        if cls is not None:
            query = "MATCH (n:%s:Class_%s) RETURN n" % (self.subnet_label, cls.__name__)
        else:
            query = "MATCH (n:%s) RETURN n" % self.subnet_label
        return self.association.store.load_cypher_nodes(query)

    @staticmethod
    def find_subnet_by_name(store, subnet_name):
        """
        Locate the subnet with the given name.

        :param store: Store: our Store object
        :param subnet_name: str: subnet name
        :return: Subnet: the desired subnet -- or None
        """
        query = "MATCH (n:Class_Subnet) WHERE n.name = $name RETURN n"
        return store.load_cypher_node(query, {"name": subnet_name})

    @staticmethod
    def find_matching_subnet(ip, subnets):
        """
        Find a matching subnet from the iterable 'subnets'
        :param ip: str: IP in IPv6 format
        :param subnets: iterable(Subnet): list of subnets
        :return: Subnet or None
        """
        for subnet in subnets:
            if subnet is not None and subnet.belongs_on_this_subnet(ip):
                return subnet
        return None

    @staticmethod
    def find_subnet(store, ipaddr, cidrmask, domain, context="_GLOBAL_", net_segment=None):
        """
        Find this subnet based on some combination of the parameters
        :param store: Store; the Store to use to find the subnet
        :param ipaddr: str: Base IP address, possibly with '/' notation for the CIDR mask
        :param cidrmask: int: CIDR mask (ipv6) - overriddeden by ipaddr if it has a /
        :param domain: str: domain
        :param context: str: context (if known)
        :param net_segment: network segment (if known)
        :return: Subnet: or None
        """
        ipaddr, cidrmask = Subnet.str_to_ip_cidr(ipaddr, cidrmask)
        query = """
        MATCH (n:Class_Subnet) WHERE n.ipaddr = $ipaddr AND n.cidrmask = $cidrmask
        AND n.domain = $domain
        """
        if context is not None:
            query += " AND n.context = $context"
        if net_segment is not None:
            query += " AND n.net_segment = $net_segment"
        parameters = {
            "cidrmask": int(cidrmask),
            "context": context,
            "domain": domain,
            "ipaddr": str(ipaddr),
            "net_segment": net_segment,
        }
        query += " RETURN n"
        return store.load_cypher_node(query, parameters)

    def belongs_on_this_subnet(self, ipaddr):
        """
        Return True if this IP address belongs on this subnet...
        :param ipaddr: pyNetAddr: Address to test
        :return: True or False
        """
        if isinstance(ipaddr, IPaddrNode):
            ipaddr = ipaddr._ipaddr
        elif isinstance(ipaddr, pyNetAddr):
            pass
        else:
            ipaddr = pyNetAddr(str(ipaddr))
        base_ip = ipaddr.and_with_cidr(self.cidrmask)
        # print("Comparing subnet %s IPaddr %s anded with %s [%s]"
        #       % (self._ipaddr, ipaddr, self.cidrmask, base_ip), file=stderr)
        return base_ip == self._ipaddr

    def __eq__(self, other):
        """
        Equal operation between two Subnet objects
        :param other: Subnet: The other subnet
        :return: bool: what you'd expect...
        """
        return self.name == other.name if isinstance(other, Subnet) else False

    def equivalent(self, other):
        """
        Return True if these two subnets are equivalent
        :param other: Subnet
        :return: bool: True if the two subnets are equivalent
        """
        return self.base_address == other.base_address and self.cidrmask == other.cidrmask

    def subsumes(self, other):
        """
        Return True if our subnet subsumes (includes) the other subnet
        :param other: Subnet: other subnet to compare
        :return: bool: True if the this subnet subsumes the other subnet
        """
        return self.belongs_on_this_subnet(other.base_address) and (self.cidrmask <= other.cidrmask)

    @classmethod
    def meta_key_attributes(cls):
        """
        Return our key attributes in order of significance
        Everything else is redundant with respect to name
        Do I need the others indexed too?
        """
        return ["name", "context", "ipaddr", "cidrmask", "domain", "net_segment"]


@registergraphclass
class NetworkSegment(GraphNode):
    """
    A Class to represent a network segment.
    Network segments are tricky. Although they are associated with
     a collection of Subnets (usually one), they have no natural naming conventions
     and no natural names. So we generate a name for each one with a UUID.
    """

    def __init__(self, domain, name=None):

        GraphNode.__init__(self, domain=domain)
        if name is None:
            name = str(uuid.uuid4())
        self.name = name

    def __str__(self):
        return "%s::%s" % (self.domain, self.name)

    @staticmethod
    def guess_net_segment(store, domain, ip_mac_pairs, fraction=0.5):
        """
        Determine (guess) the network segment for this NICNode if we can figure it out...
        The theory behind this is that the same combination of IP:MAC pairs only exists
        in this one network segment. This is not guaranteed, and in fact, may happen
        quite a bit for the case of local container or VM networks

        The most reliable use of this algorithm would be when looking at ARP discovery
        output. It could be used for a single IP/MAC pair as well - but not as reliably...

        :param store: Store: store to query
        :param domain: str: Domain
        :param ip_mac_pairs: [(str,str)]: list of (MAC, ip) tuples
        :param fraction: What % of ip_mac_pairs must be matched?
        :return: str: matching net segment name or None
        """
        if len(ip_mac_pairs) < 1:
            return None
        mac_addrs = list({str(each[0]) for each in ip_mac_pairs})
        ip_addrs = list({str(each[1]) for each in ip_mac_pairs})

        query = """
        MATCH (ip:Class_IPaddrNode)-[:ipowner]->(mac:Class_NICNode)
        WHERE ip.ipaddr in $ip_addrs AND mac.macaddr in $mac_addrs
        AND ip.domain = $domain AND mac.domain = $domain
        AND mac.net_segment IS NOT NULL
        RETURN ip.ipaddr as ipaddr, mac.macaddr as macaddr, mac.net_segment as net_segment
        """
        #
        # The return result is not guaranteed to be what we're looking for,
        # but it's likely to be the one we're looking for.
        # Let's go after the best match.
        #
        possible_segments = {}
        parameters = {"domain": domain, "mac_addrs": mac_addrs, "ip_addrs": ip_addrs}
        for row in store.load_cypher_query(query, params=parameters):
            pair = (row.macaddr, row.ipaddr)
            segment = row.net_segment
            if segment not in possible_segments:
                possible_segments[segment] = 0
            if pair in ip_mac_pairs:
                possible_segments[segment] += 1
            else:
                possible_segments[segment] -= 1
        # Now we have a count of how many times we have a good match minus how many
        # we had a mismatch on... We'll take the segment with the highest positive count...
        max_count = 0
        best_segment = None
        for segment, count in possible_segments.viewitems():
            if count > max_count:
                best_segment = segment
                max_count = count
        return best_segment if max_count >= int((len(ip_mac_pairs) * fraction) + 0.5) else None

    @classmethod
    def meta_key_attributes(cls):
        """
        Return our key attributes in order of significance
        Domain is redundant with respect to name
        """
        return ["name"]


@registergraphclass
class IPtcpportNode(GraphNode):
    """An object that represents an IP:port combination characterized by the pair"""

    def __init__(self, domain, ipaddr, port=None, protocol="tcp"):
        """Construct an IPtcpportNode - validating our parameters"""
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
                raise ValueError("Invalid port for constructor: %s" % str(port))
            addrtype = ipaddr.addrtype()
            if addrtype == ADDR_FAMILY_IPV4:
                ipaddr = ipaddr.toIPv6()
            elif addrtype != ADDR_FAMILY_IPV6:
                raise ValueError(
                    "Invalid network address type [%s] for constructor: %s"
                    % (addrtype, str(ipaddr))
                )
            ipaddr.setport(0)
        else:
            raise ValueError(
                "Invalid initial value for IPtcpportNode constructor: %s type(%s)"
                % (str(ipaddr), type(ipaddr))
            )
        # self.ipaddr = unicode(str(ipaddr))
        self.ipaddr = str(ipaddr)
        self.port = port
        self.protocol = protocol
        self.ipport = self.format_ipport()

    @classmethod
    def meta_key_attributes(cls):
        """Return our key attributes in order of significance"""
        return ["ipport", "domain"]

    def format_ipport(self):
        """
        Format the ip and port into our key field
        Note that we make the port the most significant part of the key - which
        should allow some more interesting queries.
        """
        return "%s_%s_%s" % (self.port, self.protocol, self.ipaddr)


@registergraphclass
class ProcessNode(GraphNode):
    """A node representing a running process in a host"""

    # R0913: Too many arguments (9/7)
    # pylint: disable=R0913
    def __init__(
        self,
        domain,
        processname,
        host,
        pathname,
        argv,
        uid,
        gid,
        cwd,
        roles=None,
        is_monitored=False,
    ):
        GraphNode.__init__(self, domain=domain)
        self.host = host
        self.pathname = pathname
        self.argv = argv
        self.uid = uid
        self.gid = gid
        self.cwd = cwd
        self.is_monitored = is_monitored
        if roles is None:
            self.roles = [""]
        else:
            self.roles = None
            self.addrole(roles)
        # self.processname='%s|%s|%s|%s:%s|%s' \
        # %       (path.basename(pathname), path.dirname(pathname), host, uid, gid, str(argv))
        # procstring = '%s|%s|%s:%s|%s' \
        # %       (str(path.dirname(pathname)), str(host), str(uid), str(gid), str(argv))
        # hashsum = hashlib.sha1()
        # E1101: Instance of 'sha1' has no 'update' member (but it does!)
        # pylint: disable=E1101
        # hashsum.update(procstring)
        # self.processname = '%s::%s' % (path.basename(pathname), hashsum.hexdigest())
        self.processname = processname

    def addrole(self, roles):
        """Add a role to our ProcessNode"""
        self.roles = add_an_array_item(self.roles, roles)
        # Make sure the Processnode 'roles' attribute gets marked as dirty...
        self.association.dirty_attrs.add("roles")
        self.association.store.add_labels(
            self, ["Role_%s" % role for role in roles if role not in self.roles]
        )
        return self.roles

    def delrole(self, roles):
        """Delete a role from our ProcessNode"""
        self.roles = delete_an_array_item(self.roles, roles)
        # Mark our Processnode 'roles' attribute dirty...
        self.association.dirty_attrs.add("roles")
        self.association.store.delete_labels(
            self, ["Role_%s" % role for role in roles if role in self.roles]
        )
        return self.roles

    @classmethod
    def meta_key_attributes(cls):
        """Return our key attributes in order of significance"""
        return ["processname", "domain"]


@registergraphclass
class JSONMapNode(GraphNode):
    """A node representing a map object encoded as a JSON string
    This has everything to do with performance in Neo4j.
    They don't support maps, and they do a poor (*very* slow) job of supporting large strings.
    These used to be stored in the Drone nodes themselves, but that meant that every time
    a Drone was transferred to the python code, it transferred *all* of its attributes,
    which means transferring lots and lots of very slow and rarely needed string data.

    Although these are transmitted in UDP packets, they are compressed, and JSON compresses very
    well, and in some cases extremely well. I've actually seen 3M of (unusually verbose)
    JSON discovery data compress down to less than 40K of binary.
    XML blobs are typically more compressible than the average JSON blob.

    Nowadays we are storing the undelying JSON in a separate storage method - outside of Neo4j
    Too bad we can't store it effectively in Neo4j at the moment :-(
    """

    JSONTYPE_FIELD = "discovertype"

    @inject.params(persistentjson="PersistentJSON")
    def __init__(self, json=None, jhash=None, is_current=True, jsontype=None, persistentjson=None):
        """
        Constructor for JSONMapNode:

        :param json: str: JSON from this object
        :param jhash: str: Hash value associated with this json string
        :param jsontype: str: Type of JSON being stored [Value of JSONTYPE_FIELD in the JSON]
        :param persistentjson: Object to store big JSON strings
        """
        if persistentjson is None or isinstance(persistentjson, str):
            raise ValueError("Invariant storage object must be specified.")
        if json is None and (jhash is None or jsontype is None):
            raise ValueError("json and jhash can't both be None.")
        GraphNode.__init__(self, domain="metadata")

        if json is None:
            self._map = pyConfigContext(persistentjson.get(jsontype, jhash))
        else:
            self._map = pyConfigContext(json)
            jsontype = self._map.get(self.JSONTYPE_FIELD, "unknowntype")
        json = str(self._map)
        # We use sha224 to keep the length under 60 characters (56 to be specific)
        # This is a performance consideration for Neo4j
        # We might run into duplicates as we get somewhere near 2^112 different JSON values
        # Not a highly likely event ;-) - it's somewhere in the range of 10^33 or so...
        #
        # The reason for needing to know which type of JSON we have is because each type
        # has different indexing needs. So, once we start indexing on the JSON, then we'll
        # need to know what to index on...
        #
        if jhash is None:
            jhash = self.strhash(json)
        self.jhash = jhash
        self.jsontype = jsontype
        self.is_current = is_current
        if (jsontype, jhash) not in persistentjson:
            persistentjson.put(jsontype, jhash, json)

    @staticmethod
    def strhash(string):
        """Return our canonical hash value (< 60 chars long)"""
        return hashlib.sha224(string).hexdigest()

    def __str__(self):
        """Convert to string - returning the JSON string itself"""
        return str(self._map)

    def hash(self):
        """Return the (sha224) hash of this JSON string"""
        return self.jhash

    def map(self):
        """Return the map (pyConfigContext) that corresponds to our JSON string"""
        return self._map

    def keys(self):
        """Return the keys that go with our map"""
        return self.map().keys()

    def get(self, key, alternative=None):
        """Return value if object contains the given *structured* key - 'alternative' if not."""
        return self.map().deepget(key, alternative)

    def deepget(self, key, alternative=None):
        """Return value if object contains the given *structured* key - 'alternative' if not."""
        return self.map().deepget(key, alternative)

    def __getitem__(self, key):
        return self.map()[key]

    def __iter__(self):
        """Iterate over self.keys() - giving the names of all our *top level* attributes."""
        for key in self.keys():
            yield key

    def __contains__(self, key):
        return key in self.map()

    def __len__(self):
        return len(self.map())

    @classmethod
    def meta_key_attributes(cls):
        """Return our key attributes in order of significance"""
        return ["jhash"]


# pylint  R0903: too few public methods. Not appropriate here...
# pylint: disable=R0903
class NeoRelationship(object):
    """Our encapsulation of a Neo4j Relationship - good for displaying them """

    def __init__(self, relationship):
        """
        Constructor for our Relationship proxy
        Relationship should be a neo4j.Relationship
        """
        self._relationship = relationship
        self._id = getattr(relationship, "_id")  # Make pylint happy...
        self.type = relationship.type
        self.start_node = getattr(relationship.start_node, "_id")  # Make pylint happy...
        self.end_node = getattr(relationship.end_node, "_id")  # Make pylint happy...
        self.properties = dict(relationship)
