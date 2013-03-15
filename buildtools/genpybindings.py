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
#  The Assimilation software is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
import os, sys
glibpkgname='glib-2.0'

def readcmdline(cmd):
    'Read the first line of output from running a command'
    fd = os.popen(cmd, 'r')
    line=fd.readline()
    fd.close()
    return line.strip()

glibheaderfile='glib.h'

# Ask pkg-config for the -I flags for glib2
glibincflags=readcmdline('pkg-config --cflags-only-I %s' % glibpkgname)
# Ask pkg-config for the loader library flags for glib2
gliblibflags=readcmdline('pkg-config --libs %s' % glibpkgname).split(' ')

# Compute the list of include directories for glib (without -I prefixes)
glibincdirs=[]
for iflag in glibincflags.split():
    if not iflag.startswith('-I'):
        continue
    glibincdirs.append(iflag[2:])

def findincfile(incdirs, filename):
    'Find a(n include) file somewhere under this list of directories'
    for dir in incdirs:
        pathname=os.path.join(dir, filename)
        if os.path.exists(pathname):
            return pathname

def find_cpp():
    'Return a string saying how to find the C preprocessor - along with any necessary arguments'
    # See http://code.google.com/p/ctypesgen/wiki/GettingStarted for Windows details...
    return '--cpp=gcc -E -DCTYPESGEN -D__signed__=signed'

def build_cmdargs(outfile, sourceroot, buildroot, libdir, libfiles):
    'Build the ctypesgen command line to execute - and run it'
    args=[  '--no-macro-warnings',
            find_cpp(),
            '-o', outfile,
            '--runtime-libdir', libdir,
            '--compile-libdir', os.path.join(buildroot, 'clientlib'),
            '-I' + os.path.join(sourceroot, 'include')]
    args.append('-L')

    # Glib library flags - typically -lglib-2.0
    for flag in gliblibflags:
        args.append(flag)

    # Our local libraries
    for lib in libfiles:
        args.append('-l')
        args.append(lib)
    # -I flags for glib
    for iflag in glibincflags.split():
        args.append(iflag)
    includedir=os.path.join(sourceroot, 'include')
    # -I directive for our include directory
    args.append('-I' + includedir)
    # -I directive for our build include directory
    buildincludedir=os.path.join(buildroot, 'include')
    args.append('-I' + buildincludedir)

    # All the flags are set - now list out the headers to parse
    #   Starting with the full pathname to glib.h
    args.append(findincfile(glibincdirs, glibheaderfile))
    # Add on the pathnames of all our header files
    hdrfiles=os.listdir(includedir)
    for hfile in hdrfiles:
        if not hfile.endswith('.h'):
            continue
        args.append(os.path.join(includedir, hfile))

    # Now build the quoted command line from the arguments
    cmdline='ctypesgen.py'
    for arg in args:
        cmdline += ' "%s"' % arg

    #print ('Running', cmdline)
    return cmdline

if len(sys.argv) < 5:
    sys.stderr.write('Usage: %s outfile sourceroot buildroot libdir libfile ...\n' % sys.argv[0])
    raise SystemExit(1)

outfile=sys.argv[1]
sourceroot=sys.argv[2]
buildroot=sys.argv[3]
libdir=sys.argv[4]
libfiles = sys.argv[5:]
os.system(build_cmdargs(outfile, sourceroot, buildroot, libdir, libfiles))
raise SystemExit(0)
