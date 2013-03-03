/**
@page GettingStarted Getting Started - Installation and Configuration

A normal installation consists of one instance of a CMA (collective management authority)
and <i>n+1</i> nanoprobes.  Only one machine runs the CMA software, but every machine being
monitored (including the CMA itself) runs a copy of the nanoprobe daemon.

There is a package for the nanoprobe daemon, called <i>assimilation-nanoprobe</i>, and a separate 
package for the CMA called (unsurprisingly) <i>assimilation-cma</i>.

The CMA also requires the <a href="http://neo4j.org">Neo4j</a> graph database to store
all the configuation and status information for the collection of machines
(aka the <i>collective</i>).  The CMA also requires the <a href="http://py2neo.org">py2neo</a>
package to talk to <i>neo4j</i>.

This document is a more detailed version of the information provided in the project
<a href="http://linux-ha.org/source-doc/assimilation/html/_r_e_a_d_m_e.html">README</a> file.

@section BuildPrereqs Build, Test and Documentation Prerequisites

The following packages are needed for building the packages, testing them, or creating documentation.

<b>Nanoprobe (and CMA library) packages</b>
- <a href="cmake.org">cmake</a> and cpack
- <a href="http://www.gnu.org/software/gcc/">gcc</a>,
  <a href="http://www.gnu.org/software/make/">make</a> and friends
- <a href="http://developer.gnome.org/glib">glib2-dev</a> (aka libglib2.0-dev)
- <a href="http://www.tcpdump.org">libpcap-dev</a> (or winpcap for Windows)
- <a href="http://www.freedesktop.org/wiki/Software/pkg-config">pkg-config</a>
- <a href="http://valgrind.org/">valgrind</a> (for some of the tests)

<b>Documentation packages</b>
- <a href="http://doxygen.org">Doxygen</a> - for producing this documenation
- dot (part of <a href="http://www.graphviz.org/">graphviz</a>) for creating graphs for the source documentation - and handy for printing graphs from Neo4j.

<b>CMA-only packages</b>
- <a href="http://www.neo4j.org/install">Neo4j</a> graph database
- <a href="http://www.python.org/">Python 2.7</a> (approximately) interpreter for the Python language
- <a href="https://github.com/Yelp/Testify">Testify</a> - Python testing framework
- <a href="http://code.google.com/p/ctypesgen/">ctypesgen</a> (will become mandatory)
- <a href="http://py2neo.org/">py2neo</a> Python bindings for Neo4j
- <a href="www.tornadoweb.org">tornado</a> web server

All of the Nanoprobe and documentation packages are readily available on most modern operating systems.

Depending on your environment, you may not have OS-level packages for all of the python
pieces (testify, ctypesgen, py2neo, tornado).
If you don't have OS packages for those pieces, then you can use
<a href="https://pypi.python.org/pypi/pip">pip</a> to easily install them.

@subsection InstallingNeo4j Installing Neo4j
There are no packages available for Neo4j, so you have to install it from their tar ball
following their
<a href="http://docs.neo4j.org/chunked/stable/server-installation.html">directions</a>.
There is also a short
<a href="http://www.neo4j.org/install#installvideo">video installation guide</a> as well.
The Assimilation code has been tested most recently with the <i>Community 1.9M04</i> version.
Fortunately, they do provide an init script for it, so it can easily be started as a service,
called <i>neo4j-service</i>.
It must be started before the CMA starts.

@section GettingOurSource Getting a copy of the Assimilation source code
There are two ways you can get a copy of the Assimilation Project source - as a tar ball
or in a <a href="http://mercurial.selenic.com/">Mercurial</a> source code repository.

You can obtain a <i>tar ball</i> of the bleeding edge source from http://hg.linux-ha.org/%7Cexperimental/assimilation/archive/tip.tar.gz
You can download it using a web browser, or <a href="www.gnu.org/software/wget/">wget</a>.

If you'd rather have an active source code repository to use to watch the development
or contribute to it, then follow these steps:
- Install Mercurial
- cd <i><some-suitable-source-directory</i>
- <tt><b>hg clone 'http://hg.linux-ha.org/%7Cexperimental/assimilation/'</b></tt>

This completes all the preparation necessary to begin building the system.

@section BuildingTheCode Building The Code
- create a <i>new-binary-directory</i> to hold the completed binaries - separate from the source tree above
- cd <i>new-binary-directory</i>
- cmake <i>pathname-of-source-directory</i>
- cpack

This should produce two packages - one named <i>assimilation-nanoprobe</i> and one named <i>assimilation-cma</i>.

If you run into difficulties, it is likely the result of missing or incorrect dependencies.
It is also possible that you're compiling for an older system - but this is likely solvable.
Please report any problems you encounter to the mailing list.

@section MakingTheDocs Making The Documentation (this web site)
To make the documentation for the project, issue this command
- make doc

This will create all the documentation on the <i>assimmon.org</i> web site.

@section InstallingTheCode Installing the Code
Every machine you wish to discover and monitor, including the CMA must have the nanoprobe
code installed on it.  The CMA code makes extensive use of the libraries created
for the nanoprobes.

@subsection InstallingTheNanoprobeCode Installing the Nanoprobe code
This is how to install the nanoprobe code on Debian-based systems:
- <tt>sudo dpkg-install assimilation-nanoprobe-<i>version-architecture</i>.deb</tt>
This is how to install the nanoprobe code on RPM-based systems
- <tt>sudo rpm --install assimilation-nanoprobe-<i>version-architecture</i>.rpm</tt>

@subsection InstallingTheCMA Installing the CMA Code
This is how to install the nanoprobe code on Debian-based systems:
- <tt>sudo dpkg-install assimilation-cma-<i>version-architecture</i>.deb</tt>
This is how to install the nanoprobe code on RPM-based systems
- <tt>sudo rpm --install assimilation-cma-<i>version-architecture</i>.rpm</tt>

If you are unable to build an RPM or DEB package, you can use <tt>sudo make install</tt>.
This installs both the nanoprobe and CMA code.


@section RunningBasicTests Running Basic Tests
These tests require that the CMA and nanoprobe are not stopped on the
current machine while they run.
The project runs these tests are run before updating the master source
control instance on <i>hg.linux-ha.org</i>.

@subsection ValgrindTest testcode/grind.sh test
This code is a pure-C test which exercises the nanoprobe code with
a simulated CMA.  It is run under valgrind to look for memory leaks
outside our object system (those are noted automatically).
There is a variety of hard-coded IP addresses used in these tests.
This can be ignored for the time being.
However, the test binds to port 1984, so it will fail if port 1984 is not available.

Various things in the glib2 library do not free all their memory at exit, so
it is possible (likely?) that you will see things not being freed that are harmless.
Nevertheless, please report them to the mailing list.

@subsection TestifyTests testify tests
There are a large number of tests performed on the Python code
including the CMA code with database.
These regression tests also significantly exercises the C code underlying the
python code, and the interfaces between the two bodies of code.
These tests bind to port 1984, so some of them will fail if port 1984 is not available.

The final line should look something like this:

PASSED.  42 tests / 15 cases: 42 passed, 0 failed.  (Total test time 16.78s)


@subsection PingerTest testcode/pinger
The pinger program exercies the reliable UDP retransmission code in the
project.  It is hard-wired to use port 19840.  Hope that works for you.
It sends a number of packets with 5% simulated packet reception loss,
and 5% simulated packet transmission loss.  This is 9.75% overall packet loss rate.


@section ConfiguringTheServices Configuring the Services
There is currently no configuration needed for these systems
under most circumstances.  If your network does not support multicast,
then you will have to invoke the nanoprobes with an argument
specifying the address of the CMA.
By default communication takes place on UDP port 1984.
If port 1984 is not available to the nanoprobes, it will bind
to an ephemeral port.  This happens every time when
starting a nanoprobe on the CMA - since the CMA has already bound
to that address.


@section ActivatingTheServices Activating The Services
As of this writing, the packages we install do not activate the services, 
so you will need to activate them manually. Sorry :-(

Keep in mind that you need to install and start all the services on the CMA,
but you will only need to install and start the nanoprobe service on all
other machines.

- Start neo4j -- <tt>service neo4j-service start</tt>

On Debian-based systems:
- <tt>/usr/sbin/update-rc.d nanoprobe defaults</tt>
- <tt>/usr/sbin/update-rc.d cma defaults</tt>
- <tt>service cma start</tt>
- <tt>service nanoprobe start</tt>

On SuSE systems
- <tt>insserv nanoprobe</tt>
- <tt>insserv cma</tt>
- <tt>service cma start</tt>
- <tt>service nanoprobe start</tt>

On RedHat systems
- <tt>chkconfig --add nanoprobe</tt>
- <tt>chkconfig --add cma</tt>
- <tt>service cma start</tt>
- <tt>service nanoprobe start</tt>

On LSB-compliant systems
- <tt>/usr/lib/lsb/install_initd nanoprobe</tt>
- <tt>/usr/lib/lsb/install_initd cma</tt>
- <tt>service cma start</tt>
- <tt>service nanoprobe start</tt>

*/
