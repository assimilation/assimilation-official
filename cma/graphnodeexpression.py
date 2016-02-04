
#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
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
from AssimCclasses import pyNetAddr, pyConfigContext
import sys
#
#
class GraphNodeExpression(object):
    '''We implement Graph node expressions - we are't a real class'''
    functions = {}
    def __init__(self):
        raise NotImplementedError('This is not a real class')

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
        if not isinstance(expression, (str, unicode)):
            # print >> sys.stderr, 'RETURNING NONSTRING:', expression
            return expression
        expression = expression.strip()
        if not hasattr(context, 'get') or not hasattr(context, '__setitem__'):
            context = ExpressionContext(context)
        # print >> sys.stderr, '''EVALUATE('%s') (%s):''' % (expression, type(expression))
        # The value of this parameter is a constant...
        if expression.startswith('"'):
            if expression[-1] != '"':
                print >> sys.stderr, "Unterminated string '%s'" % expression
            # print >> sys.stderr, '''Constant string: "%s"''' % (expression[1:-1])
            return expression[1:-1] if expression[-1] == '"' else None
        if (expression.startswith('0x') or expression.startswith('0X')) and len(expression) > 3:
            return int(expression[2:], 16)
        if expression.isdigit():
            return int(expression, 8) if expression.startswith('0') else int(expression)
        if expression.find('(') >= 0:
            value = GraphNodeExpression.functioncall(expression, context)
            context[expression] = value
            return value
        # if expression.startswith('$'):
            # print >> sys.stderr, 'RETURNING VALUE OF %s' % expression[1:]
        # print >> sys.stderr, 'Context is %s' % str(context)
        # print >> sys.stderr, 'RETURNING VALUE OF %s = %s'\
        #   % (expression, context.get(expression[1:], None))
        return context.get(expression[1:], None) if expression.startswith('$') else expression

    # pylint R0912: too many branches - really ought to write a lexical analyzer and parser
    # On the whole it would be simpler and easier to understand...
    # pylint: disable=R0912
    @staticmethod
    def _compute_function_args(arglist, context):
        '''Compute the arguments to a function call. May contain function calls
        and other GraphNodeExpression, or quoted strings...
        Ugly lexical analysis.
        Really ought to write a real recursive descent parser...
        '''
        # print >> sys.stderr, '_compute_function_args(%s)' % str(arglist)
        args = []
        argstrings = []
        nestcount=0
        arg = ''
        instring = False
        prevwasquoted = False
        for char in arglist:
            if instring:
                if char == '"':
                    instring = False
                    prevwasquoted = True
                else:
                    arg += char
            elif nestcount == 0 and char == '"':
                instring = True
            elif nestcount == 0 and char == ',':
                if prevwasquoted:
                    prevwasquoted = False
                    args.append(arg)
                    argstrings.append(arg)
                else:
                    arg = arg.strip()
                    if arg == '':
                        continue
                    #print >> sys.stderr, "EVALUATING [%s]" % arg
                    args.append(GraphNodeExpression.evaluate(arg, context))
                    argstrings.append(arg)
                    arg = ''
            elif char == '(':
                nestcount += 1
                #print >> sys.stderr, "++nesting: %d" % (nestcount)
                arg += char
            elif char == ')':
                arg += char
                nestcount -= 1
                #print >> sys.stderr, "--nesting: %d" % (nestcount)
                if nestcount < 0:
                    return (None, None)
                if nestcount == 0:
                    if prevwasquoted:
                        #print >> sys.stderr, '_compute_function_args: QUOTED argument: "%s"' % arg
                        args.append(arg)
                    else:
                        arg = arg.strip()
                        #print >> sys.stderr, "GnE.functioncall [%s]" % arg
                        args.append(GraphNodeExpression.functioncall(arg, context))
                    argstrings.append(arg)
                    arg = ''
            else:
                arg += char
        if nestcount > 0 or instring:
            #print "Nestcount: %d, instring: %s" % (nestcount, instring)
            return (None, None)
        if arg != '':
            if prevwasquoted:
                #print >> sys.stderr, '_compute_function_args: quoted argument: "%s"' % arg
                args.append(arg)
            else:
                #print >> sys.stderr, "GnE.evaluate [%s]" % arg
                args.append(GraphNodeExpression.evaluate(arg, context))
            argstrings.append(arg)
        #print >> sys.stderr, 'RETURNING [%s] [%s]' % (args, argstrings)
        return (args, argstrings)

    @staticmethod
    def functioncall(expression, context):
        '''Performs a function call for our expression language

        Figures out the function name, and the arguments and then
        calls that function with those arguments.

        All our defined functions take an argv argument string first, then an
        ExpressionContext argument.

        This parsing is incredibly primitive.  Feel free to improve it ;-)

        '''
        expression = expression.strip()
        if expression[-1] != ')':
            print >> sys.stderr, '%s does not end in )' % expression
            return None
        expression = expression[:len(expression)-1]
        (funname, arglist) = expression.split('(', 1)
        # print >> sys.stderr, 'FUNCTIONCALL: %s(%s)' % (funname, arglist)
        funname = funname.strip()
        arglist = arglist.strip()
        #
        # At this point we have all our arguments as a string , but it might contain
        # other (nested) calls for us to evaluate
        #
        # print >> sys.stderr, 'FunctionCall: arglist: [%s]' % (arglist)
        args, _argstrings = GraphNodeExpression._compute_function_args(arglist, context)
        # print >> sys.stderr, 'args: %s' % (args)
        # print >> sys.stderr, '_argstrings: %s' % (_argstrings)
        if args is None:
            return None

        if funname.startswith('@'):
            funname = funname[1:]
        if funname not in GraphNodeExpression.functions:
            print >> sys.stderr, 'BAD FUNCTION NAME: %s' % funname
            return None
        # print >> sys.stderr, 'ARGSTRINGS %s(%s)' % (funname, str(_argstrings))
        # print >> sys.stderr, 'ARGS: %s' % (str(args))
        ret = GraphNodeExpression.functions[funname](args, context)
        # print >> sys.stderr, '%s(%s) => %s' % (funname, args, ret)
        return ret

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
        return function


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
        self.objects = objects if isinstance(objects, (list, tuple)) else (objects,)
        self.prefix = prefix
        self.values = {}

    def __str__(self):
        ret = 'ExpressionContext('
        delim='['
        for obj in self.objects:
            ret +=  ('%s%s' % (delim, str(obj)))
            delim=', '
        ret += '])'
        return ret


    def keys(self):
        '''Return the complete set of keys in all our constituent objects'''
        retkeys = set()
        for obj in self.objects:
            for key in obj:
                retkeys.add(key)
        return retkeys

    def get(self, key, alternative=None):
        '''Return the value associated with a key - cached or otherwise
        and cache it.'''
        if key in self.values:
            return self.values[key]
        for obj in self.objects:
            ret = None
            try:
                #print >> sys.stderr, 'GETTING %s in %s: %s' % (key, type(obj), obj)
                ret = obj.get(key, None)
                if ret is None and hasattr(obj, 'deepget'):
                    ret = obj.deepget(key, None)
                #print >> sys.stderr, 'RETURNED %s' % ret
            # Too general exception catching...
            # pylint: disable=W0703
            except Exception as e:
                ret = None
                print >> sys.stderr, 'OOPS: self.objects = %s / exception %s' % (str(self.objects),
                                                                                 e)
                print >> sys.stderr, 'OOPS: OUR object = %s (%s)' % (str(obj), type(obj))
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
        'Return the number of keys in our objects'
        return len(self.keys())

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
def IGNORE(_ignoreargs, _ignorecontext):
    '''Function to ignore its argument(s) and return True all the time.
    This is a special kind of no-op in that it is used to override
    and ignore an underlying rule. It is expected that its arguments
    will explain why it is being ignored in this rule set.
    '''
    return True

