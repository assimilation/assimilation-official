#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2013 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community - http://assimproj.org
# Paid support is available from Assimilation Systems Limited - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
'''
This module provides classes associated with querying - including providing metadata
about these queries for the client code.
'''
import os, sys, re
import collections, operator
from py2neo import neo4j
from graphnodes import GraphNode, RegisterGraphClass
from AssimCclasses import pyConfigContext, pyNetAddr
from AssimCtypes import ADDR_FAMILY_IPV6, ADDR_FAMILY_IPV4, ADDR_FAMILY_802
from assimjson import JSONtree
from bestpractices import BestPractices
from cmadb import CMAdb
from droneinfo import Drone
from consts import CMAconsts

@RegisterGraphClass
class ClientQuery(GraphNode):
    '''This class defines queries which can be requested from clients (typically JavaScript)
    The output of all queries is JSON - as filtered by our security mechanism
    '''
    node_query_url = "/doquery/GetaNodeById"
    def __init__(self, queryname, JSON_metadata=None):
        '''Parameters
        ----------
        JSON_metadata  - a JSON string containing
                'querytype':    a string denoting our query type - defaults to 'cypher'
                'cypher':       a string containing our cypher query (if a cypher query)
                'subtype':      a string giving the query subtype (if applicable)
                'descriptions': a dict containing descriptions in various languages
                    'language-key': A locale-language key
                         'short'    a short description of this query in 'language-key'
                         'long'     a long description of this query in 'language-key'
                'parameters': a dict containing
                        'name':     name of the parameter to the query
                        'type':     the type of the parameter one of several noted
                        'min':      optional minimum value for 'name'
                        'max':      optional maximum value for 'name'
                        'enumlist': array of possible enum values  (type = enum only)
                        'lang':     language for this description as a dict:
                                        'short':a short description of 'name' in language 'lang'
                                        'long': a long description of 'name' in language 'lang'
                                        'enumlist': dict of explanations for enumlist above

        Languages are the typical 'en' 'en_us', 'es', 'es_mx', as per the locale-usual
        Currently-known types are as follows:
            int     - an integer
            float   - an floating point number
            string  - a string
            ipaddr  - an IP address either ipv4 or ipv6 (as a string)
            macaddr - a 48 or 64 bit MAC address (as a string)
            bool    - a boolean value
            hostname- a host name (as string - always converted to lower case)
            dnsname - a DNS name (as a string - always converted to lower case)
            enum    - a finite enumeration of permissible values (case-insensitive)
        '''

        GraphNode.__init__(self, domain='metadata')
        self.queryname = queryname
        self.JSON_metadata = JSON_metadata
        self._store = None
        self._db = None
        self._queryobj = None
        if JSON_metadata is None:
            self._JSON_metadata = None
        else:
            self._JSON_metadata = pyConfigContext(JSON_metadata)
            if self._JSON_metadata is None:
                raise ValueError('Parameter JSON_metadata is invalid [%s]' % JSON_metadata)

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of decreasing significance'
        return ['queryname']

    @staticmethod
    def set_node_query_url(node_query_url):
        'Set the base URL for the query operation that returns a node by node id'
        ClientQuery.node_query_url = node_query_url

    def post_db_init(self):
        GraphNode.post_db_init(self)
        if self._JSON_metadata is None:
            self._JSON_metadata = pyConfigContext(self.JSON_metadata)
            self.validate_json()

    def bind_store(self, store):
        'Connect our query to a database'
        db = store.db
        if self._store is not store:
            self._store = store
        if self._db is not db:
            self._db = db
        self._queryobj = QueryExecutor.construct_query(self._store, self._JSON_metadata)
        self.validate_json()

    def parameter_names(self):
        'Return the parameter names that go with this query'
        return self._queryobj.parameter_names()

    def execute(self, executor_context, idsonly=False, expandJSON=False, maxJSON=0, elemsonly=False
    ,       **params):
        'Execute the query and return an iterator that produces sanitized (filtered) results'
        if self._db is None:
            raise ValueError('query must be bound to a Store')

        queryobj = QueryExecutor.construct_query(self._store, self._JSON_metadata)
        qparams = queryobj.parameter_names()
        for pname in qparams:
            if pname not in params:
                raise ValueError('Required parameter "%s" for %s query is missing'
                %    (pname, self.queryname))
        for pname in params.keys():
            if pname not in qparams:
                raise ValueError('Excess parameter "%s" supplied for %s query'
                %    (pname, self.queryname))
        fixedparams = self.validate_parameters(params)
        resultiter = queryobj.result_iterator(fixedparams)
        return self.filter_json(executor_context, idsonly, expandJSON
        ,   maxJSON, resultiter, elemsonly)


    def supports_cmdline(self, language='en'):
        'Return True if this query supports command line formatting'
        meta = self._JSON_metadata
        return 'cmdline' in meta and language in meta['cmdline']

    def cmdline_exec(self, executor_context, language='en', fmtstring=None, **params):
        'Execute the command line version of the query for the specified language'
        if fmtstring is None:
            fmtstring = self._JSON_metadata['cmdline'][language]
        fixedparams = self.validate_parameters(params)
        for json in self.execute(executor_context, expandJSON=True
        ,           maxJSON=5120, elemsonly=True, **fixedparams):
            obj = pyConfigContext(json)
            yield ClientQuery._cmdline_substitute(fmtstring, obj)

    @staticmethod
    def _cmdline_substitute(fmtstring, queryresult):
        '''Perform expression substitution for command line queries.
        'Substitute fields into the command line output'''
        chunks = fmtstring.split('${')
        result = chunks[0]
        for j in range(1, len(chunks)):
            # Now we split it up into variable-expression, '}' and extrastuff...
            (variable, extra) = chunks[j].split('}',1)
            result += str(JSONtree(queryresult.deepget(variable, 'undefined')))
            result += extra
        return result

    def filter_json(self, executor_context, idsonly, expandJSON, maxJSON
    ,       resultiter, elemsonly=False):
        '''Return a sanitized (filtered) JSON stream from the input iterator
        The idea of the filtering is to enforce security restrictions on which
        things can be returned and which fields the executor is allowed to view.
        This is currently completely ignored, and everthing is returned - as is.
        This function is a generator.

        parameters
        ----------
        executor_context - security context to execute this in
        ids_only - if True, return only the URL of the objects (via object id)
                        otherwise return the objects themselves
        resultiter - iterator giving return results for us to filter
        '''
        self = self

        idsonly = idsonly
        executor_context = executor_context
        rowdelim = '{"data":[' if not elemsonly else ''
        rowcount = 0
        for result in resultiter:
            # result is a namedtuple
            rowcount += 1
            if len(result) == 1:
                if idsonly:
                    yield '%s"%s/%d"' % (
                        rowdelim
                    ,   ClientQuery.node_query_url
                    ,   Store.id(result[0]))
                else:
                    yield rowdelim + str(JSONtree(result[0], expandJSON=expandJSON
                    ,   maxJSON=maxJSON))
            else:
                delim = rowdelim + '{'
                row = ''
                # W0212: Access to a protected member _fields of a client class
                # No other way to get the list of columns/fields...
                # OK - there may be another way, but I didn't how to apply what Nigel told me
                # pylint: disable=W0212
                for attr in result._fields:
                    value = getattr(result, attr)
                    if idsonly:
                        row +=  '%s"%s":"%s"' % (
                                delim
                            ,   attr
                            ,   Store.id(value))

                    else:
                        row += '%s"%s":%s' % (
                                delim
                            ,   attr
                            ,   str(JSONtree(value, expandJSON=expandJSON, maxJSON=maxJSON)))
                    delim = ','
                yield row + '}'
            if not elemsonly:
                rowdelim = ','
        if not elemsonly:
            if rowcount == 0:
                yield '{"data":[]}'
            else:
                yield ']}'

    # R0912: Too many branches; R0914: too many local variables
    # pylint: disable=R0914,R0912
    def validate_json(self):
        '''Validate the JSON metadata for this query - it's complicated!'''
        queryobj = QueryExecutor.construct_query(self._store, self._JSON_metadata)
        query_parameter_names = queryobj.parameter_names()
        if 'parameters' not in self._JSON_metadata:
            raise ValueError('parameters missing from metadata')
        paramdict = self._JSON_metadata['parameters']
        if 'descriptions' not in self._JSON_metadata:
            print >> sys.stderr, 'METADATA:', self._JSON_metadata
            raise ValueError('descriptions missing from metadata')

        # Validate query descriptions
        languages = self._JSON_metadata['descriptions']
        for lang in languages:
            thislang = languages[lang]
            if 'short' not in thislang:
                raise ValueError('"short" query description missing from language %s' % lang)
            if 'long' not in thislang:
                raise ValueError('"long" query description missing from language %s' % lang)
        if 'en' not in languages:
            raise ValueError("Query description must include language en'")
        for name in query_parameter_names:
            if name not in paramdict:
                raise ValueError('Required parameter %s missing from JSON parameters' % name)
        for name in paramdict.keys():
            if name not in query_parameter_names:
                raise ValueError('JSON parameter %s not required by query' % name)

        # Validate query parameters
        for param in queryobj.parameter_names():
            pinfo = paramdict[param]
            ptype = pinfo['type']
            self.validate_query_parameter_metadata(param, pinfo)
            # Validate parameter information for this (param) language
            if 'lang' not in pinfo:
                raise ValueError("Parameter %s must include 'lang' information" % param)
            langs = pinfo['lang']
            for lang in languages.keys():
                if lang not in langs:
                    raise ValueError("Language %s missing from parameter %s"  % param)
            for lang in langs.keys():
                if lang not in languages:
                    raise ValueError("Language %s missing from query description %s"  % lang)
            for eachlang in langs.keys():
                thislang = langs[eachlang]
                if 'short' not in thislang:
                    raise ValueError("Parameter %s, language %s must include 'short' info"
                    %       (param, eachlang))
                if 'long' not in thislang:
                    raise ValueError("Parameter %s, language %s must include 'long' info"
                    %       (param, eachlang))
                if ptype == 'enum' or (ptype == 'list' and pinfo['listtype']['type'] == 'enum'):
                    if 'enumlist' not in thislang:
                        raise ValueError("Parameter %s, language %s must include 'enumlist' info"
                        %       (param, eachlang))
                    enums = thislang['enumlist']
                    elist = pinfo['enumlist'] if ptype == 'enum' else pinfo['listtype']['enumlist']
                    for e in elist:
                        if e not in enums:
                            raise ValueError("Parameter %s, language %s missing enum value %s"
                            %       (param, eachlang, e))
        return True


    def validate_query_parameter_metadata(self, param, pinfo):
        'Validate the paramater metadata for this query'
        if 'type' not in pinfo:
            raise ValueError('Parameter %s missing type field' % param)
        ptype = pinfo['type']
        if ptype not in ClientQuery._validationmethods:
            raise ValueError('Parameter %s has invalid type %s'% (param, ptype))
        if 'min' in pinfo and ptype != 'int' and ptype != 'float':
            raise ValueError('Min only valid on numeric fields [%s]'% param )
        if 'max' in pinfo and ptype != 'int' and ptype != 'float':
            raise ValueError('Max only valid on numeric fields [%s]'% param )
        if ptype == 'list':
            if 'listtype' not in pinfo:
                raise ValueError('List type [%s] requires listtype'% (param))
            self.validate_query_parameter_metadata('list', pinfo['listtype'])
        if ptype == 'enum':
            if 'enumlist' not in pinfo:
                raise ValueError('Enum type [%s] requires enumlist'% (param))
            elist = pinfo['enumlist']
            for enum in elist:
                if not isinstance(enum, str) and not isinstance(enum, unicode):
                    raise ValueError('Enumlist values [%s] must be strings - not %s'
                    %   (enum, type(enum)))

    def validate_parameters(self, parameters):
        '''
        parameters is a Dict-like object containing parameter names and values
        '''
        # Let's see if all the parameters were supplied
        paramdict = self._JSON_metadata['parameters']
        queryobj = QueryExecutor.construct_query(self._store, self._JSON_metadata)
        for param in queryobj.parameter_names():
            if param not in parameters:
                raise ValueError('Parameter %s not supplied' % param)
        # Let's see if any extraneous parameters were supplied
        for param in parameters.keys():
            if param not in paramdict:
                raise ValueError('Invalid Parameter %s supplied' % param)
        result = {}
        for param in parameters.keys():
            value = parameters[param]
            canonvalue = ClientQuery._validate_value(param, paramdict[param], value)
            result[param] = canonvalue
        return result



    @staticmethod
    def _validate_int(name, paraminfo, value):
        'Validate an int value'
        val = int(value)
        if 'min' in paraminfo:
            minval = paraminfo['min']
            if val < minval:
                raise ValueError('Value of %s [%s] smaller than mininum [%s]'
                %   (name, val, minval))
        if 'max' in paraminfo:
            maxval = paraminfo['max']
            if val > maxval:
                raise ValueError('Value of %s [%s] larger than maximum [%s]'
                %   (name, val, maxval))
        return val

    @staticmethod
    def _validate_float(name, paraminfo, value):
        'Validate an floating point value'
        val = float(value)
        if 'min' in paraminfo:
            minval = paraminfo['min']
            if val < minval:
                raise ValueError('Value of %s[%s] smaller than mininum [%s]'
                %   (name, val, minval))
        if 'max' in paraminfo:
            maxval = paraminfo['max']
            if val > maxval:
                raise ValueError('Value of %s [%s] larger than maximum [%s]'
                %   (name, val, maxval))
        return val

    @staticmethod
    def _validate_string(_name, _paraminfo, value):
        'Validate a string value (FIXME: should this always be valid??)'
        # FIXME: This should probably make sure no " or ' or [], ;'s - maybe others?
        # Probably should allow ":"
        return value

    @staticmethod
    def _validate_macaddr(name, _paraminfo, value):
        'Validate an MAC address value'
        mac = pyNetAddr(value)
        if mac is None:
            raise ValueError('value of %s [%s] not a valid MAC address' % (name, value))
        if mac.addrtype() != ADDR_FAMILY_802:
            raise ValueError('Value of %s [%s] not a MAC address' % (name, value))
        return str(mac)

    @staticmethod
    def _validate_ipaddr(name, _paraminfo, value):
        'Validate an IP address value'
        ip = pyNetAddr(value)
        if ip is None:
            raise ValueError('Value of %s [%s] not a valid IP address' % (name, value))
        ip.setport(0)
        if ip.addrtype() == ADDR_FAMILY_IPV6:
            return str(ip)
        if ip.addrtype() == ADDR_FAMILY_IPV4:
            return str(ip.toIPv6())
        raise ValueError('Value of %s [%s] not an IP address' % (name, value))

    @staticmethod
    def _validate_bool(name, _paraminfo, value):
        'Validate an Boolean value'
        if not isinstance(value, bool):
            raise ValueError('Value of %s [%s] not a boolean' % (name, value))
        return value

    @staticmethod
    def _validate_regex(name, _paraminfo, value):
        'Validate a regular expression'
        try:
            re.compile(value)
        except re.error as e:
            raise ValueError('Value of %s ("%s") is not a valid regular expression [%s]' %
                             (name, value, str(e)))
        return value

    @staticmethod
    def _validate_hostname(name, paraminfo, value):
        'Validate a hostname value'
        return ClientQuery._validate_dnsname(name, paraminfo, value)

    @staticmethod
    def _validate_dnsname(_name, _paraminfo, value):
        'Validate an DNS name value'
        value = str(value)
        return value.lower()

    @staticmethod
    def _validate_enum(name, paraminfo, value):
        'Validate an enumeration value'
        if 'enumlist' not in paraminfo:
            raise TypeError("No 'enumlist' for parameter" % name)
        value = value.tolower()
        for val in paraminfo['enumlist']:
            cmpval = val.lower()
            if cmpval == value:
                return cmpval
        raise ValueError('Value of %s [%s] not in enumlist' % (paraminfo['name'], value))

    @staticmethod
    def _validate_list(name, paraminfo, listvalue):
        'Validate a list value'
        if isinstance(listvalue, (str, unicode)):
            listvalue = listvalue.split(',')
        result = []
        listtype = paraminfo['listtype']
        for elem in listvalue:
            result.append(ClientQuery._validate_value(name, listtype, elem))
        return result

    @staticmethod
    def _get_nodetype(nodetype):
        'Return the value of a node type - if valid'
        nodetypes = set()
        for attr in dir(CMAconsts):
            if attr.startswith('NODE_') and isinstance(getattr(CMAconsts, attr), (str, unicode)):
                nodetypes.add(attr[5:])
                nodetypes.add(getattr(CMAconsts, attr))
        if nodetype not in nodetypes:
            return None
        defname = 'NODE_' + nodetype
        return getattr(CMAconsts, defname) if hasattr(CMAconsts, defname) else nodetype


    @staticmethod
    def _validate_nodetype(name, _paraminfo, value):
        'validate a node type - ignoring case'
        ret = ClientQuery._get_nodetype(value)
        if ret is not None:
            return ret
        raise ValueError('Value of %s [%s] is not a known node type' % (name, value))


    @staticmethod
    def _get_reltype(reltype):
        'Return the value of a relationship type - if valid'
        reltypes = set()
        for attr in dir(CMAconsts):
            if attr.startswith('REL_') and isinstance(getattr(CMAconsts, attr), (str, unicode)):
                reltypes.add(attr[4:])
                reltypes.add(getattr(CMAconsts, attr))
        if reltype not in reltypes:
            return None
        defname = 'REL_' + reltype
        return getattr(CMAconsts, defname) if hasattr(CMAconsts, defname) else reltype

    @staticmethod
    def _validate_reltype(name, _paraminfo, value):
        'Validate a relationship type - ignoring case'
        ret = ClientQuery._get_reltype(value)
        if ret is not None:
            return ret
        raise ValueError('Value of %s [%s] is not a known relationship type' % (name, value))

    _validationmethods = {}

    @staticmethod
    def _validate_value(name, paraminfo, value):
        '''Validate the value given our metadata'''
        valtype = paraminfo['type']
        return ClientQuery._validationmethods[valtype](name, paraminfo, value)

    @staticmethod
    def load_from_file(store, pathname, queryname=None):
        'Load a query with metadata from a file'
        fd = open(pathname, 'r')
        json = fd.read()
        fd.close()
        if pyConfigContext(json) is None:
            raise ValueError ('ERROR: Contents of %s is not valid JSON.' % (pathname))
        if queryname is None:
            queryname = os.path.basename(pathname)
        #print 'LOADING %s as %s' % (pathname, queryname)
        ret = store.load_or_create(ClientQuery, queryname=queryname, JSON_metadata=json)
        ret.JSON_metadata = json
        ret.bind_store(store)
        if not ret.validate_json():
            print >> sys.stderr, ('ERROR: Contents of %s is not a valid query.' % pathname)

        return ret

    @staticmethod
    def load_directory(store, directoryname):
        'Returns a generator that returns all the Queries in that directory'
        files = os.listdir(directoryname)
        files.sort()
        for filename in files:
            path = os.path.join(directoryname, filename)
            try:
                yield ClientQuery.load_from_file(store, path)
            except ValueError as e:
                print >> sys.stderr, 'File %s is invalid: %s' % (path, str(e))

    @staticmethod
    def load_tree(store, rootdirname, followlinks=False):
        'Returns a generator that will returns all the Queries in that directory structure'
        tree = os.walk(rootdirname, topdown=True, onerror=None, followlinks=followlinks)
        rootprefixlen = len(rootdirname)+1
        for walktuple in tree:
            (dirpath, dirnames, filenames) = walktuple
            dirnames.sort()
            prefix = dirpath[rootprefixlen:]
            filenames.sort()
            for filename in filenames:
                queryname = prefix + filename
                path = os.path.join(dirpath, filename)
                if filename.startswith('.'):
                    continue
                try:
                    yield ClientQuery.load_from_file(store, path, queryname)
                except ValueError as e:
                    print >> sys.stderr, 'File %s is invalid: %s' % (path, str(e))

