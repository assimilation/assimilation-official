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
import time
import json
import gzip

try:
    import io.StringIO as StringIO
except ImportError:
    import StringIO
from version_utils import rpm
import requests


# pylint: disable=R0903
class Mbox(object):
    """
    Object to make handle mbox-format messages
    """

    KEYWORD_RE = re.compile(r"([^:]*): *(.*)")

    def __init__(self, msg_string):
        self._msg_string = msg_string
        self._fileobj = StringIO.StringIO(msg_string)
        self.firstline = None

    # pylint: disable=R0912
    def emails(self):
        """
        Yield each email in the mbox in turn...
        :return: (dict, str) - dictionary of keywords, and string with body text
        """
        state = "init"
        body = ""
        keyword = None
        keywords = {}
        if self.firstline is None:
            line = self._fileobj.readline()
            if line == "":
                return
            line = line.rstrip()
        else:
            line = self.firstline
            # print('GOT FIRSTLINE2', line, file=stderr)
        if line == "":
            return
        while line is not None:
            self.firstline = line
            if state == "init":
                if line == "":
                    state = "body"
                    # print('STARTING BODY...', file=stderr)
                elif line.startswith("From "):
                    keywords["fromline"] = line
                elif line.startswith(" ") or line.startswith("\t"):
                    line = line.replace("\t", " ")
                    keywords[keyword] += line
                else:
                    match = self.KEYWORD_RE.match(line)
                    if match:
                        keyword = match.group(1).lower()
                        keywords[keyword] = match.group(2)
                    else:
                        print("OOPS: Line is [%s]" % line, file=stderr)
            else:
                if line.startswith("From "):
                    state = "init"
                    self.firstline = line
                    yieldval = (keywords, body)
                    keywords = {}
                    body = ""
                    yield yieldval
                body += line + "\n"
            line = self._fileobj.readline()
            if line == "":
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
        if "not a gzipped file" in str(io_error).lower():
            return
        raise

    bad_names = cls.KNOWN_BAD_NAMES
    for headers, body in Mbox(mbox_text).emails():
        headers["announcement-source"] = url
        subject = headers["subject"].lower()
        if (
            "bugfix" in subject
            or "errata" in subject
            or ("security" not in subject and "usn" not in subject)
        ):
            # We only care about security fixes...
            print("Skipping %s" % subject)
            continue
        try:
            result = cls(url=url, text=body, metadata=headers)
            # https://lists.centos.org/pipermail/centos-announce/2017-March.txt.gz
            basename = os.path.basename(url).split(".", 1)[0]
            if basename in bad_names and bad_names[basename] == result.data["name"]:
                print(
                    "Skipping known bad announcement: %s in %s: %s"
                    % (bad_names[basename], basename, subject),
                    file=stderr,
                )
                continue
            yield result
        except ValueError as err:
            if "in-reply-to" in headers:
                continue
            print(
                "Cannot parse vulnerability: %s in %s [%s]" % (headers["subject"], url, err),
                file=stderr,
            )
            # print('EMAIL headers:\n%s' % str(headers), file=stderr)
            # raise
        except NotImplementedError:
            pass  # Unsupported release


