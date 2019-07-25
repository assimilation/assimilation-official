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
"""
We implement the Drone class - which implements all the properties of
drones as a Python class.
"""
from __future__ import print_function
import time, sys

# import os, traceback
from cmadb import CMAdb
from consts import CMAconsts
from graphnodes import registergraphclass
from systemnode import SystemNode
from frameinfo import FrameSetTypes, FrameTypes
from AssimCclasses import pyNetAddr, DEFAULT_FSP_QID, pyCryptFrame
from assimevent import AssimEvent
from cmaconfig import ConfigFile


# droneinfo.py:39: [R0904:Drone] Too many public methods (21/20)
# droneinfo.py:39: [R0902:Drone] Too many instance attributes (11/10)
# pylint: disable=R0904,R0902
@registergraphclass
class Drone(SystemNode):
    """Everything about Drones - endpoints that run our nanoprobes.

    There are two Cypher queries that get initialized later:
    Drone.IPownerquery_1: Given an IP address, return th SystemNode (probably Drone) 'owning' it.
    Drone.OwnedIPsQuery:  Given a Drone object, return all the IPaddrNodes that it 'owns'
    """

    IPownerquery_1 = None
    OwnedIPsQuery = None
    IPownerquery_1_txt = """MATCH (n:Class_IPaddrNode)<-[:%s]-()<-[:%s]-(drone)
                            WHERE n.ipaddr = $ipaddr AND n.domain = $domain
                            RETURN drone LIMIT 1"""
    OwnedIPsQuery_txt = """MATCH (d:Class_Drone)-[:%s]->()-[:%s]->(ip:Class_IPaddrNode)
                           WHERE ID(d) = $droneid
                           return ip"""

    # R0913: Too many arguments to __init__()
    # pylint: disable=R0913
    def __init__(
        self,
        designation,
        port=None,
        startaddr=None,
        primary_ip_addr=None,
        domain=CMAconsts.globaldomain,
        status="(unknown)",
        reason="(initialization)",
        roles=None,
        key_id="",
    ):
        """Initialization function for the Drone class.
        We mainly initialize a few attributes from parameters as noted above...

        The first time around we also initialize a couple of class-wide query
        strings for a few queries we know we'll need later.

        We also behave as though we're a dict from the perspective of JSON attributes.
        These discovery strings are converted into pyConfigContext objects and are
        then searchable like dicts themselves - however updating these dicts has
        no direct impact on the underlying JSON strings stored in the database.

        The reason for treating these as a dict is so we can easily change
        the implementation to put JSON strings in separate nodes, or perhaps
        eventually in a separate data store.

        This is necessary because the performance of putting lots of really large
        strings in Neo4j is absolutely horrible. Putting large strings in is dumb
        and what Neo4j does with them is even dumber...
        The result is at least DUMB^2 -not 2*DUMB ;-)
        """
        SystemNode.__init__(self, domain=domain, designation=designation)
        if roles is None:
            roles = ["host", "drone"]
        self.addrole(roles)
        self._io = CMAdb.io
        self.lastjoin = "None"
        self._active_nic_count = None
        self.status = status
        self.reason = reason
        self.key_id = key_id
        self.startaddr = str(startaddr)
        self.primary_ip_addr = str(primary_ip_addr)
        self.time_status_ms = int(round(time.time() * 1000))
        self.time_status_iso8601 = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        if port is not None:
            self.port = int(port)
        else:
            self.port = None

        if Drone.IPownerquery_1 is None:
            Drone.IPownerquery_1 = Drone.IPownerquery_1_txt % (
                CMAconsts.REL_ipowner,
                CMAconsts.REL_nicowner,
            )
            Drone.OwnedIPsQuery_subtxt = Drone.OwnedIPsQuery_txt % (
                CMAconsts.REL_nicowner,
                CMAconsts.REL_ipowner,
            )
            Drone.OwnedIPsQuery = Drone.OwnedIPsQuery_subtxt
        self.set_crypto_identity()
        if self.association.is_abstract and not CMAdb.store.readonly:
            # print 'Creating BP rules for', self.designation
            from bestpractices import BestPractices

            bprules = CMAdb.config["bprulesbydomain"]
            rulesetname = bprules[domain] if domain in bprules else bprules[CMAconsts.globaldomain]
            for rule in BestPractices.gen_bp_rules_by_ruleset(CMAdb.store, rulesetname):
                # print ('ADDING RELATED RULE SET for',
                #       self.designation, rule.bp_class, rule, file=sys.stderr)
                CMAdb.store.relate(
                    self, CMAconsts.REL_bprulefor, rule, properties={"bp_class": rule.bp_class}
                )

    def gen_current_bp_rules(self):
        """Return a generator producing all the best practice rules
        that apply to this Drone.
        """
        return CMAdb.store.load_related(self, CMAconsts.REL_bprulefor)

    def get_bp_head_rule_for(self, trigger_discovery_type):
        """
        Return the head of the ruleset chain for the particular set of rules
        that go with this particular node
        """
        rules = CMAdb.store.load_related(self, CMAconsts.REL_bprulefor)
        for rule in rules:
            if rule.bp_class == trigger_discovery_type:
                return rule
        return None

    def get_merged_bp_rules(self, trigger_discovery_type):
        """Return a merged version of the best practices rules for this
        particular discovery type.  This involves creating a hash table
        of rules, where the contents are merged together such that we return
        a single consolidated view of the rules to our viewer.
        We start out with the head of the ruleset chain and then merge in the
        ones its based on.

        We return a dict-like object reflecting this merger suitable
        for evaluating the rules. You just walk the set of rules
        and evaluate them.
        """
        # Although we ought to hit the database once and get the PATH of the
        # rules in one fell swoop, we don't yet support PATHs, so we're going
        # at it the somewhat slower way -- incrementally.
        start = self.get_bp_head_rule_for(trigger_discovery_type)
        if start is None:
            return {}
        ret = start.jsonobj()
        this = start
        while True:
            nextrule = None
            for nextrule in CMAdb.store.load_related(this, CMAconsts.REL_basis):
                break
            if nextrule is None:
                break
            nextobj = nextrule.jsonobj()
            for elem in nextobj:
                if elem not in ret:
                    ret[elem] = nextobj[elem]
            this = nextrule
        return ret

    @staticmethod
    def bp_category_score_attrname(category):
        "Compute the attribute name of a best practice score category"
        return "bp_category_%s_score" % category

    def bp_category_list(self):
        "Provide the list best practice score categories that we have stored"
        result = []
        for attr in dir(self):
            if attr.startswith("bp_category_") and attr.endswith("_score"):
                result.append(attr[12:-6])
        return result

    def bp_discoverytypes_list(self):
        "List the discovery types that we have recorded"
        result = []
        for attr in dir(self):
            if attr.startswith("BP_") and attr.endswith("_rulestatus"):
                result.append(attr[3:-11])
        return result

    @staticmethod
    def bp_discoverytype_result_attrname(discoverytype):
        "Compute the attribute name of a best practice score category"
        return "BP_%s_rulestatus" % discoverytype

    def get_owned_ips(self):
        """Return a list of all the IP addresses that this Drone owns"""
        params = {"droneid": self.association.node_id}
        if CMAdb.debug:
            print(
                "IP owner query:\n%s\nparams %s" % (Drone.OwnedIPsQuery_subtxt, str(params)),
                file=sys.stderr,
            )

        ip_list = [
            node for node in CMAdb.store.load_cypher_nodes(Drone.OwnedIPsQuery, params=params)
        ]
        # print ("Query returned: %s"
        #                       % str([str(ip) for ip in ip_list]), file=sys.stderr)
        return ip_list

    def get_owned_nics(self):
        """Return an iterator returning all the NICs that this Drone owns"""
        return CMAdb.store.load_related(self, CMAconsts.REL_nicowner)

    def get_active_nic_count(self):
        """Return the number of "active" NICs this Drone has"""
        if self._active_nic_count is not None:
            return self._active_nic_count
        count = 0
        for nic in self.get_owned_nics():
            if nic.operstate == "up" and nic.carrier and nic.macaddr != "00-00-00-00-00-00":
                count += 1
        self._active_nic_count = count
        return count

    def crypto_identity(self):
        """Return the Crypto Identity that should be associated with this Drone
        Note that this current algorithm isn't ideal for a multi-tenant environment.
        """
        return self.designation

    def destaddr(self, ring=None):
        """Return the "primary" IP for this host as a pyNetAddr with port"""
        return pyNetAddr(self.select_ip(ring=ring), port=self.port)

    def select_ip(self, ring=None):
        """Select an appropriate IP address for talking to a partner on this ring
        or our primary IP if ring is None"""
        # Current code is not really good enough for the long term,
        # but is good enough for now...
        # In particular, when talking on a particular switch ring, or
        # subnet ring, we want to choose an IP that's on that subnet,
        # and preferably on that particular switch for a switch-level ring.
        # For TheOneRing, we want their primary IP address.
        ring = ring
        return self.primary_ip_addr

    def send_frames(self, framesettype, frames):
        "Send messages to our real concrete Drone system..."
        # This doesn't work if the client has bound to a VIP
        ourip = pyNetAddr(self.select_ip())  # meaning select our primary IP
        if ourip.port() == 0:
            ourip.setport(self.port)
        # print('ADDING PACKET TO TRANSACTION: %s', str(frames), file=sys.stderr)
        if CMAdb.debug:
            CMAdb.log.debug("Sending request to %s Frames: %s" % (str(ourip), str(frames)))
        CMAdb.net_transaction.add_packet(ourip, framesettype, frames)
        # print('Sent Discovery request to %s Frames: %s'
        #       %	(str(ourip), str(frames)), file=sys.stderr)

    # Current implementation does not use 'self'
    # pylint: disable=R0201
    def send_hbmsg(self, dest, fstype, addrlist):
        """Send a message with an attached pyNetAddr list - each including port numbers'
           This is intended primarily for start or stop heartbeating messages."""

        # Now we create a collection of frames that looks like this:
        #
        #   One FrameTypes.RSCJSON frame containing JSON Heartbeat parameters
        #   one frame per dest, type FrameTypes.IPPORT
        #
        params = ConfigFile.agent_params(CMAdb.config, "heartbeats", None, self.designation)
        framelist = [{"frametype": FrameTypes.RSCJSON, "framevalue": str(params)}]
        for addr in addrlist:
            if addr is None:
                continue
            framelist.append({"frametype": FrameTypes.IPPORT, "framevalue": addr})

        CMAdb.net_transaction.add_packet(dest, fstype, framelist)

    def death_report(self, status, reason, fromaddr, frameset):
        "Process a death/shutdown report for us.  RIP us."
        from hbring import HbRing

        # print ('DEAD REPORT: %s' % self, file=sys.stderr)
        frameset = frameset  # We don't use the frameset at this point in time
        if reason != "HBSHUTDOWN":
            if self.status != status or self.reason != reason:
                CMAdb.log.info(
                    "Node %s has been reported as %s by address %s. Reason: %s"
                    % (self.designation, status, str(fromaddr), reason)
                )
        oldstatus = self.status
        self.status = status
        self.reason = reason
        self.monitors_activated = False
        self.time_status_ms = int(round(time.time() * 1000))
        self.time_status_iso8601 = time.strftime("%Y-%m-%d %H:%M:%S")
        if status == oldstatus:
            # He was already dead, Jim.
            return
        # There is a need for us to be a little more sophisticated
        # in terms of the number of peers this particular drone had
        # It's here in this place that we will eventually add the ability
        # to distinguish death of a switch or subnet or site from death of a single drone
        for ring in self.find_associated_rings():
            # print ('Calling Ring(%s).leave(%s).' % (ring_name, self), file=sys.stderr)
            ring.leave(self)
        deadip = pyNetAddr(self.select_ip(), port=self.port)
        if CMAdb.debug:
            CMAdb.log.debug("Closing connection to %s/%d" % (deadip, DEFAULT_FSP_QID))
        #
        # So, if this is a death report from another system we could shut down ungracefully
        # and it would be OK.
        #
        # But if it's a graceful shutdown, we need to not screw up the comm shutdown in progress
        # If it's broken, our tests and the real world will eventually show that up :-D.
        #
        if reason != "HBSHUTDOWN":
            self._io.closeconn(DEFAULT_FSP_QID, deadip)
        AssimEvent(self, AssimEvent.OBJDOWN)

    def find_associated_rings(self):
        """
        Return a generator yielding the ring objects which this Drone is a member of
        This could be more efficient, albeit without some error checking we're doing now...
        :return: generator(HbRing)
        """
        for label in self.association.store.labels(self):
            if label.startswith("Ring_"):
                ring_name = label[5:]
                query = "MATCH(r:Class_HbRing) WHERE r.name=$name RETURN r"
                ring = self.association.store.load_cypher_node(query, {"name": ring_name})
                if ring is None:
                    raise RuntimeError("Cannot locate ring [%s] for %s" % (ring_name, self))
                else:
                    yield ring

    def start_heartbeat(self, ring, partner1, partner2=None):
        """Start heartbeating to the given partners.
        We insert ourselves between partner1 and partner2.
        We only use forward links - because we can follow them in both directions in Neo4J.
        So, we need to create a forward link from partner1 to us and from us to partner2 (if any)
        """
        ouraddr = pyNetAddr(self.select_ip(), port=self.port)
        partner1addr = pyNetAddr(partner1.select_ip(ring), port=partner1.port)
        if partner2 is not None:
            partner2addr = pyNetAddr(partner2.select_ip(ring), port=partner2.port)
        else:
            partner2addr = None
        if CMAdb.debug:
            CMAdb.log.debug(
                "STARTING heartbeat(s) from %s [%s] to %s [%s] and %s [%s]"
                % (self, ouraddr, partner1, partner1addr, partner2, partner2addr)
            )
        self.send_hbmsg(ouraddr, FrameSetTypes.SENDEXPECTHB, (partner1addr, partner2addr))

    def stop_heartbeat(self, ring, partner1, partner2=None):
        """Stop heartbeating to the given partners.'
        We don't know which node is our forward link and which our back link,
        but we need to remove them either way ;-).
        """
        ouraddr = pyNetAddr(self.select_ip(), port=self.port)
        partner1addr = pyNetAddr(partner1.select_ip(ring), port=partner1.port)
        if partner2 is not None:
            partner2addr = pyNetAddr(partner2.select_ip(ring), port=partner2.port)
        else:
            partner2addr = None
        # Stop sending the heartbeat messages between these (former) peers
        if CMAdb.debug:
            CMAdb.log.debug(
                "STOPPING heartbeat(s) from %s [%s] to %s [%s] and %s [%s]"
                % (self, ouraddr, partner1, partner1addr, partner2, partner2addr)
            )
        self.send_hbmsg(ouraddr, FrameSetTypes.STOPSENDEXPECTHB, (partner1addr, partner2addr))

    def set_crypto_identity(self, keyid=None):
        "Associate our IP addresses with our key id"
        if CMAdb.store.readonly or not CMAdb.use_network:
            return
        if keyid is not None and keyid != "":
            if self.key_id != "" and keyid != self.key_id:
                raise ValueError(
                    "Cannot change key ids for % from %s to %s." % (str(self), self.key_id, keyid)
                )
            self.key_id = keyid
        # Encryption is required elsewhere - we ignore this here...
        if self.key_id != "":
            pyCryptFrame.dest_set_key_id(self.destaddr(), self.key_id)
            pyCryptFrame.associate_identity(self.crypto_identity(), self.key_id)

    def __str__(self):
        "Give out our designation"
        return "Drone(%s)" % self.designation

    def find_child_system_from_json(self, jsonobj):
        """Locate the child drone that goes with this JSON - or maybe it's us"""
        if "proxy" in jsonobj:
            path = jsonobj["proxy"]
            if path == "local/local":
                return self
        else:
            return self
        # This works - could be a bit slow if you have lots of child nodes...
        q = """MATCH (drone)<-[:parentsys*]-(child)
               WHERE ID(drone) = {id} AND child.childpath = {path}
               RETURN child"""
        store = self.association.store
        child = store.load_cypher_node(q, {"id": self.association.node_id, "path": path})
        if child is None:
            raise (
                ValueError(
                    "Child system %s from %s [%s] was not found."
                    % (path, str(self), str(self.association.node_id))
                )
            )
        return child

    @staticmethod
    def find(designation, port=None, domain=None):
        """Find a drone with the given designation or IP address, or Neo4J node."""
        desigstr = str(designation)
        if isinstance(designation, Drone):
            designation.set_crypto_identity()
            return designation
        elif isinstance(designation, str):
            if domain is None:
                domain = CMAconsts.globaldomain
            designation = designation.lower()
            drone = CMAdb.store.load_or_create(
                Drone, port=port, domain=domain, designation=designation
            )
            assert drone.designation == designation
            assert drone.association.node_id is not None
            drone.set_crypto_identity()
            return drone
        elif isinstance(designation, pyNetAddr):
            desig = designation.toIPv6()
            desig.setport(0)
            desigstr = str(desig)
            # We do everything by IPv6 addresses...
            drone = CMAdb.store.load_cypher_node(
                Drone.IPownerquery_1, {"ipaddr": desigstr, "domain": str(domain)}
            )
            if drone is not None:
                assert drone.association.node_id is not None
                drone.set_crypto_identity()
                return drone
            if CMAdb.debug:
                CMAdb.log.warn(
                    "Could not find IP NetAddr address in Drone.find... %s [%s] [%s]"
                    % (designation, desigstr, type(designation))
                )

        if CMAdb.debug:
            CMAdb.log.debug("DESIGNATION2 (%s) = %s" % (designation, desigstr))
            CMAdb.log.debug("QUERY (%s) = %s" % (designation, Drone.IPownerquery_1))
            print("DESIGNATION2 (%s) = %s" % (designation, desigstr), file=sys.stderr)
            print("QUERY (%s) = %s" % (designation, Drone.IPownerquery_1), file=sys.stderr)
        if CMAdb.debug:
            raise RuntimeError(
                "drone.find(%s) (%s) (%s) => returning None"
                % (str(designation), desigstr, type(designation))
            )
            # tblist = traceback.extract_stack()
            # tblist = traceback.extract_tb(trace, 20)
            # CMAdb.log.info('======== Begin missing IP Traceback ========')
            # for tbelem in tblist:
            #     (filename, line, funcname, text) = tbelem
            #     filename = os.path.basename(filename)
            #     CMAdb.log.info('%s.%s:%s: %s'% (filename, line, funcname, text))
            # CMAdb.log.info('======== End missing IP Traceback ========')
            # CMAdb.log.warn('drone.find(%s) (%s) (%s) => returning None' % (
        return None

    @staticmethod
    def add(
        designation,
        reason,
        status="up",
        port=None,
        domain=CMAconsts.globaldomain,
        primary_ip_addr=None,
    ):
        """Add a drone to our set unless it is already there."""
        drone = CMAdb.store.load_or_create(
            Drone,
            domain=domain,
            designation=designation,
            primary_ip_addr=primary_ip_addr,
            port=port,
            status=status,
            reason=reason,
        )
        assert drone.association.node_id is not None
        drone.reason = reason
        drone.status = status
        drone.statustime = int(round(time.time() * 1000))
        drone.iso8601 = time.strftime("%Y-%m-%d %H:%M:%S")
        if port is not None:
            drone.port = port
        if primary_ip_addr is not None and drone.primary_ip_addr != primary_ip_addr:
            # This means they've changed their IP address and/or port since we last saw them...
            CMAdb.log.info(
                "DRONE %s changed IP address from %s to %s"
                % (str(drone), drone.primary_ip_addr, primary_ip_addr)
            )
            drone.primary_ip_addr = str(primary_ip_addr)
            if port is None:
                drone.port = int(primary_ip_addr.port())
        return drone
