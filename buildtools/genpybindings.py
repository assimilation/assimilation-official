#!/usr/bin/env python3.6
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
"""
Generated with:
/usr/local/bin/ctypesgen --no-macro-warnings --cpp=gcc -E -DCTYPESGEN -D__signed__=signed -U__HAVE_FLOAT32X -U__HAVE_FLOAT64X -DFLT64X_EPSILON=1.08420217248550443400745280086994171e-19 -o /tmp/src/cma/AssimCtypes.py
--runtime-libdir /tmp/bin
--compile-libdir /tmp/src/clientlib
-I/tmp/src/include
-L -lglib-2.0
-l /usr/lib/.so
-l libassimilationclient.so
-l libsodium.so -I/usr/include/glib-2.0
-I/usr/lib/x86_64-linux-gnu/glib-2.0/include
-I/tmp/src/include
-I/tmp/src/include
/usr/include/glib-2.0/glib.h
/tmp/src/include/address_family_numbers.h
/tmp/src/include/resourcecmd.h
/tmp/src/include/tlvhelper.h
/tmp/src/include/authlistener.h
/tmp/src/include/resourceocf.h /tmp/src/include/childprocess.h /tmp/src/include/seqnoframe.h /tmp/src/include/server_dump.h /tmp/src/include/jsondiscovery.h /tmp/src/include/resourcelsb.h /tmp/src/include/hbsender.h /tmp/src/include/cryptcurve25519.h /tmp/src/include/cstringframe.h /tmp/src/include/cmalib.h /tmp/src/include/misc.h /tmp/src/include/discovery.h /tmp/src/include/resourcequeue.h /tmp/src/include/gmainfd.h /tmp/src/include/tlv_valuetypes.h /tmp/src/include/cryptframe.h /tmp/src/include/netioudp.h /tmp/src/include/netio.h /tmp/src/include/netaddr.h /tmp/src/include/arpdiscovery.h /tmp/src/include/logsourcefd.h /tmp/src/include/packetdecoder.h /tmp/src/include/pcap_GSource.h /tmp/src/include/assimobj.h /tmp/src/include/fsqueue.h /tmp/src/include/nvpairframe.h /tmp/src/include/compressframe.h /tmp/src/include/reliableudp.h /tmp/src/include/generic_tlv_min.h /tmp/src/include/resourcenagios.h /tmp/src/include/proj_classes.h /tmp/src/include/configcontext.h /tmp/src/include/fsprotocol.h /tmp/src/include/frame.h /tmp/src/include/nanoprobe.h /tmp/src/include/pcap_min.h /tmp/src/include/unknownframe.h /tmp/src/include/listener.h /tmp/src/include/lldp.h /tmp/src/include/projectcommon.h /tmp/src/include/addrframe.h /tmp/src/include/frameset.h /tmp/src/include/hblistener.h /tmp/src/include/cdp.h /tmp/src/include/ipportframe.h /tmp/src/include/intframe.h /tmp/src/include/signframe.h /tmp/src/include/netgsource.h /tmp/src/include/switchdiscovery.h /tmp/src/include/frametypes.h /tmp/src/include/framesettypes.h

"""
import os, sys
import ctypesgen

glibpkgname = "glib-2.0"


def readcmdline(cmd):
    "Read the first line of output from running a command"
    fd = os.popen(cmd, "r")
    line = fd.readline()
    fd.close()
    return line.strip()


glibheaderfile = "glib.h"

# Ask pkg-config for the -I flags for glib2
glibincflags = readcmdline("pkg-config --cflags-only-I %s" % glibpkgname)
# Ask pkg-config for the loader library flags for glib2
gliblibflags = readcmdline("pkg-config --libs %s" % glibpkgname).split(" ")

# Compute the list of include directories for glib (without -I prefixes)
glibincdirs = []
for iflag in glibincflags.split():
    if not iflag.startswith("-I"):
        continue
    glibincdirs.append(iflag[2:])


def findincfile(incdirs, filename):
    "Find a(n include) file somewhere under this list of directories"
    for dir in incdirs:
        pathname = os.path.join(dir, filename)
        if os.path.exists(pathname):
            return pathname


def find_cpp():
    "Return a string saying how to find the C preprocessor - along with any necessary arguments"
    # See http://code.google.com/p/ctypesgen/wiki/GettingStarted for Windows details...
    return "--cpp=gcc -E -DCTYPESGEN -D__signed__=signed -U__HAVE_FLOAT32X -U__HAVE_FLOAT64X -DFLT64X_EPSILON=1.08420217248550443400745280086994171e-19"


def build_cmdargs(outfile, sourceroot, buildroot, libdir, libfiles):
    "Build the ctypesgen command line to execute - and run it"
    args = [
        "--no-macro-warnings",
        find_cpp(),
        "-o",
        outfile,
        "--runtime-libdir",
        libdir,
        "--compile-libdir",
        os.path.join(buildroot, "clientlib"),
        "-I" + os.path.join(sourceroot, "include"),
    ]
    args.append("-L")

    # Glib library flags - typically -lglib-2.0
    for flag in gliblibflags:
        args.append(flag)

    # Our local libraries
    for lib in libfiles:
        args.append("-l")
        if lib.endswith('/'):
            raise RuntimeError(f"OOPS! Bad local libraries {libfiles}")
        args.append(lib + ".so")  # Obviously needs to change for windows - or so I think ;-)
    # -I flags for glib
    for iflag in glibincflags.split():
        args.append(iflag)
    includedir = os.path.join(sourceroot, "include")
    # -I directive for our include directory
    args.append("-I" + includedir)
    # -I directive for our build include directory
    buildincludedir = os.path.join(buildroot, "include")
    args.append("-I" + buildincludedir)

    # All the flags are set - now list out the headers to parse
    #   Starting with the full pathname to glib.h
    args.append(findincfile(glibincdirs, glibheaderfile))
    # Add on the pathnames of all our header files
    hdrfiles = os.listdir(includedir)
    hfileset = {}
    for hfile in hdrfiles:
        if not hfile.endswith(".h"):
            continue
        hfileset[hfile] = True
        args.append(os.path.join(includedir, hfile))
    # Add on the pathnames of all our generated header files
    hdrfiles = os.listdir(buildincludedir)
    for hfile in hdrfiles:
        # Sometimes people do an in-place build...
        if not hfile.endswith(".h") or hfile in hfileset:
            continue
        args.append(os.path.join(buildincludedir, hfile))

    # Now build the quoted command line from the arguments
    cmdline = "ctypesgen"
    for arg in args:
        cmdline += ' "%s"' % arg

    # print ('Running', cmdline)
    return cmdline


if len(sys.argv) < 6:
    sys.stderr.write("Usage: %s outfile sourceroot buildroot libdir libfile ...\n" % sys.argv[0])
    raise SystemExit(1)

outfile = sys.argv[1]
sourceroot = sys.argv[2]
buildroot = sys.argv[3]
libdir = sys.argv[4]
libfiles = sys.argv[5:]
print(f"#  Output file: {outfile}")
print(f"#  Source root: {sourceroot}")
print(f"#  Build root:  {buildroot}")
print(f"#  Lib dir:     {libdir}")
print(f"#  Lib files:   {libfiles}")
rc = os.system(build_cmdargs(outfile, sourceroot, buildroot, libdir, libfiles))
sys.exit(rc)
