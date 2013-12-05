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
This file implements Monitoring-related classes.

MonitorAction is a class that represents currently active monitoring actions.

MonitoringRule and its subclasses implement the logic to automatically create monitoring
rules for certain kinds of services automatically.
'''


from AssimCtypes import REQCLASSNAMEFIELD, REQTYPENAMEFIELD, REQPROVIDERNAMEFIELD        \
,   REQENVIRONNAMEFIELD, REQRSCNAMEFIELD, REQREPEATNAMEFIELD, REQTIMEOUTNAMEFIELD
from AssimCclasses import pyConfigContext
from frameinfo import FrameTypes, FrameSetTypes
from graphnodes import GraphNode, RegisterGraphClass
from droneinfo import Drone
from cmadb import CMAdb
from consts import CMAconsts
import re
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


class MonitoringRule:
    '''Abstract base class for implementing monitoring rules

    This particular class implements it for simple regex matching on arbitrary regexes
    on fields on ProcessNodes or Drones -- in reality on any set of graph nodes.

    The question is how many subclasses should there be?  It's obvious that we need to have
    specialized subclasses for Java, Python and other interpreted languages.
    What comes to mind to implement first is simple monitoring using LSB scripts.

    The reason for doing this is that they don't take any parameters, so all you have to do
    is match the pattern and then know what init script name is used for that service on that OS.

    It does vary by Linux distribution, for example...
    So... (cmd-pattern, arg-pattern, OS-pattern, distro-pattern) see to be the things that
    uniquely determine what init script to use to monitor that particular resource type.

    The second question that comes to mind is how to connect these rules into a rule
    hierarchy.

    For example, if the command name matches Java, then invoke the java rules.

    If a java rule matches Neo4j, then return the Neo4j monitoring action
        and so on...

    Note that for Java, the monitoring rule is likely to match the _last_ argument
        in the argument string...
            arg[-1] - python-style

    If it matches python, then match it against the second argument (arg[1])

    '''
    NOMATCH = 0
    PARTMATCH = 2
    LOWPRIOMATCH = 2
    HIGHPRIOMATCH = 3
    def __init__(self, tuplespec):
        '''It is constructed from an list of tuples, each one of which represents
        a field specification and a regular expression.  Each field expression
        is a specification to a GraphNode 'get' operation.  Each regular expression
        is a specification of a regex to match against the corresponding field
        expression (GraphNode.get()) operation.
        This rule can only apply if all the RegExes match.
        NOTE: It can still fail to apply even if the RegExes all match.
        '''
        self.tuplespec = []
        for tup in tuplespec:
            if len(tup) < 2 or len(tup) > 3:
                raise ValueError('Improperly formed constructor argument')
            if len(tup) == 3:
                regex = re.compile(tup[1], tup[2])
            else:
                regex = re.compile(tup[1])
            if regex is None:
                raise ValueError('Improperly formed regular expression')


    def specmatch(self, graphnodes):
        '''Return a MonitorAction if this rule can be applies to this particular set of GraphNodes
        Note that the GraphNodes that we're given at the present time are typically expected to be
        the Drone node for the node it's running on and the Process node for the process
        to be monitored.
        We return None on no match
        '''
        values = {}
        for tup in self.tuplespec:
            match = False
            for node in graphnodes:
                value = node.get(tup[0])
                if value is not None:
                    values[tup[0]] = value
                    match = True
                    continue
            if not match:
                return (MonitoringRule.NOMATCH, None)
        # We now have a complete set of values to match against our regexes...
        for tup in self.tuplespec:
            name = tup[0]
            regex = tup[1]
            if not regex.match(values[name]):
                return (MonitoringRule.NOMATCH, None)
        # We now have a matching set of values to give our monitoring constructor
        return self.constructaction(values)

    def constructaction(self, values):
        '''Return a tuple consisting of a tuple as noted:
            (MonitoringRule.PRIORITYVALUE, MonitorActionArgs, optional-information)
        If PRIORITYVALUE is NOMATCH, the MonitorAction will be None -- and vice versa

        If PRIORITYVALUE IS PARTMATCH, then more information is needed to determine
        exactly how to monitor it.  In this case, the optional-information element
        will be present and is a list the names of the fields whose values have to
        be supplied in order to monitor this service/host/resource.

        If PRIORITYVALUE is LOWPRIOMATCH or HIGHPRIOMATCH, then there is no optional-information
        element in the tuple.

        A LOWPRIOMATCH method of monitoring is presumed to do a minimal form of monitoring.
        A HIGHPRIOMATCH method of monitoring is presumed to do a more complete job of
        monitoring - presumably acceptable, and preferred over a LOWPRIOMATCH.

        The caller still needs to come up with these arguments for the MonitorAction constructor
            monitorname - a unique name for this monitoring action
            interval - how often to run this monitoring action
            timeout - what timeout to use before declaring monitoring failure

        Not that the implementation in the base class does nothing, and will result in
        raising a NotImplementedError exception.
        '''
        raise NotImplementedError('Abstract class')

class LSBMonitoringRule(MonitoringRule):

    '''Class for implementing monitoring rules for sucky LSB style init script monitoring
    '''
    def __init__(self, servicename, tuplespec):
        self.servicename = servicename
        MonitoringRule.__init__(self, tuplespec)

    def constructaction(self, values):
        '''Construct arguments
        '''
        return (MonitoringRule.LOWPRIOMATCH
        ,       {   'monitorclass': 'lsb'
                ,   'monitortype':  self.servicename
                ,   'provider':     None
                ,   'arglist':      None}
        )

#
# abstract class only referenced once
# pylint: disable=R0922,R0922
class OCFMonitoringRule(MonitoringRule):
    '''Class for implementing monitoring rules for OCF style init script monitoring
    OCF ==  Open Cluster Framework

    Not really implemented yet ;-)
    '''

    def constructaction(self, values):
        '''Construct arguments
        '''
        return (MonitoringRule.NOMATCH, None)
