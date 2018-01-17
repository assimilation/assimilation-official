#!/usr/bin/env python
#
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2016 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community
#   - http://assimproj.org
# Paid support is available from Assimilation Systems Limited
#   - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.
# If not, see http://www.gnu.org/licenses/
#

from __future__ import print_function
import json
import re

"""
This file provides a few classes for sloppily parsing various kinds of patch announcements
from various vendors and format them into semi-uniform vulnerability announcements suitable
for telling if you have a particular vulnerability.
"""


class Announcement(object):
    def __init__(self, url):
        self.url = url
        if url.startswith('/'):
            self._text = self._get_file()
        self.data = self._parse_text()

    def _parse_text(self):
        """
        Parses a plain text version of a vulnerability announcement.

        :return: dict: returns dict suitable for converting to JSON
        """
        raise NotImplementedError("Abstract method _parse_text()")

    def _get_file(self):
        """
        Returns the text value from a given file
        :return: str: text from the file as a single string.
        """
        with open(self.url) as f:
            return f.read()

    def __str__(self):
        """
        Convert the parsed announcement to a JSON string - suitable for simple handling.
        :return:
        """
        return json.dumps(announcement.data, indent=4, sort_keys=True)

    @property
    def original(self):
        """

        :return:
        """
        return self._text

class CentOSAnnouncement(Announcement):
    """
    A class which is capable of parsing CentOS vulnerability announcements.
    """
    ST_START = 1
    ST_IN_SECTION = 2
    KNOWN_WORDS = {'x86_64','source', 'note'}
    PATCHES = ('x86_64', 'i386')
    CESA = re.compile('centos errata and security advisory ([^ ]*)  *([A-Za-z]*)',re.IGNORECASE)
    UPSTREAM = re.compile('upstream details.*(https://[^ ]*)', re.IGNORECASE)


    def _parse_text(self):
        sections = {}
        section_name = None
        state = self.ST_START
        for line in self._text.split('\n'):
            if line.endswith(':'):
                word = line[:-1].lower()
                if word not in self.KNOWN_WORDS:
                    print("OOPS! Unrecognized section [%s]" % word)
                section_name = word
                sections[section_name] = []
                state = self.ST_IN_SECTION
            elif state == self.ST_START:
                match = self.CESA.match(line)
                if match:
                    sections['name'] = 'CESA-%s' % match.group(1)
                    sections['importance'] = match.group(2).lower()
                else:
                    match = self.UPSTREAM.match(line)
                    if match:
                        sections['upstream'] = match.group(1)
                        if 'urls' not in sections:
                            sections['urls'] = []
                        sections['urls'].append(match.group(1))

            elif state == self.ST_IN_SECTION:
                if line.startswith('--'):
                    section_name = 'email_signature'
                    sections[section_name] = []
                else:
                    sections[section_name].append(line)
                    if line.startswith('http://') or line.startswith('https://'):
                        if 'urls' not in sections:
                            sections['urls'] = []
                        sections['urls'].append(line)

        sections['patches'] = {}
        for section_name in self.PATCHES:
            if section_name in sections:
                sections['patches'][section_name] = {}
                for index in range(0, len(sections[section_name]), 2):
                    patch = sections[section_name][index+1]
                    if patch != "":
                        sections['patches'][section_name][patch] = sections[section_name][index]
                del sections[section_name]
        if 'source' in sections:
            sections['source'] = {
                sections['source'][1]: sections['source'][0]
            }
        for sect_info in sections.viewvalues():
            if len(sect_info) > 1 and sect_info[-1] == '':
                del sect_info[-1]
        if 'name' not in sections:
            raise ValueError('No vulnerability name in %s.', self.url)
        if len(sections['patches']) == 0:
            raise ValueError('No patches in %s', self.url)
        return sections


announcement = CentOSAnnouncement("/home/alanr/monitor/announce/centos/CESA-2018:0012")
print (announcement)
