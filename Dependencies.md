# Build Process
Our build process is a bit odd and very containerish.
The steps are as follows:
 1. Build a Meson/Ninja container (based on CentOS 6)
 2. Build the nanoprobe, in a container based off our Meson/Ninja container. The only thing we retain from this container is the "universal" nanoprobe binary.
 3. Build the CMA container. This is the container which our customers will eventually run.
 
 So, in the end what customers run on their various systems throught their domain is:
  - lots of copies of the "universal" nanoprobe binary, running nearly everywhere
  - a single instance of the CMA container
# External Dependencies
There are several kinds of dependencies in this project.
The reason for documenting them here is so they can be kept up to date
after I've forgotten where all these various version dependencies and bindings are.

These include:
  - Python modules: for the CMA and for building the nanoprobe
  - C libraries for the nanoprobe
  - The version of Neo4j docker container
# Python Modules
## For building the CMA Container
The CMA's direct dependencies are in ```cma/min-requirements.txt```.
Fully specified requirements are in ```cma/requirements.txt```
As an aside, it requires the libraries the nanoprobe is built with.
Of special note is [ctypesgen](https://github.com/davidjamesca/ctypesgen), which is used to generate Python bindings for calling functions in the nanoprobe libraries.
## For building our Meson Container
We use Meson and Ninja to build the nanoprobe. Towards this end, we create a meson docker container with everything we need.
This is because we want to build a version of the nanoprobe which is usable everywhere. This mean building it in an old crufty version of CentOS
with a newer version of Python.
We want as old a version of Linux as we can still get, yet a relatively recent version of Python.
Everthing for this is in **```docker/meson```**. ```docker/meson/toolrequirements.txt``` contains
the versions of [meson](https://mesonbuild.com/) and [ninja](https://ninja-build.org/) we need to build this container.
This container is built on top of an old version of CentOS (currently 6.10).
This means our fully bound nanoprobe will work on any system whose glibc is not older than the version of CentOS we built on.
You can find the version of CentOS in ```docker/meson/Dockerfile```. This also contains the version of Python that we use.
It must be >= 3.6. To summarize, the files which bind meson-related dependencies are:
  - ```docker/meson/Dockerfile``` _(for the version of Python mainly)_
  - ```docker/meson/toolrequirements.txt``` _(for the version of Meson and Ninja)_
## For building the nanoprobe
The nanoprobe is built on top of our Meson docker image - since Meson and Ninja are needed to build it.
The version of Python used for this build is whatever version is in the Meson docker image we built before.
In the end, we build a version of the nanoprobe which only relies on glibc. This means that all its dependencies are used to
build it, and there are none at runtime beyond glibc.
The versions of libsodium and libpcap which we use are controlled by ```docker/nanoprobe/dockerfile.in```
## C libraries for the Nanoprobe
These are the libraries the nanoprobe uses:
### glib2
[Glib2](https://wiki.gnome.org/Projects/GLib) is a C library (not the same as glibc or libc),
which provides some higher-level constructs including an event loop and various handy datastructures - such as hash tables, linked lists and so on.
In addition, it isolates us from platform differences. In theory, this should make a Windows port of the nanoprobe possible.
_We use the version of glib2 which comes with the version of CentOS that we used to build our Meson container._
### zlib
Zlib is a compression library
_We use the version of zlib which comes with the version of CentOS we used to build our Meson container._
### libsodium
[Libsodium](https://github.com/jedisct1/libsodium) is a cryptographic library.
It compiles easily on any platform, since it's only system connection is to system entropy (randomness).
_We compile it from source_. The version of libpcap we use is controlled by ```src/docker/nanoprobe/dockerfile.in```
Available on every platform.
### libpcap (or windows equivalent)
[Libpcap](https://www.tcpdump.org/) is a library for listening to packets. We use it to listen for CDP and LLDP packets - which are _not_ IP packets. It is part of the tcpdump project.
_We compile it from source_. The version of libpcap we use is controlled by ```src/docker/nanoprobe/dockerfile.in```
There is a different version of this code available for Windows.
The Windows version of this library's future was somewhat in flux the last time I looked.
# Neo4j container
[Neo4j](https://neo4j.com/) is a graph database. We use it through a [container](https://hub.docker.com/_/neo4j) which they supply.
The version and edition of Neo4j that we use is found in [```cma/cmainit.py```](https://github.com/assimilation/assimilation-official/blob/rel_2_dev/cma/cmainit.py) (```NEOVERSION``` and ```NEOEDITION```).
  
# Key Files controlling versions
