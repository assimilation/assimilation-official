#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
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
import os
from py2neo import neo4j
from graphnodes import GraphNode, RegisterGraphClass
from AssimCclasses import pyConfigContext, pyNetAddr
from AssimCtypes import ADDR_FAMILY_IPV6, ADDR_FAMILY_IPV4, ADDR_FAMILY_802
from assimjson import JSONtree

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
                'cypher':       a string containing our cypher query
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
        if JSON_metadata is None:
            self._JSON_metadata = None
        else:
            self._JSON_metadata = pyConfigContext(JSON_metadata)
            if self._JSON_metadata is None:
                raise ValueError('Parameter JSON_metadata is invalid [%s]' % JSON_metadata)
            self.validate_json()
        self._store = None
        self._db = None
        self._query = None

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
            self._query = neo4j.CypherQuery(db, self._JSON_metadata['cypher'])

    def execute(self, executor_context, idsonly=False, expandJSON=False, maxJSON=0, elemsonly=False
    ,       **params):
        'Execute the query and return an iterator that produces sanitized (filtered) results'
        if self._query is None:
            raise ValueError('query must be bound to a Store')

        qparams = self.json_parameter_names()
        for pname in qparams:
            if pname not in params:
                raise ValueError('Required parameter "%s" for %s query is missing'
                %    (pname, self.queryname))
        for pname in params.keys():
            if pname not in qparams:
                raise ValueError('Excess parameter "%s" supplied for %s query'
                %    (pname, self.queryname))
        fixedparams = self.validate_parameters(params)
        resultiter = self._store.load_cypher_query(self._query, GraphNode.factory
        ,       params=fixedparams)
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
        ,           maxJSON=100, elemsonly=True, **fixedparams):
            obj = pyConfigContext(json)
            yield ClientQuery._cmdline_substitute(fmtstring, obj)

    @staticmethod
    def _cmdline_substitute(fmtstring, queryresult):
        'Substitute fields into the command line output'
        chunks = fmtstring.split('${')
        result = chunks[0]
        for j in range(1, len(chunks)):
            # Now we split it up into variable-expression, '}' and extrastuff...
            (variable, extra) = chunks[j].split('}')
            result += str(queryresult.deepget(variable, 'undefined'))
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



    def json_parameter_names(self):
        'Return the parameter names supplied from the metadata'
        return self._JSON_metadata['parameters'].keys()

    def cypher_parameter_names(self):
        'Return the parameter names our cypher query uses'
        START       = 1
        BACKSLASH   = 2
        GOTLCURLY   = 3
        results     = []
        paramname   = ''
        state = START

        for c in self._JSON_metadata['cypher']:
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

    # R0912: Too many branches; R0914: too many local variables
    # pylint: disable=R0914,R0912
    def validate_json(self):
        '''Validate the JSON for this query - it's complicated!'''
        if 'cypher' not in self._JSON_metadata:
            raise ValueError('cypher query missing from metadata')
        cyphernames = self.cypher_parameter_names()
        if 'parameters' not in self._JSON_metadata:
            raise ValueError('parameters missing from metadata')
        paramdict = self._JSON_metadata['parameters']
        if 'descriptions' not in self._JSON_metadata:
            raise ValueError('descriptions missing from metadata')
        languages = self._JSON_metadata['descriptions']
        for lang in languages.keys():
            thislang = languages[lang]
            if 'short' not in thislang:
                raise ValueError('"short" query description missing from language %s' % lang)
            if 'long' not in thislang:
                raise ValueError('"long" query description missing from language %s' % lang)
        if 'en' not in languages:
            raise ValueError("Query description must include language en'")
        for name in cyphernames:
            if name not in paramdict:
                raise ValueError('Cypher parameter %s missing from JSON parameters' % name)
        for name in paramdict.keys():
            if name not in cyphernames:
                raise ValueError('JSON parameter %s not present in Cypher query' % name)

        for param in self.json_parameter_names():
            pinfo = paramdict[param]
            if 'type' not in pinfo:
                raise ValueError('Parameter %s missing type field' % param)
            ptype = pinfo['type']
            validtypes = ('int', 'float', 'string', 'ipaddr', 'macaddr', 'bool'
            ,   'hostname', 'dnsname', 'enum')
            if ptype not in validtypes:
                raise ValueError('Parameter %s has invalid type %s'% (param, ptype))
            if 'min' in pinfo and ptype != 'int' and ptype != 'float':
                raise ValueError('Min only valid on numeric fields [%s]'% param )
            if 'max' in pinfo and ptype != 'int' and ptype != 'float':
                raise ValueError('Max only valid on numeric fields [%s]'% param )
            if ptype == 'enum':
                if 'enumlist' not in pinfo:
                    raise ValueError('Enum type [%s] requires enumlist'% (param))
                elist = pinfo['enumlist']
                for enum in elist:
                    if not isinstance(enum, str) and not isinstance(enum, unicode):
                        raise ValueError('Enumlist values [%s] must be strings - not %s'
                        %   (enum, type(enum)))
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
                if ptype == 'enum':
                    if 'enumlist' not in thislang:
                        raise ValueError("Parameter %s, language %s must include 'enumlist' info"
                        %       (param, eachlang))
                    enums = thislang['enumlist']
                    for e in elist.keys():  # From code above
                        if e not in enums:
                            raise ValueError("Parameter %s, language %s missing enum value %s"
                            %       (param, eachlang, e))




    def validate_parameters(self, parameters):
        '''
        parameters is a Dict-like object containing parameter names and values
        '''
        # Let's see if all the parameters were supplied
        paramdict = self._JSON_metadata['parameters']
        for param in self.json_parameter_names():
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

    # W0613: unused argument
    # pylint: disable=W0613
    @staticmethod
    def _validate_string(name, paraminfo, value):
        'Validate an string value (always valid)'
        return value

    @staticmethod
    def _validate_macaddr(name, paraminfo, value):
        'Validate an MAC address value'
        mac = pyNetAddr(value)
        if mac is None:
            raise ValueError('value of %s [%s] not a valid MAC address' % (name, value))
        if mac.addrtype() != ADDR_FAMILY_802:
            raise ValueError('Value of %s [%s] not a MAC address' % (name, value))
        return str(mac)

    @staticmethod
    def _validate_ipaddr(name, paraminfo, value):
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
    def _validate_bool(name, paraminfo, value):
        'Validate an Boolean value'
        if not isinstance(value, bool):
            raise ValueError('Value of %s [%s] not a boolean' % (name, value))
        return value

    @staticmethod
    def _validate_hostname(name, paraminfo, value):
        'Validate a hostname value'
        return ClientQuery._validate_dnsname(name, paraminfo, value)

    # W0613: unused argument
    # pylint: disable=W0613
    @staticmethod
    def _validate_dnsname(name, paraminfo, value):
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
        if queryname is None:
            queryname = os.path.basename(pathname)
        #print 'LOADING %s as %s' % (pathname, queryname)
        ret = store.load_or_create(ClientQuery, queryname=queryname, JSON_metadata=json)
        ret.JSON_metadata = json
        ret.bind_store(store)
        return ret

    @staticmethod
    def load_directory(store, directoryname):
        'Returns a generator that returns all the Queries in that directory'
        files = os.listdir(directoryname)
        files.sort()
        for filename in files:
            path = os.path.join(directoryname, filename)
            yield ClientQuery.load_from_file(store, path)

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
                yield ClientQuery.load_from_file(store, path, queryname=queryname)