class QueryExecutor(object):
    '''An abstract class which knows which can perform a variety of types of queries
    At the moment that's "python" and "cypher".
    '''
    DEFAULT_EXECUTOR_METHOD = 'CypherExecutor'
    EXECUTOR_METHODS = {}

    def __init__(self, store, metadata):
        '''Construct an object remembering our metadata'''
        self.store = store
        self.metadata = metadata

    @staticmethod
    def construct_query(store, metadata):
        '''Construct a query of the type requested.
        We return None if we can't construct a query from our metadata.
        '''
        querytype = (metadata['querytype'] if 'querytype' in metadata
                     else QueryExecutor.DEFAULT_EXECUTOR_METHOD)

        if querytype not in QueryExecutor.EXECUTOR_METHODS:
            raise ValueError('Querytype %s is not a valid query type' % querytype)
        queryclass = QueryExecutor.EXECUTOR_METHODS[querytype]
        return (queryclass.construct_query(store, metadata)
                if querytype in QueryExecutor.EXECUTOR_METHODS else None)

    @staticmethod
    def register(ourclass):
        'Register this class as a QueryExecutor subclass'
        QueryExecutor.EXECUTOR_METHODS[ourclass.__name__] = ourclass
        return ourclass

    def parameter_names(self):
        '''We return a set of parameters that we expect.
        We return None if we are flexible (or don't know) about our expected parameters.
        '''
        raise NotImplementedError('QueryExecutor is an abstract class')

    def result_iterator(self, params):
        '''We return an iterator which will yield the results of performing
        this query with these parameters.
        '''
        raise NotImplementedError('QueryExecutor is an abstract class')


