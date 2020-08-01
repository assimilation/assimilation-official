There are several kinds of dependencies in this project.
The reason for documenting them here is so they can be kept up to date
after I've forgotten where all these various version dependencies and bindings are.

These include:
  - Python modules: for the CMA and for building the nanoprobe
  - C libraries for the nanoprobe
  - The version of Neo4j docker container
# Python Modules
## For building the CMA
## For building Meson
We use Meson to build the nanoprobe. Towards this end, we create a meson docker container with everything we need.
This is because we want to build a version of the nanoprobe which is usable everywhere. This mean building it in an old crufty version of CentOS
with a newer version of Python.
We want as old a version of Linux as we can still get, yet a relatively recent version of Python.
Everthing for this is in **```docker/rel2/meson```** (rel2 should go away by release time). ```docker/rel2/meson/toolrequirements.txt``` contains
the versions of [meson](https://mesonbuild.com/) and [ninja](https://ninja-build.org/) we need to build this container.
This container is built on top of an old version of CentOS (currently 6.10).
This means our fully bound nanoprobe will work on any system whose glibc is not older than the version of CentOS we built on.
You can find the version of CentOS in ```docker/rel2/meson/Dockerfile```. This also contains the version of Python that we use.
It must be >= 3.6. To summarize, the files which bind meson-related dependencies are:
  - ```docker/rel2/meson/Dockerfile```
  - ```docker/rel2/meson/toolrequirements.txt```

## For building the nanoprobe
The nanoprobe is built on top of our Meson docker image - since Meson and Ninja are needed to build it nowadays.
In the end, we build a version of the nanoprobe which only relies on glibc. This means that all its dependencies are used to
build it, and there are none at runtime beyond glibc.
## C libraries for the Nanoprobe
These are the libraries we use:
### glibc
Glibc is a C library (not the same as glib or libc),
which provides some higher-level constructs including an event loop and various handy datastructures - such as hash tables, linked lists and so on.
In addition, it isolates us from platform differences.
### libsodium
Libsodium is a cryptographic library. It compiles easily on any platform, since it's only system connection is to system entropy (randomness).
### libpcap (or windows equivalent)
Libpcap is a library for listening to packets. We use it to listen for CDP and LLDP packets.
# Neo4j container
Neo4j is a graph database. We use it through a container which they supply. So ou
  
