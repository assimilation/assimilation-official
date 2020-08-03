# Our Build Process
Our build process is a bit odd and _very_ containerish - and fully reproducible (or so we believe).
It's all triggered by the script ```docker/dockit``` - which in turn calls subsidiary dockit scripts to build the various containers.
In the end, we want a single CMA container, and a single "universal" nanoprobe binary.
The steps are as follows:
 1. Build a Meson/Ninja container (based on CentOS 6) using ```docker/meson/dockit```.
 This is a "throwaway" container.
 2. Build the nanoprobe, in a container based off our Meson/Ninja container using ```docker/nanoprobe/dockit```.
 The only thing we retain from this container is the "universal" nanoprobe binary.
 This is also a "throwaway" container - once we extract the nanoprobe binary we've built from it.
 3. Build the CMA container using ```docker/cma/dockit```.
 This is the container which our customers will eventually run.
 
 So, in the end what customers run on their various systems throught their domain is:
  - lots of copies of the "universal" nanoprobe binary, running nearly everywhere
  - a single instance of the CMA container, which in turn runs and controls
  - a single instance of a Neo4j container.
# External Dependencies
There are several kinds of dependencies in this project.
The reason for documenting them here is so they can be kept up to date
after I've forgotten where all these various version dependencies and bindings are - which time will probably best be measured in hours ;-).

These include:
  - Python modules: for the CMA and for building the nanoprobe
  - C libraries for the nanoprobe
  - The version of Neo4j docker container
# Python Modules
## For building our Meson Container
We use Meson and Ninja to build the nanoprobe.
Towards this end, we create a meson docker container with everything we need.
This is because we want to build a version of the nanoprobe which is usable everywhere.
his mean building it in an old crufty version of CentOS with a newer version of Python (**compiled from source**).
We want as old a version of Linux as we can still get, yet a relatively recent version of Python.
Everthing for this is in **```docker/meson```**.
```docker/meson/toolrequirements.txt``` controls
the versions of [meson](https://mesonbuild.com/) and [ninja](https://ninja-build.org/) we include in this container.
This container is built on top of an old version of CentOS (currently 6.10).
This means our fully bound nanoprobe will work on any system whose glibc is not older than the version of CentOS we built on.
You can find the version of CentOS in ```docker/meson/Dockerfile```.
This file also specifies the version of Python that we use to run Meson and Ninja.
It must be >= 3.6.
## For building the nanoprobe
The nanoprobe is built on top of our Meson docker image - since Meson and Ninja are needed to build it.
The version of Python used for this build is whatever version is in the Meson docker image we built before.
In the end, we build a version of the nanoprobe which only relies on glibc.
This means that all its dependencies are used to
build it, and there are none at runtime beyond glibc.
The versions of libsodium and libpcap which we use are controlled by ```docker/nanoprobe/dockerfile.in```
## For building the CMA Container
The CMA's direct dependencies are in ```cma/min-requirements.txt```.
Fully specified requirements are in ```cma/requirements.txt```
As an aside, it requires the libraries the nanoprobe is built with.
Of special note is [ctypesgen](https://github.com/davidjamesca/ctypesgen), which is used to generate Python bindings for calling functions in the nanoprobe libraries.
# C libraries for building the Nanoprobe
These are the libraries the nanoprobe uses:
## glibc
[Glibc](https://www.gnu.org/software/libc/) is the GNU C library.
It is the only library which we dynamically link to be referenced as a shared library.
Every Linux machine has a version of glibc, which we will then use at runtime.
This will work nicely, provided that the version of glibc installed on the target machine is
no older than the one we built against.
_All other libraries are statically linked_.
## glib2
[Glib2](https://wiki.gnome.org/Projects/GLib) is a C library (not the same as glibc or libc),
which provides some higher-level constructs including an event loop and various handy datastructures - such as hash tables, linked lists and so on.
In addition, it isolates us from platform differences.
In theory, this should make a Windows port of the nanoprobe possible.
_We statically link against the version of glib2 which comes with the version of CentOS that we used to build our Meson container._
This library should compile for Windows, but suitable versions of the library for Windows are no longer available precompiled.
## zlib
Zlib is a compression library
_We statically link against the version of zlib which comes with the version of CentOS we used to build our Meson container._
## libsodium
[Libsodium](https://github.com/jedisct1/libsodium) is a cryptographic library.
**We compile libsodium from source**.
It compiles easily on any platform, since it's only system connection is to system entropy (randomness).
The version of libpcap we use is controlled by ```src/docker/nanoprobe/dockerfile.in```
Libsodium is compilable for every platform.
It's worth noting that there is a miminal verison of libsodium ([libhydrogen](https://github.com/jedisct1/libhydrogen)) under development for
embedded systems.
## libpcap (or windows equivalent)
[Libpcap](https://www.tcpdump.org/) is a library for listening to packets.
We use it to listen for ARP, CDP and LLDP packets - which are _not_ IP packets.
Libpcap is part of the tcpdump project.
**We compile libpcap from source**.
The version of libpcap we use is controlled by ```src/docker/nanoprobe/dockerfile.in```.
Although this library works on every UNIX-like systems, it is highly system dependent.
There is a library providing this capability for Windows.
The Windows version of this library's future was somewhat in flux the last time I looked.
# Neo4j container
[Neo4j](https://neo4j.com/) is a graph database.
We use it through a [container](https://hub.docker.com/_/neo4j) which they supply.
The version and edition of Neo4j that we use is found in
[```cma/cmainit.py```](https://github.com/assimilation/assimilation-official/blob/rel_2_dev/cma/cmainit.py) (```NEOVERSION``` and ```NEOEDITION```).
  
# Summary of Key Files controlling Versions
  - [```docker/meson/Dockerfile```](https://github.com/assimilation/assimilation-official/blob/rel_2_dev/docker/meson/Dockerfile): Controls for the version of Python used by Meson and Ninja, and the version of CentOS - which in turn specifies the version of glibc and zlib used to build the nanoprobe.
  - [```docker/meson/toolrequirements.txt```](https://github.com/assimilation/assimilation-official/blob/rel_2_dev/docker/meson/toolrequirements.txt): Controls the version of Meson and Ninja used to build the nanoprobe.
  - [```docker/nanoprobe/dockerfile.in```](https://github.com/assimilation/assimilation-official/blob/rel_2_dev/docker/nanoprobe/dockerfile.in): Controls the version of libsodium and libpcap that the nanoprobe uses.
  - [```cma/min-requirements.txt```](https://github.com/assimilation/assimilation-official/blob/rel_2_dev/cma/min-requirements.txt): Specifies direct dependencies of Python packages used by the CMA (with minimal version constraints).
  - [```cma/requirements.txt```](https://github.com/assimilation/assimilation-official/blob/rel_2_dev/cma/requirement.txt): Fully specified set of all packages used by the CMA directly and indirectly.
  Built from min-requirements.txt.
  - [```cma/cmainit.py```](https://github.com/assimilation/assimilation-official/blob/rel_2_dev/cma/cmainit.py): controls the version and edition of Neo4j that we use at runtime.