@QueryExecutor.register
class CypherExecutor(QueryExecutor):
    '''QueryExecutor subclass for Cypher queries'''

    @staticmethod
    def construct_query(store, metadata):
        'Call the CypherExecutor constructor'
        return CypherExecutor(store, metadata)

    def __init__(self, store, metadata):
        if 'cypher' not in metadata:
            raise ValueError('cypher query missing from metadata: %s' % str(metadata))
        QueryExecutor.__init__(self, store, metadata)
        self.query = metadata['cypher']

    def parameter_names(self):
        '''We return a set of parameters that we expect.
        We return None if we are flexible (or don't know) about our expected parameters.
        Return the parameter names our cypher query uses'''

        START       = 1
        BACKSLASH   = 2
        GOTLCURLY   = 3
        results     = []
        paramname   = ''
        state = START

        for c in self.metadata['cypher']:
            if state == START:
                if c == '\\':
                    state = BACKSLASH
                if c == '{':
                    state = GOTLCURLY
            elif state == BACKSLASH:
                state = START
            else: # GOTLCURLY
                if c == '}':
                    if paramname != '':
                        results.append(paramname)
                        paramname = ''
                    state = START
                else:
                    paramname += c
        return results

    def result_iterator(self, params):
        '''We return an iterator which will yield the results of performing
        this query with these parameters.
        '''
        return self.store.load_cypher_query(self.query, GraphNode.factory, params=params)