class Announcement(object):
    """
    Class defining various kinds of announcements
    """

    HREF_RE = re.compile("(.*)< *a[^>]*>([^<>]+)</ *a *>(.*)", re.IGNORECASE)
    BASE_PACKAGE_RE = re.compile("[A-Za-z_0-9]+(-[A-Za-z_+]+)*")
    SPACES_RE = re.compile("[ ]+")
    NEXTPART = re.compile("----* next part --*$", re.IGNORECASE)
    KNOWN_BAD_NAMES = {}
    MBOX_ANNOUNCEMENT_URL_FMT = None

    def __init__(self, url, text=None, metadata=None):
        self.url = url
        self.metadata = metadata
        if text is None:
            if url.startswith("/"):
                self._text = self._get_file()
            elif url.startswith("http://") or url.startswith("https://"):
                self._text = self.scrape_email_from_archives(url)
        else:
            self._text = text
        self.data = self._parse_text()
        if metadata is not None:
            for key in metadata:
                if key in self.data:
                    raise ValueError("Metadata key % overrides discovered key.")
                self.data[key] = metadata[key]
        if "date" in self.data:
            # Make sorting by date easier later...
            self.data["epoch_time"] = int(
                time.mktime(time.strptime(self.data["date"][:-6], "%a, %d %b %Y %H:%M:%S"))
            )

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

    @staticmethod
    def check_a_single_url(url):
        """
        Return True if this URL is good
        :param: url: str: URL to check
        :return: bool: True if we got success on the head operation
        """
        try:
            head = requests.head(url)
            # print("%d: %s" % (head.status_code, url))
            return head.status_code in (200, 301)
        except requests.exceptions.ConnectionError:
            return False

    @staticmethod
    def rpm_version_info(version_or_package_filename):
        """
        Return the RPM version info from the given version or package name
        :param version_or_package_filename:
        :return: Package object - whatever rpm.package returns...
        """
        return rpm.package(
            version_or_package_filename[:-4]
            if version_or_package_filename.endswith(".rpm")
            else version_or_package_filename
        )

    @staticmethod
    def scrape_email_from_archives(url):
        """
        Scrape plain text from email archive file
        :param url: str: URL of email archive
        :return: str: contents of plain text archive message
        """
        headers = {"accept-encoding": "gzip"}
        web_page = requests.get(url, headers=headers).content.split("\n")
        basic_text = []
        state = "skip"
        for line in web_page:
            if state == "skip":
                if line.startswith("<PRE>"):
                    state = "reading"
            elif line.startswith("</PRE>"):
                break
            else:
                line = Announcement._strip_anchors(line)
                basic_text.append(line)
        return "\n".join(basic_text)


