There are several kinds of dependencies in this project.
The reason for documenting them here is so they can be kept up to date
after I've forgotten where all these various version dependencies and bindings are.

These include:
  - Python modules: for the CMA and for building the nanoprobe
  - C libraries for the nanoprobe
  - The version of Neo4j docker container
# Python Modules
## For building the CMA
## For building the nanorpobe
## For the nanoprobe itself
# C libraries for the Nanoprobe
These are the libraries we use:
## glibc
Glibc is a C library (not the same as glib or libc),
which provides some higher-level constructs including an event loop and various handy datastructures - such as hash tables, linked lists and so on.
In addition, it isolates us from platform differences.
## libsodium
Libsodium is a cryptographic library. It compiles easily on any platform, since it's only system connection is to system entropy.
## libpcap (or windows equivalent)
Libpcap is a library for listening to packets. We use it to listen for CDP and LLDP packets.
# Neo4j container
Neo4j is a graph database. We use it through a container which they supply. So ou
  
