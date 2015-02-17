
#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2013, 2014 - Alan Robertson <alanr@unix.sh>
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
''' This module defines Functions to evaluate GraphNode expressions...  '''

import re, os, inspect
from AssimCtypes import ADDR_FAMILY_IPV4, ADDR_FAMILY_IPV6
from AssimCclasses import pyNetAddr
import sys
#
#
class GraphNodeExpression(object):
    '''We implement Graph node expressions - we are't a real class'''
    functions = {}
    def __init__(self):
        raise NotImplementedMethod('This is not a real class')

    @staticmethod
    def evaluate(expression, context):
        '''
        Evaluate an expression.
        It can be:
            None - return None
            'some-value -- return some-value (it's a constant)
            or an expression to find in values or graphnodes
            or @functionname(args) - for defined functions...

            We may add other kinds of expressions in the future...
        '''
        if expression is None:
            return None
        if expression.startswith("'"):
            # The value of this parameter is a constant...
            return expression[1:]
        if expression.startswith('0x') and len(expression) > 3:
            return int(expression[2:], 16)
        if expression.isdigit():
            if expression.startswith('0'):
                return int(expression, 8)
            else:
                return int(expression)
        if expression.startswith('@'):
            value = GraphNodeExpression.functioncall(expression[1:], context)
            context[expression] = value
        return context.get(expression, None)

    @staticmethod
    def functioncall(expression, context):
        '''Performs a function call for our expression language

        Figures out the function name, and the arguments and then
        calls that function with those arguments.

        All our defined functions take an argv argument string first, then an
        ExpressionContext argument.

        '''
        expression = expression.strip()
        if expression[-1] != ')':
            return None
        expression = expression[:len(expression)-1]
        (funname, arglist) = expression.split('(', 1)
        funname = funname.strip()
        arglist = arglist.strip()
        argsin = arglist.split(',')
        args = []
        for arg in argsin:
            arg = arg.strip()
            if arg != '':
                args.append(arg.strip())
        if funname not in GraphNodeExpression.functions:
            return None
        return GraphNodeExpression.functions[funname](args, context)
 
    @staticmethod
    def FunctionDescriptions():
        '''Return a list of tuples of (funcname, docstring) for all our GraphNodeExpression
        defined functions.  The list is sorted by function name.
        '''
        names = GraphNodeExpression.functions.keys()
        names.sort()
        ret = []
        for name in names:
            ret.append((name, inspect.getdoc(GraphNodeExpression.functions[name])))
        return ret

    @staticmethod
    def RegisterFun(function):
        'Function to register other functions as built-in GraphNodeExpression functions'
        GraphNodeExpression.functions[function.__name__] = function


class ExpressionContext(object):
    '''This class defines a context for an expression evaluation.
    There are three parts to it:
        1)  A cache of values which have already been computed
        2)  A scope/context for expression evaluation - a default name prefix
        3)  A set of objects which implement the 'get' operation to be used in
            evaluating values of names

    We act like a dict, implementing these member functions:
    __iter__, __contains__, __len__, __getitem__ __setitem__, __delitem__,
    get, keys, has_key, clear, items
    '''

    def __init__(self, objects, prefix=None):
        'Initialize our ExpressionContext'
        self.objects = objects
        self.prefix = prefix
        self.values = {}

    def keys(self):
        '''Return the keys in our cache - this is NOT all known keys'''
        return self.values.keys()

    def get(self, key, alternative=None):
        '''Return the value associated with a key - cached or otherwise
        and cache it.'''
        if key in self.values:
            return self.values[key]
        for obj in self.objects:
            ret = obj.get(key, None)
            if ret is not None:
                self.values[key] = ret
                return ret
            if self.prefix is not None:
                ret = obj.get('%s.%s' % (self.prefix, key), None)
                if ret is not None:
                    self.values[key] = ret
                    return ret
        return alternative

    def clear(self):
        'Clear our cached values'
        self.values = {}

    def items(self):
        'Return all items from our cache'
        return self.values.items()
        

    def __iter__(self):
        'Yield each key from self.keys() in turn'
        for key in self.keys():
            yield key

    def __contains__(self, key):
        'Return True if we can get() this key'
        return self.get(key, None) is not None

    def has_key(self, key):
        'Return True if we can get() this key'
        return self.get(key, None) is not None


    def __len__(self):
        'Return the length of our cache in self.keys() - probably not useful'
        return len(self.values)

    def __getitem__(self, key):
        'Return the given item, or raise KeyError if not found'
        ret = self.get(key, None)
        if ret is None:
            raise KeyError(key)
        return ret

    def __setitem__(self, key, value):
        'Cache the value associated with this key'
        self.values[key] = value

    def __delitem__(self, key):
        'Remove the cache value associated with this key'
        del self.values[key]


