/**
@mainpage Incredibly easy to configure, easy on your network, incredibly scalable.
@section overview Overview
Welcome to the Assimilation project. (@ref README "README") @htmlonly<a href="https://scan.coverity.com/projects/9"><img alt="Coverity Status" src="https://scan.coverity.com/projects/9/badge.svg"></a>@endhtmlonly - proudly sponsored by <a href="http://assimilationsystems.com">Assimilation Systems Limited</a>.

We provide open source discovery with zero network footprint integrated with <i>highly</i>-scalable monitoring.
Here are the problems we address:
- Organizations are vulnerable to attack through forgotten or unknown systems (30% of all intrusions)
- Organizations have no automatic infrastructure discovery, or they run it infrequently
 - => System configuration information is out of date, or only in people's heads
- System discovery is not integrated with monitoring
 - Most organizations have no way of <i>knowing</i> they're monitoring everything - and probably aren't
 - Most monitoring is time-consuming to configure, incomplete, out-of-date, easily confused
- Monitoring is complex and expensive to scale.

What we do: Continually discover and monitor systems, services, switches and dependencies with very low human and network overhead
- Discover systems, services, switches and dependencies using zero network footprint techniques
- Monitor systems and services with very low overhead and extreme scalability
- Make montoring easy to configure and manage
@section intro Introduction

The Assimilation Project is designed to discover and monitor infrastructure, services, and dependencies on a network of
potentially unlimited size, without significant growth in centralized resources.
The work of discovery and monitoring is delegated uniformly in tiny pieces to the various
machines in a network-aware topology - minimizing network overhead and being naturally geographically sensitive.

The two main ideas are:
- distribute discovery throughout the network, doing most discovery locally
- distribute the monitoring as broadly as possible in a network-aware fashion.
- use autoconfiguration and zero-network-footprint discovery techniques to monitor most resources automatically.
during the initial installation and during ongoing system addition and maintenance.

The original monitoring scalability idea was outlined in two different articles
 -# http://techthoughts.typepad.com/managing_computers/2010/10/big-clusters-scalable-membership-proposal.html
 -# http://techthoughts.typepad.com/managing_computers/2010/11/a-proposed-network-discovery-design-for-scalable-membership-and-monitoring.html

These two main ideas create a system which will provide significant important capabilities giving both a great out-of-the-box
experience for new users and smooth accommodation of growth to virtually all environments.

For a human-driven overview, we recommend our
<a href="http://assimilationsystems.com/category/videos/">videos</a> from interviews and conference presentations.

We also have a few <a href="http://assimilationsystems.com/category/demos/">demos</a>, which demonstrate the ease of use and power of the Assimilation software.

@section ProjectSponsors Project Sponsors
<a href="http://assimilationsystems.com">Assimilation Systems Limited </a> was founded by project founder Alan Robertson
to provide paid support and alternative licenses for the Assimilation Project.
@section ProjectIntegrity Project Integrity
The project software undergoes a number of rigorous static and dynamic tests to ensure its continued integrity.
- Highly restrictive gcc options in all compiles - no warnings allowed (<b>-Werror</b>)
- Static Analysis via the <a href="http://clang-analyzer.llvm.org/">Clang</a> static analyzer - zero warnings allowed before changes are pushed to public repository
- Static Analysis by Coverity before each release candidate (and other times)@htmlonly<a href="https://scan.coverity.com/projects/9"><img alt="Coverity Status" src="https://scan.coverity.com/projects/9/badge.svg"></a>@endhtmlonly
- Four collections of regression tests - successful run required before any changes are pushed to public repository
- <a href="http://www.pylint.org/">pylint</a> Python code checker - enforces Python coding standards and performs static error checks

@section ProgressReports Progress Reports on the project
The team currently posts updates in the following places:

- \#assimilation channel on freenode IRC
- [<a href="https://plus.google.com/+AssimprojOrg/posts" rel="publisher">Google+</a>] page for the Assimilation Project.
- Twitter - fairly frequent from <a href="https://twitter.com/#!/@OSSAlanR">@@OSSAlanR</a> - using hash tag <A HREF="https://twitter.com/#!/search/realtime/%23AssimMon">\#AssimMon</A>
- <a href="http://assimilationsystems.com/category/blog/">Assimilation Systems Blog</a> - about weekly
- Older <a href="http://techthoughts.typepad.com/managing_computers/">Managing Computers with Automation Blog</a>
- <a href="http://lists.community.tummy.com/cgi-bin/mailman/listinfo/assimilation">Assimilation Mailing List</a> - not quite as often - shooting for weekly.
- Assimilation <a href="http://trello.com">Trello</a> project management boards.  These give a very good overview of the project goals, current and future work items along with <b>open project roles</b>.  Come find your future here!
 - <a href="https://trello.com/b/KKs4rI8g/assimilation-user-stories">Assimilation user stories</a>.
 - <a href="https://trello.com/b/98QrdEK1/issues-bugs">Assimilation bugs / issues / proposed features</a>.
 - <a href="https://trello.com/b/OpaED3AT">Assimilation brain dump</a>.
- <a href="http://lists.linux-ha.org/mailman/listinfo/linux-ha-dev">linux-ha-dev mailing list</a> - parent project

@section ExternalLinks External Links
- <a href="https://www.ohloh.net/p/assimmon">Ohloh entry for the Assimilation Project</a>.
- <a href="http://searchdatacenter.techtarget.com/news/2240161696/Assimilation-Monitoring-Project-hopes-to-ease-monitoring-sucks-woes">Assimilation Interview - Fall 2012</a>.
- <a href="http://searchdatacenter.techtarget.com/news/2240182002/Open-source-monitoring-software-ready-for-final-release">Assimilation Interview - April 2013</a>.
- LinuxCon 2012 <a href="https://speakerdeck.com/ossalanr/how-to-assimilate-a-million-servers-without-getting-indigestion-linuxcon-na-2012">slides</a>, <a href="http://bit.ly/AssimMonVid">video</a>.
- <a href="http://techthoughts.typepad.com/managing_computers/2012/07/fullsys.png">A picture of what our graphs look like</a>.
- Blog articles on our Neo4j schema:
 - <a href="http://techthoughts.typepad.com/managing_computers/2012/07/assimilation-ring-neo4j-schema.html">Monitoring rings</a>
 - <a href="http://techthoughts.typepad.com/managing_computers/2012/07/discovering-switches-its-amazing-what-you-can-learn-just-by-listening.html">Switch discovery</a>
 - <a href="http://techthoughts.typepad.com/managing_computers/2012/07/clients-servers-and-dependencies-oh-my.html">Service Dependencies</a>
 - <a href="http://techthoughts.typepad.com/managing_computers/2012/08/an-assimilation-type-schema-in-neo4j.html">Type schema</a>
 - <a href="http://freecode.com/projects/assimilation-monitoring-project">Project page on Freecode</a>

@section architecture Architecture
This concept has two kinds of participating entities:
 - a Centralized Management Authority - monitoring the collective, and collecting discovery information
 - a potentially very large number of lightweight monitoring/discovery agents (aka <i>nanoprobes</i>)

@section Scalability Scalable Monitoring
The picture below shows the architecture for discovering system outages.
@image html MultiRingHeartbeat.png "Multi-Ring Heartbeating Architecture"
Each of the blue boxes represents a server.  Each of the connecting arcs represent bidirectional heartbeat paths.
When a failure occurs, the systems which observe it report directly to the central collective management
authority (not shown on this diagram).
Several things are notable about this kind of heartbeat architecture:
- It has no single points of failure.  Each system is monitored by at least two other systems.
- It is simple to detect the difference between a switch failure and a host failure by which systems
report the failure, and which ones do not.
- Each system talks to no more than 4 systems - no matter how big the collection being monitored.
Since the central system only hears from the monitored systems when a failure occurs, the work to perform
monitoring of systems does not go up as the number of systems being monitored goes up.
- Approximately 96% of all monitoring traffic stays within edge switches.
- This architecture is naturally geographically sensitive.
Very little traffic goes between sites to monitor multiple sites from a central location.
- This architecture is simple and easy to understand.

This is all controlled and directed by the collective monitoring authority (CMA) -
which is designed to be configured to run in an HA cluster using a product like Pacemaker.
The disadvantage of this approach is the getting started after a complete data center outage/shutdown
can take a while - this part is <i>not</i> <i><b>O</b></i>(1).

An alternative approach would be to make the rings self-organizing.  The advantage of this is
that startup after an full datacenter outage would happen much more quickly.  The disadvantage
is that this solution is much more complex, and embeds knowledge of the desired topology
(which is to some degree a policy issue) into the nanoprobes.  It also is not likely to work
as well when CDP or LLDP are not available, and to properly diagnose complex faults, it is necessary
to know the order nodes are placed on rings.


@section autoconfiguration Autoconfiguration through Discovery
One of the key aspects of this system is it be largely auto-configuring,
and incorporates discovery into its basic philosophy.
It is expected that a customer will drop the various nanoprobes onto the clients being
monitored, and once those are running, the systems register themselves
and get automatically configured into the system once the nanoprobes are
installed and activated.
@subsection ZeroNetworkFootprint What is Zero Network Footprint Discovery&tm;?
Zero-network-footprint discovery is a process of discovering systems and services without sendign
active probes across the network which might trigger security alarms.  Some examples of current
and anticipated zero-network-footprint discovery techniques include:
 - Discovery of newly installed systems by auto-registration
 - Discovery of network topology using LLDP and CDP aggregation
 - Discovery of services using netstat -utnlp
 - Discovery of services using "service" command and related techniques
 - Discovery of systems using arp -n
 - Discovery of systems using netstat -utnp
 - Discovery of service interdependencies using netstat -utnp
 - Discovery of network filesystem mount dependencies using the mount table

These techniques will not immediately provide a complete list of all systems
in the environment.  However as nanoprobes are activated on systems discovered
in this way, this process will converge to include the complete set of systems
and edge switches in the environment - without setting off even the most
sensitive security alarms.

In addition, the netstat information correlated across the servers also
provides information about dependencies and service groups.

Furthermore, these nanoprobes use zero-network-footprint discovery methods to discover systems
not being monitored and services on the systems being monitored.
Zero-network-footprint discovery methods are methods which cannot trip even the most sensitive network
security alarm - because no probes (packets) are sent over the network to perform discovery.

This discovery process is intended to achieve these goals:
- Simplify initial installation
- Provide a continuous audit of the monitoring configuration
- Create a rich collection of information about the data center
@image html DiscoveryMethods.png "Zero-Network-Footprint Discovery Process"

@section lightweight Lightweight monitoring agents
The nanoprobe code is written largely in C and minimizes use of:
 - CPU
 - memory
 - disk
 - network resources

To do this, we will follow a <i>management by exception</i> philosophy for exception monitoring -
when nothing is wrong, nothing will be reported.
Although the central part of the code will likely be only available on POSIX systems, 
the nanoprobes will also be available on various flavors of Windows as well.

@subsection service_mon Service Monitoring
To the degree possible, we will perform exception monitoring of services on the machine they're provided on - which 
implies zero network overhead to monitor working services.  Stated another way, we follow a
<i>management by exception</i> philosophy.
Our primary tool for monitoring services is through the use of a re-implemented Local Resource Manager
from the Linux-HA project.

@section TestingStrategy Testing Strategy
There are three kinds of testing I see as necessary
- junit/pyunit et al level of testing for the python code
- Testing for the C nanoprobes in situ
- System level (simulated) testing for the CMA
Each of these areas is discussed below.

@subsection UnitTesting Unit-level testing
We are currently using the Testify software written by the folks at Yelp.
Probably will try some of the alternatives as well.
Very pleased with the results it's bringing.
The nice thing about this is much of the detailed gnarly C code is wrapped
by the python code, so when I run the python tests of those wrappers, the
C code under it gets well tested as well.

@subsection NanobotTesting Testing of the Nanoprobes
Not quite sure how to best accomplish this.  Some of it can just
be my home network, but I suppose I could also spin up some cloud
VMs too...  Not sure yet...  Automation is a GoodThing.

@subsection CMATesting Testing of the Collective Management Code
I have been thinking about this quite a bit, and have what I think is a
reasonable idea about it.  It involves writing a simulator
to simulate up to hundreds of thousands of nanoprobe clients through
a separate python process - probably using the Twisted framework.
It would accept and ACK requests from the CMA and randomly create failure
conditions similar to those in the "real world" - except at a
radically faster rate.  This is a big investment, but likely
worth it.  It helps to have this in mind while designing
the CMA as well - since there are things that it could do to
make this job a little easier.


*/