class CentOSAnnouncement(Announcement):
    """
    A class which is capable of parsing CentOS vulnerability announcements.
    """

    ST_START = 1
    ST_IN_SECTION = 2
    KNOWN_WORDS = {"x86_64", "i386", "source", "note"}
    PATCHES = ("x86_64", "i386", "source")
    CESA = re.compile("centos errata and security advisory ([^ ]*) +([A-Za-z]*)", re.IGNORECASE)
    CESA2 = re.compile("centos errata and security advisory ([^ ]*)", re.IGNORECASE)
    UPSTREAM = re.compile("upstream details.*(https://[^ ]*)", re.IGNORECASE)
    PKG_PARSE = re.compile(r".*\.el([0-9]+[0-9_.]*).*\.([^.]*)\.rpm$")
    SRCPKG_PARSE = re.compile(r".*\.el([0-9_.]*[0-9])\..*src.rpm$")
    VERSION_RE = re.compile(r"-?([0-9][-_0-9.A-Za-z]*)\.el[0-9]")

    BINARY_BASE_URL = "http://mirror.centos.org/centos/%s/updates/%s/Packages/%s"
    INFO_BASE_URL = "https://centos.pkgs.org/%s/centos-updates-x86_64/%s.html"
    SRC_BASE_URL = "http://vault.centos.org/centos/%s/updates/Source/SPackages/%s"
    MBOX_ANNOUNCEMENT_URL_FMT = "https://lists.centos.org/pipermail/centos-announce/%s-%s.txt.gz"
    # http://vault.centos.org/centos/7/updates/Source/SPackages/
    # https://centos.pkgs.org/6/centos-i386/microcode_ctl-1.17-25.el6.i686.rpm.html
    # https://centos.pkgs.org/6/centos-updates-i386/microcode_ctl-1.17-25.2.el6_9.i686.rpm.html
    # http://vault.centos.org/6.9/updates/Source/SPackages/microcode_ctl-1.17-25.2.el6_9.src.rpm
    # For CentOS 5 and before, we really can't figure this out...
    # http://vault.centos.org/5.11/updates/SRPMS/thunderbird-38.5.0-1.el5.centos.src.rpm
    # http://vault.centos.org/5.11/updates/i386/RPMS/thunderbird-38.5.0-1.el5.centos.i386.rpm
    # http://mirror.centos.org/centos/6/updates/x86_64/Packages/qemu-guest-agent-0.12.1.2-2.503.el6_9.4.x86_64.rpm
    # http://mirror.centos.org/centos/6/updates/x86_64/Packages/qemu-guest-agent-0.12.1.2-2.503.el6_9.4.x86_64.rpm

    KNOWN_BAD_NAMES = {
        "2017-January": "CESA-2017:0001",  # IPA tools
        "2017-February": "CESA-2017:0294",  # Kernel update - Incorrect - later corrected...
        "2017-March": "CESA-2017:0388",  # IPA tools
        "2017-June": "CESA-2017:1430",  # Qemu/kvm patch - doesn't exist
    }
    UNSUPPORTED = {
        "7.2",
        "7.2.1",
        "7.2.2",
        "7.2.3",
        "7.2.4",
        "7.2.5",
        "7.2.6",
        "7.2.7",
        "7.3",
        "7.3.1",
        "7.3.2",
        "7.3.3",
        "7.3.4",
        "7.3.5",
        "7.3.6",
        "6.8",
        "6.8.1",
        "6.8.2",
        "6.8.3",
        "6.8.4",
        "6.8.6",
        "6.8.7",
        "6.7",
        "6.7.1",
        "6.7.2",
        "6.7.3",
        "6.7.4",
        "6.7.5",
        "6.7.6",
        "6.7.7",
        "6.6",
        "6.5",
        "6.4",
        "6.3",
        "6.2",
        "6.1",
        "6",
        "5",
    }

    def compute_arch_osrel(self, package_name):
        """

        :param package_name: str: name of the package
        :return: (str, str): (architecture, OS release)
        """
        package = self.rpm_version_info(package_name)
        match = self.PKG_PARSE.match(package_name)
        if not match:
            raise ValueError(
                "package [%s] doesn't match [%s]" % (package_name, self.PKG_PARSE.pattern)
            )
        osrel = str(match.group(1))
        if osrel.endswith("."):
            osrel = osrel[:-1]
        return package.arch, osrel  # architecture, os release

    def compute_binary_url(self, package):
        """
        Translate the package name into the URL of the binary package
        :param package: str: CentOS package name
        :return: str: URL of CentOS package
        """

        arch, rel = self.compute_arch_osrel(package)
        if arch == "i686":
            arch = "i386" if int(rel[0]) < 7 else "x86_64"
        elif arch == "noarch":
            arch = "x86_64"
        intrel = int(rel[0])
        if intrel < 6:
            raise NotImplementedError("We only support CentOS6.9 and beyond.")
        return self.BINARY_BASE_URL % (intrel, arch, package)

    def compute_src_url(self, package):
        """
        Translate the source package name into the URL of the source package
        :param package: str: CentOS source package name
        :return: str: URL of CentOS package
        """
        match = self.SRCPKG_PARSE.match(package)
        if not match:
            raise ValueError(
                "package [%s] doesn't match [%s]" % (package, self.SRCPKG_PARSE.pattern)
            )
        rel = match.group(1)
        rel = rel.replace("_", ".")
        rel_pieces = rel.split(".")
        if len(rel_pieces) > 2 and rel_pieces[0] == "6":
            rel = ".".join(rel_pieces[0:1])
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
        rel = match.group(1)[0]
        return self.INFO_BASE_URL % (rel, package)

    # pylint: disable=R0903,R0912,R0914
    def _parse_text(self):
        """
        Parse the text...

        :return: dict(str, str): Text divided up by section
        """
        sections = {}
        unsupported = False
        section_name = None
        for line in self._text.split("\n"):
            if line.endswith(":"):
                word = line[:-1].lower()
                if word not in self.KNOWN_WORDS:
                    if ">" in word or " " in word:
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
                    sections["name"] = "CESA-%s" % match.group(1)
                    sections["importance"] = match.group(2).lower()
                    continue
                match = self.CESA2.match(line)
                if match:
                    sections["name"] = "CESA-%s" % match.group(1)
                    sections["importance"] = "unknown"
                    continue
                match = self.UPSTREAM.match(line)
                if match:
                    sections["upstream"] = match.group(1)
                    if "urls" not in sections:
                        sections["urls"] = []
                    sections["urls"].append(match.group(1))
                    continue
                if line.startswith("--"):
                    section_name = "email-signature"
                    sections[section_name] = []
                    continue
                if section_name is not None:
                    sections[section_name].append(line)
                    if line.startswith("http://") or line.startswith("https://"):
                        if "urls" not in sections:
                            sections["urls"] = []
                        sections["urls"].append(line)

        sections["patches"] = {}
        for section_name in self.PATCHES:
            if section_name in sections:
                this_sect = " ".join(sections[section_name])
                this_sect = self.SPACES_RE.split(this_sect)
                for index in range(0, len(this_sect), 2):
                    if this_sect[index] == "":
                        break
                    patch = this_sect[index + 1]
                    match = self.BASE_PACKAGE_RE.match(patch)
                    if not match:
                        raise ValueError(
                            "Unsupported package name:%s: doesn't match %s"
                            % (patch, self.BASE_PACKAGE_RE.pattern)
                        )
                    base_package = match.group(0)
                    if patch != "":
                        _arch, osrel = self.compute_arch_osrel(patch)
                        osrel = osrel.replace("_", ".")
                        if osrel in self.UNSUPPORTED:
                            unsupported = True
                            continue
                        regex = re.compile(r"(.*)\.el[0-9_.]*")
                        package = self.rpm_version_info(patch)
                        version = "%s-%s" % (package.version, regex.match(package.release).group(1))
                        assert package.epoch == "0"
                        if section_name == "source":
                            sections["patches"][patch] = {
                                "arch": "src",
                                "base_package": base_package,
                                "os": "centos",
                                "osrel": osrel,
                                "package": self.compute_src_url(patch),
                                "sha256": this_sect[index],
                                "version": version,
                            }
                        else:
                            sections["patches"][patch] = {
                                "arch": package.arch,
                                "base_package": base_package,
                                "info": self.compute_info_url(patch),
                                "os": "centos",
                                "osrel": osrel,
                                "package": self.compute_binary_url(patch),
                                "sha256": this_sect[index],
                                "version": version,
                            }
                del sections[section_name]
        for sect_name, sect_info in sections.viewitems():
            # print ('SECT_INFO:', len(sect_info), type(sect_info), sect_info, file=stderr)
            if isinstance(sect_info, list) and sect_name != "urls":
                if sect_info[-1] == "":
                    del sect_info[-1]
                sections[sect_name] = "\n".join(sections[sect_name])

        if "name" not in sections:
            raise ValueError("No vulnerability name in %s." % self.url)
        if len(sections["patches"]) == 0:
            if unsupported:
                raise NotImplementedError("Announcement for Unsupported release")
            raise ValueError("No patches in %s", self.url)
        return sections

    @staticmethod
    def guess_other_urls(url):
        """
        We're given a URL that we can't find. Try and figure out other places it might be and
        return them...
        :param url: str: URL that gets 404...
        :return: [str] list of other URLs to try...
        """
        results = []
        if ".el7.centos.1." in url:
            mod = "/os/".join(url.split("/updates/", 1))
            results.append(".el7.centos.2.".join(mod.split(".el7.centos.1.", 1)))
        if ".el7.centos.3." in url:
            results.append("/os/".join(url.split("/updates/", 1)))
        if "/centos/7/" in url:
            try1 = "/7.2.1511/".join(url.split("/centos/7/", 1))
            results.append(try1)
            results.append("/vault.centos.org/".join(try1.split("/mirror.centos.org/", 1)))
        if "/centos/7.4/" in url:
            results.append("/7.4.1708/".join(url.split("/centos/7.4/", 1)))
        if "/centos/7.4.1/" in url:
            results.append("/7.4.1708/".join(url.split("/centos/7.4.1/", 1)))
        if "/centos/7.4.2/" in url:
            results.append("/7.4.1608/".join(url.split("/centos/7.4.2/", 1)))
            results.append("/7.4.1708/".join(url.split("/centos/7.4.2/", 1)))
        if "/centos/7.4.4/" in url:
            results.append("/7.4.1708/".join(url.split("/centos/7.4.4/", 1)))
        if "/centos/7.4.6/" in url:
            results.append("/7.4.1708/".join(url.split("/centos/7.4.6/", 1)))
        if "/centos/7.4.7/updates/" in url and ".el7_4.7." in url:
            mod = "/7.4.1708/os/".join(url.split("/centos/7.4.7/updates/", 1))
            results.append(".el7.".join(mod.split(".el7_4.7.", 1)))
        if "/centos/7.4.8/" in url:
            results.append("/7.4.1708/".join(url.split("/centos/7.4.8/", 1)))

        return results


