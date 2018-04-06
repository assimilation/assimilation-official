[![Build Status](https://travis-ci.org/assimilation/assimilation-official.svg?branch=master)](https://travis-ci.org/assimilation/assimilation-official)
[![Coverity Status](https://scan.coverity.com/projects/9/badge.svg)](https://scan.coverity.com/projects/9) [![Documentation](https://codedocs.xyz/assimilation/assimilation-official.svg)](https://codedocs.xyz/assimilation/assimilation-official/)

# Welcome to the Assimilation README file :-D.

The Assimilation System Management Suite provides a variety of system management capabilities with near-zero configuration. The project web site is at [assimproj.org](http://assimproj.org/), and commercial support and alternative licenses are available from [Assimilation Systems](http://AssimilationSystems.com). A more comprehensive explanation of our many capabilities can be found on the [Assimilation Systems](http://AssimilationSystems.com) site, and on their [blog](http://assimilationsystems.com/category/blog/).

Although we use the github issues mechanism, most of our issues can be found [on Trello](https://trello.com/b/98QrdEK1/issues-bugs).

This code builds with cmake, not autotools.
A more detailed Getting Started guide can be found [here](http://linux-ha.org/source-doc/assimilation/html/_getting_started.html).
The open source project home page is at http://assimproj.org/ - check it out!
Please join the open source project mailing list [on Mailman](http://lists.community.tummy.com/cgi-bin/mailman/listinfo/assimilation).
This project proudly sponsored by [Assimilation Systems Limited](http://AssimilationSystems.com)</a>.


## Dependencies

We like to have a reasonable number of things in the build environment.
- Cmake (and cpack) - http://cmake.org/
- C compiler (gcc, clang, or MS VC tools) - http://www.gnu.org/software/gcc/ <i>et al</i>
- make tools - like Gnu make, or MSVC - http://www.gnu.org/software/make/ <i>et al</i>
- Recent version of Glib2 - http://developer.gnome.org/glib/
- libpcap (or winpcap) - http://www.tcpdump.org/
- pkg-config (even for Windows) - http://www.freedesktop.org/wiki/Software/pkg-config
- valgrind - The 'C' level tests use it - http://valgrind.org/
- Testify - testing framework from Yelp - https://github.com/Yelp/Testify (<tt>pip install testify</tt>)
- doxygen (for documentation) - http://doxygen.org/. The current documentation can be found [here](https://codedocs.xyz/assimilation/assimilation-official/).
- dot (for doxygen graphs) - http://www.graphviz.org/
- Ctypesgen ( for the CMA code) http://code.google.com/p/ctypesgen/ (<tt>pip install ctypesgen</tt>)

In addition, the following systems are needed in the runtime environment for the CMA:
- Neo4J - http://neo4j.org/
- py2neo - http://py2neo.org/	(<tt>pip install py2neo</tt>)

## Getting Source for the Assimilation Monitoring Project
The source to the Assimilation Project can be found at https://github.com/assimilation/assimilation-official

## Making It

Making The Assimilation Monitoring System from Source is done with cmake.

### Making The Assimilation Monitoring System for \*NIX Systems

You can follow these instructions for \*NIX type systems.
- Extract the source into "path-to-source-directory"
- mkdir "path-to-binary-directory"
- cd "path-to-binary-directory"
- cmake "path-to-source-directory"
- make install

### Making RPM or DEB packages

The Cmake project provides cpack to make minimal RPM and DEB packages
Cpack also makes OS X and Windows packages - but that's untested.
Patches to make this work would be appreciated.

The procedure for making packages is as follows:

- Extract the source into "path-to-source-directory"
- mkdir "path-to-binary-directory"
- cd "binary-directory"
- cmake "path-to-source-directory"
- cpack

If it can't figure out which kind of package to build, it will default to building RPMs.
Patches are being solicited to build Windows and OS X packages (read the cpack docs).
Other package formats aren't supported by cpack, and will have to be supported by other mechanisms.

### Making The Assimilation Monitoring System for Windows

- That's something we need to work out.  An earlier verison of 'nanoprobe' did compile and run successfully on Windows

## Running our Tests

There are currently two test modules that you can run after building it.  They can be run
like this:
```bash
- cd testcode; sh path-to-source-tree/testcode/grind.sh # Assumes you have valgrind installed.
- cd testcode; ./pinger ::1 # Does a ping test of reliable UDP
- cd cma; testify tests     # Runs significant python tests
```

For the testcode piece, you have to be in the cma directory of *build tree*.
For the testify portion, you have to either be in the cma directory of the source tree or the installed version in the python install place
(on my machine that's currently /usr/lib/python2.7/dist-packages/assimilation)


## Other Make Targets

- doc - makes the documentation If you just want to view the latest version online, go to http://assimmon.org/
