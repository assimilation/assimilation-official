#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2013,2014 Assimilation Systems Limited - author Alan Robertson <alanr@unix.sh>
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


from AssimCtypes import REQCLASSNAMEFIELD, CONFIGNAME_TYPE, REQPROVIDERNAMEFIELD       \
,   REQENVIRONNAMEFIELD, CONFIGNAME_INSTANCE, REQREASONENUMNAMEFIELD, CONFIGNAME_INTERVAL    \
,   CONFIGNAME_TIMEOUT ,   REQOPERATIONNAMEFIELD, REQIDENTIFIERNAMEFIELD               \
,   REQRCNAMEFIELD, REQSIGNALNAMEFIELD                                                  \
,   EXITED_TIMEOUT, EXITED_SIGNAL, EXITED_NONZERO, EXITED_HUNG, EXITED_ZERO
from AssimCclasses import pyConfigContext
from frameinfo import FrameTypes, FrameSetTypes
from graphnodes import GraphNode, RegisterGraphClass
from graphnodeexpression import GraphNodeExpression, ExpressionContext
from assimevent import AssimEvent
from cmadb import CMAdb
from consts import CMAconsts
import os, re, time
import sys
from py2neo import neo4j
from store import Store
#
#
# too many instance attributes
# pylint: disable=R0902
@RegisterGraphClass
class MonitorAction(GraphNode):
    '''Class representing monitoring actions
    '''
    request_id = time.time()
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
        self.interval = int(interval)
        self.timeout = int(timeout)
        self.provider = provider
        self.isactive = False
        self.isworking = True
        self.reason = 'initial monitor creation'
        self.request_id = MonitorAction.request_id
        MonitorAction.request_id += 1
        if arglist is None:
            self.arglist = None
            self._arglist = {}
        elif isinstance(arglist, list):
            listlen = len(arglist)
            if (listlen % 2) != 0:
                raise(ValueError('arglist list must have an even number of elements'))
            self._arglist = {}
            for j in range(0, listlen, 2):
                self._arglist[arglist[j]] = arglist[j+1]
            self.arglist = arglist
        else:
            self._arglist = arglist
            self.arglist = []
            for name in self._arglist:
                self.arglist.append(name)
                self.arglist.append(str(self._arglist[name]))

    def longname(self):
        'Return a long name for the type of monitoring this rule provides'
        if self.provider is not None:
            return '%s::%s:%s' % (self.monitorclass, self.provider, self.monitortype)
        return '%s:%s' % (self.monitorclass, self.monitortype)

    def shortname(self):
        'Return a short name for the type of monitoring this rule provides'
        return self.monitortype

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
        from droneinfo import Drone
        if runon is None:
            runon = monitoredentity
        assert isinstance(monitoredentity, GraphNode)
        assert isinstance(runon, Drone)
        CMAdb.store.relate_new(self, CMAconsts.REL_monitoring, monitoredentity)
        CMAdb.store.relate_new(runon, CMAconsts.REL_hosting, self)
        if self.monitorclass == 'NEVERMON':
            # NEVERMON is a class that doesn't monitor anything
            # A bit like the The Pirates Who Don't Do Anything
            # So, we create the node in the graph, but don't activate it, don't
            # send a message to the server to try and monitor it...
            #       And we never go to Boston in the fall...
            CMAdb.log.info("Avast! Those Scurvy 'Pirates That Don't Do Anything'"
            " spyed lounging around on %s"
            %   (str(runon)))
        else:
            reqjson = self.construct_mon_json()
            CMAdb.transaction.add_packet(runon.destaddr(), FrameSetTypes.DORSCOP, reqjson
            ,   frametype=FrameTypes.RSCJSON)
            self.isactive = True
        CMAdb.log.info('Monitoring of service %s activated' % (self.monitorname))

    def deactivate(self):
        '''Deactivate this monitoring action. Does not remove relationships from the graph'''
        from droneinfo import Drone
        reqjson = self.construct_mon_json()
        for drone in CMAdb.store.load_related(self, CMAconsts.REL_hosting, Drone):
            CMAdb.transaction.add_packet(drone.primary_ip(), FrameSetTypes.STOPRSCOP
            ,   reqjson, frametype=FrameTypes.RSCJSON)
        self.isactive = False


    findquery = None
    @staticmethod
    def find(name, domain=None):
        'Iterate through a series of MonitorAction nodes matching the criteria'
        if MonitorAction.findquery is None:
            cypher = 'START m=node:MonitorAction({q}) RETURN m'
            MonitorAction.findquery = neo4j.CypherQuery(CMAdb.store.db, cypher)
        name = Store.lucene_escape(name)
        qvalue = '%s:%s' % (name, '*' if domain is None else domain)
        return CMAdb.store.load_cypher_nodes(MonitorAction.findquery, MonitorAction
        ,   params={'q': qvalue})

    @staticmethod
    def find1(name, domain=None):
        'Return the MonitorAction node matching the criteria'
        for ret in MonitorAction.find(name, domain):
            return ret
        return None

    @staticmethod
    def logchange(origaddr, monmsgobj):
        '''
        Make the necessary changes to the monitoring data when a particular
        monitoring action changes status (to success or to failure)
        This includes locating the MonitorAction object in the database.

        Parameters
        ----------
        origaddr: pyNetAddr
            address where monitoring action originated
        monmsgobj: pyConfigContext
            object containing the monitoring message
        '''

        rscname = monmsgobj[CONFIGNAME_INSTANCE]
        monnode = MonitorAction.find1(rscname)
        if monnode is None:
            CMAdb.log.critical('Could not locate monitor node for %s from %s'
            %   (str(monmsgobj), str(origaddr)))
        else:
            monnode.monitorchange(origaddr, monmsgobj)

    def monitorchange(self, origaddr, monmsgobj):
        '''
        Make the necessary changes to the monitoring data when a particular
        monitoring action changes status (to success or to failure)

        Parameters
        ----------
        origaddr: pyNetAddr
            address where monitoring action originated
        monmsgobj: pyConfigContext
            object containing the monitoring message
        '''
        success = False
        fubar = False
        reason_enum = monmsgobj[REQREASONENUMNAMEFIELD]
        if reason_enum == EXITED_ZERO:
            success = True
            explanation = 'is now operational'
        elif reason_enum == EXITED_NONZERO:
            explanation = 'monitoring failed with return code %s' % monmsgobj[REQRCNAMEFIELD]
        elif reason_enum == EXITED_SIGNAL:
            explanation = 'monitoring was killed by signal %s' % monmsgobj[REQSIGNALNAMEFIELD]
        elif reason_enum == EXITED_HUNG:
            explanation = 'monitoring could not be killed'
        elif reason_enum == EXITED_TIMEOUT:
            explanation = 'monitoring timed out'
        else:
            explanation = 'GOT REAL WEIRD'
            fubar = True
        rscname = monmsgobj[CONFIGNAME_INSTANCE]
        msg = 'Service %s %s' % (rscname, explanation)
        self.isworking = success and not fubar
        self.reason = explanation
        print >> sys.stderr, 'MESSAGE:', msg
        if fubar:
            CMAdb.log.critical(msg)
        else:
            extrainfo = {'comment': explanation, 'origaddr': origaddr
            ,   'resourcename': rscname, 'monmsg': monmsgobj}
            if success:
                CMAdb.log.info(msg)
                AssimEvent(self, AssimEvent.OBJUP, extrainfo=extrainfo)
            else:
                CMAdb.log.warning(msg)
                AssimEvent(self, AssimEvent.OBJDOWN, extrainfo=extrainfo)


    def construct_mon_json(self, operation='monitor'):
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
            arglist_str = ', "%s": {' % (REQENVIRONNAMEFIELD)
            comma = ''
            for arg in self._arglist:
                arglist_str += '%s"%s":"%s"' % (comma, str(arg)
                ,   str(self._arglist[arg]))
                comma = ', '
            arglist_str += '}'

        if self.provider is None:
            provider_str = ''
        else:
            provider_str = ', "%s":"%s"' % (REQPROVIDERNAMEFIELD, self.provider)

        json = '{"%s": %d, "%s":"%s", "%s":"%s", "%s":"%s", "%s":"%s", "%s":%d, "%s":%d%s%s}' % \
        (   REQIDENTIFIERNAMEFIELD, self.request_id
        ,   REQOPERATIONNAMEFIELD, operation
        ,   REQCLASSNAMEFIELD, self.monitorclass
        ,   CONFIGNAME_TYPE, self.monitortype
        ,   CONFIGNAME_INSTANCE, self.monitorname
        ,   CONFIGNAME_INTERVAL, self.interval
        ,   CONFIGNAME_TIMEOUT, self.timeout
        ,   provider_str, arglist_str)
        return str(pyConfigContext(init=json))


