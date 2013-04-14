/**
@page ReleaseDescriptions Release Descriptions

<B>DRAFT DRAFT DRAFT DRAFT DRAFT DRAFT DRAFT DRAFT DRAFT DRAFT DRAFT DRAFT DRAFT DRAFT</B>

@section Version0_1_0- version 0.1.0-RC4 - the Toy release - 17 March 2013
The very first release candidate of the <i>Assimilation Monitoring Project</i> - here at last!
The purpose of this Linux-only release is to get the code out there and get it in people's hands so
that they can evaluate the concepts, provide feedback, and find bugs.
It is highly recommended that you read the @ref GettingStarted documentation.
@subsection Features_0_1 Features
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
