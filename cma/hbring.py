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
'''
This file is all about the Rings - we implement rings.
'''
#import sys
from cmadb import CMAdb
from py2neo import neo4j
from droneinfo import Drone
from graphnodes import GraphNode, RegisterGraphClass
from store import Store

@RegisterGraphClass
class HbRing(GraphNode):
    'Class defining the behavior of a heartbeat ring.'
    SWITCH      =  1
    SUBNET      =  2
    THEONERING  =  3 # And The One Ring to rule them all...
    memberprefix = 'RingMember_'
    nextprefix = 'RingNext_'

    def __init__(self, name, ringtype):
        '''Constructor for a heartbeat ring.
        '''
        GraphNode.__init__(self, domain=CMAdb.globaldomain)
        if ringtype < HbRing.SWITCH or ringtype > HbRing.THEONERING:
            raise ValueError("Invalid ring type [%s]" % str(ringtype))
        self.ringtype = ringtype
        self.name = str(name)
        self.ourreltype = HbRing.memberprefix + self.name # Our membership relationship type
        self.ournexttype = HbRing.nextprefix + self.name # Our 'next' relationship type
        self._ringinitfinished = False
        self._insertpoint1 = None
        self._insertpoint2 = None

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of decreasing significance'
        return ['name']


    def post_db_init(self):
        GraphNode.post_db_init(self)
        if self._ringinitfinished:
            return
        self._ringinitfinished = True
        self._insertpoint1 = None
        self._insertpoint2 = None
        #print >> sys.stderr, 'CMAdb(hbring.py):', CMAdb
        #print >> sys.stderr, 'CMAdb.store(hbring.py):', CMAdb.store
        #print >> sys.stderr, 'Our relation type: %s' % self.ourreltype
        rellist = CMAdb.store.load_related(self, self.ourreltype, Drone)
        for rel in rellist:
            self._insertpoint1 = rel
            #print >> sys.stderr, 'INSERTPOINT1: ', self._insertpoint1
            #print >> sys.stderr, 'Our relation type: %s' % self.ournexttype
            ip2rellist = CMAdb.store.load_related(self._insertpoint1, self.ournexttype, Drone)
            for rel2 in ip2rellist:
                self._insertpoint2 = rel2
                break
            break
        # Need to figure out what to do about pre-existing members of this ring...
        # For the moment, let's make the entirely inadequate assumption that
        # the data in the database is correct.
        ## FIXME - assumption about database being correct :-D


    def _findringpartners(self, drone):
        '''Find (one or) two partners for this drone to heartbeat with.
        We _should_ do this in such a way that we don't continually beat on the
        same nodes in the ring as we insert new nodes into the ring.'''
        drone = drone # Eventually we'll use this argument...
        partners = None
        if self._insertpoint1 is not None:
            partners = []
            partners.append(self._insertpoint1)
            if self._insertpoint2 is not None:
                partners.append(self._insertpoint2)
        return partners

    def join(self, drone):
        'Add this drone to our ring'
        if CMAdb.debug:
            CMAdb.log.debug('1:Adding Drone %s to ring %s w/port %s' \
            %   (str(drone), str(self), drone.port))
        # Make sure he's not already in our ring according to our 'database'
        if not Store.is_abstract(drone):
            rels = CMAdb.store.load_in_related(drone, self.ourreltype, HbRing)
            rels = [rel for rel in rels]
            if len(rels) > 0:
                CMAdb.log.critical("%s is already a member of this ring [%s]"
                " - removing and re-adding." % (drone, self))
                self.leave(drone)

        # Create a 'ringmember' relationship to this drone
        CMAdb.store.relate(self, self.ourreltype, drone)
        # Should we keep a 'ringip' relationship for this drone?
        # Probably eventually...

        #print >>sys.stderr,'Adding drone %s to talk to partners' % drone

        if self._insertpoint1 is None:   # Zero nodes previously
            self._insertpoint1 = drone
            return

        if CMAdb.debug:
            CMAdb.log.debug('2:Adding Drone %s to ring %s w/port %s' \
            %   (str(drone), str(self), drone.port))
        if self._insertpoint2 is None:   # One node previously
            # Create the initial circular list.
            ## FIXME: Ought to label ring membership relationships with IP involved
            # This is because we might change configurations and we need to know
            # what IP we're actually using for this connection...
            CMAdb.store.relate(drone, self.ournexttype, self._insertpoint1)
            CMAdb.store.relate(self._insertpoint1, self.ournexttype, drone)
            if CMAdb.debug:
                CMAdb.log.debug('3:Adding Drone %s to ring %s w/port %s'
                %       (str(drone), str(self), drone.port))
            drone.start_heartbeat(self, self._insertpoint1)
            self._insertpoint1.start_heartbeat(self, drone)
            self._insertpoint2 = self._insertpoint1
            self._insertpoint1 = drone
            #print >>sys.stderr, 'RING2 IS NOW:', str(self)
            return

        # Two or more nodes previously
        nextnext = None
        for nextnext in CMAdb.store.load_related(self._insertpoint2, self.ournexttype, Drone):
            break
        if CMAdb.debug:
            CMAdb.log.debug('4:Adding Drone %s to ring %s w/port %s' \
            %   (str(drone), str(self), drone.port))
        if nextnext is not None and nextnext is not self._insertpoint1:
            #print >> sys.stderr, 'HAD AT LEAST 3 NODES BEFORE'
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
        CMAdb.store.separate(self._insertpoint1, self.ournexttype, self._insertpoint2)
        # Now we just have had X->point1 and point2->Y
        if CMAdb.debug:
            CMAdb.log.debug('5:Adding Drone %s to ring %s w/port %s' \
            %       (str(drone), str(self), drone.port))
        drone.start_heartbeat(self, self._insertpoint1, self._insertpoint2)
        self._insertpoint1.start_heartbeat(self, drone)
        self._insertpoint2.start_heartbeat(self, drone)
        CMAdb.store.relate(self._insertpoint1, self.ournexttype, drone)
        # after above statement: we have x->insertpoint1-> drone and insertpoint2->y
        CMAdb.store.relate(drone, self.ournexttype, self._insertpoint2)
        # after above statement: we have insertpoint1-> drone->insertpoint2
        #
        # In the future we might want to mark these relationships with the IP addresses involved
        # so that even if the systems change network configurations we can still know what IP to
        # remove.  Right now we rely on the configuration not changing "too much".
        ## FIXME: Ought to label relationships with IP addresses involved.
        #
        # We should ensure that we don't keep beating the same nodes over and over
        # again as new nodes join the system.  Instead the latest newbie becomes the next
        # insert point in the ring - spreading the work to the new guys as they arrive.
        # Probably should use nextnext from above...
        self._insertpoint1 = drone
        #print >>sys.stderr, 'RING3 IS NOW:', str(self), 'DRONE ADDED:', drone

    def leave(self, drone):
        'Remove a drone from this heartbeat Ring.'
        #print >> sys.stderr, 'DRONE %s leaving Ring [%s]' % (drone, self)
        #ringlist = self.members_ring_order()
        #print >>sys.stderr, 'RING IN ORDER:'
        #for elem in ringlist:
            #print >>sys.stderr, 'RING NODE: %s' % elem

        prevnode = None
        for prevnode in CMAdb.store.load_in_related(drone, self.ournexttype, Drone):
            break
        nextnode = None
        for nextnode in CMAdb.store.load_related(drone, self.ournexttype, Drone):
            break

        # Clean out the parent (ring) relationship to our dearly departed drone
        #print >> sys.stderr, 'Separating ourselves (%s) from drone %s' % (self, drone)
        CMAdb.store.separate(self, self.ourreltype, drone)
        # Clean out the next link relationships to our dearly departed drone
        if nextnode is None and prevnode is None:   # Previous length:  1
            self._insertpoint1 = None               # result length:    0
            self._insertpoint2 = None
            # No other database links to remove
            if CMAdb.debug:
                CMAdb.log.debug('Last Drone %s has now left the building...' % (drone))
            return

        # Clean out the next link relationships to our dearly departed drone
        CMAdb.store.separate(prevnode, self.ournexttype, obj=drone)
        CMAdb.store.separate(drone,    self.ournexttype, obj=nextnode)

        #print >> sys.stderr, ('PREVNODE: %s NEXTNODE: %s prev is next? %s'
        #%           (str(prevnode), str(nextnode), prevnode is nextnode))

        if prevnode is nextnode:                  # Previous length:  2
            #drone.stop_heartbeat(self, prevnode)  # Result length:    1
            # but drone is dead - don't talk to it.
            prevnode.stop_heartbeat(self, drone)
            self._insertpoint2 = None
            self._insertpoint1 = prevnode
            return

        # Previous length had to be >= 3        # Previous length:  >=3
                                                # Result length:    >=2
        nextnext = None
        for nextnext in CMAdb.store.load_related(nextnode, self.ournexttype, Drone):
            break
        prevnode.stop_heartbeat(self, drone)
        nextnode.stop_heartbeat(self, drone)
        if nextnext is not prevnode:                  # Previous length:  >= 4
            nextnode.start_heartbeat(self, prevnode)  # Result length:    >= 3
            prevnode.start_heartbeat(self, nextnode)
            # (in the nextnext is prevnode case, they're already heartbeating)
        # Poor drone -- all alone in the universe... (maybe even dead...)
        #drone.stop_heartbeat(self, prevnode, nextnode) # don't send packets to dead machines
        self._insertpoint1 = prevnode
        self._insertpoint2 = nextnode
        CMAdb.store.relate(prevnode, self.ournexttype, nextnode)

    def are_partners(self, drone1, drone2):
        'Return True if these two drones are heartbeat partners in our ring'
        nextelems =  CMAdb.store.load_related(drone1, self.ournexttype, Drone)
        if drone2 in nextelems:
            return True
        prevelems =  CMAdb.store.load_in_related(drone1, self.ournexttype, Drone)
        return drone2 in prevelems

    def members(self):
        'Return all the Drones that are members of this ring - in some random order'
        return CMAdb.store.load_related(self, self.ourreltype, Drone)

    def members_ring_order(self):
        'Return all the Drones that are members of this ring - in ring order'
        ## FIXME - There's a cypher query that will return these all in one go
        # START Drone=node:Drone(Drone="drone000001")
        # MATCH Drone-[:RingNext_The_One_Ring*]->NextDrone
        # RETURN NextDrone.designation, NextDrone

        if self._insertpoint1 is None:
            #print >> sys.stderr, 'NO INSERTPOINT1'
            return
        if Store.is_abstract(self._insertpoint1):
            #print >> sys.stderr, ('YIELDING INSERTPOINT1:', self._insertpoint1
            #,       type(self._insertpoint1))
            yield self._insertpoint1
            return
        startid = Store.id(self._insertpoint1)
        # We can't pre-compile this, but we hopefully we won't use it much...
        q = '''START Drone=node(%s)
             MATCH p=Drone-[:%s*0..]->NextDrone
             WHERE length(p) = 0 or Drone <> NextDrone
             RETURN NextDrone''' % (startid, self.ournexttype)
        query = neo4j.CypherQuery(CMAdb.cdb.db, q)
        for elem in CMAdb.store.load_cypher_nodes(query, Drone):
            yield elem
        return

    def AUDIT(self):
        '''Audit our ring to see if it's well-formed'''
        listmembers = {}
        ringmembers = {}
        mbrcount = 0
        for drone in self.members():
            ringmembers[drone.designation] = None
            mbrcount += 1

        for drone in self.members_ring_order():
            listmembers[drone.designation] = None
            nextcount = 0
            nextlist = CMAdb.store.load_related(drone, self.ournexttype, Drone)
            # pylint: disable=W0612
            for elem in nextlist:
                nextcount += 1
            incount = 0
            inlist = CMAdb.store.load_in_related(drone, self.ournexttype, Drone)
            for elem in inlist:
                incount += 1
            ringcount = 0
            dronelist = CMAdb.store.load_in_related(drone, self.ourreltype, Drone)
            for elem in dronelist:
                ringcount += 1
            #print >> sys.stderr    \
            #,   ('%s status: %s mbrcount: %d, nextcount:%d, incount:%d, ringcount:%d'
            #%   (drone, drone.status, mbrcount, nextcount, incount, ringcount))
            assert drone.status == 'up'
            assert mbrcount < 2 or 1 == nextcount
            assert mbrcount < 2 or 1 == incount
            assert 1 == ringcount

        for drone in listmembers.keys():
            assert(drone in ringmembers)
        for drone in ringmembers.keys():
            assert(drone in listmembers)



    def __str__(self):
        ret = 'Ring("%s"' % self.name
        #comma = ', ['
        #for drone in self.members_ring_order():
        #    ret += '%s%s' % (comma, drone)
        #    comma = ', '
        #ret += ']'
        ret += ')'
        return ret

if __name__ == '__main__':
    db = CMAdb()
