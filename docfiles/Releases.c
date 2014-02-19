/**
@page ReleaseDescriptions Release Descriptions

@section Version0_1_1- version 0.1.1 - the 'possibly trial-worthy' release - 11 Feb 2013
This is the first in a series of releases intended to culminate in a truly useful release.
This release is suitable for limited trials in an environment where the caveats are acceptable.
You can find a few pre-built Ubuntu packages for this version here: https://www.dropbox.com/sh/h32lz3mtb8wwgmp/WZKH4OWw1h/Releases/0.1.1
A tar ball for this version can be found here: http://hg.linux-ha.org/assimilation/archive/v0.1.1.tar.gz

@subsection Features_0_1_1 Features
These features are new with release 0.1.1.
- new Neo4j schema
- service monitoring
- automatic (zero-config) service monitoring through templates
- basic fork/exec event notification feature - /usr/share/assimilation/notification.d
- hooks for more sophisticated event notification
- added Pylint analysis and verification
- added Coverity static analysis
- added root ulimit discovery
- added discovery of locally installed monitoring agents
- integration of all tests under testify
- added a Neo4j OCF resource agent
- added Flask code to support the creation of a JavaScript User Interface
- Added Query objects in support of the Flask code.
- Added the ability for for the Flask code to invoke Query objects and get results
- significant internal improvements in Neo4j access
- allow parsing of MAC addresses - they're now all in XX-YY-ZZ (etc) format.
- Added transactions for the database and the network
- removed "Monitoring" from the project name (but not from its capabilities)

@subsection BugFixes_0_1_1 Bug Fixes
- check to make sure requested discovery scripts are present before executing them
- much improved tcp service discovery
- fixed a number of 64-bit-only assumptions in the code and tests
- improved compatibility with old versions of Ubuntu
- All graph node creation now checks to see if it already exists - avoiding accumulating superfluous objects
- lots of other bugs associated with new features ;-)

@subsection Caveats_0_1_1 Caveats
- The CMA has a known slowish memory leak.  It'll still take it a long time to grow larger than a small Java program ;-)
  More importantly, it is very unlikely to happen <i>at all</i> in a production system.
- You will have to recreate your Neo4j database from scratch to convert to this release.
- Object deletion not yet reliable or complete
- No alerting, or interface to alerting (hooks to build your own interface are included)
- communication is neither authenticated nor private
- heterogeneous system support (POSIX and Windows)
- statistical data collection
- CDP support for Cisco switch discovery
- high availability option for the CMA

Features that are expected for a monitoring solution but are <b>not</b> included include these:
- useful alerting (but you can probably integrate your own)
- heterogeneous system support (POSIX and Windows)
- statistical data collection
Note that these features are understood to be important and are planned - but this first release
does not include them.

@section Version0_1_0- version 0.1.0 - the 'toy' release - 19 March 2013
The very first release of the <i>Assimilation Monitoring Project</i> - here at last!
The purpose of this Linux-only release is to get the code from this
revolutionary new architecture out there and get it in people's hands so
that they can evaluate the concepts, provide feedback, and find bugs.
It is highly recommended that you read the @ref GettingStarted documentation.
@subsection Features_0_1_0 Features
- easily extensible discovery mechanism
- Neo4J graph database documenting the data center configuration
- fully distributed, extremely lightweight, reliable monitoring
- <b>no</b> configuration needed for most environments - very simple configuration for all environments.
- basic <i>host</i> monitoring
- continuous, integrated stealth discovery of these kinds of information:
 - host network configuration - NICs, IP addresses, MAC addresses
 - host OS version information
 - basic hardware
 - ARP cache information
 - detailed information about TCP services offered (server role)
 - detailed information about TCP services consumed (client role)
 - LLDP-based server/switch topology discovery - which host NICs are connected to which switch ports
 - Tested extensively on Linux systems.
 - Source code known to compile on Windows systems (will eventually run there too).

Features that are expected for a monitoring solution but are <b>not</b> included include these:
- meaningful alerting
- service monitoring
- heterogeneous system support (POSIX and Windows)
- statistical data collection
- CDP support for switch discovery
- high availability option for the CMA

Note that these features are understood to be important and are planned - but this first release
does not include them.

@subsection BugFixes_0_1 Bug Fixes
Since this is the first release, you could consider everything a bug fix - or nothing -- take your pick.
@subsection Caveats_0_1 Caveats
This is the very first baby release of the project - nicknamed the <i>toy</i> release for a reason.
Although the code looks very stable for a release of this nature, and is unlikely to consume
vast quantities of resources or crash your machines - it has never seen real field action before -
and such results are not out of the realm of possibility for any software - much less
for software so new as this release.

It is recommended that you deploy this release on test machines until sufficient feedback has been
received to determine how it plays out in the field.

Other more mundane caveats:
- efficiency - the code is currently wildly inefficient compared to what it should be to achieve its scalability goals
  There are many known issues in this area.
- service discovery duplication
- no doubt many others which are not known, or have been forgotten about
- CMA restart might lose data from nanoprobes for discovery or system outages

*/
