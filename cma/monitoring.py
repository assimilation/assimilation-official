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

#
#
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
                arg[__last__]...  Maybe that would be a good choice??

    If it matches python, then match it against the second argument (arg[1])

    '''
    rulelist = []

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of significance'
        return ['designation', 'domain']

    def __init__(self):
        'Register this rule in the rule registry'
        MonitoringRules.register(self)

    def makerule(self, service, servicehost, monitorrunningon=None):
        raise NotImplementedError('abstract class (MonitoringRules)')
        return False


    def construct_mon_json(self, monitorclass, monitortype, monitorname, interval, timeout, provider=None, arglist=None):
        '''Add
          Parameters
          ----------
          monitorclass : str
                The class of monitoring agent being invoked
          monitortype : str
                Which particular agent of class 'class' is being invoked to monitor the resource
          monitorname : str
                The name of this instance of resource being monitored
          interval : int
                The number of seconds between monitor operations
          timeout : int
                The maximum number of seconds to wait before declaring the monitor failed
          provider : str, optional
                The provider name (required for OCF agents, ignored otherwise).
          arglist : dict-like, optional
                A list of name/value pairs to be given to the resource agent
                Currently only supported by OCF agents.

          Returns
          ----------
          pyConfigContext object (whose __str__ method returns JSON).
          '''
        if arglist is None:
            arglist_str = ''
        else:
            arglist_str = ', "%s": %s' % (REQENVIRONNAMEFIELD, str(pyConfigContext(init=arglist)))

        if provider is None:
            provider_str = ''
        else:
            provider_str = ', "%s":"%s"' % (REQPROVIDERNAMEFIELD, provider)


        json = '{"%s":"%s", "%s":"%s", "%s":"%s", "%s":%d "%s":%d%s%s}' % (
        REQCLASSNAMEFIELD, monitorclass,
        REQTYPENAMEFIELD, monitortype,
        REQRSCNAMEFIELD, monitorname,
        REQREPEATNAMEFIELD, interval,
        REQTIMEOUTNAMEFIELD, timeout,
        provider_str, arglist_str)
        return pyConfigContext(init=json)
        
        

    @staticmethod
    def createamonitoringrule(cls, service, monitorclass, monitortype, monitorname
    ,           interval, timeout, monitorrunningon, arglist=None, provider=None):
        '''Add rules for the requested kind of monitoring method to the graph,
        and give it to the nanoprobe.
        We have several steps to perform here:
          1) Create monitor-action node in the graph
          2) Relate the monitor-action node to the service
          3) Relate the monitor-action node to the monitorrunningon node
          4) Send the repeating monitor action to the monitorrunningon Drone

          Parameters
          ----------
          cls : Class
                The class which this node should be created for if it does not exist
          service : GraphNode
                The graph node which represents the entity to be monitored
          monitorclass : str
                The class of monitoring agent being invoked
          monitortype : str
                Which particular agent of class 'class' is being invoked to monitor the resource
          monitorname : str
                The name of this monitoring action
          interval : int
                The number of seconds between monitor operations
          timeout : int
                The maximum number of seconds to wait before declaring the monitor failed
          monitorrunningon : Drone
                The Drone graph node which runs this particular agent
          arglist : dict-like, optional
                A list of name/value pairs to be given to the resource agent
          provider : str, optional
                The provider name (required for OCF agents, ignored otherwise).

          Returns
          ----------
          None
        '''
        pass


    @staticmethod
    def register(ruleobj):
        rulelist.append(ruleobj)

    @staticmethod
    def makearule(service, servicehost, monitorrunningon=None):
        if monitoringrunningon is None:
            monitoringrunningon=servicehost
        for rule in rulelist:
            if rule.makerule(service, servicehost, monitorrunningon):
                return True
        return False

class MonitorLSB(MonitoringRules):
    '''Class for automatically creating monitoring rules for LSB services'''

    def __init__(self, servicename, exepattern, interval, timeout
        ,   casesensitive=True, monclass='lsb'):
        '''If the exe for the service being monitored matches our regex, then we add a rule
        for monitoring it using the status operation of the service.
        This kind of monitoring only works <i>on</i> the machine where the service is running
        - not over the network.
        '''
        self.servicename=servicename
        self.monclass=monclass
        flags = 0
        if not casesensitive:
            flags=re.IGNORECASE
        self.regex = re.compile(exepattern, flags)
        self.servicename = servicename
        MonitoringRules.__init__(self)

    def makerule(self, service, servicehost=None, monitorrunningon=None):
        'Add a monitoring rule if this matches our (compiled) regular expression'
        if monitoringrunningon is None:
            monitoringrunningon=servicehost
        if servicehost is None or monitorrunningon is not servicehost:
            return False
        exename = service['exe']
        if self.regex.match(exename) is not None:
            self.createamonitoringrule(self.monclass, self.servicename)
            return True
        return False

if __name__ == '__main__':
    mon = MonitorAction('global', 'DummyName', 'OCF', 'Dummy', 1, 120, provider='heartbeat')
    print mon.construct_mon_json()