class UbuntuAnnouncement(Announcement):
    """
    A class which is capable of parsing Ubuntu vulnerability announcements.
    """

    MBOX_ANNOUNCEMENT_URL_FMT = (
        "https://lists.ubuntu.com/archives/ubuntu-security-announce/%s-%s.txt.gz"
    )
    UNSUPPORTED = {"ubuntu 13.10", "ubuntu 13.04", "ubuntu 12.10", "ubuntu 12.04 esm"}
    PATCHES = {"ubuntu 17.10", "ubuntu 17.04", "ubuntu 16.04 lts", "ubuntu 14.04 lts"}
    PATCHES = PATCHES.union(UNSUPPORTED)
    KNOWN_WORDS = {
        "a security issue affects these releases of ubuntu and its derivatives",
        "summary",
        "software description",
        "advisory details",
        "details",
        "original advisory details",
        "update instructions",
        "references",
        "package versions",
        "package information",
        "please see the following for more information",
        "mitigations for the ppc64el architecture. original advisory details",
    }
    KNOWN_WORDS = KNOWN_WORDS.union(PATCHES)

    # PATCHES = ("package information",)

    USN_RE = re.compile("ubuntu security notice (USN-[-A-Za-z0-9]*)", re.IGNORECASE)
    RELEASE_RE = re.compile(r"[0-9]+\.[0.9]+")

    # pylint: disable=R0912
    def _parse_text(self):
        """
        Parses a plain text version of a vulnerability announcement.

        :return: dict: returns dict suitable for converting to JSON
        """
        sections = {}
        unsupported = False
        section_name = None
        for line in self._text.split("\n"):
            if line.endswith(":"):
                word = line[:-1].lower()
                if word not in self.KNOWN_WORDS:
                    if ">" in word or " " in word:
                        raise ValueError("Email format error [%s]" % word)
                    print("OOPS! Unrecognized section [%s:]" % word, file=stderr)
                section_name = word
                if section_name not in sections:
                    sections[section_name] = []
            else:
                if self.NEXTPART.match(line):
                    break
                match = self.USN_RE.match(line)
                if match:
                    sections["name"] = match.group(1)
                    section_name = "introduction"
                    sections["introduction"] = []
                if line.startswith("--"):
                    section_name = "email-signature"
                    sections[section_name] = []
                    continue
                if section_name is not None:
                    sections[section_name].append(line)
                    if line.startswith("http://") or line.startswith("https://"):
                        if "urls" not in sections:
                            sections["urls"] = []
                        sections["urls"].append(line)

        sections["patches"] = {}
        for section_name in self.PATCHES:
            osrel = section_name
            if osrel in self.UNSUPPORTED:
                unsupported = True
                continue
            if section_name in sections:
                this_sect = " ".join(sections[section_name])
                this_sect = self.SPACES_RE.split(this_sect)
                for index in range(0, len(this_sect), 2):
                    if this_sect[index] == "":
                        break
                    base_package = this_sect[index]
                    version = this_sect[index + 1]
                    sections["patches"][base_package + "::" + osrel] = version
                del sections[section_name]
        for sect_name, sect_info in sections.viewitems():
            # print ('SECT_INFO:', len(sect_info), type(sect_info), sect_info, file=stderr)
            if isinstance(sect_info, list):
                while len(sect_info) > 1 and sect_info[-1] == "":
                    del sect_info[-1]
                while len(sect_info) > 0 and sect_info[0] == "":
                    del sect_info[0]
                sections[sect_name] = "\n".join(sections[sect_name])

        if "name" not in sections:
            raise ValueError("No vulnerability name in %s." % self.url)
        if len(sections["patches"]) == 0:
            if unsupported:
                raise NotImplementedError("Announcement for unsupported release")
            raise ValueError("No patches in %s", self.url)
        return sections


