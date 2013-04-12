#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2011, 2012 - Alan Robertson <alanr@unix.sh>
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
import os
def print_posix():
    maxcount=0
    selection='RPM'
    names = { 'RPM': 'rpm -q -a', 'DEB': 'dpkg -l'}
    counts = {}
    for name in names:
        cmd=names[name]
        fd = os.popen('%s 2>/dev/null' % cmd, 'r')
        packages = fd.readlines()
        fd.close()
        counts[name] = len(packages)
        packages = None
    for name in names:
        if counts[name] > maxcount:
            selection = name
    print selection

# posix, nt, dos, mac, ce, java, os2, or riscos.
if os.name == 'posix':
    print_posix()
elif os.name == 'mac':
    print 'PackageMaker'
elif os.name == 'nt' or os.name == 'dos' or os.name == 'ce':
    print 'NSIS'

