#!/usr/bin/python
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
from py2neo import neo4j
from graphnodes import GraphNode
from AssimCclasses import pyConfigContext, pyNetAddr
from AssimCtypes import ADDR_FAMILY_IPV6, ADDR_FAMILY_IPV4, ADDR_FAMILY_802

class ClientQuery(GraphNode):
    '''This class defines queries which can be requested from clients (typically JavaScript)
    The output of all queries is JSON - as filtered by our security mechanism
    '''
    def __init__(self, queryname, JSON_metadata):
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
            enum    - an finite enumeration of permissible values (case-insensitive)
        '''

        GraphNode.__init__()
        self.queryname = queryname
        self.database = None
        self.JSON_metadata = JSON_metadata
        self._JSON_metadata = pyConfigContext(JSON_metadata)
        if self._JSON_metadata is None:
            raise ValueError('Parameter JSON_metadata is invalid [%s]' % JSON_metadata)
        self._db = None
        self._query = None
        self.validate_json()

    @staticmethod
    def __meta_keyattrs__():
        'Return our key attributes in order of decreasing significance'
        return ['queryname']

    def bind_database(self, db):
        'Connect our query to a database'
        if self._db is not db:
            self._db = db
            self._query = neo4j.CypherQuery(db, self._JSON_metadata['cypher'])




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

    _validationmethods = {
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

    @staticmethod
    def _validate_value(name, paraminfo, value):
        '''Validate the value given our metadata'''
        valtype = paraminfo['type']
        return ClientQuery._validationmethods[valtype](name, paraminfo, value)


if __name__ == '__main__':
    metadata1 = \
    '''
    {   "cypher": "BEGIN n=node:ClientQuery('*:*') RETURN n",
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
    {   "cypher":   "BEGIN n=node:ClientQuery('{queryname}:metadata') RETURN n",
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
        "cypher": "BEGIN ip=node:IPaddr('{ipaddr}:*')
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

    print "All done!"