@GraphNodeExpression.RegisterFun
def EQ(args, _context):
    '''Function to return True if each non-None argument in the list matches
    every non-None argument and at least one of its subsequent arguments are not None.
    '''
    #print >> sys.stderr, 'EQ(%s) =>?' % str(args)
    val0 = args[0]
    if val0 is None:
        return None
    anymatch = None
    for val in args[1:]:
        if val is None:
            continue
        if type(val0) != type(val):
            if str(val0) != str(val):
                return False
        elif val0 != val:
            return False
        anymatch = True
    #print >> sys.stderr, 'EQ(%s) => %s' % (str(args), str(anymatch))
    return anymatch

@GraphNodeExpression.RegisterFun
def NE(args, _context):
    '''Function to return True if no non-None argument in the list matches
    the first one or None if all subsequent arguments are None'''
    #print >> sys.stderr, 'NE(%s, %s)' % (args[0], str(args[1:]))
    val0 = args[0]
    if val0 is None:
        return None
    anymatch = None
    for val in args[1:]:
        #print >> sys.stderr, '+NE(%s, %s) (%s, %s)' % (val0, val, type(val0), type(val))
        if val is None:
            return None
        if val0 == val or str(val0) == str(val):
            return False
        anymatch = True
    return anymatch

@GraphNodeExpression.RegisterFun
def LT(args, _context):
    '''Function to return True if each non-None argument in the list is
    less than the first one or None if all subsequent arguments are None'''
    val0 = args[0]
    if val0 is None:
        return None
    anymatch = None
    for val in args[1:]:
        if val is None:
            continue
        if val0 >= val:
            return False
        anymatch = True
    return anymatch

