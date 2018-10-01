#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
#   Genpybindings - generate python bindings for Assimilation C classes
#
#   usage: genpybindings.py outfile sourceroot buildddir libdir libfile...
#
#   outfile     name of file to put output into
#   sourceroot  root of source directory tree
#   buildroot   root of build (binary) directory tree
#   libdir      where the runtime libraries are located
#   libfiles    list of library files that we might want to bind to (just one today)
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
#  The Assimilation software is distributed in the hope that it will be
#  useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with the Assimilation Project software.
#  If not, see http://www.gnu.org/licenses/
#
#
import os, sys
import ctypesgencore
glibpkgname='glib-2.0'

def patch_ctypes(source_dir):
    patches = ['ints1.diff', 'floats1.diff', 'floats2.diff']
    ctypes_dir = os.path.dirname(ctypesgencore.__file__)
    for patch in patches:
        syscmd = '(cd %s; sudo patch --forward -p1 --posix --reject-file -) < %s/%s' % (ctypes_dir, source_dir, patch)
        print('running %s' % syscmd)
        os.system(syscmd)
    rc = os.system('sudo rm -f %s/parser/lextab.py %s/parser/lextab.pyc' % (ctypes_dir, ctypes_dir))
    if rc != 0:
        sys.exit(rc)
    os.system('sudo ctypesgen /dev/null </dev/null >/dev/null 2>&1')
    sys.exit(0)

source_dir = os.path.dirname(sys.argv[0])
patch_ctypes(source_dir)
