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
File containing the JSONtree class
'''

import re
from AssimCclasses import pyConfigContext, pyNetAddr

# R0903: Too few public methods
# pylint: disable=R0903
class JSONtree(object):
    "Class to convert things to JSON strings - that's about all"
    REESC = re.compile('\\\\')
    REQUOTE = re.compile('"')

    def __init__(self, tree, expandJSON=False, maxJSON=0):
        self.tree = tree
        self.expandJSON = expandJSON
        self.maxJSON = maxJSON

    def __str__(self):
        'Convert our internal tree to JSON.'
        return self._jsonstr(self.tree)

    @staticmethod
    def _jsonesc(stringthing):
        'Escape this string according to JSON string escaping rules'
        stringthing = JSONtree.REESC.sub('\\\\\\\\', stringthing)
        stringthing = JSONtree.REQUOTE.sub('\\\\"', stringthing)
        return stringthing

    # R0911 is too many return statements
    # pylint: disable=R0911
    def _jsonstr(self, thing):
        'Recursively convert ("pickle") this thing to JSON'

        if isinstance(thing, list) or isinstance(thing, tuple):
            ret = ''
            comma = '['
            if len(thing) == 0:
                ret += '['
            for item in thing:
                ret += '%s%s' % (comma, self._jsonstr(item))
                comma = ','
            ret += ']'
            return ret

        if isinstance(thing, dict):
            ret = '{'
            comma = ''
            for key in thing.keys():
                value = thing[key]
                ret += '%s"%s":%s' % (comma, JSONtree._jsonesc(key), self._jsonstr(value))
                comma = ','
            ret += '}'
            return ret

        if isinstance(thing, pyNetAddr):
            return '"%s"' % (str(thing))

        if isinstance(thing, bool):
            if thing:
                return 'true'
            return 'false'

        if isinstance(thing, (int, long, float, pyConfigContext)):
            return str(thing)

        if isinstance(thing, unicode) or isinstance(thing, pyNetAddr):
            return '"%s"' % (JSONtree._jsonesc(str(thing)))

        if isinstance(thing, str):
            return '"%s"' % (JSONtree._jsonesc(thing))

        if thing is None:
            return 'null'

        return self._jsonstr_other(thing)

    def _jsonstr_other(self, thing):
        'Do our best to make JSON out of a "normal" python object - the final "other" case'
        ret = '{'
        comma = ''
        attrs = thing.__dict__.keys()
        attrs.sort()
        for attr in attrs:
            if attr.startswith('_'):
                continue
            value = getattr(thing, attr)
            if self.maxJSON > 0 and attr.startswith('JSON_') and len(value) > self.maxJSON:
                continue
            if self.expandJSON and attr.startswith('JSON_'):
                js = pyConfigContext(value)
                if js is not None:
                    value = js
            ret += '%s"%s":%s' % (comma, attr, self._jsonstr(value))
            comma = ','
        ret += '}'
        return ret
