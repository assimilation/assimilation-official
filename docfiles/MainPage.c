/**
@mainpage The Assimilation Monitoring Project - Incredibly scalable, Incredibly easy to configure, easy on your network.
@section intro Introduction
Welcome to the Assimilation monitoring project. (@ref README "README")

What we do: monitoring systems with near-zero overhead both on the systems and on their administrators.
- Monitor systems and services with very low overhead
- Stealth discovery&tm; (system and service)
- Easy to configure and manage

This is a new project designed to to monitor systems and services on a network of
potentially unlimited size, without significant growth in centralized resources.
The work of monitoring is delegated uniformly in tiny pieces to the various
machines being monitored in a network-aware topology - minimizing network overhead
and being naturally geographically sensitive.

The two main ideas are:
-  distribute the monitoring as broadly as possible in a network-aware fashion.
-  use autoconfiguration and stealth discovery techniques to simplify configuration
during the initial installation and during ongoing system addition and maintenance.

The original scalability idea was outlined in two different articles
 -# http://techthoughts.typepad.com/managing_computers/2010/10/big-clusters-scalable-membership-proposal.html
 -# http://techthoughts.typepad.com/managing_computers/2010/11/a-proposed-network-discovery-design-for-scalable-membership-and-monitoring.html

These two main ideas create a system which will have both a great out-of-the-box
experience for new users and smooth accommodation of growth to virtually
all environments.

@section ProgressReports Progress Reports on the project
The team currently posts updates in the following places:
- Twitter - fairly frequent from @@OSSAlanR
- linux-ha-dev mailing list - less frequent - lists.linux-ha.org/mailman/listinfo/linux-ha-dev
- Pegby work in progress list - https://www.pegby.com/board/view/assimilationproject.alanr

@section architecture Architecture
This concept has two kinds of participating entities:
 - a Centralized Monitoring Authority - monitoring the collective
 - a potentially very large number of lightweight monitoring agents (aka <i>nanoprobes</i>)

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
can take a while - this part is <i>not</i> <i>O</i>(1).

An alternative approach would be to make the rings self-organizing.  The advantage of this is
that startup after an full datacenter outage would happen much more quickly.  The disadvantage
is that this solution is much more complex, and embeds knowledge of the desired topology
(which is to some degree a policy issue) into the nanoprobes.  It also is not likely to work
as well when CDP or LLDP are not available.


@section autoconfiguration Autoconfiguration through Stealth Discovery
One of the key aspects of this system is it be largely auto-configuring,
and incorporates discovery into its basic philosophy.
It is expected that a customer will drop the various nanoprobes onto the clients being
monitored, and once those are running, the systems register themselves
and get automatically configured into the system once the nanoprobes are
installed and activated.
@subsection Stealth What is Stealth Discovery&tm;?
Stealth discovery is a process of discovering systems and services without using
active probes which might trigger security alarms.  Some examples of current
and anticipated stealth discovery techniques include:
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

Furthermore, these nanoprobes use stealth discovery methods to discover systems
not being monitored and services on the systems being monitored.
Stealth discovery methods are methods which cannot trip even the most sensitive network
security alarm - because no probes are sent over the network.

This discovery process is intended to achieve these goals:
- Simplify initial installation
- Provide a continuous audit of the monitoring configuration
- Create a rich collection of information about the data center
@image html DiscoveryMethods.png "Stealth Discovery Process"

@section lightweight Lightweight monitoring agents
The nanoprobe code is written largely in C and minimizes use of:
 - CPU
 - memory
 - disk
 - network resources

To do this, we will follow a <i>no news is good news</i> philosophy for exception monitoring -
when nothing is wrong, nothing will be reported.
Although the central part of the code will likely be only available on POSIX systems, 
the nanoprobes will also be available on various flavors of Windows as well.

@subsection service_mon Service Monitoring
To the degree possible, we will perform exception monitoring of services on the machine they're provided on - which 
implies zero network overhead to monitor working services.  Stated another way, we follow a
<i>no news is good news</i> philosophy.
Our primary tool for monitoring services is through the use of the Local Resource Manager
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
