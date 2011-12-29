/**
@mainpage The Assimilation Monitoring Project - Incredibly scalable, Incredibly easy to configure, easy on your network.
@section intro Introduction
Welcome to the Assimilation monitoring project.

What we do: monitoring systems with near-zero overhead both on the systems and on their administrators.
- Monitor systems and services with very low overhead
- Stealth discovery (system and service)
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

@subsection ProgressReports Progress Reports on the project
The team currently posts updates in the following places:
- Twitter - fairly frequent from @@OSSAlanR
- linux-ha-dev mailing list - less frequent - lists.linux-ha.org/mailman/listinfo/linux-ha-dev
@subsection architecture Architecture
This concept has two kinds of participating entities:
 - a Centralized Monitoring Authority - monitoring the collective
 - a potentially very large number of lightweight monitoring agents

@subsection Autoconfiguration
One of the key aspects of this system is it be largely auto-configuring,
and incorporates discovery into its basic philosophy.
It is expected that a customer will drop the various nanoprobes onto the clients being
monitored, and once those are running, the systems register themselves
and get automatically configured into the system once the nanoprobes are
installed and activated.

Furthermore, these nanoprobes use stealth discovery methods to discover systems
not being monitored and services on the systems being monitored.

@subsection lightweight Lightweight monitoring agents
The nanoprobe code is written largely in C and minimizes use of:
 - CPU
 - memory
 - disk
 - network resources

To do this, we will follow a <i>no news is good news</i> philosophy for exception monitoring -
when nothing is wrong, nothing will be reported.
Although the central part of the code will likely be only available on POSIX systems, 
the nanoprobes are expected to be available on various flavors of Windows as well.

@subsection Stealth What is Stealth Discovery?
Stealth discovery is a process of discovering systems and services without using
active probes which might trigger security alarms.  Some examples of current
and anticipated stealth discovery techniques include:
 - Discovery of newly installed systems by auto-registration
 - Discovery of network topology using LLDP and CDP aggregation
 - Discovery of services using netstat -utnlp
 - Discovery of services using "service" command and related techniques
 - Discovery of systems using arp -n
 - Discovery of systems using netstat -tnp

These techniques will not immediately provide a complete list of all systems
in the environment.  However as nanoprobes are activated on systems discovered
in this way, this process will converge to include the complete set of systems
and edge switches in the environment - without setting off even the most
sensitive security alarms.

@subsection service_mon Service Monitoring
To the degree possible, we will perform exception monitoring of services on the machine they're provided on - which 
imples zero network overhead to monitor working services.  Stated another way, we follow a
<i>no news is good news</i> philosophy.

@subsection server_mon System Monitoring
For system monitoring, we follow a ring monitoring where each member of a ring sends
heartbeats to the the machine ahead of it in the ring, and the machine after it,
and expects heartbeats from each in the same fashion.
There is also a hierarchy of rings, one for the local (edge or top of rack) switch,
one for the switches on a subnet, and one connecting all subnets.
No machine would need to participate in more than two of these rings -
hence will only need to directly communicate with at most four machines -
with the overwhelming majority of systems only needing to talk to two other
ring members.
This is all controlled and directed by the collective monitoring authority (CMA) -
which is designed to be configured to run in an HA cluster using a product like Pacemaker.

@section TestingStrategy Testing Strategy
There are three kinds of testing I see as necessary
- junit/pyunit et al level of testing for the python code
- Testing for the C nanobots in situ
- System level (simulated) testing for the CMA
Each of these areas is discussed below.

@subsection PyunitTesting Unit-level testing
We are currently using the Testify software written by the folks at Yelp.
Probably will try some of the alternatives as well.
Very pleased with the results it's bringing.
The nice thing about this is much of the detailed gnarly C code is wrapped
by the python code, so when I run the python tests of those wrappers, the
C code under it gets well tested as well.

@subsection NanobotTesting Testing of the Nanobots
Not quite sure how to best accomplish this.  Some of it can just
be my home network, but I suppose I could also spin up some cloud
VMs too...  Not sure yet...  Automation is a GoodThing(TM).

@subsection CMATesting Testing of the Collective Management Code
I have been thinking about this quite a bit, and have what I think is a
reasonable idea about it.  It involves writing a simulator
to simulate up to hundreds of thousands of nanobot clients through
a separate python process - probably using the Twisted framework.
It would accept and ACK requests from the CMA and randomly create failure
conditions similar to those in the "real world" - except at a
radically faster rate.  This is a big investment, but likely
worth it.  It helps to have this in mind while designing
the CMA as well - since there are things that it could do to
make this job a little easier.


@section AutoconfigurationStrategy Autoconfiguration Strategy
For details on this, see the separate
@ref AutoConfigureStrategy "Autoconfiguration Strategy and Philosophy" page.  


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
 *  @todo Find someone to do the Windows port
 *
 *  @todo Find someone interested in structuring the testing effort - <b>automated testing is an absolute necessity</b>.
 *
 *  @todo Find people interested in doing test deployments
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
 *  @todo implement the frameset/frame abstraction.
 *
 *  @todo implement a UDP GSource which connects to the frameset abstraction, and also supports packet transmission...
 *  Carefully check the heartbeat IPC GSource code to make sure we understand how to respond to
 *  back-pressure and resume transmitting after the flow control is removed.
 *  @} 
 *
 * @defgroup todos_research Farther out TODOs - things needing research
 *  @{ 
 *  @ingroup todos_project
 *  @todo Think more about server architecture
 *
 *  @todo What tool set to use on Windows? - do winpcap or glib have constraints?
 *
 *  @todo "portable" methods of grabbing the local ARP cache (for discovery)
 *
 *  @todo windows-specific methods of grabbing the local ARP cache (for discovery) - <i>arp -a</i> would work but it's kinda ugly...
 *  @} 
 */