@QueryExecutor.register
class PythonExec(QueryExecutor):
    '''QueryExecutor subclass for Python code queries'''

    EXECUTOR_METHODS = {}
    PARAMETERS = []

    def parameter_names(self):
        '''We return a set of parameters that we expect.
        We return None if we are flexible (or don't know) about our expected parameters.
        Return the parameter names our cypher query uses'''
        return self.PARAMETERS

    @staticmethod
    def register(ourclass):
        PythonExec.EXECUTOR_METHODS[ourclass.__name__] = ourclass
        return ourclass

    def result_iterator(self, params):
        '''We return an iterator which will yield the results of performing
        this query with these parameters.
        '''
        raise NotImplementedError('PythonExec is an abstract class')

    @staticmethod
    def construct_query(store, metadata):
        'Call the subclass constructor'
        if 'subtype' not in metadata:
            raise ValueError('subtype missing from PythonExec metadata')
        subclassname = metadata['subtype']
        if subclassname not in PythonExec.EXECUTOR_METHODS:
            raise ValueError('%s is not a valid PythonExec subtype' % subclassname)
        subclass = PythonExec.EXECUTOR_METHODS[subclassname]
        return subclass(store, metadata)

@PythonExec.register
class AllPythonRuleScores(PythonExec):
    '''Return discovery type+rule scores for all discovery types'''
    PARAMETERS = []

    def result_iterator(self, _params):
        '''We return an iterator which will yield the results of performing
        this query with these parameters.
        '''
        dtype_totals, _drone_totals, rule_totals = grab_category_scores(self.store)
        # 0:  domain
        # 1:  category name
        # 2:  discovery-type
        # 3:  total score for this discovery type _across all rules
        # 4:  rule id
        # 5:  total score for this rule id
        sortkeys = operator.itemgetter(1,3,5,2,4,0)
        for tup in sorted(yield_rule_scores([], dtype_totals, rule_totals),
                          key=sortkeys, reverse=True):
            yield tup

