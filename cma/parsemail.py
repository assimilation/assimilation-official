#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100 fileencoding=utf-8
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
"""
This file provides a few classes for sloppily parsing various kinds of security announcements
from various vendors and format them into semi-uniform vulnerability announcements suitable
for telling if you have a particular vulnerability.
"""

from __future__ import print_function
from sys import stderr
import os
import re
import json
import gzip

try:
    import io.StringIO as StringIO
except ImportError:
    import StringIO
import requests


class Mbox(object):
    """
    Object to make handle mbox-format messages
    """
    KEYWORD_RE = re.compile('([^:]*): *(.*)')

    def __init__(self, msg_string):
        self._msg_string = msg_string
        self._fileobj = StringIO.StringIO(msg_string)
        self.firstline = None

    def emails(self):
        """
        Yield each email in the mbox in turn...
        :return: (dict, str) - dictionary of keywords, and string with body text
        """
        state = 'init'
        body = ''
        keyword = None
        keywords = {}
        if self.firstline is None:
            line = self._fileobj.readline()
            if line == '':
                return
            line = line.rstrip()
        else:
            line = self.firstline
            # print('GOT FIRSTLINE2', line, file=stderr)
        if line == '':
            return
        while line is not None:
            self.firstline = line
            if state == 'init':
                if line == '':
                    state = 'body'
                    # print('STARTING BODY...', file=stderr)
                elif line.startswith('From '):
                    keywords['fromline'] = line
                elif line.startswith(' ') or line.startswith('\t'):
                    line = line.replace('\t', ' ')
                    keywords[keyword] += line
                else:
                    match = self.KEYWORD_RE.match(line)
                    if match:
                        keyword = match.group(1).lower()
                        keywords[keyword] = match.group(2)
                    else:
                        print('OOPS: Line is [%s]' % line, file=stderr)
            else:
                if line.startswith('From '):
                    state = 'init'
                    self.firstline = line
                    yieldval = (keywords, body)
                    keywords = {}
                    body = ''
                    yield yieldval
                body += line + '\n'
            line = self._fileobj.readline()
            if line == '':
                break
            line = line.rstrip()
            # print('GOT LINE3 [%s] state %s' % (line, state), file=stderr)


def parse_email_mbox_gz(url, cls):
    """
    Parse an email archive in mbox format - gzipped
    :param url: URL of the mbox format
    :param cls: class to instantiate the announcements with
    :return: [Announcement]
    """
    try:
        mbox_text = gzip.GzipFile(fileobj=StringIO.StringIO(requests.get(url).content)).read()
    except IOError as io_error:
        if 'not a gzipped file' in str(io_error).lower():
            return
        raise
    bad_names = cls.KNOWN_BAD_NAMES
    for headers, body in Mbox(mbox_text).emails():
        headers['announce-source'] = gz
        subject = headers['subject'].lower()
        if 'bugfix' in subject or 'errata' in subject or 'security' not in subject:
            # We only care about security fixes...
            continue
        try:
            result = cls(url=url, text=body, metadata=headers)
            # https://lists.centos.org/pipermail/centos-announce/2017-March.txt.gz
            basename = os.path.basename(url).split('.', 1)[0]
            if basename in bad_names and bad_names[basename] == result.data['name']:
                print('Skipping known bad announcement: %s in %s'
                      % (bad_names[basename], basename), file=stderr)
                continue
            yield result
        except ValueError as err:
            if 'in-reply-to' in headers:
                continue
            print('Cannot parse vulnerability: %s in %s [%s]' % (headers['subject'], gz, err),
                  file=stderr)
            # print('EMAIL headers:\n%s' % str(headers), file=stderr)
            # raise
        except NotImplementedError:
            pass  # Unsupported release


