#!/usr/bin/python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2014 - Assimilation Systems Limited
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
'''
This file implements things related to Configuration files for the CMA.
Not quite sure what all it will do, but hey, this comment is slightly better than nothing.
'''
from AssimCclasses import pyConfigContext
class ConfigFile:
    '''
    This class implements stuff around configuration files, validation and things like that...
    '''
    # A template is a pattern for how to validate a dict-like object
    # like those that come from pyConfigContexts -- which in turn model JSON
    default_template = {
        'OUI':                  {str: str}, # Addendum for locally-known OUI mappings
        'optional_modules':     [str],      # List of optional modules to be included
        'contrib_modules':      [str],      # List of contrib modules to be included
        'port':                 int,        # Our listening port
        'compression_threshold':int,
        'discovery': {
                'repeat':   int,
                'timeout':  int,
                'agents': {
                    str:    str
                },
        },
        'monitoring': { 
                'repeat':   int,    # Default repeat interval in seconds
                'timeout':  int,
                'agents': {         # Configuration information for individual agent types,
                                    # optionally including machine
                            str:    {'repeat': int,
                                     'timeout': int
                        },
                },
        },
        'heartbeats':   {
            'repeat':   int,    # how frequently to heartbeat - in seconds
            'warn':     int,    # How long to wait when issuing a late heartbeat warning
            'dead':     int,    # How long to wait before declaring a system dead
        },
    }
    # This is the default configuration for the Assimilation project CMA
    # It should conform to the default_template above
    default_config = {
        'OUI': {            # Addendum of locally-known OUIs
                'b0-79-3c': 'Revolv, Inc.',
                '18-0c-ac': 'Canon, Inc.',
                'cc-3a-61': 'SAMSUNG ELECTRO MECHANICS CO., LTD.',
                'd8-50-e6': 'ASUSTek COMPUTER INC.',
        },
        'optional_modules':     [  # List of optional modules to be included
                                    'discoverylistener',
                                    'linkdiscovery',
                                    'checksumdiscovery',
                                    'monitoringdiscovery',
                                    'arpdiscovery'
                                ],
        'contrib_modules':      [],  # List of contrib modules to be included
        'port':                     1984,    # Our listening port
        'compression_threshold':    20000,
        'discovery': {
                'repeat':           3600,   # Default repeat interval in seconds
                'timeout':          300,    # Default timeout interval in seconds
                'agents': {
                },
        },
        'monitoring': { 
                'repeat':           120,    # Default repeat interval in seconds
                'timeout':          180,    # Default repeat interval in seconds
                'agents': {         # Configuration information for individual agent types,
                                    # optionally including machine
                                    # "lsb::ssh":               {'repeat': int, 'timeout': int},
                                    # "ocf::Neo4j/servidor":    {'repeat': int, 'timeout': int},
                },
        },
        'heartbeats':   {
            'repeat':   1,    # how frequently to heartbeat - in seconds
            'warn':     5,    # How long to wait when issuing a late heartbeat warning
            'dead':     30,   # How long to wait before declaring a system dead
        },
    }
    def __init__(self, filename=None, template=None, defaults=None):
        'Init function for ConfigFile class, give us a filename!'
        if template is None:
            template = ConfigFile.default_template
        self.template = template
        if defaults is None:
            defaults = ConfigFile.default_config
        self.defaults = defaults
        if filename is None:
            self.config = pyConfigContext()


    @staticmethod
    def _merge_config_elems(defaults, config):
        'Merge data from our defaults into the configuration.'
        for elem in defaults:
            delem = defaults[elem]
            if isinstance(delem, dict):
                if elem not in config:
                    config[elem] = pyConfigContext()
                ConfigFile._merge_config_elems(delem, config[elem])
            elif elem not in config:
                if delem == []:
                    print 'CONFIG:', config
                print 'SETTING elem %s to delem %s' % (elem, delem)
                config[elem] = delem
    
    def complete_config(self):
        '''Create a complete configuration by merging with defaults
        and validating the merged config against our template.'''
        ConfigFile._merge_config_elems(self.defaults, self.config)
        ret = self.isvalid(self.config)
        if ret[0]:
            return self.config
        else:
            raise ValueError(ret[1])


    def isvalid(self, config=None):
        '''Validate the given configuration against our template.
        Return is a Tuple (True/False, 'explanation of errors')'''
        if config is None:
            config = self.default_config
        return ConfigFile._check_validity(self.template, config)

    @staticmethod
    # Too many return statements
    # pylint: disable=R0911
    def _check_validity(template, configobj):
        'Recursively validate a complex dict-like object against a complex template object'

        # If we were given a type as template, then it has to be an instance of that type
        if isinstance(template, type):
            if (not isinstance(configobj, template)):
                return (False, '%s is not a %s' % (configobj, template))
            return (True, '')

        # Were we given a dict as the template?
        if isinstance(template, dict):
            #   Were we just given a "type" template?
            #   If so, then any names are legal, but the values all have to be the "correct" type
            if str in template:
                validatetype = template[str]
                # Any key is fine, but elements have to match the given type
                for configkey in configobj.keys():
                    data = configobj[configkey]
                    if isinstance(validatetype, type):
                        if not isinstance(data, validatetype):
                            return (False, ('%s element is not a %s' % (configkey, validatetype)))
                    else:
                        ret = ConfigFile._check_validity(validatetype, configobj[configkey])
                        if not ret[0]:
                            return (False, 'Element %s: %s' % (configkey, ret[1]))
                return (True, '')
            else:
                # We are validating a dict - make sure all keys are permitted
                try:
                    keys = configobj.keys()
                except AttributeError:
                    return (False, '%s is not dict-like' % (configobj))

                # Otherwise only the template strings are legal keys
                for elemname in keys:
                    if elemname not in template:
                        return (False, ('%s is not a legal element' % (elemname)))
                    ret = ConfigFile._check_validity(template[elemname], configobj[elemname])
                    if not ret[0]:
                        return (False, 'Element %s: %s' % (elemname, ret[1]))
                return (True, '')
        # If the template element is a list or tuple, then the item has to be a
        # list or tuple and every element of the item has to match the given template
        if isinstance(template, (list, tuple)):
            checktype = template[0]
            if not isinstance(configobj, (list, tuple)):
                return (False, ('%s is not a list or tuple' % (configobj)))
            for elem in configobj:
                ret = ConfigFile._check_validity(checktype, elem)
                if not ret[0]:
                    return (False, ('Array element: %s' % ret))
            return (True, '')
        return (False, "Case we didn't allow for: %s vs %s" % (str(configobj), str(template)))

if __name__ == '__main__':
    cf = ConfigFile()
    isvalid = cf.isvalid(ConfigFile.default_config)
    print 'DEFAULT CONFIG valid?:', isvalid
    print cf.complete_config()