@PythonExec.register
class PythonSecRuleScores(PythonExec):
    '''query executor returning discovery type+rule scores for security scores'''
    PARAMETERS = []
    def result_iterator(self, _params):
        '''We return an iterator which will yield the results of performing
        this query with these parameters.
        '''
        dtype_totals, _drone_totals, rule_totals =grab_category_scores(self.store,
                                                                      categories='security')
        # 0:  domain
        # 1:  category name
        # 2:  discovery-type
        # 3:  total score for this discovery type _across all rules
        # 4:  rule id
        # 5:  total score for this rule id
        sortkeys = operator.itemgetter(1,3,5,2,4,0)
        for tup in sorted(yield_rule_scores(['security'], dtype_totals, rule_totals),
                          key=sortkeys, reverse=True):
            yield tup

@PythonExec.register
class PythonHostSecScores(PythonExec):
    '''Return discovery type+host security scores'''
    PARAMETERS = []
    PARAMETERS = []
    def result_iterator(self, _params):
        dtype_totals, drone_totals, _rule_totals = grab_category_scores(self.store)
        # 0:  domain
        # 1:  category name
        # 2:  discovery-type
        # 3:  total score for this discovery type _across all drones
        # 4:  drone designation (name)
        # 5:  total score for this drone for this discovery type
        sortkeys = operator.itemgetter(0,3,5,2,4,1)
        for tup in sorted(yield_drone_scores([], drone_totals, dtype_totals),
                          key=sortkeys, reverse=True):
            yield tup

@PythonExec.register
class AllPythonHostScores(PythonExec):
    '''query executor returning discovery type+host scores for all score types'''
    PARAMETERS = []
    def result_iterator(self, _params):
        dtype_totals, drone_totals, _rule_totals = grab_category_scores(self.store)
        # 0:  domain
        # 1:  category name
        # 2:  discovery-type
        # 3:  total score for this discovery type _across all drones
        # 4:  drone designation (name)
        # 5:  total score for this drone for this discovery type
        sortkeys = operator.itemgetter(0,3,5,2,4,1)
        for tup in sorted(yield_drone_scores([], drone_totals, dtype_totals),
                          key=sortkeys, reverse=True):
            yield tup
@PythonExec.register
class AllPythonTotalScores(PythonExec):
    '''query executor returning domain, score-category, total-score'''
    PARAMETERS = []
    def result_iterator(self, _params):
        dtype_totals, _drone_totals, _rule_totals = grab_category_scores(self.store)
        for tup in yield_total_scores(dtype_totals):
            yield tup


def setup_dict3(d, key1, key2, key3):
    'Initialize the given subkey (3 layers down)to 0.0'
    if key1 not in d:
        d[key1] = {}
    if key2 not in d[key1]:
        d[key1][key2] = {}
    if key3 not in d[key1][key2]:
        d[key1][key2][key3] = 0.0

def setup_dict4(d, key1, key2, key3, key4):
    'Initialize the given subkey (4 layers down)to 0.0'
    if key1 not in d:
        d[key1] = {}
    if key2 not in d[key1]:
        d[key1][key2] = {}
    if key3 not in d[key1][key2]:
        d[key1][key2][key3] = {}
    if key4 not in d[key1][key2][key3]:
        d[key1][key2][key3][key4] = 0.0