/** @defgroup DefineEnums #define enumerations
 *  @{ 
 *  @} 
 */


/** @defgroup todos_project Project-wide (global) todos
 *  @{ 
 *  @} 
 */

/**  @defgroup todos_staffing Staffing - People to look for 
 *  @{ 
 *  @ingroup todos_project
 *  @todo Find someone interested in structuring the testing effort - <b>automated testing is an absolute necessity</b>.
 *
 *  @todo Find people interested in doing test deployments - making good progress on that - but always looking for more.
 *  @} 
 *
 *  @defgroup todos_near_term Nearer term TODOs
 *  @{ 
 *  @ingroup todos_project
 *
 *  @todo Think about how to implement packet injection so we can test without a network...
 *  Only need to do it for the LLDP/PCAP layer and the UDP layer.
 *  For UDP also need to dummy up transmitting packets...
 *
 *  @todo Decide how to structure/document system differences for portability
 *
 *  @todo Write code to encapsulate libpcap packets along with the header info etc - similar
 *   to what would be needed to create a pcap file from it / or maybe the exact pcap file format image?
 *
 *  @todo What should we do about logging? - glib logging?
 *
 *  Carefully check the heartbeat IPC GSource code to make sure we understand how to respond to
 *  back-pressure and resume transmitting after the flow control is removed.
 *  @} 
 *
 * @defgroup todos_research Farther out TODOs - things needing research
 *  @{ 
 *  @ingroup todos_project
 *  @todo Think more about server architecture
 *
 *  @todo What tool set to use on Windows? - do winpcap or glib have constraints? - Roger is looking into that...
 *
 *  @todo "portable" methods of grabbing the local ARP cache (for discovery)
 *
 *  @todo windows-specific methods of grabbing the local ARP cache (for discovery) - <i>arp -a</i> would work but it's kinda ugly...
 *  @} 
 */