@GraphNodeExpression.RegisterFun
def GT(args, _context):
    '''Function to return True if each non-None argument in the list is
    greater than the first one or None if all subsequent arguments are None'''
    val0 = args[0]
    if val0 is None:
        return None
    anymatch = None
    for val in args[1:]:
        if val is None:
            continue
        if val0 <=val:
            return False
        anymatch = True
    return anymatch

@GraphNodeExpression.RegisterFun
def LE(args, _context):
    '''Function to return True if each non-None argument in the list is
    less than or equal to first one or None if all subsequent arguments are None'''
    val0 = args[0]
    if val0 is None:
        return None
    anymatch = None
    for val in args[1:]:
        if val is None:
            continue
        if val0 > val:
            return False
        anymatch = True
    return anymatch

@GraphNodeExpression.RegisterFun
def GE(args, _context):
    '''Function to return True if each non-None argument in the list is
    greater than or equal to first one or None if all subsequent arguments are None'''
    val0 = args[0]
    if val0 is None:
        return None
    anymatch = None
    for val in args[1:]:
        if val is None:
            continue
        if val0 < val:
            return False
        anymatch = True
    return anymatch

@GraphNodeExpression.RegisterFun
def IN(args, _context):
    '''Function to return True if first argument is in the list that follows.
    If the first argument is iterable, then each element in it must be 'in'
    the list that follows.
    '''

    val0 = args[0]
    if val0 is None:
        return None
    if hasattr(val0, '__iter__') and not isinstance(val0, (str, unicode)):
        # Iterable
        anyTrue = False
        for elem in val0:
            if elem is None:
                continue
            if elem not in args[1:] and str(elem) not in args[1:]:
                return False
            anyTrue = True
        return True if anyTrue else None
    # Not an iterable: string, int, NoneType, etc.
    if val0 is None:
        return None
    #print >> sys.stderr, type(val0), val0, type(args[1]), args[1]
    return val0 in args[1:] or str(val0) in args[1:]

@GraphNodeExpression.RegisterFun
def NOTIN(args, _context):
    'Function to return True if first argument is NOT in the list that follows'
    val0 = args[0]
    if val0 is None:
        return None
    if hasattr(val0, '__iter__') and not isinstance(val0, (str, unicode)):
        # Iterable
        for elem in val0:
            if elem in args[1:] or str(elem) in args[1:]:
                return False
        return True
    return val0 not in args[1:] and str(val0) not in args[1:]

@GraphNodeExpression.RegisterFun
def NOT(args, _context):
    'Function to Negate the Truth value of its single argument'
    try:
        val0 = args[0]
    except TypeError:
        val0 = args
    return None if val0 is None else not val0