@GraphNodeExpression.RegisterFun
def EQ(args, context):
    'Function to return True if each argument in the list matches the first one'
    val0 = GraphNodeExpression.evaluate(args[0], context)
    for arg in args[1:]:
        val = GraphNodeExpression.evaluate(arg, context)
        if val0 != val:
            return False
    return True

@GraphNodeExpression.RegisterFun
def NE(args, context):
    'Function to return True if no argument in the list matches the first one'
    val0 = GraphNodeExpression.evaluate(args[0], context)
    for arg in args[1:]:
        val = GraphNodeExpression.evaluate(arg, context)
        if val0 == val:
            return False
    return True

@GraphNodeExpression.RegisterFun
def IN(args, context):
    'Function to return True if first argument is in the list that follows'
    val0 = GraphNodeExpression.evaluate(args[0], context)
    for arg in args[1:]:
        val = GraphNodeExpression.evaluate(arg, context)
        if val0 == val:
            return True
    return False

@GraphNodeExpression.RegisterFun
def NOTIN(args, context):
    'Function to return True if first argument is NOT in the list that follows'
    val0 = GraphNodeExpression.evaluate(args[0], context)
    for arg in args[1:]:
        val = GraphNodeExpression.evaluate(arg, context)
        if val0 == val:
            return False
    return True

@GraphNodeExpression.RegisterFun
def NOT(args, context):
    'Function to Negate the Truth value of its single argument'
    return not GraphNodeExpression.evaluate(args[0], context)

_regex_cache = {}
@GraphNodeExpression.RegisterFun
def match(args, context):
    'Function to return True if first argument matches the second argument (a regex) - optional 3rd argument is RE flags'
    lhs = GraphNodeExpression.evaluate(args[0], context)
    rhs = GraphNodeExpression.evaluate(args[1], context)
    global _regex_cache
    flags = args[2] if len(args) > 2 else None
    cache_key = '%s//%s' % (str(rhs), str(flags))
    if cache_key in _regex_cache:
        regex = _regex_cache[cache_key]
    else:
        regex = re.compile(args[1], flags)
        _regex_cache[cache_key] = regex
    return regex.search(lhs) is not None

@GraphNodeExpression.RegisterFun
def argequals(args, context):
    '''
    A function which searches a list for an argument of the form name=value.
    The name is given by the argument in args, and the list 'argv'
    is assumed to be the list of arguments.
    If there are two arguments in args, then the first argument is the
    array value to search in for the name=value string instead of 'argv'
    '''
    if len(args) > 2 or len(args) < 1:
        return None
    if len(args) == 2:
        argname = args[0]
        definename = args[1]
    else:
        argname = 'argv'
        definename = args[0]
    if argname in context:
        listtosearch = context[argname]
    else:
        listtosearch = context.get(argname, None)
    if listtosearch is None:
        return None
    prefix = '%s=' % definename
    # W0702: No exception type specified for except statement
    # pylint: disable=W0702
    try:
        for elem in listtosearch:
            if elem.startswith(prefix):
                return elem[len(prefix):]
    except: # No matter the cause of failure, return None...
        pass
    return None

@GraphNodeExpression.RegisterFun
def flagvalue(args, context):
    '''
    A function which searches a list for a -flag and returns
    the value of the option which is the next argument.
    The -flag is given by the argument in args, and the list 'argv'
    is assumed to be the list of arguments.
    If there are two arguments in args, then the first argument is the
    array value to search in for the -flag string instead of 'argv'
    The flag given must be the entire flag complete with - character.
    For example -X or --someflag.
    '''
    if len(args) > 2 or len(args) < 1:
        return None
    if len(args) == 2:
        argname = args[0]
        flagname = args[1]
    else:
        argname = 'argv'
        flagname = args[0]

    progargs = GraphNodeExpression.evaluate(argname, context)
    argslen = len(progargs)
    flaglen = len(flagname)
    for pos in range(0, argslen):
        progarg = progargs[pos]
        progarglen = len(progarg)
        if progarg.startswith(flagname):
            if progarg == flagname:
                # -X foobar
                if (pos+1) < argslen:
                    return progargs[pos+1]
            elif flaglen == 2 and progarglen > flaglen:
                # -Xfoobar -- single character flags only
                return progarg[2:]
    return None

@GraphNodeExpression.RegisterFun
def OR(args, context):
    '''
    A function which evaluates the each expression in turn, and returns the value
    of the first expression which is not None.
    '''
    if len(args) < 2:
        return None
    for arg in args:
        value = GraphNodeExpression.evaluate(arg, context)
        if value is not None:
            return value
    return None

@GraphNodeExpression.RegisterFun
def bitwiseOR(args, context):
    '''
    A function which evaluates the each expression and returns the bitwise OR of
    all the expressions given as arguments
    '''
    if len(args) < 2:
        return None
    result = 0
    for arg in args:
        value = GraphNodeExpression.evaluate(arg, context)
        if value is not None:
            result |= value
    return result