# [R0914:grab_category_scores] Too many local variables (19/15)
# pylint: disable=R0914
def grab_category_scores(store, categories=None, domains=None, debug=False):
    '''Method to create and return some python Dicts with security scores and totals by category
    and totals by drone/category
    Categories is None, a desired category, or a list of desired categories.
    domains is None, a desired domain, or a list of desired domains.
    '''
    if domains is None:
        cypher = '''START drone=node:Drone('*:*') RETURN drone'''
    else:
        domains = (domains,) if isinstance(domains, (str, unicode)) else list(domains)
        cypher = ("START drone=node:Drone('*:*') WHERE drone.domain IN %s RETURN drone"
                 %  str(list(domains)))
    if categories is not None:
        categories = (categories,) if isinstance(categories, (str, unicode)) else list(categories)

    bpobj = BestPractices(CMAdb.io.config, CMAdb.io, store, CMAdb.log, debug=debug)
    dtype_totals = {} # scores organized by (domain, category, discovery-type)
    drone_totals = {} # scores organized by (domain, category, discovery-type, drone)
    rule_totals  = {} # scores organized by (domain, category, discovery-type, rule)

    for drone in store.load_cypher_nodes(cypher, Drone):
        domain = drone.domain
        designation = drone.designation
        discoverytypes = drone.bp_discoverytypes_list()
        for dtype in discoverytypes:
            dattr = Drone.bp_discoverytype_result_attrname(dtype)
            statuses = getattr(drone, dattr)
            for rule_obj in BestPractices.eval_objects[dtype]:
                rulesobj = rule_obj.fetch_rules(drone, None, dtype)
                _, scores, rulescores = bpobj.compute_scores(drone, rulesobj, statuses)
                for category in scores:
                    if categories and category not in categories:
                        continue
                    # Accumulate scores by (domain, category, discovery_type)
                    setup_dict3(dtype_totals, domain, category, dtype)
                    dtype_totals[domain][category][dtype] += scores[category]
                    # Accumulate scores by (domain, category, discovery_type, drone)
                    setup_dict4(drone_totals, domain, category, dtype, designation)
                    drone_totals[domain][category][dtype][designation] += scores[category]
                    # Accumulate scores by (domain, category, discovery_type, ruleid)
                    for ruleid in rulescores[category]:
                        setup_dict4(rule_totals, domain, category, dtype, ruleid)
                        rule_totals[domain][category][dtype][ruleid] += rulescores[category][ruleid]

    return dtype_totals, drone_totals, rule_totals

def yield_total_scores(dtype_totals, categories=None):
    '''Format the total scores by category as a named tuple.
    We output the following fields:
        0:  domain
        1:  category name
        3:  total score for this category
    '''
    TotalScore = collections.namedtuple('TotalScore', ['domain', 'category', 'score'])
    for domain in sorted(dtype_totals):
        domain_scores = dtype_totals[domain]
        for category in sorted(domain_scores):
            total = 0.0
            if categories is not None and category not in categories:
                continue
            cat_scores = domain_scores[category]
            for dtype in cat_scores:
                total += cat_scores[dtype]
            yield TotalScore(domain, category, total)

def yield_drone_scores(categories, drone_totals, dtype_totals):
    '''Format the drone_totals + dtype_totals as a named tuple
    We output the following fields:
        0:  domain
        1:  category name
        2:  discovery-type
        3:  total score for this discovery type _across all drones_
        4:  drone designation (name)
        5:  total score for this drone for this discovery type
    '''
    DroneScore = collections.namedtuple('DroneScore', ['domain', 'category', 'discovery_type',
                                           'dtype_score', 'drone', 'drone_score'])
    for domain in drone_totals:
        for cat in drone_totals[domain]:
            if categories and cat not in categories:
                continue
            for dtype in drone_totals[domain][cat]:
                for drone in drone_totals[domain][cat][dtype]:
                    score = drone_totals[domain][cat][dtype][drone]
                    if score > 0:
                        yield DroneScore(domain, cat, dtype, dtype_totals[domain][cat][dtype],
                                         drone, score)

def yield_rule_scores(categories, dtype_totals, rule_totals):
    '''Format the rule totals + dtype_totals as a CSV-style output
    We output the following fields:
        0:  domain
        1:  category name
        2:  discovery-type
        3:  total score for this discovery type _across all rules
        5:  rule id
        6:  total score for this rule id
    '''
    # rule_totals = # scores organized by (category, discovery-type, rule)

    RuleScore = collections.namedtuple('RuleScore',
                          ['domain', 'category', 'discovery_type', 'dtype_score',
                           'ruleid', 'ruleid_score'])
    for domain in rule_totals:
        for cat in rule_totals[domain]:
            if categories and cat not in categories:
                continue
            for dtype in rule_totals[domain][cat]:
                for ruleid in rule_totals[domain][cat][dtype]:
                    score = rule_totals[domain][cat][dtype][ruleid]
                    if score > 0:
                        yield RuleScore(domain, cat, dtype, dtype_totals[domain][cat][dtype],
                                        ruleid, score)
PackageTuple = collections.namedtuple('PackageTuple',
                                      ['domain', 'drone', 'package', 'version', 'packagetype'])
@PythonExec.register
class PythonPackagePrefixQuery(PythonExec):
    '''query executor returning packages matching the given prefix'''
    PARAMETERS = ['prefix']
    def result_iterator(self, params):
        prefix = params['prefix']
        # 0:  domain
        # 1:  Drone
        # 2:  Package name
        # 3:  Package Version
        # 4:  Package type
        cypher = (
        '''START drone=node:Drone('*:*')
        MATCH (drone)-[rel:jsonattr]->(jsonmap)
        WHERE rel.jsonname = '_init_packages' AND jsonmap.json CONTAINS '"%s'
        return drone, jsonmap.json AS json
        '''     %   prefix)
        for (drone, json) in self.store.load_cypher_query(cypher, Drone):
            jsonobj = pyConfigContext(json)
            # pylint is confused here - jsonobj['data'] _is_ very much iterable...
            # pylint: disable=E1133
            jsondata = jsonobj['data']
            for pkgtype in jsondata:
                for package in jsondata[pkgtype]:
                    if package.startswith(prefix):
                        yield PackageTuple(drone.domain, drone, package,
                                           jsondata[pkgtype][package], pkgtype)