# message 0212: access to protected member of client class
# pylint: disable=W0212
ClientQuery._validationmethods = {
    'int':      ClientQuery._validate_int,
    'float':    ClientQuery._validate_float,
    'bool':     ClientQuery._validate_bool,
    'string':   ClientQuery._validate_string,
    'enum':     ClientQuery._validate_enum,
    'ipaddr':   ClientQuery._validate_ipaddr,
    'macaddr':  ClientQuery._validate_macaddr,
    'hostname': ClientQuery._validate_hostname,
    'dnsname':  ClientQuery._validate_dnsname,
}

if __name__ == '__main__':
    import sys
    from store import Store
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
                   MATCH ip<-[:ipowner]-()<-[:nicowner]-system
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
    q3 = ClientQuery('ipowners', metadata3)

    neodb = neo4j.GraphDatabaseService()
    neodb.clear()
    print >> sys.stderr, '========>classmap: %s' % (GraphNode.classmap)

    umap  = {'ClientQuery': True}
    ckmap = {'ClientQuery': {'index': 'ClientQuery', 'kattr':'queryname', 'value':'None'}}

    qstore = Store(neodb, uniqueindexmap=umap, classkeymap=ckmap)
    for classname in GraphNode.classmap:
        GraphNode.initclasstypeobj(qstore, classname)

    print "LOADING TREE!"
    queries = ClientQuery.load_tree(qstore, "/home/alanr/monitor/src/queries")
    qlist = [q for q in queries]
    qstore.commit()
    print "%d node TREE LOADED!" % len(qlist)
    qe2 = qstore.load_or_create(ClientQuery, queryname='list')
    qe2.bind_store(qstore)
    testresult = ''
    for s in qe2.execute(None, idsonly=False, expandJSON=True):
        testresult += s
    print testresult
    # Test out a command line query
    for s in qe2.cmdline_exec(None):
        print s

    print "All done!"
