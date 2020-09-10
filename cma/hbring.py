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
"""
This file is all about the Rings - we implement rings.
"""
from sys import stderr
from cmadb import CMAdb
from graphnodes import GraphNode, registergraphclass


@registergraphclass
class HbRing(GraphNode):
    """Class defining the behavior of a heartbeat ring."""
    SWITCH = 1
    SUBNET = 2
    THEONERING = 3  # And The One Ring to rule them all...
    memberprefix = "RingMember_"
    nextprefix = "RingNext_"

    def __init__(self, name, ringtype):
        """Constructor for a heartbeat ring.
        """
        GraphNode.__init__(self, domain=CMAdb.globaldomain)
        if ringtype < HbRing.SWITCH or ringtype > HbRing.THEONERING:
            raise ValueError("Invalid ring type [%s]" % str(ringtype))
        self.ringtype = ringtype
        self.name = str(name)
        self.ourreltype = HbRing.memberprefix + self.name
        self.ournexttype = HbRing.nextprefix + self.name  # Our 'next' relationship type
        self.our_member_label = "Ring_" + self.name
        self._ringinitfinished = False
        self._insertpoint1 = None
        self._insertpoint2 = None

    @classmethod
    def meta_key_attributes(cls):
        """Return our key attributes in order of decreasing significance"""
        return ["name", "domain"]

    def post_db_init(self):
        GraphNode.post_db_init(self)
        if self._ringinitfinished:
            return
        self._ringinitfinished = True
        self._insertpoint1 = None
        self._insertpoint2 = None
        # print('CMAdb(hbring.py):', CMAdb, file=stderr)
        # print('self.association.store(hbring.py):', self.association.store, file=stderr)
        # print('Our relation type: %s' % self.our_member_label, file=stderr)
        # query = ('OPTIONAL MATCH (node1:Class_Drone)-[:%s]->(node2) RETURN node1, node2 LIMIT 1'
        #          % self.ournexttype)
        # for  member1, member2 in self.association.store.load_cypher_query(query):
        #    break
        # print("MEMBER1: %s, MEMBER2: %s" % (member1, member2), file=stderr)
        for rel in self.members():
            self._insertpoint1 = rel
            # print('INSERTPOINT1: ', self._insertpoint1, file=stderr)
            # print('Our relation type: %s' % self.ournexttype, file=stderr)
            ip2rellist = self.association.store.load_related(self._insertpoint1, self.ournexttype)
            for rel2 in ip2rellist:
                self._insertpoint2 = rel2
                break
            break
        # print('INSERTPOINT1: %s, POINT2: %s '
        #       % (self._insertpoint1, self._insertpoint2)), file=stderr)

    def _findringpartners(self, drone):
        """Find (one or) two partners for this drone to heartbeat with.
        We _should_ do this in such a way that we don't continually beat on the
        same nodes in the ring as we insert new nodes into the ring."""
        _drone = drone  # Eventually we'll use this argument...
        partners = None
        if self._insertpoint1 is not None:
            partners = list()
            partners.append(self._insertpoint1)
            if self._insertpoint2 is not None:
                partners.append(self._insertpoint2)
        return partners

    def join(self, drone):
        """Add this drone to our ring"""
        assert drone.association.node_id is not None
        if CMAdb.debug:
            CMAdb.log.debug(
                "1:Adding Drone %s to ring %s w/port %s" % (str(drone), str(self), drone.port)
            )
        assert self.our_member_label not in self.association.store.labels(drone)
        # Create a 'ringmember' relationship to this drone
        #######  self.association.store.relate(self, self.ourreltype, drone)
        self.association.store.add_labels(drone, (self.our_member_label,))
        # Should we keep a 'ringip' relationship for this drone?
        # Probably eventually...

        # print('Adding drone %s to talk to partners' % drone, file=stderr)
        thisring = {"ring_name": self.name}
        if self._insertpoint1 is None:  # Zero nodes previously
            self._insertpoint1 = drone
            return

        if CMAdb.debug:
            CMAdb.log.debug(
                "2:Adding Drone %s to ring %s w/port %s" % (str(drone), str(self), drone.port)
            )
        if self._insertpoint2 is None:  # One node previously
            # Create the initial circular list.
            # FIXME: Ought to label ring membership relationships with IP involved
            # This is because we might change configurations and we need to know
            # what IP we're actually using for this connection...
            self.association.store.relate(
                drone, self.ournexttype, self._insertpoint1, attrs=thisring
            )
            self.association.store.relate(
                self._insertpoint1, self.ournexttype, drone, attrs=thisring
            )
            if CMAdb.debug:
                CMAdb.log.debug(
                    "3:Adding Drone %s to ring %s w/port %s" % (str(drone), str(self), drone.port)
                )
            drone.start_heartbeat(self, self._insertpoint1)
            self._insertpoint1.start_heartbeat(self, drone)
            self._insertpoint2 = self._insertpoint1
            self._insertpoint1 = drone
            # print('RING2 IS NOW:', str(self), file=stderr)
            return

        # Two or more nodes previously
        nextnext = None
        for nextnext in self.association.store.load_related(
            self._insertpoint2, self.ournexttype, attrs=thisring
        ):
            break
        if CMAdb.debug:
            CMAdb.log.debug(
                "4:Adding Drone %s to ring %s w/port %s" % (str(drone), str(self), drone.port)
            )
        if nextnext is not None and nextnext is not self._insertpoint1:
            # print('HAD AT LEAST 3 NODES BEFORE', file=stderr)
            # At least 3 nodes before
            # We had X->point1->point2->nextnext (where X and nextnext might be the same)
            # We just verified that point1 and Y are different
            #
            # What we have right now is insertpoint1->insertpoint2->nextnext
            # Let's move the insert point down the ring so that the same node doesn't get hit
            # over and over with stop/start requests
            #
            self._insertpoint1 = self._insertpoint2
            self._insertpoint2 = nextnext
            self._insertpoint1.stop_heartbeat(self, self._insertpoint2)
            self._insertpoint2.stop_heartbeat(self, self._insertpoint1)
        self.association.store.separate(
            self._insertpoint1, self.ournexttype, self._insertpoint2, attrs=thisring
        )
        # Now we just have had X->point1 and point2->Y
        if CMAdb.debug:
            CMAdb.log.debug(
                "5:Adding Drone %s to ring %s w/port %s" % (str(drone), str(self), drone.port)
            )
        drone.start_heartbeat(self, self._insertpoint1, self._insertpoint2)
        self._insertpoint1.start_heartbeat(self, drone)
        self._insertpoint2.start_heartbeat(self, drone)
        self.association.store.relate(self._insertpoint1, self.ournexttype, drone, attrs=thisring)
        # after above statement: we have x->insertpoint1-> drone and insertpoint2->y
        self.association.store.relate(drone, self.ournexttype, self._insertpoint2, attrs=thisring)
        # after above statement: we have insertpoint1-> drone->insertpoint2
        #
        # In the future we might want to mark these relationships with the IP addresses involved
        # so that even if the systems change network configurations we can still know what IP to
        # remove.  Right now we rely on the configuration not changing "too much".
        # FIXME: Ought to label relationships with IP addresses involved.
        #
        # We should ensure that we don't keep beating the same nodes over and over
        # again as new nodes join the system.  Instead the latest newbie becomes the next
        # insert point in the ring - spreading the work to the new guys as they arrive.
        # Probably should use nextnext from above...
        self._insertpoint1 = drone
        # print('RING3 IS NOW:', str(self), 'DRONE ADDED:', drone, file=stderr)

    def dump_ring_in_order(self, title="Drones in Ring Order", our_drone=None):
        """
        Dump the given ring to stderr
        :param title: Title to put in output
        :param our_drone: The 'distinguished' drone...
        :return: None
        """
        print("%s++++++++++" % title)
        for drone in self.members_ring_order():
            print(
                "%s %s %s" % ("-->" if drone is our_drone else "   ", drone, object.__str__(drone)),
                file=stderr,
            )

    def leave(self, drone):
        """Remove a drone from this heartbeat Ring."""
        store = self.association.store
        # print('DRONE %s leaving Ring [%s]' % (drone, self), file=stderr)
        # self.dump_ring_in_order('RING BEFORE DELETION', drone)

        # labels = store.labels(drone)
        # print("ALL LABELS (del): %s" % str(labels), file=sys.stderr)
        assert self.our_member_label in store.labels(drone)
        store.delete_labels(drone, (self.our_member_label,))
        thisring = {"ring_name": self.name}
        prevnode = None
        nextnode = None
        for prevnode in store.load_in_related(drone, self.ournexttype, attrs=thisring):
            break
        for nextnode in store.load_related(drone, self.ournexttype, attrs=thisring):
            break

        # Clean out the parent (ring) relationship to our dearly departed drone
        # print('Separating ourselves (%s) from drone %s' % (self, drone), file=stderr)
        # Clean out the next link relationships to our dearly departed drone
        if nextnode is None and prevnode is None:  # Previous length:  1
            self._insertpoint1 = None  # result length:    0
            self._insertpoint2 = None
            # No other database links to remove
            if CMAdb.debug:
                CMAdb.log.debug("Last Drone %s has now left the building..." % drone)
            # self.dump_ring_in_order('RING AFTER DELETION(1)', drone)
            return

        # Clean out the next link relationships to our dearly departed drone
        store.separate(prevnode, self.ournexttype, obj=drone, attrs=thisring)
        store.separate(drone, self.ournexttype, obj=nextnode, attrs=thisring)

        # print('PREVNODE: %s NEXTNODE: %s prev is next? %s'
        #       % (str(prevnode), str(nextnode), prevnode is nextnode), file=stderr)

        if prevnode is nextnode:  # Previous length:  2
            # drone.stop_heartbeat(self, prevnode)  # Result length:    1
            # but drone is dead - don't talk to it.
            prevnode.stop_heartbeat(self, drone)
            self._insertpoint2 = None
            self._insertpoint1 = prevnode
            # self.dump_ring_in_order('RING AFTER DELETION(2)', drone)
            return

        # Previous length had to be >= 3        # Previous length:  >=3
        #                                       # Result length:    >=2
        nextnext = None
        for nextnext in store.load_related(nextnode, self.ournexttype, attrs=thisring):
            break
        prevnode.stop_heartbeat(self, drone)
        nextnode.stop_heartbeat(self, drone)
        if nextnext is not prevnode:  # Previous length:  >= 4
            nextnode.start_heartbeat(self, prevnode)  # Result length:    >= 3
            prevnode.start_heartbeat(self, nextnode)
            # (in the nextnext is prevnode case, they're already heartbeating)
        # Poor drone -- all alone in the universe... (maybe even dead...)
        # drone.stop_heartbeat(self, prevnode, nextnode) # don't send packets to dead machines
        self._insertpoint1 = prevnode
        self._insertpoint2 = nextnode
        store.relate(prevnode, self.ournexttype, nextnode, attrs=thisring)
        # self.dump_ring_in_order('RING AFTER DELETION(3)', drone)

    def are_partners(self, drone1, drone2):
        "Return True if these two drones are heartbeat partners in our ring"
        thisring = {"ring_name": self.name}
        CMAdb.log.debug("calling are_partners(%s-[%s]-%s)" % (drone1, self.ournexttype, drone2))
        nextelems = self.association.store.load_related(drone1, self.ournexttype, attrs=thisring)
        for elem in nextelems:  # nextelems is a generator
            if elem is drone2:
                return True
        prevelems = self.association.store.load_in_related(drone1, self.ournexttype, attrs=thisring)
        for elem in prevelems:  # prevelems is a generator
            return elem is drone2
        return False

    def members(self):
        "Return all the Drones that are members of this ring - in some random order"
        query = "MATCH (drone:%s) RETURN drone" % self.our_member_label
        return self.association.store.load_cypher_nodes(query)

    def members_ring_order(self, start=None):
        "Return all the Drones that are members of this ring - in ring order"
        if start is None:
            for member in self.members():
                start = member
                break
        if start is None:
            # print('NO START', file=stderr)
            return
        startid = start.association.node_id
        # We can't pre-compile this, but we hopefully we won't use it much...
        q = (
            """MATCH p=allShortestPaths((Drone:Class_Drone)-[:%s*0..]->(NextDrone))
             WHERE ID(Drone) = $id
             RETURN NextDrone ORDER BY length(p)"""
            % self.ournexttype
        )
        for elem in self.association.store.load_cypher_nodes(q, {"id": startid}):
            yield elem
        return

    def AUDIT(self):
        """Audit our ring to see if it's well-formed"""
        listmembers = {}
        ringmembers = {}
        mbrcount = 0
        ringmembers = {drone for drone in self.members()}
        listmembers = {drone for drone in self.members_ring_order()}
        assert listmembers.difference(ringmembers) == set()
        assert ringmembers.difference(listmembers) == set()

        for drone in listmembers:
            nextcount = 0
            nextlist = self.association.store.load_related(drone, self.ournexttype)
            # pylint: disable=W0612
            for elem in nextlist:
                nextcount += 1
            incount = 0
            inlist = self.association.store.load_in_related(drone, self.ournexttype)
            for elem in inlist:
                incount += 1
            #  print('CHECKING %s status: %s mbrcount: %d, nextcount:%d'
            #  ', incount:%d, labels: %s'
            #  %   (drone, drone.status, mbrcount, nextcount, incount,
            #       str(drone.association.store.labels(drone))), file=stderr)
            # assert drone.status == 'up'
            assert mbrcount < 2 or nextcount == 1
            assert mbrcount < 2 or incount == 1

        for drone in listmembers:
            assert drone in ringmembers
        for drone in ringmembers:
            assert drone in listmembers

    def __str__(self):
        ret = 'Ring("%s"' % self.name
        # comma = ', ['
        # for drone in self.members_ring_order():
        #    ret += '%s%s' % (comma, drone)
        #    comma = ', '
        # ret += ']'
        ret += ")"
        return ret
