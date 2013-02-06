#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab
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
import sys
from cmadb import CMAdb
from py2neo import neo4j
from droneinfo import DroneInfo
class HbRing:
    'Class defining the behavior of a heartbeat ring.'
    SWITCH      =  1
    SUBNET      =  2
    THEONERING  =  3 # And The One Ring to rule them all...
    memberprefix = 'RingMember_'
    nextprefix = 'RingNext_'

    ringnames = {}

    def __init__(self, name, ringtype, parentring=None):
        '''Constructor for a heartbeat ring.
        Although we generally avoid keeping hash tables of nodes in the
        database, I'm currently making an exception for rings.  There are
        many fewer of those than any other kind of node.
        '''
        if ringtype < HbRing.SWITCH or ringtype > HbRing.THEONERING: 
            raise ValueError("Invalid ring type [%s]" % str(ringtype))
        self.node = CMAdb.cdb.new_ring(name, parentring, ringtype=ringtype)
        self.ringtype = ringtype
        self.name = str(name)
        self.parentring = parentring
        self.ourreltype = HbRing.memberprefix + self.name # Our relationship type
        self.ournexttype = HbRing.nextprefix + self.name # Our 'next' relationship type
        self.insertpoint1 = None
        self.insertpoint2 = None

        try:
            ip1node = self.node.get_single_related_node(neo4j.Direction.OUTGOING, self.ourreltype)
            if ip1node is not None:
                self.insertpoint1 = DroneInfo(ip1node)
                if self.insertpoint1 is not None:
                    try:
                      #print 'INSERTPOINT1: ', self.insertpoint1
                      ip2 = self.insertpoint1.node.get_single_related_node(neo4j.Direction.OUTGOING, self.ournexttype)
                      self.insertpoint2 = DroneInfo(ip2)
                    except ValueError:
                        pass
        except ValueError:
            pass
        # Need to figure out what to do about pre-existing members of this ring...
        # For the moment, let's make the entirely inadequate assumption that
        # the data in the database is correct.
        ## FIXME - assumption about database being correct
        HbRing.ringnames[self.name] = self

        
    def _findringpartners(self, drone):
        '''Find (one or) two partners for this drone to heartbeat with.
        We do this in such a way that we don't continually beat on the same
        nodes in the ring as we insert new nodes into the ring.'''
        partners=None
        if self.insertpoint1 is not None:
            partners=[]
            partners.append(self.insertpoint1)
            if self.insertpoint2 is not None:
                partners.append(self.insertpoint2)
        return partners

    def join(self, drone):
        'Add this drone to our ring'
        if CMAdb.debug: CMAdb.log.debug('1:Adding Drone %s to ring %s w/port %s' % (str(drone), str(self), drone.getport()))
        # Make sure he's not already in our ring according to our 'database'
        if drone.node.has_relationship_with(self.node, neo4j.Direction.OUTGOING, self.ourreltype):
            CMAdb.log.warning("Drone %s is already a member of this ring [%s] - removing and re-adding."
            %               (drone.node['name'], self.name))
            self.leave(drone)
        
        # Create a 'ringmember' relationship to this drone
        drone.node.create_relationship_to(self.node, self.ourreltype)
        #print 'New ring membership: %s' % (str(self))
        # Should we keep a 'ringip' relationship for this drone?
        # Probably eventually...

        #print >>sys.stderr,'Adding drone %s to talk to partners'%drone.node['name'], self.insertpoint1, self.insertpoint2

        if self.insertpoint1 is None:   # Zero nodes previously
            self.insertpoint1 = drone
            #print >>sys.stderr, 'RING1 IS NOW:', str(self)
            return

        if CMAdb.debug: CMAdb.log.debug('2:Adding Drone %s to ring %s w/port %s' % (str(drone), str(self), drone.getport()))
        if self.insertpoint2 is None:   # One node previously
        # Create the initial circular list.
            ## FIXME: Ought to label ring membership relationships with IP involved
            # (see comments below)
            CMAdb.cdb.db.relate((drone.node, self.ournexttype, self.insertpoint1.node),
                      (self.insertpoint1.node, self.ournexttype, drone.node))
            if CMAdb.debug: CMAdb.log.debug('3:Adding Drone %s to ring %s w/port %s' % (str(drone), str(self), drone.getport()))
            drone.start_heartbeat(self, self.insertpoint1)
            self.insertpoint1.start_heartbeat(self, drone)
            self.insertpoint2 = self.insertpoint1
            self.insertpoint1 = drone
            #print >>sys.stderr, 'RING2 IS NOW:', str(self)
            return
        
        #print >>sys.stderr, 'Finding insert point [%s: %s]' % \
    #   (self.insertpoint2.node['name'], self.ournexttype)
        # Two or more nodes previously
        #print >>sys.stderr, 'DRONE:', drone.node
        #print >>sys.stderr, 'INSERTPOINT1:', self.insertpoint1.node
        #print >>sys.stderr, 'INSERTPOINT2:', self.insertpoint2.node
        #print >>sys.stderr, 'OURNEXTTYPE:', self.ournexttype
        nextnext = self.insertpoint2.node.get_single_related_node(neo4j.Direction.OUTGOING, self.ournexttype)
        if CMAdb.debug: CMAdb.log.debug('4:Adding Drone %s to ring %s w/port %s' % (str(drone), str(self), drone.getport()))
        if nextnext is not None and nextnext.id != self.insertpoint1.node.id:
            # At least 3 nodes before
            self.insertpoint1.stop_heartbeat(self, self.insertpoint2)
            self.insertpoint2.stop_heartbeat(self, self.insertpoint1)
        if CMAdb.debug: CMAdb.log.debug('5:Adding Drone %s to ring %s w/port %s' % (str(drone), str(self), drone.getport()))
        drone.start_heartbeat(self, self.insertpoint1, self.insertpoint2)
        self.insertpoint1.start_heartbeat(self, drone)
        self.insertpoint2.start_heartbeat(self, drone)
        point1rel = self.insertpoint1.node.get_single_relationship(neo4j.Direction.OUTGOING, self.ournexttype)
        # Somehow we sometimes get here with "point1rel is None"... Bug??
        point1rel.delete()
        point1rel = None
        # In the future we might want to mark these relationships with the IP addresses involved
        # so that even if the systems change network configurations we can still know what IP to
        # remove.  Right now we rely on the configuration not changing "too much".
        ## FIXME: Ought to label relationships with IP addresses involved.
        CMAdb.cdb.db.relate((self.insertpoint1.node, self.ournexttype, drone.node),
                      (drone.node, self.ournexttype, self.insertpoint2.node))
        # This should ensure that we don't keep beating the same nodes over and over
        # again as new nodes join the system.  Instead the latest newbie becomes the next
        # insert point in the ring - spreading the work to the new guys as they arrive.
        #self.insertpoint2 = self.insertpoint1
        self.insertpoint1 = drone
        #print >>sys.stderr, 'RING3 IS NOW:', str(self), 'DRONE ADDED:', drone

    def leave(self, drone):
        'Remove a drone from this heartbeat Ring.'
        try: 
            prevnode = drone.node.get_single_related_node(neo4j.Direction.INCOMING, self.ournexttype)
        except ValueError:
            prevnode = None
        try: 
            nextnode = drone.node.get_single_related_node(neo4j.Direction.OUTGOING, self.ournexttype)
        except ValueError:
            nextnode = None

        # Clean out the next link relationships to our dearly departed drone
        ringrel = drone.node.get_single_relationship(neo4j.Direction.OUTGOING, self.ourreltype)
        ringrel.delete()
        ringrel = None
        if nextnode is None and prevnode is None:   # Previous length:  1
            self.insertpoint1 = None        # result length:    0
            self.insertpoint2 = None
            # No other database links to remove
            return

        # Clean out the next link relationships to our dearly departed drone
        relationships = drone.node.get_relationships('all', self.ournexttype)
        # Should have exactly two link relationships (one incoming and one outgoing)
        # BUT SOMETIMES WE DON'T -- then this crashes
        assert len(relationships) == 2
        for rel in relationships:
            rel.delete()
            rel = None
        relationships = None
        rel = None

        if prevnode.id == nextnode.id:          # Previous length:  2
            node = prevnode             # Result length:    1
            if node is None: node = nextnode
            partner = DroneInfo(node)
            drone.stop_heartbeat(self, partner)
            partner.stop_heartbeat(self, drone)
            #prevnode.create_relationship_to(nextnode, self.ournexttype)
            self.insertpoint2 = None
            self.insertpoint1 = partner
            return

        # Previous length had to be >= 3        # Previous length:  >=3
                            # Result length:    >=2
        prevdrone = DroneInfo(prevnode['name'])
        nextdrone = DroneInfo(nextnode['name'])
        nextnext = nextnode.get_single_related_node(neo4j.Direction.OUTGOING, self.ournexttype)
        prevdrone.stop_heartbeat(self, drone)
        nextdrone.stop_heartbeat(self, drone)
        if nextnext.id != prevnode.id:          # Previous length:  >= 4
            nextdrone.start_heartbeat(self, prevdrone)  # Result length:    >= 3
            prevdrone.start_heartbeat(self, nextdrone)
        # Poor drone -- all alone in the universe... (maybe even dead...)
        drone.stop_heartbeat(self, prevdrone, nextdrone)
        self.insertpoint1 = prevdrone   # non-minimal, but correct and cheap change
        self.insertpoint2 = nextdrone
        prevnode.create_relationship_to(nextnode, self.ournexttype)

    def members(self):
        ret = []
        for node in self.node.get_related_nodes(neo4j.Direction.INCOMING, self.ourreltype):
            ret.append(DroneInfo.find(node))
        return ret

    def membersfromlist(self):
        firstdrone=self.insertpoint1
        if firstdrone is None:
           return []
        ret = [firstdrone]
        firstdrone = firstdrone.node
        nextdrone = firstdrone
        while True:
            nextdrone = nextdrone.get_single_related_node(neo4j.Direction.OUTGOING, self.ournexttype)
            if nextdrone is None or nextdrone.id == firstdrone.id:  break
            ret.append(DroneInfo.find(nextdrone))
        return ret

    def __str__(self):
        ret = 'Ring("%s", [' % self.node['name']
        comma=''
        for drone in self.membersfromlist():
             ret += '%s%s' % (comma, drone.node['name'])
             comma=', '
        ret += '])'
        return ret
