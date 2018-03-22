#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
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
"""
This file implements things related to Configuration files for the CMA.
Not quite sure what all it will do, but hey, this comment is slightly better than nothing.
"""
from __future__ import print_function, absolute_import
# from sys import stderr
from types import ClassType
from AssimCclasses import pyConfigContext, pyNetAddr, pySignFrame, pyCompressFrame
from consts import CMAconsts


class ConfigFile(object):
    """
    This class implements configuration file management, including validation
    and default values for parameters.
    """
    callbacks = []
    # A template is a pattern for how to validate a dict-like object
    # like those that come from pyConfigContexts -- which in turn model JSON
    default_template = {
        'OUI': {str: str},  # Addendum for locally-known OUI mappings
        'optional_modules': [  # List of optional modules to be included
            # Below is the list of all known optional modules
            {'linkdiscovery',  # listens for CMA/LLDP packets
             'checksumdiscovery',  # Checksums network-facing files
             'monitoringdiscovery',  # Automatically monitors services
             'arpdiscovery',  # Listens for ARP packets for
             # network mapping...
             'procsysdiscovery',  # Discovers content of /proc/sys
             }
        ],
        'contrib_modules': [str],  # List of contrib modules to be included
        # We have no idea what contrib modules there might be
        'initial_discovery':  # Below is the list of known discovery agents...
            {'auditd_conf',  # /etc/audit/auditd.conf config
             'commands',  # Discovers installed commands
             'cpu',  # CPU details
             'docker',  # Docker host & container configuration
             'vagrant',  # Vagrant host & VM configuration
             'login_defs',  # /etc/login.defs configuration
             'pam',  # PAM configuration
             'findmnt',  # Discovers mounted filesystems (Linux)
             'packages',  # Discovers installed packages
             'monitoringagents',  # Discovers monitoring agents
             'nsswitch',  # Discovers nsswitch configuration (GNU)
             'os',  # Discovers OS version information
             'sshd',  # Discovers sshd configuration
             'sudoers',  # Discovers /etc/sudoers configuration
             'tcpdiscovery',  # Discovers network-facing processes
             'ulimit',  # Discovers ulimit settings
             },
        'cmaport': {int, long},  # CMA listening port
        'cmainit': pyNetAddr,  # Initial contact address for the CMA
        'cmaaddr': pyNetAddr,  # CMA's base address...
        'cmadisc': pyNetAddr,  # Address to send discovery information
        'cmafail': pyNetAddr,  # Address to send failure reports
        'outsig': pySignFrame,  # Packet signature frame
        'compress': pyCompressFrame,  # Packet compression frame
        'compression_method': {'zlib'},  # Packet compression method
        'compression_threshold': {int, long},  # Threshold for when to start compressing
        'score_severity_map': {str: {'high': float, 'medium': float, 'low': float}},
        'discovery': {
            'repeat': {int, long},  # how often to repeat a discovery action
            'warn': {int, long},  # How long to wait when issuing a slow discovery warning
            'timeout': {int, long},  # how long wait before declaring failure
            'nice': {int, long},  # Optional UNIX-style 'nice' value
            'agents': {  # Configuration information for individual agent types,
                # optionally including machine
                str: {
                    'repeat': {int, long},  # repeat for this particular agent
                    'warn': {int, long},  # How long before slow discovery warning
                    'timeout': {int, long},  # timeout for this particular agent
                    'nice': {int, long},  # UNIX-style nice value
                },
            },
        },
        'monitoring': {
            'repeat': {int, long},  # Default repeat interval in seconds
            'warn': {int, long},  # How long to wait when issuing a slow monitoring warning
            'timeout': {int, long},  # How long to wait before declaring failure
            'nice': {int, long},  # Optional UNIX-style 'nice' value
            'agents': {  # Configuration information for individual agent types,
                # optionally including machine
                str: {
                    'repeat': {int, long},  # repeat for this particular agent
                    'warn': {int, long},  # How long before slow warning
                    'timeout': {int, long},  # timeout for this particular agent
                    'nice': {int, long},  # UNIX-style nice value
                    'argv': [str],
                    'env': {str: str},
                },
            },
            'nagiospath': [str],
        },
        'heartbeats': {
            'repeat': {int, long},  # how frequently to heartbeat - in seconds
            'warn': {int, long},  # How long to wait when issuing a late heartbeat warning
            'timeout': {int, long},  # How long to wait before declaring a system dead
        },
        'bprulesbydomain': {str: str},  # Which best practice rule sets to use by default?
        'allbpdiscoverytypes': [str],  # List of all best practice discovery types
        'checksum_cmds': [str],  # Ordered List of checksum commands to use
        'checksum_files': [str],  # Files to always perform the checksum of
        'permission_files': [str],  # Files to always check the permissions of
        'sysfile_fileattrs': [str],  # Standard/common system files perms to discover
        'libmodules_fileattrs': [str],  # Standard/common library directories perms to discover
        'lib_fileattrs': [str],  # Standard/common library perms to discover
        'lib64_fileattrs': [str],  # Standard/common library perms to discover
        'libgnu_fileattrs': [str],  # Standard/common library perms to discover
        'libgnu64_fileattrs': [str],  # Standard/common library perms to discover
        'usrlib_fileattrs': [str],  # Standard/common library perms to discover
        'usrlib64_fileattrs': [str],  # Standard/common library perms to discover
        'usrlibgnu_fileattrs': [str],  # Standard/common library perms to discover
        'usrlibgnu64_fileattrs': [str],  # Standard/common library perms to discover
        'bin_fileattrs': [str],  # Standard/common command directories perms to discover
        'sbin_fileattrs': [str],  # Standard/common command directories perms to discover
        'usr_bin_fileattrs': [str],  # Standard/common command directories perms to discover
        'usr_local_fileattrs': [str],  # Standard/common command directories perms to discover
        'usr_sbin_fileattrs': [str],  # Standard/common command directories perms to discover
        'perm_discovery_lists': [str],  # List of all the collections of perms to discover
        'containers': {
            'docker': {
            },
            'vagrant': {
            },
        }
    }

    @staticmethod
    def register_callback(function, **args):
        'Register a callback to let someone know when we create or modify this configuration'
        ConfigFile.callbacks.append((function, args))

    # This is the default configuration for the Assimilation project CMA
    # It should/must conform to the default_template above
    @staticmethod
    def default_defaults():
        """This is our default - for defaults
        Sounds kinda weird, but it makes sense - and is handy for our tests to not have to
        have the current defaults updated all the time...
        """
        retval = {
            'OUI': {
                # Addendum of locally-known OUIs - feel free to contribute ones you find...
                # Python includes lots of them, but is missing newer ones.
                # Note that they have to be in lower case with '-' separators.
                # You can find the latest data here:
                #      http://standards.ieee.org/cgi-bin/ouisearch
                '18-0c-ac': 'Canon, Inc.',
                '28-d2-44': 'LCFC(HeFei) Electronics Technology Co., Ltd.',
                '56-84-7a': '(linux bridge)',
                '64-bc-0c': 'LG Electronics',
                '84-7a-88': 'HTC Corporation',
                'a8-66-7f': 'Apple, Inc.',
                'b0-79-3c': 'Revolv, Inc.',
                'b8-ee-65': 'Liteon Technology Corporation',
                'bc-ee-7b': 'ASUSTek Computer, Inc.',
                'c8-b5-b7': 'Apple, Inc.',
                'cc-3a-61': 'SAMSUNG ELECTRO MECHANICS CO., LTD.',
                'd8-50-e6': 'ASUSTek COMPUTER INC.',
                'd8-cb-8a': 'Micro-Star INTL CO., LTD.',
                'e8-ab-fa': 'Shenzhen Reecam Tech.Ltd.',
            },
            #
            #   Below is the set of modules that we import before starting up
            #   Each of them triggers different kinds of conditional discovery
            #   as per its design...
            'optional_modules': [  # List of optional modules to be included
                'linkdiscovery',  # Perform CDP/LLDP monitoring
                'checksumdiscovery',  # Perform tripwire-like checksum monitoring
                'monitoringdiscovery',  # Initiates monitoring based on service
                # discovery
                'arpdiscovery',  # Listen for ARP packets: IPs and MACs
                'procsysdiscovery',  # Discovers content of /proc/sys
            ],
            'contrib_modules': [],  # List of contrib modules to be imported
            #
            #   Always start these discovery plugins below when a Drone comes online
            #
            'initial_discovery': ['os',  # OS properties
                                  'cpu',  # CPU properties
                                  'packages',  # What packages are installed?
                                  'commands',  # Discovers installed commands
                                  'monitoringagents',  # What monitoring agents are installed?
                                  'login_defs',  # /etc/login.defs configuration
                                  'auditd_conf',  # /etc/audit/auditd.conf config
                                  'pam',  # PAM configuration
                                  'sudoers',  # Discovers /etc/sudoers configuration
                                  'ulimit',  # What are current ulimit values?
                                  'nsswitch',  # Discovers nsswitch configuration (Linux)
                                  'findmnt',  # Discovers mounted filesystems (Linux)
                                  'sshd',  # Discovers sshd configuration
                                  'docker',  # Docker host & container configuration
                                  'vagrant',  # Vagrant host & VM configuration
                                  'tcpdiscovery'  # Discover services
                                  ],
            'cmaport': 1984,  # Our listening port
            'cmainit': pyNetAddr("0.0.0.0:1984"),  # Our listening address
            'compression_threshold': 20000,  # Compress packets >= 20 kbytes
            'compression_method': "zlib",  # Compression method
            'score_severity_map': {'security': {'high': 3.0, 'medium': 2.0, 'low': 1.0},
                                   'networking': {'high': 3.0, 'medium': 2.0, 'low': 1.0},
                                   },
            'discovery': {
                'repeat': 60,  # Default repeat interval in seconds
                'warn': 120,  # Default slow discovery warning time
                'timeout': 300,  # Default timeout interval in seconds
                'agents': {  # Configuration information for individual agent types,
                    # optionally including machine
                    "checksums": {'repeat': 3600 * 8, 'timeout': 10 * 60,
                                  'warn': 5 * 60},
                    "os": {'repeat': 0, 'timeout': 60, 'warn': 5},
                    "cpu": {'repeat': 0, 'timeout': 60, 'warn': 5}
                },
            },
            'monitoring': {
                'repeat': 15,  # Default repeat interval in seconds
                'warn': 60,  # Default slow monitoring warning time
                'timeout': 180,  # Default repeat interval in seconds
                'agents': {  # Configuration information for individual agent types,
                    # optionally including machine
                    # "lsb::ssh":               {'repeat': int, 'timeout': int},
                    # "ocf::Neo4j/servidor":    {'repeat': int, 'timeout': int},
                    #
                    "nagios::check_load": {'repeat': 60, 'timeout': 30,
                                           #
                                           # I would really rather have a pure run queue length
                                           # but there's no agent for that. Sigh...
                                           #
                                           # -r == scale load average by by number of CPUs
                                           # -w == floating point warning load averages
                                           #       (1,5,15 minute values)
                                           # -c == floating point critical load averages
                                           #       (1,5,15 minute values)
                                           #
                                           'argv': ['-r', '-w', '4,3,2', '-c', '4,3,2']},
                },
                'nagiospath': ["/usr/lib/nagios/plugins",  # places to look for Nagios agents
                               "/usr/local/nagios/libexec",
                               "/usr/nagios/libexec",
                               "/opt/nrpe/libexec"
                               ],
            },
            'heartbeats': {
                'repeat': 1,  # how frequently to heartbeat - in seconds
                'warn': 5,  # How long to wait when issuing a late heartbeat warning
                'timeout': 30,  # How long to wait before declaring a system dead
            },
            'bprulesbydomain': {  # Default best practice rule sets by domain
                # Default the global domain to the base rule set
                CMAconsts.globaldomain: CMAconsts.BASERULESETNAME,
                # If you want different defaults for the global domain or
                # for any other domain, put them in your local config file.
                # I suspect these default rules will turn out to be a bit
                # harsh for many sites.
            },
            # List of all the known best practice discovery types
            'allbpdiscoverytypes': ['auditd_conf', 'auditd_fileattrs', 'fileattrs',
                                    'login_defs', 'pam', 'proc_sys', 'sshd'],
            # Prioritized list of checksum commands to use
            # we use the first one that's installed.
            'checksum_cmds': [
                '/usr/bin/sha256sum',
                '/usr/bin/sha224sum',
                '/usr/bin/sha384sum',
                '/usr/bin/sha512sum',
                '/usr/bin/sha1sum',
                '/usr/bin/md5sum',
                '/usr/bin/cksum',
                '/usr/bin/crc32'],
            # Files we *always* checksum
            'checksum_files': [
                '/bin/sh',
                '/bin/bash',
                '/bin/login',
                '/usr/bin/passwd',
            ],
            # Files/directories to always get the permissions of
            # Directories ending in / also have their contained files checked.
            'sysfile_fileattrs': [
                '/',
                '/etc/audit/',
                '/etc/bash.bashrc',
                '/etc/bashrc',
                '/etc/bash_completion',
                '/etc/bash_completion.d/',
                '/etc/default/grub',
                '/etc/group',
                '/etc/grub.conf',
                '/etc/grub.d/',
                '/etc/gshadow',
                '/etc/init.d/',
                '/etc/login.defs',
                '/etc/passwd',
                '/etc/profile',
                '/etc/profile.d/',
                '/etc/csh.cshrc',
                '/etc/selinux/',
                '/etc/shadow',
                '/usr/',
                '/usr/local/',
                '/var/',
            ],
            # A collection of directories to gather the permissions of
            # Note that all these discovery names are in 'perm_discovery_lists' below
            # That's what triggers them to be discovered.
            # They are all broken up into several lists because the output is verbose
            # Both UDP and Neo4j hate large discovery blobs
            'libmodules_fileattrs': ['/lib/modules/'],
            'lib_fileattrs': ['/lib/', '/lib/i386-linux-gnu/'],
            'lib64_fileattrs': ['/lib64', '/lib/x86_64-linux-gnu/'],
            'usrlib_fileattrs': ['/usr/lib/', '/usr/lib/i386-linux-gnu/'],
            'usrlib64_fileattrs': ['/usr/lib64/', '/usr/lib/x86_64-linux-gnu/'],
            'bin_fileattrs': ['/bin/', '/sbin/'],
            'usr_bin_fileattrs': ['/usr/bin/', '/usr/sbin/'],
            'usr_local_fileattrs': ['/usr/local/bin/', '/usr/local/sbin/', '/usr/local/lib/'],
            'perm_discovery_lists': [
                'bin_fileattrs',
                'lib64_fileattrs',
                'libmodules_fileattrs',
                'lib_fileattrs',
                'sysfile_fileattrs',
                'usrlib64_fileattrs',
                'usrlib_fileattrs',
                'usr_bin_fileattrs',
                'usr_local_fileattrs',
            ],
            'containers': {
                'docker': {
                    'initial_discovery': [
                        'os',  # OS properties
                        'packages',  # What packages are installed?
                        'commands',  # Discovers installed commands
                        'ulimit',  # What are current ulimit values?
                    ],
                },
                'vagrant': {
                    'initial_discovery': [
                        'os',  # CPU properties
                        'netconfig',  # Network configuration
                        'packages',  # What packages are installed?
                        'commands',  # Discovers installed commands
                        'ulimit',  # What are current ulimit values?
                        'tcpdiscovery'  # Discover services
                    ],
                },
            }
        }  # End of return value
        retval['allbpdiscoverytypes'].extend(retval['perm_discovery_lists'])
        return retval

    def __init__(self, filename=None, template=None, defaults=None):
        """Init function for ConfigFile class, give us a filename - or None!"""
        if template is None:
            template = ConfigFile.default_template
        self.template = template
        if defaults is None:
            defaults = ConfigFile.default_defaults()
        self.defaults = defaults
        if filename is None:
            self.config = pyConfigContext(self.defaults)
        else:
            self.config = pyConfigContext(filename=filename)
        # Call any registered callbacks
        for callbacktuple in ConfigFile.callbacks:
            function, args = callbacktuple
            function(self, None, args)

    def __contains__(self, name):
        """We're basically a dict lookalike - implement __contains__"""
        return name in self.config

    def get(self, name, default=None):
        """We're basically a dict lookalike - implement get()"""
        return self.config[name] if name in self.config else default

    def __getitem__(self, name):
        """We're basically a dict lookalike - implement __getitem__"""
        return self.config[name]

    def __delitem__(self, name):
        """We're basically a dict lookalike - implement __delitem__"""
        del self.config[name]

    def __len__(self):
        """We're basically a dict lookalike - implement __len__"""
        return len(self.config)

    def __setitem__(self, name, value):
        """We're basically a dict lookalike - implement __setitem__"""
        self.config[name] = value
        valid = self.isvalid()
        if not valid[0]:
            raise ValueError(valid[1])
        for callbacktuple in ConfigFile.callbacks:
            callback, args = callbacktuple
            callback(self, name, args)

    @staticmethod
    def _merge_config_elems(defaults, config):
        """
        Any element which is not included in the specified configuration is pulled
        from the default value for that element.
        NOTE that if you override a name which has an array for a value, you are
        eliminating all the array values.  The arrays are NOT somehow merged.
        """
        for elem in defaults:
            delem = defaults[elem]
            if isinstance(delem, (dict, pyConfigContext)):
                if elem not in config:
                    config[elem] = pyConfigContext()
                ConfigFile._merge_config_elems(delem, config[elem])
            elif elem not in config:
                # print('SETTING elem %s to delem %s' % (elem, delem), file=stderr)
                config[elem] = delem

    def complete_config(self):
        """Create a complete configuration by merging with defaults
        and validating the merged config against our template."""
        ConfigFile._merge_config_elems(self.defaults, self.config)
        ret = self.isvalid(self.config)
        if ret[0]:
            return self.config
        else:
            raise ValueError(ret[1])

    def isvalid(self, config=None):
        """Validate the given configuration against our template.
        Return is a Tuple (True/False, 'explanation of errors')"""
        if config is None:
            config = self.default_defaults()
        return ConfigFile._check_validity(self.template, config)

    @staticmethod
    def _check_validity(template, configobj):
        """Recursively validate a complex dict-like object against a complex template object
        This is an interesting, but somewhat complex operation.

        Return value is a Tuple (True/False, 'explanation of errors')
        """

        if isinstance(template, (type, ClassType)):
            return ConfigFile._check_validity_type(template, configobj)
        if isinstance(template, dict):
            return ConfigFile._check_validity_dict(template, configobj)
        if isinstance(template, (list, tuple)):
            return ConfigFile._check_validity_list(template, configobj)
        if isinstance(template, set):
            return ConfigFile._check_validity_set(template, configobj)

        return (False, "Case we didn't allow for: %s vs %s" % (str(template), str(configobj)))

    @staticmethod
    def _check_validity_type(template, configobj):
        'Make sure the configobj is of the given type'
        if (not isinstance(configobj, template)):
            return (False, '%s is not of %s' % (configobj, template))
        return (True, '')

    @staticmethod
    def _check_validity_set(template, configobj):
        'Make sure the configobj is of a string matching something in the set'
        if isinstance(configobj, list):
            # Or maybe a list of things all of which have to be in the set...
            for elem in configobj:
                ret = ConfigFile._check_validity_set(template, elem)
                if not ret[0]:
                    return (False, 'Element %s: %s' % (elem, ret[1]))
            return (True, '')

        # Pylint doesn't like our type matching - so I hid it from pylint through 'configtype'
        configtype = type(configobj)
        if configobj not in template and configtype not in template:
            return (False, '%s is not in %s' % (configobj, template))
        return (True, '')

    @staticmethod
    def _check_validity_dict(template, configobj):
        'Check a configobj for validity against a "dict" template'
        try:
            keys = configobj.keys()
        except AttributeError:
            return (False, '%s is not a dict' % (configobj))
        # Were we just given "str" as a key value?
        #   If so, then any names are legal, but the values all have to be the "correct" type
        if str in template:
            validatetype = template[str]
            # Any key is fine, but elements have to match the given type
            for configkey in keys:
                ret = ConfigFile._check_validity(validatetype, configobj[configkey])
                if not ret[0]:
                    return (False, 'Element %s: %s' % (configkey, ret[1]))
        else:
            # Every key in the configobj must also be in the template
            for elemname in keys:
                if elemname not in template:
                    return (False, ('%s is not one of %s' % (elemname, str(template.keys()))))
                ret = ConfigFile._check_validity(template[elemname], configobj[elemname])
                if not ret[0]:
                    return (False, 'Element %s: %s' % (elemname, ret[1]))
        return (True, '')

    @staticmethod
    def _check_validity_list(template, configobj):
        'Check a configobj for validity against a list/tuple template'
        # When the template element is a list or tuple, then the item has to be a
        # list or tuple and every element of the item has to match the given template
        # Note that all lists (currently) have to be of the same type...
        if not isinstance(configobj, (list, tuple)):
            return (False, ('%s is not a list or tuple' % (configobj)))
        checktype = template[0]
        if isinstance(checktype, set):
            for elem in configobj:
                if elem not in checktype:
                    return (False, ('%s is not in %s' % (elem, checktype)))
        else:
            for elem in configobj:
                ret = ConfigFile._check_validity(checktype, elem)
                if not ret[0]:
                    return (False, ('Array element: %s' % ret[1]))
        return (True, '')

    @staticmethod
    def agent_params(config, agenttype, agentname, dronedesignation):
        """We return the agent parameters for the given type, agent name and drone
        The most specific values take priority over the less specific values
        creating a 3-level value inheritance scheme.
        - Top level is for all agents.
        - Second level is for specific agents.
        - Third level is for specific agents on specific machines.
        agenttype should be one of 'monitoring' or 'discovery'
        agentname for discovery:
            name of discovery agent
        agentname for monitoring:
            monitoring-class::provider:monitortype for OCF
            monitoring-class::monitortype for non-OCF

        We implement this.
        """
        compoundname = '%s/%s' % (agentname, dronedesignation)
        subconfig = config[agenttype]
        result = pyConfigContext('{"type": "%s", "parameters":{}}' % agentname)
        if compoundname in subconfig:
            result['parameters'] = subconfig[compoundname]
        if 'agents' in subconfig and agentname in subconfig['agents']:
            agentlist = subconfig['agents']
            for tag in agentlist[agentname]:
                if tag not in result:
                    subval = agentlist[agentname][tag]
                    result['parameters'][tag] = agentlist[agentname][tag]
        for tag in subconfig:
            if tag not in result:
                subval = subconfig[tag]
                if not hasattr(subval, 'keys'):
                    result['parameters'][tag] = subconfig[tag]
        return result


# Simplify setting up initial discovery validation for our container types
for container in ConfigFile.default_template['containers']:
    ConfigFile.default_template['containers'][container]['initial_discovery'] \
        = ConfigFile.default_template['initial_discovery']
ConfigFile.default_template['containers']['vagrant']['initial_discovery'].add('netconfig')

if __name__ == '__main__':
    # pylint: disable=C0411,C0413
    import subprocess

    cf = ConfigFile()
    assert cf.isvalid()
    # Make sure it's making correct JSON...
    pyConfigContext(str(cf.complete_config()))
    # print ('Complete config:', cf.complete_config(), file=stderr)  # also checks for validity
    lint = subprocess.Popen(('jsonlint', '-f'), stdin=subprocess.PIPE)
    print('%s\n' % cf.complete_config(), file=lint.stdin)
    lint.stdin.close()
    assert lint.wait() == 0