@PythonExec.register
class PythonAllPackageQuery(PythonExec):
    '''query executor returning all packages on all systems'''
    PARAMETERS = []
    def result_iterator(self, params):
        # 0:  domain
        # 1:  Drone
        # 2:  Package name
        # 3:  Package Version
        cypher = (
        '''START drone=node:Drone('*:*')
           MATCH (drone)-[rel:jsonattr]->(jsonmap)
           WHERE rel.jsonname = '_init_packages'
           RETURN drone, jsonmap.json AS json
        ''')

        for (drone, json) in self.store.load_cypher_query(cypher, GraphNode.factory):
            jsonobj = pyConfigContext(json)
            # pylint is confused here - jsonobj['data'] _is_ very much iterable...
            # pylint: disable=E1133
            jsondata = jsonobj['data']
            for pkgtype in jsondata:
                for package in jsondata[pkgtype]:
                    yield PackageTuple(drone.domain, drone, package,
                                       jsondata[pkgtype][package], pkgtype)

@PythonExec.register
class PythonPackageRegexQuery(PythonExec):
    '''query executor returning packages matching the given regular expression'''
    PARAMETERS = ['regex']
    def result_iterator(self, params):
        regex = params['regex']
        # 0:  domain
        # 1:  Drone
        # 2:  Package name
        # 3:  Package Version
        cypher = (
        '''START drone=node:Drone('*:*')
           MATCH (drone)-[rel:jsonattr]->(jsonmap)
           WHERE rel.jsonname = '_init_packages' AND jsonmap.json =~ '.*%s.*.*'
           RETURN drone, jsonmap.json AS json
        '''     %   regex)

        regexobj = re.compile('.*' + regex)
        for (drone, json) in self.store.load_cypher_query(cypher, GraphNode.factory):
            jsonobj = pyConfigContext(json)
            # pylint is confused here - jsonobj['data'] _is_ very much iterable...
            # pylint: disable=E1133
            jsondata = jsonobj['data']
            for pkgtype in jsondata:
                for package in jsondata[pkgtype]:
                    if regexobj.match(package):
                        yield PackageTuple(drone.domain, drone, package,
                                           jsondata[pkgtype][package], pkgtype)


@PythonExec.register
class PythonPackageQuery(PythonExec):
    '''query executor returning packages of the given name'''
    PARAMETERS = ['packagename']
    def result_iterator(self, params):
        packagename = params['packagename']
        if packagename.find('::') < 0:
            packagename += '::'
        # 0:  domain
        # 1:  Drone
        # 2:  Package name
        # 3:  Package Version
        cypher = (
        '''START drone=node:Drone('*:*')
        MATCH (drone)-[rel:jsonattr]->(jsonmap)
        WHERE rel.jsonname = '_init_packages' AND jsonmap.json CONTAINS '"%s'
        return drone, jsonmap.json as json
        '''     %   packagename)
        for (drone, json) in self.store.load_cypher_query(cypher, GraphNode.factory):
            jsonobj = pyConfigContext(json)
            # pylint is confused here - jsonobj['data'] _is_ very much iterable...
            # pylint: disable=E1133
            jsondata = jsonobj['data']
            for pkgtype in jsondata:
                for package in jsondata[pkgtype]:
                    if package.startswith(packagename):
                        yield PackageTuple(drone.domain, drone, package,
                                           jsondata[pkgtype][package], pkgtype)

def reltype_expr(reltypes):
    'Create a Cypher query expression for (multiple) relationship types'
    if isinstance(reltypes, (str, unicode)):
        reltypes = (reltypes,)
    relationship_expression = ''
    delim=''
    for reltype in reltypes:
        relationship_expression  += '%s:%s' % (delim, reltype)
        delim = '|'
    return relationship_expression

@PythonExec.register
class PythonDroneSubgraphQuery(PythonExec):
    'A class to return a subgraph centered around one or more Drones'
    PARAMETERS = ['nodetypes', 'reltypes', 'hostname']
    basequery = \
        '''START start=node:Drone('*:*')
        WHERE start.nodetype = 'Drone' AND start.designation in '%s'
        MATCH p = shortestPath( (start)-[%s*]-(m) )
        WHERE m.nodetype IN %s
        UNWIND nodes(p) AS n
        UNWIND rels(p) AS r
        RETURN [x in COLLECT(DISTINCT n) WHERE x.nodetype in %s] AS nodes,
        COLLECT(DISTINCT r) AS relationships'''

    def result_iterator(self, params):
        nodetypes = params['nodetypes']
        reltypes  = params['reltypes']
        designation = params['hostname']
        if isinstance(designation, (str, unicode)):
            designation = [designation]
        designation_s = str(designation)
        relstr = reltype_expr(reltypes)
        nodestr = str(nodetypes)
        query = PythonDroneSubgraphQuery.basequery % (designation_s, relstr, nodestr, nodestr)
        #print >> sys.stderr, 'RUNNING THIS QUERY:', query
        for row in self.store.load_cypher_query(query, GraphNode.factory):
            yield row

@PythonExec.register
class PythonAllDronesSubgraphQuery(PythonExec):
    'A class to return a subgraph centered around a Drone'
    PARAMETERS = ['nodetypes', 'reltypes']
    basequery = \
        '''START start=node:Drone('*:*')
        WHERE start.nodetype = 'Drone'
        MATCH p = shortestPath( (start)-[%s*]-(m) )
        WHERE m.nodetype IN %s
        UNWIND nodes(p) AS n
        UNWIND rels(p) AS r
        RETURN [x in COLLECT(DISTINCT n) WHERE x.nodetype in %s] AS nodes,
        COLLECT(DISTINCT r) AS relationships'''

    def result_iterator(self, params):
        nodetypes = params['nodetypes']
        reltypes  = params['reltypes']
        relstr = reltype_expr(reltypes)
        nodestr = str(nodetypes)
        query = PythonAllDronesSubgraphQuery.basequery % (relstr, nodestr, nodestr)
        #print >> sys.stderr, 'RUNNING THIS QUERY:', query
        for row in self.store.load_cypher_query(query, GraphNode.factory):
            yield row