class MonitoringRule(object):
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
    NOMATCH = 0         # Did not match this rule
    NEVERMATCH = 1      # Matched this 'un-rule' - OK not to monitor this service
    PARTMATCH = 2       # Partial match - we match this rule, but need more config info
    LOWPRIOMATCH = 3    # We match - but we aren't a very good monitoring method
    HIGHPRIOMATCH = 4   # We match and we are a good monitoring method

    monitorobjects = {}

    def __init__(self, monitorclass, tuplespec):
        '''It is constructed from an list of tuples, each one of which represents
        a value expression and a regular expression.  Each value expression
        is a specification to a GraphNode 'get' operation.  Each regular expression
        is a specification of a regex to match against the corresponding field
        expression.  By default, all regexes are anchored (implicitly start with ^)
        This rule can only apply if all the RegExes match.
        NOTE: It can still fail to apply even if the RegExes all match.
        '''
        if tuplespec is None or len(tuplespec) == 0:
            raise ValueError('Improper tuplespec')

        self.monitorclass = monitorclass
        self._tuplespec = []
        for tup in tuplespec:
            if len(tup) < 2 or len(tup) > 3:
                raise ValueError('Improperly formed constructor argument')
            try:
                if len(tup) == 3:
                    flags = tup[2]
                    regex = re.compile(tup[1], flags)
                else:
                    regex = re.compile(tup[1])
            except:
                raise ValueError('Improperly formed regular expression: %s'
                %   tup[1])
            self._tuplespec.append((tup[0], regex))

        # Register us in the grand and glorious set of all monitoring rules
        if monitorclass not in MonitoringRule.monitorobjects:
            MonitoringRule.monitorobjects[monitorclass] = []
        MonitoringRule.monitorobjects[monitorclass].append(self)


    def specmatch(self, context):
        '''Return a MonitorAction if this rule can be applies in this context (GraphNodes)
        Note that the GraphNodes that we're given at the present time are typically expected to be
        the Drone node for the node it's running on and the Process node for the process
        to be monitored.
        We return (MonitoringRule.NOMATCH, None) on no match
        '''
        #print >> sys.stderr, 'SPECMATCH BEING EVALED:', self._tuplespec, self.__class__
        for tup in self._tuplespec:
            expression = tup[0]
            value = GraphNodeExpression.evaluate(expression, context)
            if value is None:
                #print >> sys.stderr, 'NOMATCH from expression', expression
                return (MonitoringRule.NOMATCH, None)
        # We now have a complete set of values to match against our regexes...
        for tup in self._tuplespec:
            name = tup[0]
            regex = tup[1]
            #print >> sys.stderr, 'TUPLE BEING EVALED:', name, regex.pattern
            val = GraphNodeExpression.evaluate(name, context)
            #print >> sys.stderr, 'EXPRESSION %s => %s' % (name, val)
            if not isinstance(val, (str, unicode)):
                val = str(val)
            if not regex.match(val):
                #print >> sys.stderr, 'NOMATCH from regex [%s] [%s]' % (regex.pattern, val)
                return (MonitoringRule.NOMATCH, None)
        # We now have a matching set of values to give our monitoring constructor
        #print >> sys.stderr, 'CALLING CONSTRUCTACTION:', self._tuplespec
        ret =  self.constructaction(context)
        #print >> sys.stderr, 'CONSTRUCTACTION => %s' % str(ret)
        return ret



    def constructaction(self, context):
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
        a NEVERMATCH match means that we know about this type of service, and
        that it's OK for it to not be monitored.

        MonitorActionArgs is a hash table giving the values of the various arguments
        that you need to give to the MonitorAction constuctor.  It will always supply
        the values of the monitorclass and monitortype argument.  If needed, it will
        also supply the values of the provider and arglist arguments.

        If PRIORITYVALUE is PARTMATCH, then it will supply an incomplete 'arglist' value.
        and optional-information list consists of a list of those arguments whose values
        cannot be determined automatically from the given value set.

        The caller still needs to come up with these arguments for the MonitorAction constructor
            monitorname - a unique name for this monitoring action
            interval - how often to run this monitoring action
            timeout - what timeout to use before declaring monitoring failure

        Not that the implementation in the base class does nothing, and will result in
        raising a NotImplementedError exception.
        '''
        raise NotImplementedError('Abstract class')

    @staticmethod
    def ConstructFromString(s):
        '''
        Construct a MonitoringRule from a string parameter.
        It will construct the appropriate subclass depending on its input
        string.  Note that the input is JSON -- with whole-line comments.
        A whole line comment has to _begin_ with a #.
        '''
        obj = pyConfigContext(s)
        #print >> sys.stderr, 'CONSTRUCTING MONITORING RULE FROM', obj
        if obj is None:
            raise ValueError('Invalid JSON: %s' % s)
        if 'class' not in obj:
            raise ValueError('Must have class value')
        legit = {'ocf':
                    {'class': True, 'type': True, 'classconfig': True, 'provider': True},
                 'lsb':
                    {'class': True, 'type': True, 'classconfig': True},
                 'NEVERMON':
                    {'class': True, 'type': True, 'classconfig': True}
                }
        rscclass = obj['class']
        if rscclass not in legit:
            raise ValueError('Illegal class value: %s' % rscclass)

        l = legit[obj['class']]
        for key in l.keys():
            if l[key] and key not in obj:
                raise ValueError('%s object must have %s field' % (rscclass, key))
        for key in obj.keys():
            if key not in l:
                raise ValueError('%s object cannot have a %s field' % (rscclass, key))

        if rscclass == 'lsb':
            return LSBMonitoringRule(obj['type'], obj['classconfig'])
        if rscclass == 'ocf':
            return OCFMonitoringRule(obj['provider'], obj['type'], obj['classconfig'])
        if rscclass == 'NEVERMON':
            return NEVERMonitoringRule(obj['type'], obj['classconfig'])

        raise ValueError('Invalid resource class ("class" = "%s")' % rscclass)

    @staticmethod
    def compute_available_agents(context):
        '''Create a cache of all our available monitoring agents - and return it'''
        for node in context.objects:
            if not hasattr(node, 'JSON_monitoringagents'):
                continue
            if hasattr(node, '_agentcache'):
                # Keep pylint from getting irritated...
                return getattr(node, '_agentcache')
            agentobj = pyConfigContext(node.JSON_monitoringagents)
            agentobj = agentobj['data']
            ret = {}
            for cls in agentobj.keys():
                agents = agentobj[cls]
                for agent in agents:
                    if cls not in ret:
                        ret[cls] = {}
                    ret[cls][agent] = True
            setattr(node, '_agentcache', ret)
            #print >> sys.stderr, 'AGENT CACHE IS ', ret
            return ret
        return {}


    @staticmethod
    def findbestmatch(context, preferlowoverpart=True):
        '''
        Find the best match among the complete collection of MonitoringRules
        against this particular set of graph nodes.

        Return value
        -------------
        A tuple of (priority, config-info).  When we can't find anything useful
        in the complete set of rules, we return (MonitoringRule.NOMATCH, None)

        Parameters
        ----------
        context: ExpressionContext
            The set of graph nodes with relevant attributes.  This is normally the
                     ProcessNode being monitored and the Drone the services runs on
        preferlowoverpath: Bool
            True if you the caller prefers a LOWPRIOMATCH result over a PARTMATCH result.
            This should be True for automated monitoring and False for possibly manually
            configured monitoring.  The default is to assume that we'd rather
            automated monitoring running now over finding a human to fill in the
            other parameters.

            Of course, we always prefer a HIGHPRIOMATCH monitoring method.
        '''
        rsctypes = ['ocf', 'lsb', 'NEVERMON'] # Priority ordering...
        # This will make sure the priority list above is maintained :-D
        if len(rsctypes) < len(MonitoringRule.monitorobjects.keys()):
            raise RuntimeError('Update rsctypes list in findbestmatch()!')

        bestmatch = (MonitoringRule.NOMATCH, None)

        # Search the rule types in priority order
        for rtype in rsctypes:
            if rtype not in MonitoringRule.monitorobjects:
                continue
            # Search every rule of class 'rtype'
            for rule in MonitoringRule.monitorobjects[rtype]:
                match = rule.specmatch(context)
                #print >> sys.stderr, 'GOT A MATCH------------->', match
                prio = match[0]
                if prio == MonitoringRule.NOMATCH:
                    continue
                if prio == MonitoringRule.HIGHPRIOMATCH:
                    return match
                bestprio = bestmatch[0]
                if bestprio == MonitoringRule.NOMATCH:
                    bestmatch = match
                    continue
                if prio == bestprio:
                    continue
                # We have different priorities - which do we prefer?
                if preferlowoverpart:
                    if prio == MonitoringRule.LOWPRIOMATCH:
                        bestmatch = match
                elif prio == MonitoringRule.PARTMATCH:
                    bestmatch = match
        return bestmatch

    @staticmethod
    def findallmatches(context):
        '''
        We return all possible matches as seen by our complete and wonderful set of
        MonitoringRules.
        '''
        result = []
        keys = MonitoringRule.monitorobjects.keys()
        keys.sort()
        for rtype in keys:
            for rule in MonitoringRule.monitorobjects[rtype]:
                match = rule.specmatch(context)
                if match[0] != MonitoringRule.NOMATCH:
                    result.append(match)
        return result


    @staticmethod
    def ConstructFromFileName(filename):
        '''
        Construct a MonitoringRule from a filename parameter.
        It will construct the appropriate subclass depending on its input
        string.  Note that the input is JSON -- with # comments.
        '''
        f = open(filename, 'r')
        s = f.read()
        f.close()
        return MonitoringRule.ConstructFromString(s)

    @staticmethod
    def load_tree(rootdirname, pattern=r".*\.mrule$", followlinks=False):
        '''
        Add a set of MonitoringRules to our universe from a directory tree
        using the ConstructFromFileName function.
        Return: None
        '''
        tree = os.walk(rootdirname, topdown=True, onerror=None, followlinks=followlinks)
        pat = re.compile(pattern)
        for walktuple in tree:
            (dirpath, dirnames, filenames) = walktuple
            dirnames.sort()
            filenames.sort()
            for filename in filenames:
                if not pat.match(filename):
                    continue
                path = os.path.join(dirpath, filename)
                MonitoringRule.ConstructFromFileName(path)

class LSBMonitoringRule(MonitoringRule):

    '''Class for implementing monitoring rules for sucky LSB style init script monitoring
    '''
    def __init__(self, servicename, tuplespec):
        self.servicename = servicename
        MonitoringRule.__init__(self, 'lsb', tuplespec)

    def constructaction(self, context):
        '''Construct arguments
        '''
        agentcache = MonitoringRule.compute_available_agents(context)
        if 'lsb' in agentcache and self.servicename not in agentcache['lsb']:
            return (MonitoringRule.NOMATCH, None)
        return (MonitoringRule.LOWPRIOMATCH
        ,       {   'monitorclass': 'lsb'
                ,   'monitortype':  self.servicename
                ,   'rscname':      'lsb_' + self.servicename # There can only be one
                ,   'provider':     None
                ,   'arglist':      None}
        )

class NEVERMonitoringRule(MonitoringRule):

    '''Class for implementing monitoring rules for things that should never be monitored
    This is mostly things like Skype and friends which are started by users not
    by the system.
    '''
    def __init__(self, servicename, tuplespec):
        self.servicename = servicename
        MonitoringRule.__init__(self, 'NEVERMON', tuplespec)

    def constructaction(self, context):
        '''Construct arguments
        '''
        return (MonitoringRule.NEVERMATCH
        ,       {   'monitorclass': 'NEVERMON'
                ,   'monitortype':  self.servicename
                ,   'provider':     None
                ,   'arglist':      None}
        )

class OCFMonitoringRule(MonitoringRule):
    '''Class for implementing monitoring rules for OCF style init script monitoring
    OCF ==  Open Cluster Framework
    '''
    def __init__(self, provider, rsctype, triplespec):
        '''
        Parameters
        ----------
        provider: str
            The OCF provider name for this resource
            This is the directory name this resource is found in
        rsctype: str
            The OCF resource type for this resource (service)
            This is the same as the script name for the resource

        triplespec: list
            Similar to but wider than the MonitoringRule tuplespec
            (name,  expression, regex,  regexflags(optional))

            'name' is the name of an OCF RA parameter or None or '-'
            'expression' is an expression for computing the value for that name
            'regex' is a regular expression that the value of 'expression' has to match
            'regexflags' is the optional re flages for 'regex'

            If there is no name to go with the tuple, then the name is given as None or '-'
            If there is no regular expression to go with the name, then the expression
                and remaining tuple elements are missing.  This can happen if there
                is no mechanical way to determine this value from discovery information.
            If there is a name and expression but no regex, the regex is assumed to be '.'
        '''
        self.provider = provider
        self.rsctype = rsctype
        self.nvpairs = {}
        tuplespec = []

        for tup in triplespec:
            tuplen = len(tup)
            if tuplen == 4:
                (name, expression, regex, flags) = tup
                if regex is not None:
                    tuplespec.append((expression, regex, flags))
            elif tuplen == 3:
                (name, expression, regex) = tup
                if regex is not None:
                    tuplespec.append((expression, regex))
            elif tuplen == 2:
                (name, expression) = tup
            elif tuplen == 1:
                name = tup[0]
                expression = None
            else:
                raise ValueError('Invalid tuple length (%d)' % tuplen)
            if name is not None and name != '-':
                self.nvpairs[name] = expression
        MonitoringRule.__init__(self, 'ocf', tuplespec)


    def constructaction(self, context):
        '''Construct arguments to give MonitorAction constructor
            We can either return a complete match (HIGHPRIOMATCH)
            or an incomplete match (PARTMATCH) if we can't find
            all the parameter values in the nodes we're given
            We can also return NOMATCH if some things don't match
            at all.
        '''
        agentcache = MonitoringRule.compute_available_agents(context)
        agentpath = '%s/%s' % (self.provider, self.rsctype)
        if 'ocf' in agentcache and agentpath not in agentcache['ocf']:
            return (MonitoringRule.NOMATCH, None)
        #
        missinglist = []
        arglist = {}
        # Figure out what we know how to supply and what we need to ask
        # a human for -- in order to properly monitor this resource
        for name in self.nvpairs:
            if name.startswith('?'):
                optional = True
                exprname = name[1:]
            else:
                optional = False
                exprname=name
            expression = self.nvpairs[name]
            val = GraphNodeExpression.evaluate(expression, context)
            #print >> sys.stderr, 'CONSTRUCTACTION.eval(%s) => %s' % (expression, val)
            if val is None and not optional:
                missinglist.append(exprname)
            else:
                arglist[exprname] = str(val)
        if len(missinglist) == 0:
            # Hah!  We can automatically monitor it!
            return  (MonitoringRule.HIGHPRIOMATCH
                    ,    {   'monitorclass': 'ocf'
                            ,   'monitortype':  self.rsctype
                            ,   'provider':     self.provider
                            ,   'arglist':      arglist
                        }
                    )
        else:
            # We can monitor it with some more help from a human
            # Better incomplete than a sharp stick in the eye ;-)
            return (MonitoringRule.PARTMATCH
                    ,   {   'monitorclass': 'ocf'
                            ,   'monitortype':  self.rsctype
                            ,   'provider':     self.provider
                            ,   'arglist':      arglist
                        }
                    ,   missinglist
                    )

if __name__ == '__main__':
    from graphnodes import ProcessNode
    neolsbargs = (
                ('$argv[0]', r'.*/[^/]*java[^/]*$'),   # Might be overkill
                ('$argv[3]', r'-server$'),             # Probably overkill
                ('$argv[-1]', r'org\.neo4j\.server\.Bootstrapper$'),
        )
    neorule = LSBMonitoringRule('neo4j-service', neolsbargs)
    neolsbargs = (
                ('$argv[0]', r'.*/[^/]*java[^/]*$'),   # Might be overkill
                ('$argv[3]', r'-server$'),             # Probably overkill
                ('$argv[-1]', r'org\.neo4j\.server\.Bootstrapper$'),
        )
    neoocfargs = (
        (None,          "@basename()",               "java$"),
        (None,          "$argv[-1]",                 "org\\.neo4j\\.server\\.Bootstrapper$"),
        #("ipport",      "@serviceipport()",          "..."),
        ("neo4j_home",  "@argequals(-Dneo4j.home)", "/"),
        ("neo4j",       "@basename(@argequals(-Dneo4j.home))",".")
    )
    neoocfrule = OCFMonitoringRule('assimilation', 'neo4j', neoocfargs)

    #ProcessNode:
    #   (domain, processname, host, pathname, argv, uid, gid, cwd, roles=None):
    sshnode = ProcessNode('global', 'fred', 'servidor', '/usr/bin/sshd', ['/usr/bin/sshd', '-D' ]
    ,   'root', 'root', '/', roles=(CMAconsts.ROLE_server,))

    sshargs = (
                # This means one of our nodes should have a value called
                # pathname, and it should end in '/sshd'
                ('$pathname', '.*/sshd$'),
        )
    sshrule = LSBMonitoringRule('ssh', sshargs)

    udevnode = ProcessNode('global', 'fred', 'servidor', '/usr/bin/udevd', ['/usr/bin/udevd']
    ,   'root', 'root', '/', roles=(CMAconsts.ROLE_server,))


    neoprocargs = ("/usr/bin/java", "-cp"
    , "/var/lib/neo4j/lib/concurrentlinkedhashmap-lru-1.3.1.jar:"
    "/var/lib/neo4j/lib/geronimo-jta_1.1_spec-1.1.1.jar:/var/lib/neo4j/lib/lucene-core-3.6.2.jar"
    ":/var/lib/neo4j/lib/neo4j-cypher-2.0.0-M04.jar"
    ":/var/lib/neo4j/lib/neo4j-graph-algo-2.0.0-M04.jar"
    ":/var/lib/neo4j/lib/neo4j-graph-matching-2.0.0-M04.jar"
    ":/var/lib/neo4j/lib/neo4j-jmx-2.0.0-M04.jar"
    ":/var/lib/neo4j/lib/neo4j-kernel-2.0.0-M04.jar"
    ":/var/lib/neo4j/lib/neo4j-lucene-index-2.0.0-M04.jar"
    ":/var/lib/neo4j/lib/neo4j-shell-2.0.0-M04.jar"
    ":/var/lib/neo4j/lib/neo4j-udc-2.0.0-M04.jar"
    "/var/lib/neo4j/system/lib/neo4j-server-2.0.0-M04-static-web.jar:"
    "AND SO ON:"
    "/var/lib/neo4j/system/lib/slf4j-api-1.6.2.jar:"
    "/var/lib/neo4j/conf/", "-server", "-XX:"
    "+DisableExplicitGC"
    ,   "-Dorg.neo4j.server.properties=conf/neo4j-server.properties"
    ,   "-Djava.util.logging.config.file=conf/logging.properties"
    ,   "-Dlog4j.configuration=file:conf/log4j.properties"
    ,   "-XX:+UseConcMarkSweepGC"
    ,   "-XX:+CMSClassUnloadingEnabled"
    ,   "-Dneo4j.home=/var/lib/neo4j"
    ,   "-Dneo4j.instance=/var/lib/neo4j"
    ,   "-Dfile.encoding=UTF-8"
    ,   "org.neo4j.server.Bootstrapper")

    neonode = ProcessNode('global', 'fred', 'servidor', '/usr/bin/java', neoprocargs
    ,   'root', 'root', '/', roles=(CMAconsts.ROLE_server,))

    print 'Should be (3, {something}):	', sshrule.specmatch(ExpressionContext((sshnode,)))
    print 'This should be (0, None):	', sshrule.specmatch(ExpressionContext((udevnode,)))
    print 'This should be (0, None):	', sshrule.specmatch(ExpressionContext((neonode,)))
    print 'This should be (0, None):	', neorule.specmatch(ExpressionContext((sshnode,)))
    print 'Should be (3, {something}):	', neorule.specmatch(ExpressionContext((neonode,)))
    print 'Should be (4, {something}):	', neoocfrule.specmatch(ExpressionContext((neonode,)))
    print 'Documentation of functions available for use in match expressions:'
    longest = 0
    for (funcname, description) in GraphNodeExpression.FunctionDescriptions():
        if len(funcname) > longest:
            longest = len(funcname)
    fmt = '%%%ds: %%s' % longest
    pad = (longest +2) * ' '
    fmt2 = pad + '%s'

    for (funcname, description) in GraphNodeExpression.FunctionDescriptions():
        descriptions = description.split('\n')
        print fmt % (funcname, descriptions[0])
        for descr in descriptions[1:]:
            print fmt2 % descr

    MonitoringRule.load_tree("monrules")
    print MonitoringRule.monitorobjects
