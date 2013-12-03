#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2013 Assimilation Systems Limited - author Alan Robertson <alanr@unix.sh>
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
'''
This file implements the MonitorAction class.
MonitorAction is a class that represents currently active monitoring actions.
'''


from AssimCtypes import REQCLASSNAMEFIELD, REQTYPENAMEFIELD, REQPROVIDERNAMEFIELD        \
,   REQENVIRONNAMEFIELD, REQRSCNAMEFIELD, REQREPEATNAMEFIELD, REQTIMEOUTNAMEFIELD
from AssimCclasses import pyConfigContext
from frameinfo import FrameTypes, FrameSetTypes
from graphnodes import GraphNode, RegisterGraphClass
from droneinfo import Drone
from cmadb import CMAdb
from consts import CMAconsts
#
#
@RegisterGraphClass
class MonitorAction(GraphNode):
    '''Class representing monitoring actions
    '''
    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of significance (sort order)'
        return ['monitorname', 'domain']


    # R0913: too many arguments
    # pylint: disable=R0913
    def __init__(self, domain, monitorname, monitorclass, monitortype, interval
    ,   timeout, provider=None, arglist=None):
        'Create the requested monitoring rule object.'
        GraphNode.__init__(self, domain)
        self.monitorname = monitorname
        self.monitorclass = monitorclass
        self.monitortype = monitortype
        self.interval = interval
        self.timeout = timeout
        self.provider = provider
        self.arglist = arglist
        self.isactive = False

    def activate(self, monitoredentity, runon=None):
        '''Relate this monitoring action to the given entity, and start it on the 'runon' system
          Parameters
          ----------
          monitoredentity : GraphNode
                The graph node which we are monitoring
          runon : Drone
                The particular Drone which is running this monitoring action.
                Defaults to 'monitoredentity'
        '''
        if runon is None:
            runon = monitoredentity
        assert isinstance(monitoredentity, GraphNode)
        assert isinstance(runon, Drone)
        CMAdb.store.relate_new(self, CMAconsts.REL_monitoring, monitoredentity)
        CMAdb.store.relate_new(runon, CMAconsts.REL_hosting, self)
        reqjson = self.construct_mon_json()
        CMAdb.transaction.add_packet(runon.primary_ip(), FrameSetTypes.DORSCOP, reqjson
        ,   frametype=FrameTypes.RSCJSON)
        self.isactive = True
        
    def deactivate(self):
        '''Deactivate this monitoring action. Does not remove relationships from the graph'''
        reqjson = self.construct_mon_json()
        for drone in CMAdb.store.load_related(self, CMAconsts.REL_hosting, Drone):
            CMAdb.transaction.add_packet(drone.primary_ip(), FrameSetTypes.STOPRSCOP
            ,   reqjson, frametype=FrameTypes.RSCJSON)
        self.isactive = False

    def construct_mon_json(self):
        '''
          Parameters
          ----------
          Returns
          ----------
          JSON string representing this particular monitor action.
          '''
        if self.arglist is None:
            arglist_str = ''
        else:
            arglist_str = ', "%s": [' % (REQENVIRONNAMEFIELD)
            comma = ''
            for arg in self.arglist:
                arglist_str += '%s"%s"' % (comma, str(arg))
                comma = ','
            arglist_str += ']'

        if self.provider is None:
            provider_str = ''
        else:
            provider_str = ', "%s":"%s"' % (REQPROVIDERNAMEFIELD, self.provider)

        json = '{"%s":"%s", "%s":"%s", "%s":"%s", "%s":%d, "%s":%d%s%s}' % \
        (   REQCLASSNAMEFIELD, self.monitorclass
        ,   REQTYPENAMEFIELD, self.monitortype
        ,   REQRSCNAMEFIELD, self.monitorname
        ,   REQREPEATNAMEFIELD, self.interval
        ,   REQTIMEOUTNAMEFIELD, self.timeout
        ,   provider_str, arglist_str)
        return str(pyConfigContext(init=json))

if __name__ == '__main__':
    mon = MonitorAction('global', 'DummyName', 'OCF', 'Dummy', 1, 120, provider='heartbeat')
    print mon.construct_mon_json()