class Announcement(object):
    """
    Class defining various kinds of announcements
    """

    HREF_RE = re.compile('(.*)< *a[^>]*>([^<>]+)</ *a *>(.*)', re.IGNORECASE)
    KNOWN_BAD_NAMES = {}

    def __init__(self, url, text=None, metadata=None):
        self.url = url
        self.metadata = metadata
        if text is None:
            if url.startswith('/'):
                self._text = self._get_file()
            elif url.startswith('http://') or url.startswith('https://'):
                self._text = self.scrape_email_from_archives(url)
        else:
            self._text = text
        self.data = self._parse_text()
        if metadata is not None:
            for key in metadata:
                if key in self.data:
                    raise ValueError('Metadata key % overrides discovered key.')
                self.data[key] = metadata[key]

    def _parse_text(self):
        """
        Parses a plain text version of a vulnerability announcement.

        :return: dict: returns dict suitable for converting to JSON
        """
        raise NotImplementedError("Abstract method _parse_text()")

    @staticmethod
    def scrape_email_from_archives(url):
        """
        Scrapes a single plain text email from email archives

        :param url: URL to find an email archive message
        :return: dict: returns dict suitable for converting to JSON
        """
        raise NotImplementedError("Abstract method scrape_email_from_archives()")

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
        :return: str: output string in JSON format.
        """
        return json.dumps(self.data, indent=4, sort_keys=True)

    @staticmethod
    def _strip_anchors(s):
        """
        Strip <a> anchors from strings
        :param s: str: string to strip
        :return: str: string w/o href links (anchors)
        """
        match_result = Announcement.HREF_RE.match(s)
        while match_result:
            s = match_result.group(1) + match_result.group(2) + match_result.group(3)
            match_result = Announcement.HREF_RE.match(s)
        return s

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
    KNOWN_WORDS = {'x86_64', 'i386', 'source', 'note'}
    PATCHES = ('x86_64', 'i386', 'source')
    CESA = re.compile('centos errata and security advisory ([^ ]*) +([A-Za-z]*)', re.IGNORECASE)
    CESA2 = re.compile('centos errata and security advisory ([^ ]*)', re.IGNORECASE)
    UPSTREAM = re.compile('upstream details.*(https://[^ ]*)', re.IGNORECASE)
    NEXTPART = re.compile('----* next part --*$', re.IGNORECASE)
    PKG_PARSE = re.compile('.*\.el([0-9]+)[0-9_.]*.*\.([^.]*)\.rpm$')
    SRCPKG_PARSE = re.compile('.*\.el([0-9_.]*[0-9])\..*src.rpm$')

    SPACES_RE = re.compile('[ ]+')

    BINARY_BASE_URL = 'http://mirror.centos.org/centos/%s/updates/%s/Packages/%s'
    INFO_BASE_URL = 'https://centos.pkgs.org/%s/centos-updates-%s/%s.html'
    SRC_BASE_URL = 'http://vault.centos.org/%s/updates/Source/SPackages/%s'
    # https://centos.pkgs.org/6/centos-i386/microcode_ctl-1.17-25.el6.i686.rpm.html
    # https://centos.pkgs.org/6/centos-updates-i386/microcode_ctl-1.17-25.2.el6_9.i686.rpm.html
    # http://vault.centos.org/6.9/updates/Source/SPackages/microcode_ctl-1.17-25.2.el6_9.src.rpm
    # For CentOS 5 and before, we really can't figure this out...
    # http://vault.centos.org/5.11/updates/SRPMS/thunderbird-38.5.0-1.el5.centos.src.rpm
    # http://vault.centos.org/5.11/updates/i386/RPMS/thunderbird-38.5.0-1.el5.centos.i386.rpm

    KNOWN_BAD_NAMES = {
        '2017-February': 'CESA-2017:0294',
    }

    def compute_binary_url(self, package):
        """
        Translate the package name into the URL of the binary package
        :param package: str: CentOS package name
        :return: str: URL of CentOS package
        """
        match = self.PKG_PARSE.match(package)
        if not match:
            raise ValueError("package [%s] doesn't match [%s]" % (package, self.PKG_PARSE.pattern))
        rel = match.group(1)
        arch = match.group(2)
        if arch == 'i686':
            arch = 'i386'
        intrel = int(rel[0])
        if intrel < 6:
            raise NotImplementedError('We only support CentOS6 and beyond.')
        return self.BINARY_BASE_URL % (rel, arch, package)

    def compute_src_url(self, package):
        """
        Translate the source package name into the URL of the source package
        :param package: str: CentOS source package name
        :return: str: URL of CentOS package
        """
        match = self.SRCPKG_PARSE.match(package)
        if not match:
            raise ValueError("package [%s] doesn't match [%s]"
                             % (package, self.SRCPKG_PARSE.pattern))
        rel = match.group(1)
        rel = rel.replace('_', '.')
        return self.SRC_BASE_URL % (rel, package)

    def compute_info_url(self, package):
        """
        Translate the package name into the URL of the info page for this package
        :param package: str: CentOS package name
        :return: str: URL of CentOS info page
        """
        match = self.PKG_PARSE.match(package)
        if not match:
            raise ValueError("package [%s] doesn't match [%s]" % (package, self.PKG_PARSE.pattern))
        rel = match.group(1)
        arch = match.group(2)
        if arch == 'i686':
            arch = 'i386'
        return self.INFO_BASE_URL % (rel, arch, package)

    @staticmethod
    def scrape_email_from_archives(url):
        """
        Scrape plain text from email archive file
        :param url: str: URL of email archive
        :return: str: contents of plain text archive message
        """

        web_page = requests.get(url).content.split('\n')
        basic_text = []
        state = 'skip'
        for line in web_page:
            if state == 'skip':
                if line.startswith('<PRE>'):
                    state = 'reading'
            elif line.startswith('</PRE>'):
                break
            else:
                line = Announcement._strip_anchors(line)
                basic_text.append(line)
        return '\n'.join(basic_text)

    def _parse_text(self):
        sections = {}
        section_name = None
        for line in self._text.split('\n'):
            if line.endswith(':'):
                word = line[:-1].lower()
                if word not in self.KNOWN_WORDS:
                    if '>' in word or ' ' in word:
                        raise ValueError("Email format error [%s" % word)
                    print("OOPS! Unrecognized section [%s:]" % word, file=stderr)
                section_name = word
                if section_name not in sections:
                    sections[section_name] = []
            else:
                if self.NEXTPART.match(line):
                    break
                match = self.CESA.match(line)
                if match:
                    sections['name'] = 'CESA-%s' % match.group(1)
                    sections['importance'] = match.group(2).lower()
                    continue
                match = self.CESA2.match(line)
                if match:
                    sections['name'] = 'CESA-%s' % match.group(1)
                    sections['importance'] = 'unknown'
                    continue
                match = self.UPSTREAM.match(line)
                if match:
                    sections['upstream'] = match.group(1)
                    if 'urls' not in sections:
                        sections['urls'] = []
                    sections['urls'].append(match.group(1))
                    continue
                if line.startswith('--'):
                    section_name = 'email-signature'
                    sections[section_name] = []
                    continue
                if section_name is not None:
                    sections[section_name].append(line)
                    if line.startswith('http://') or line.startswith('https://'):
                        if 'urls' not in sections:
                            sections['urls'] = []
                        sections['urls'].append(line)

        sections['patches'] = {}
        for section_name in self.PATCHES:
            if section_name in sections:
                this_sect = ' '.join(sections[section_name])
                this_sect = self.SPACES_RE.split(this_sect)
                for index in range(0, len(this_sect), 2):
                    if this_sect[index] == '':
                        break
                    patch = this_sect[index+1]
                    if patch != "":
                        if section_name == 'source':
                            sections['patches'][patch] = {'sha256': this_sect[index],
                                                          'package': self.compute_src_url(patch)
                                                          }
                        else:
                            sections['patches'][patch] = {'sha256': this_sect[index],
                                                          'package': self.compute_binary_url(patch),
                                                          'info': self.compute_info_url(patch),
                                                          }
                del sections[section_name]
        for sect_name, sect_info in sections.viewitems():
            # print ('SECT_INFO:', len(sect_info), type(sect_info), sect_info, file=stderr)
            if isinstance(sect_info, list) and sect_name != 'urls':
                if sect_info[-1] == '':
                    del sect_info[-1]
                sections[sect_name] = '\n'.join(sections[sect_name])

        if 'name' not in sections:
            raise ValueError('No vulnerability name in %s.' % self.url)
        if len(sections['patches']) == 0:
            raise ValueError('No patches in %s', self.url)
        return sections


for year in ('2016', '2017', '2018'):
    for month in ('January', 'February', 'March', 'April', 'May', 'June', 'July'
                  'August', 'September', 'October', 'November', 'December'):
        gz = 'https://lists.centos.org/pipermail/centos-announce/%s-%s.txt.gz' % (year, month)
        for vulnerability in parse_email_mbox_gz(gz, CentOSAnnouncement):
            print(vulnerability)