# message W0212: access to protected member of client class
# pylint: disable=W0212
ClientQuery._validationmethods = {
    'int':      ClientQuery._validate_int,
    'float':    ClientQuery._validate_float,
    'bool':     ClientQuery._validate_bool,
    'string':   ClientQuery._validate_string,
    'enum':     ClientQuery._validate_enum,
    'ipaddr':   ClientQuery._validate_ipaddr,
    'list':     ClientQuery._validate_list,
    'macaddr':  ClientQuery._validate_macaddr,
    'hostname': ClientQuery._validate_hostname,
    'dnsname':  ClientQuery._validate_dnsname,
    'regex':    ClientQuery._validate_regex,
    'nodetype': ClientQuery._validate_nodetype,
    'reltype':  ClientQuery._validate_reltype,
}

if __name__ == '__main__':
    # pylint: disable=C0413
    from store import Store
    from cmadb import Neo4jCreds
    metadata1 = \
    '''
    {   "cypher": "START n=node:ClientQuery('*:*') RETURN n",
        "parameters": {},
        "descriptions": {
            "en": {
                "short":    "list all queries",
                "long":     "return a list of all available queries"
            }
        }
    }
    '''
    q1 = ClientQuery('allqueries', metadata1)

    metadata2 = \
    '''
    {   "cypher":   "START n=node:ClientQuery('{queryname}:metadata') RETURN n",
        "parameters": {
            "queryname": {
                "type": "string",
                "lang": {
                    "en": {
                        "short":    "query name",
                        "long":     "Name of query to retrieve"
                    }
                }
            }
        },
        "descriptions": {
            "en": {
                "short":    "Retrieve a query",
                "long":     "Retrieve all the information about a query"
            }
        }
    }
    '''
    q2 = ClientQuery('allqueries', metadata2)

    metadata3 = \
    '''
    {
        "cypher": "START ip=node:IPaddr('{ipaddr}:*')
                   MATCH (ip)<-[:ipowner]-()<-[:nicowner]-(system)
                   RETURN system",

        "descriptions": {
            "en": {
                "short":    "get system from IP",
                "long":     "retrieve the system owning the requested IP"
            }
        },
        "parameters": {
            "ipaddr": {
                "type": "ipaddr",
                "lang": {
                    "en": {
                        "short":    "IP address",
                        "long":     "IP (IPv4 or IPv6) address of system of interest"
                    }
                }
            }
        }
    }
    '''
    metadata4 =  \
    r''' {
        "cypher": 	"START start=node:Drone('*:*')
                    WHERE start.nodetype = 'Drone' AND start.designation = '{host}'
                    MATCH p = shortestPath( (start)-[*]-(m) )
                    WHERE m.nodetype IN {nodetypes}
                    UNWIND nodes(p) as n
                    UNWIND rels(p) as r
                    RETURN [x in collect(distinct n) WHERE x.nodetype in {nodetypes}]] as nodes,
                   collect(distinct r) as relationships",
        "copyright": "Copyright(C) 2014 Assimilation Systems Limited",
        "descriptions": {
            "en": {
                "short":    "return entire graph",
                "long":     "retrieve all nodes and all relationships"
            }
        },
        "parameters": {
            "host": {
                "type": "hostname",
                "lang": {
                    "en": {
                        "short":    "starting host name",
                        "long":     "name of host to start the query at"
                    }
                }
            },
            "nodetypes": {
                "type": "list",
                "listtype": {
                    "type": "nodetype"
                },
                "lang": {
                    "en": {
                        "short":    "node types",
                        "long":     "set of node types to include in query result",
                     }
                }
            }
        },
        "cmdline": {
            "en":	  "{\"nodes\":${nodes}, \"relationships\": ${relationships}}",
            "script": "{\"nodes\":${nodes}, \"relationships\": ${relationships}}"
        },
    }'''
    q3 = ClientQuery('ipowners', metadata3)
    q3.validate_json()
    q4 = ClientQuery('subgraph', metadata4)
    q4.validate_json()

    Neo4jCreds().authenticate()
    neodb = neo4j.Graph()
    neodb.delete_all()

    umap  = {'ClientQuery': True}
    ckmap = {'ClientQuery': {'index': 'ClientQuery', 'kattr':'queryname', 'value':'None'}}

    qstore = Store(neodb, uniqueindexmap=umap, classkeymap=ckmap)
    for classname in GraphNode.classmap:
        GraphNode.initclasstypeobj(qstore, classname)

    print "LOADING TREE!"

    dirname = os.path.dirname(sys.argv[0])
    dirname = '.' if dirname == '' else dirname
    queries = ClientQuery.load_tree(qstore, "%s/../queries" % dirname)
    qlist = [q for q in queries]
    qstore.commit()
    print "%d node TREE LOADED!" % len(qlist)
    qe2 = qstore.load_or_create(ClientQuery, queryname='list')
    qe2.bind_store(qstore)
    testresult = ''
    for s in qe2.execute(None, idsonly=False, expandJSON=True):
        testresult += s
    print 'RESULT', testresult
    # Test out a command line query
    for s in qe2.cmdline_exec(None):
        if re.match(s, '[	 ]unknown$'):
            raise RuntimeError('Search result contains unknown: %s' % s)
        print s

    print "All done!"