@GraphNodeExpression.RegisterFun
def is_upstartjob(args, context):
    '''
    Returns "true" if any of its arguments names an upstart job, "false" otherwise
    If no arguments are given, it returns whether this system has upstart enabled.
    '''


    from monitoring import MonitoringRule
    agentcache = MonitoringRule.compute_available_agents(context)

    if 'upstart' not in agentcache or len(agentcache['upstart']) == 0:
        return 'false'

    for arg in args:
        value = GraphNodeExpression.evaluate(arg, context)
        if value in agentcache['upstart']:
            return 'true'
    return len(args) == 0


# Netstat format IP:port pattern
ipportregex = re.compile('(.*):([^:]*)$')
def selectanipport(arg, context, preferlowestport=True, preferv4=True):
    '''This function searches discovery information for a suitable IP
    address/port combination to go with the service.
    '''
    def regexmatch(key):
        '''Handy internal function to pull out the IP and port into a pyNetAddr
        Note that the format is the format used in the discovery information
        which in turn is the format used by netstat.
        This is not a "standard" format, but it's what netstat uses - so it's
        what we use.
        '''
        mobj = ipportregex.match(key)
        if mobj is None:
            return None
        (ip, port) = mobj.groups()
        ipport = pyNetAddr(ip, port=int(port))
        if ipport.isanyaddr():
            if ipport.addrtype() == ADDR_FAMILY_IPV4:
                ipport = pyNetAddr('127.0.0.1', port=ipport.port())
            else:
                ipport = pyNetAddr('::1', port=ipport.port())
        return ipport

        
    try:
        portlist = {}
        for key in arg.keys():
            ipport = regexmatch(key)
            if ipport.port() == 0:
                continue
            port = ipport.port()
            if port in portlist:
                portlist[port].append(ipport)
            else:
                portlist[port] = [ipport,]

        portkeys = portlist.keys()
        if preferlowestport:
            portkeys.sort()
        for p in portlist[portkeys[0]]:
            if preferv4:
                if p.addrtype() == ADDR_FAMILY_IPV4:
                    return p
            else:
                if p.addrtype() == ADDR_FAMILY_IPV6:
                    return p
        return portlist[portkeys[0]][0]
    except (KeyError, ValueError, TypeError, IndexError):
        # Something is hinky with this data
        return None

@GraphNodeExpression.RegisterFun
def serviceip(args, context):
    '''
    This function searches discovery information for a suitable concrete IP
    address for a service.
    The argument to this function tells it an expression that will give
    it the hash table (map) of IP/port combinations for this service.
    '''
    if len(args) == 0:
        args = ('JSON_procinfo.listenaddrs',)
    for arg in args:
        nmap = GraphNodeExpression.evaluate(arg, context)
        if nmap is None:
            continue
        ipport = selectanipport(nmap, context)
        if ipport is None:
            continue
        ipport.setport(0) # Make sure return value doesn't include the port
        return str(ipport)
    return None

@GraphNodeExpression.RegisterFun
def serviceport(args, context):
    '''
    This function searches discovery information for a suitable port for a service.
    The argument to this function tells it an expression that will give
    it the hash table (map) of IP/port combinations for this service.
    '''
    if len(args) == 0:
        args = ('JSON_procinfo.listenaddrs',)
    for arg in args:
        nmap = GraphNodeExpression.evaluate(arg, context)
        if nmap is None:
            continue
        port = selectanipport(nmap, context).port()
        if port is None:
            continue
        return str(port)
    return None

@GraphNodeExpression.RegisterFun
def serviceipport(args, context):
    '''
    This function searches discovery information for a suitable ip:port combination.
    The argument to this function tells it an expression that will give
    it the hash table (map) of IP/port combinations for this service.
    The return value is a legal ip:port combination for the given
    address type (ipv4 or ipv6)
    '''
    if len(args) == 0:
        args = ('JSON_procinfo.listenaddrs',)
    for arg in args:
        nmap = GraphNodeExpression.evaluate(arg, context)
        if nmap is None:
            continue
        ipport = selectanipport(nmap, context)
        if ipport is None:
            continue
        return str(ipport)
    return None

@GraphNodeExpression.RegisterFun
def basename(args, context):
    '''
    This function returns the basename from a pathname.
    If no pathname is supplied, then the executable name is assumed.
    '''
    if len(args) == 0:
        args = ('pathname',)    # Default to the name of the executable
    for arg in args:
        pathname = GraphNodeExpression.evaluate(arg, context)
        if pathname is None:
            continue
        return os.path.basename(pathname)
    return None


@GraphNodeExpression.RegisterFun
def dirname(args, context):
    '''
    This function returns the directory name from a pathname.
    If no pathname is supplied, then the discovered service executable name is assumed.
    '''
    if len(args) == 0:
        args = ('pathname',)    # Default to the name of the executable
    for arg in args:
        pathname = GraphNodeExpression.evaluate(arg, context)
        if pathname is None:
            continue
        return os.path.dirname(pathname)
    return None