# pylint: disable=R0912,R0914
def analyze_all_mbox_vulnerabilities(years, announcement_cls):
    """
    The purpose of this function is to find all the vulnerability emails for
    the given distribution and the given years and analyze them - returning
    the set of vulnerability announcements which are still in effect.

    Vulnerability announcements which have been superceded by announcements which affect
    all the same packages are ignored.

    That is, the remaining announcements have at least one package for which this
    annoucement gives the latest version (by time).

    It is assumed that the latest version by time will also be the latest by version number.

    Latest also takes into account "latest in this OS release" - but DOES NOT take into account
    the pecularities of how several releases with different names might still be effectively
    the same release - and general confusion and inconsistency in naming releases...

    :param years: [str]: List of years to analyze
    :param announcement_cls: Class to use to analyze (Mailman) Mbox Announcement archives
    :return: List of key Announcements
    """

    url_format = announcement_cls.MBOX_ANNOUNCEMENT_URL_FMT
    mbox_archive_by_date = {}
    mbox_archive_by_name = {}
    #
    # Read in all the 'gz' mbox archives that have been requested...
    #
    for year in years:
        for month in (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ):
            gz = url_format % (year, month)
            print("GZ: %s" % gz)
            for vulnerability in parse_email_mbox_gz(gz, announcement_cls):
                print(vulnerability)
                announcement_name = vulnerability.data["name"]
                # Epoch time is when this announcement was created - in UNIX time (seconds)
                date_key = (vulnerability.data["epoch_time"], announcement_name)
                mbox_archive_by_date[date_key] = vulnerability
                mbox_archive_by_name[announcement_name] = vulnerability
    keys = mbox_archive_by_date.keys()
    keys.sort(reverse=True)
    #  print('\n'.join([str(key) for key in keys]))
    release_patches = {}
    for _, announcement_name in keys:
        announcement = mbox_archive_by_name[announcement_name]
        for patch_name, patch in announcement.data["patches"].viewitems():
            osrel = patch["osrel"] + "::" + patch["arch"]
            if osrel not in release_patches:
                release_patches[osrel] = {}
            base_package = patch["base_package"]
            if base_package in release_patches[osrel]:
                continue
            package_url = patch["package"]
            release_patches[osrel][base_package] = (patch_name, announcement_name, package_url)
    releases = release_patches.keys()
    releases.sort()
    current_announcements = {}
    better_urls = {}
    unknown = "**Unknown**"
    for release in releases:
        #  print("==== %s ============" % release)
        package_names = release_patches[release].keys()
        package_names.sort()
        for package_name in package_names:
            package_info = release_patches[release][package_name]
            #  print("%s => %s" % (package_name, release_patches[release][package_name]))
            patch_name = package_info[0]
            name = package_info[1]
            if name not in current_announcements:
                current_announcements[name] = mbox_archive_by_name[name]
            if not announcement_cls.check_a_single_url(package_info[2]):
                better_urls[package_info[2]] = unknown
                for url in announcement_cls.guess_other_urls(package_info[2]):
                    if announcement_cls.check_a_single_url(url):
                        better_urls[package_info[2]] = url
                        break
                if better_urls[package_info[2]] == unknown:
                    print(
                        "URL %s for announcement %s not found anywhere." % (package_info[2], name),
                        file=stderr,
                    )

    for announcement in current_announcements.viewvalues():
        for patch in announcement.data["patches"].viewvalues():
            url = patch["package"]
            if url in better_urls:
                patch["package"] = better_urls[url]

    return current_announcements.viewitems()


analyze_all_mbox_vulnerabilities((2018, 2017, 2016), CentOSAnnouncement)
analyze_all_mbox_vulnerabilities((2018,), UbuntuAnnouncement)