_regex_cache = {}
@GraphNodeExpression.RegisterFun
def match(args, _context):
    '''Function to return True if first argument matches the second argument (a regex)
    - optional 3rd argument is RE flags'''
    lhs = args[0]
    rhs = args[1]
    if lhs is None or rhs is None:
        return None
    flags = args[2] if len(args) > 2 else 0
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
    #print >> sys.stderr, 'ARGEQUALS(%s)' % (str(args))
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
    #print >> sys.stderr, 'SEARCHING in %s FOR %s in %s' % (argname, definename, listtosearch)
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
    the value of the string which is the next argument.
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
        argname = '$argv'
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
    A function which evaluates  each expression in turn, and returns the value
    of the first expression which is not None - or None
    '''
    #print >> sys.stderr, 'OR(%s)' % (str(args))
    if len(args) < 1:
        return None
    for arg in args:
        value = GraphNodeExpression.evaluate(arg, context)
        if value is not None and value:
            return value
    return None

@GraphNodeExpression.RegisterFun
def AND(args, context):
    '''
    A function which evaluates  each expression in turn, and returns the value
    of the first expression which is not None - or None
    '''
    # print >> sys.stderr, 'AND(%s)' % (str(args))
    argisnone = True
    if len(args) < 1:
        return None
    for arg in args:
        value = GraphNodeExpression.evaluate(arg, context)
        if value is None:
            argisnone = None
        elif not value:
            # print >> sys.stderr, 'AND(%s) => False' % (str(args))
            return False
    # print >> sys.stderr, 'AND(%s) => %s' % (str(args), argisnone)
    return argisnone

@GraphNodeExpression.RegisterFun
def ATTRSEARCH(args, context):
    '''
    Search our first context object for an attribute with the given name and (if supplied) value.
    If 'value' is None, then we simply search for the given name.
    We return True if we found what we were looking for, and False otherwise.

    The object to search in is is args[0], the name is args[1],
    and the optional desired value is args[2].
    '''
    return True if FINDATTRVALUE(args, context) else False
    # return FINDATTRVALUE(args, context) is not None
    # These are equivalent. Not sure which is clearer...

@GraphNodeExpression.RegisterFun
def FINDATTRVALUE(args, _context):
    '''
    Search our first context object for an attribute with the given name and (if supplied) value.
    We return the value found, if it is in the context objects, or None if it is not
    If 'value' is None, then we simply search for the given name.

    We return True if the desired value is None, and so is the value we found -
    otherwise we return the value associated with 'name' or None if not found.

    The object to search in is is args[0], the name is args[1],
    and the optional desired value is args[2].
    '''
    if len(args) not in (2,3):
        print >> sys.stderr, 'WRONG NUMBER OF ARGUMENTS (%d) TO FINDATTRVALUE' % (len(args))
        return None
    desiredvalue = args[2] if len(args) > 2 else None
    return _attrfind(args[0], args[1], desiredvalue)

def _is_scalar(obj):
    'Return True if this object is a pyConfigContext/JSON "scalar"'
    return isinstance(obj, (str, unicode, int, long, float, bool, pyNetAddr))

def _attrfind(obj, name, desiredvalue):
    '''
    Recursively search the given object for an attribute with the given name
    and value. If 'value' is None, then we simply search for the given name.

    We return True if the desired value is None, and the value we found is also None -
    otherwise we return the value associated with 'name' or None if not found.
    '''
    if _is_scalar(obj):
        return None
    if hasattr(obj, '__getitem__'):
        for key in obj:
            keyval = obj[key]
            if key == name:
                if desiredvalue is None:
                    return keyval if keyval is not None else True
                elif keyval == desiredvalue or str(keyval) == str(desiredvalue):
                    # We use str() to allow pyNetAddr objects to compare equal
                    # and the possibility of type mismatches (strings versus integers, for example)
                    # This may also improve the chance of floating point compares working as
                    # intended.
                    return keyval
    elif hasattr(obj, '__iter__'):
        for elem in obj:
            ret = _attrfind(elem, name, desiredvalue)
            if ret is not None:
                return ret
    return None

@GraphNodeExpression.RegisterFun
def PAMMODARGS(args, _context):
    '''
    We pass the following arguments to PAMSELECTARGS:
        section - the section value to select from
        service - service type to search for
        module - the module to select arguments from
        argument - the arguments to select

    We return the arguments from the first occurence of the module that we find.
    '''
    #print >> sys.stderr, 'PAMMODARGS(%s)' % (str(args))
    if len(args) != 4:
        print >> sys.stderr, 'WRONG NUMBER OF ARGUMENTS (%d) TO PAMMODARGS' % (len(args))
        return False
    section = args[0]
    reqservice = args[1]
    reqmodule = args[2]
    reqarg = args[3]

    if section is None:
        #print >> sys.stderr, 'Section is None in PAM object'
        return None
    # Each section is a list of lines
    for line in section:
        # Each line is a dict with potential keys of:
        #  - service: a keyword saying what kind of service
        #  - filename:(only for includes)
        #  - type: dict of keywords (requisite, required, optional, etc)
        #  - module: Module dict keywords with:
        #       - path - pathname of module ending in .so
        #       - other arguments as per the module's requirements
        #         simple flags without '=' values show up with True as value
        #
        if 'service' not in line or line['service'] != reqservice:
            #print >> sys.stderr, 'Service %s not in PAM line %s' % (reqservice, str(line))
            continue
        if 'module' not in line:
            #print >> sys.stderr, '"module" not in PAM line %s' % str(line)
            continue
        if 'path' not in line['module']:
            #print >> sys.stderr, '"path" not in PAM module %s' % str(line['module'])
            #print >> sys.stderr, '"path" not in PAM line %s' % str(line)
            continue
        modargs = line['module']
        if reqmodule != 'ANY' and (modargs['path'] != reqmodule and
                                   modargs['path'] != (reqmodule + '.so')):
            #print >> sys.stderr, 'Module %s not in PAM line %s' % (reqmodule, str(line))
            continue
        ret = modargs[reqarg] if reqarg in modargs else None
        if ret is None and reqmodule == 'ANY':
            continue
        #print >> sys.stderr, 'RETURNING %s from %s' % (ret, str(line))
        return ret
    return None



@GraphNodeExpression.RegisterFun
def MUST(args, _unused_context):
    'Return True if all args are True. A None arg is the same as False to us'
    # print >> sys.stderr, 'CALLING MUST%s' % str(tuple(args))
    if not hasattr(args, '__iter__') or isinstance(args, (str, unicode)):
        args = (args,)
    for arg in args:
        if arg is None or not arg:
            #print >> sys.stderr, '+++MUST returns FALSE'
            return False
    # print >> sys.stderr, '+++MUST returns TRUE'
    return True

@GraphNodeExpression.RegisterFun
def NONEOK(args, _unused_context):
    'Return True if all args are True or None'
    #print >> sys.stderr, 'CALLING MUST%s' % str(tuple(args))
    if not hasattr(args, '__iter__') or isinstance(args, (str, unicode)):
        args = (args,)
    for arg in args:
        if arg is not None and not arg:
            #print >> sys.stderr, '+++NONEOK returns FALSE'
            return False
    #print >> sys.stderr, '+++NONEOK returns TRUE'
    return True
@GraphNodeExpression.RegisterFun
def FOREACH(args, context):
    '''Applies the (string) expression (across all values in the context,
    returning the 'AND' of the evaluation of the expression-evaluations
    across the top level values in the context. It stops evaluation on
    the first False return.

    The final argument is the expression (predicate) to be evaluated. Any
    previous arguments in 'args' are expressions to be evaluated in the context
    'context' then used as the 'context' for this the expression in this FOREACH.
    Note that this desired predicate is a _string_, which is then evaluated
    (like 'eval').  It is not a normal expression, but a string containing
    an expression.  You _will_ have to quote it.

    When given a single argument, it will evaluate the string expression
    for each of  top-level values in the object. Normally this would be the 'data'
    portion of a discovery object. So, for example, if each of the top level keys
    is a file name and the values are file properties, then it will evaluate the
    expression on the properties of every file in the object.

    If you need to evaluate this across all the elements of a sub-object named
    "filenames" in the top level "data" object then you give "$filenames" as the
    context argument, and your predicate as the expression like this:
        ["$filenames", "<your-desired-predicate>"].

    The code to do this is simpler than the explanation ;-)
    '''
    anynone = False
    if len(args) == 1:
        objectlist = context.objects
    else:
        objectlist = [GraphNodeExpression.evaluate(obj, context) for obj in args[:-1]]

    expressionstring=args[-1]
    if not isinstance(expressionstring, (str, unicode)):
        print >> sys.stderr, 'FOREACH expression must be a string, not %s' % type(expressionstring)
        return False
    # print >>sys.stderr, 'OBJECTLIST is:', objectlist
    for obj in objectlist:
        # print >>sys.stderr, 'OBJ is:', obj
        for key in obj:
            item = obj[key]
            if not hasattr(item, '__contains__') or not hasattr(item, '__iter__'):
                print >> sys.stderr, 'UNSUITABLE FOREACH CONTEXT[%s]: %s' % (key, item)
                continue
            # print >> sys.stderr, 'CREATING CONTEXT[%s]: %s' % (key, item)
            itemcontext = ExpressionContext(item)
            # print >> sys.stderr, 'CONTEXT IS:', itemcontext
            value = GraphNodeExpression.evaluate(expressionstring, itemcontext)
            # print >> sys.stderr, 'VALUE of %s IS [%s] in context: %s' % (str(args), value, item)
            if value is None:
                anynone = True
            elif not value:
                return False
    return None if anynone else True



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
        if value is None:
            return None
        result |= int(value)
    return result

@GraphNodeExpression.RegisterFun
def bitwiseAND(args, context):
    '''
    A function which evaluates the each expression and returns the bitwise AND of
    all the expressions given as arguments
    '''
    if len(args) < 2:
        return None
    result = int(args[0])
    for arg in args:
        value = GraphNodeExpression.evaluate(arg, context)
        if value is None:
            return None
        result &= int(value)
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

def _regexmatch(key):
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

def _collect_ip_ports(service):
    'Collect out complete set of IP/Port combinations for this service'
    portlist = {}
    for key in service.keys():
        ipport = _regexmatch(key)
        if ipport.port() == 0:
            continue
        port = ipport.port()
        if port in portlist:
            portlist[port].append(ipport)
        else:
            portlist[port] = [ipport,]
    return portlist

# Netstat format IP:port pattern
ipportregex = re.compile('(.*):([^:]*)$')
def selectanipport(arg, _context, preferlowestport=True, preferv4=True):
    '''This function searches discovery information for a suitable IP
    address/port combination to go with the service.
    '''

    #print >> sys.stderr, 'SELECTANIPPORT(%s)' % arg
    try:

        portlist = _collect_ip_ports(arg)
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
        args = ('$procinfo.listenaddrs',)
    #print >> sys.stderr, 'SERVICEIP(%s)' % str(args)
    for arg in args:
        nmap = GraphNodeExpression.evaluate(arg, context)
        if nmap is None:
            continue
        #print >> sys.stderr, 'serviceip.SELECTANIPPORT(%s)' % (nmap)
        ipport = selectanipport(nmap, context)
        if ipport is None:
            continue
        ipport.setport(0) # Make sure return value doesn't include the port
        #print >> sys.stderr, 'IPPORT(%s)' % str(ipport)
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
        args = ('$procinfo.listenaddrs',)
    #print >> sys.stderr, 'SERVICEPORT ARGS are %s' % (str(args))
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
        args = ('$procinfo.listenaddrs',)
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
    if isinstance(args, (str, unicode)):
        args = (args,)
    if len(args) == 0:
        args = ('$pathname',)    # Default to the name of the executable
    for arg in args:
        pathname = GraphNodeExpression.evaluate(arg, context)
        if pathname is None:
            continue
        #print >> sys.stderr, 'BASENAME(%s) => %s' % ( pathname
        #,   os.path.basename(pathname))
        return os.path.basename(pathname)
    return None


@GraphNodeExpression.RegisterFun
def dirname(args, context):
    '''
    This function returns the directory name from a pathname.
    If no pathname is supplied, then the discovered service executable name is assumed.
    '''
    if isinstance(args, (str, unicode)):
        args = (args,)
    if len(args) == 0:
        args = ('$pathname',)    # Default to the name of the executable
    for arg in args:
        pathname = GraphNodeExpression.evaluate(arg, context)
        if pathname is None:
            continue
        return os.path.dirname(pathname)
    return None

@GraphNodeExpression.RegisterFun
def hascmd(args, context):
    '''
    This function returns True if the given list of commands are all present on the given Drone.
    It determines this by looking at the value of $commands
    '''
    cmdlist = GraphNodeExpression.evaluate('$commands', context)
    for arg in args:
        if cmdlist is None or arg not in cmdlist:
            return None
    return True

if __name__ == '__main__':

    def simpletests():
        '''These tests don't require a real context'''
        assert NOT((True,), None) == False
        assert NOT((False,), None) == True
        assert EQ((1,1,'1'), None)
        assert NOT(EQ((1,), None), None) is None
        assert MUST(NOT(EQ((1,), None), None), None) == False
        assert NONEOK(NOT(EQ((1,), None), None), None) == True
        assert NOT(EQ((1,1,'2'), None), None)
        assert NOT(EQ((0,0,'2'), None), None)
        assert EQ(('a','a','a'), None)
        assert EQ(('0','0',0), None)
        assert NOT(NE((1,1,'1'), None), None)
        assert NOT(NE((1,), None), None) is None
        assert NONEOK(NOT(NE((1,), None), None), None) == True
        assert MUST(NOT(NE((1,), None), None), None) == False
        assert NOT(NE((1,1,'2'), None), None)
        assert NOT(NE((0,0,'2'), None), None)
        assert NOT(NE(('a','a','a'), None), None)
        assert NOT(NE(('0','0',0), None), None)
        assert LE((1,1), None)
        assert LE((1,5), None)
        assert NOT(LT((1,1), None), None)
        assert LT((1,5), None)
        assert NOT(GT((1,1), None), None)
        assert GE((1,1), None)
        assert IN ((1, 2 , 3, 4, 1), None)
        assert IN ((1, 2 , 3, 4, '1'), None)
        assert NOT(IN((1, 2 , 3, 4), None), None)
        assert NOT(NOTIN((1, 2 , 3, 4, 1), None), None)
        assert NOT(NOTIN((1, 2 , 3, 4, '1'), None), None)
        assert NOTIN((1, 2 , 3, 4), None)
        assert bitwiseOR((1, 2, 4), None) == 7
        assert bitwiseOR((1, 2, '4'), None) == 7
        assert bitwiseAND((7, 3), None) == 3
        assert bitwiseAND((7, 1, '2'), None) == 0
        assert bitwiseAND(('15', '7', '3'), None) == 3
        assert IGNORE((False, False, False), None)
        assert MUST(None, None) == False
        assert MUST(True, None) == True
        assert MUST(False, None) == False
        assert NONEOK(None, None) == True
        assert NONEOK(True, None) == True
        assert NONEOK(False, None) == False
        assert match(('fred', 'fre'), None)
        assert not match(('fred', 'FRE'), None)
        assert basename(('/dev/null'), None) == 'null'
        assert dirname(('/dev/null'), None) == '/dev'
        print >> sys.stderr, 'Simple tests passed.'

    def contexttests():
        'GraphNodeExpression tests that need a context'

        lsattrs='''{
    "/var/log/audit/": {"owner": "root", "group": "root", "type": "d", "perms": {"owner":{"read":true, "write":true, "exec":true, "setid":false}, "group": {"read":true, "write":false, "exec":true, "setid":false}, "other": {"read":false, "write":false, "exec":false}, "sticky":false}, "octal": "0750"},
    "/var/log/audit/audit.log": {"owner": "root", "group": "root", "type": "-", "perms": {"owner":{"read":true, "write":true, "exec":false, "setid":false}, "group": {"read":false, "write":false, "exec":false, "setid":false}, "other": {"read":false, "write":false, "exec":false}, "sticky":false}, "octal": "0600"},
    "/var/log/audit/audit.log.1": {"owner": "root", "group": "root", "type": "-", "perms": {"owner":{"read":true, "write":false, "exec":false, "setid":false}, "group": {"read":false, "write":false, "exec":false, "setid":false}, "other": {"read":false, "write":false, "exec":false}, "sticky":false}, "octal": "0400"}
}'''
        lscontext = ExpressionContext(pyConfigContext(lsattrs,))

        Pie_context = ExpressionContext((
            pyConfigContext({'a': {'b': 'c', 'pie': 3, 'pi': 3, 'const': 'constant'},
                            'f': {'g': 'h', 'pie': '3', 'pi': 3, 'const': 'constant'}}),
            pyConfigContext({'math': {'pi': 3.14159, 'pie': 3, 'const': 'constant'}}),
            pyConfigContext({'geography': {'Europe': 'big', 'const': 'constant'}}),
            ))
        complicated_context = ExpressionContext(pyConfigContext({'a': {'b': {'pie': 3}}}),)
        assert FOREACH(("EQ(False, $perms.group.write, $perms.other.write)",), lscontext) == True
        assert FOREACH(("EQ($pi, 3)",), Pie_context) == False
        assert FOREACH(("EQ($pie, 3)",), Pie_context) is None
        assert FOREACH(("$a", "EQ($pie, 3)"), complicated_context) == True
        assert FOREACH(("$a", "EQ($pie, 3.14159)"), complicated_context) == False
        assert FOREACH(("$a", "EQ($pi, 3.14159)"), complicated_context) == None
        assert FOREACH(("EQ($const, constant)",), Pie_context) == True
        assert GraphNodeExpression.evaluate('EQ($math.pie, 3)', Pie_context) == True
        assert FOREACH(("EQ($group, root)",), lscontext) == True
        assert FOREACH(("EQ($owner, root)",), lscontext) == True
        assert FOREACH(("AND(EQ($owner, root), EQ($group, root))",), lscontext) == True
        print >> sys.stderr, 'Context tests passed.'

    simpletests()
    contexttests()
    print >> sys.stderr, 'All tests passed.'
