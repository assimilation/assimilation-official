/**
@mainpage The Assimilation Monitoring Project - Incredibly scalable, Incredibly easy to configure
@section intro Introduction
Welcome to the Assimilation monitoring project.

What we do: monitoring servers with near-zero overhead both on the servers and on their administrators.
- Monitor services
- Monitor services
- Low overhead
- Easy to configure and manage

This is a new project designed to to monitor servers and services on a network of potentially unlimited size,
without significant growth in centralized resources.  The work of monitoring is delegated in tiny pieces to
the various machines being monitored in a network-aware topology - minimizing the network overhead.

The general idea is to distribute the monitoring task out as broadly as possible, and in a network-aware fashion,
and to auto-configure as much as possible.
The original idea was outlined in two different articles
 -# http://techthoughts.typepad.com/managing_computers/2010/10/big-clusters-scalable-membership-proposal.html
 -# http://techthoughts.typepad.com/managing_computers/2010/11/a-proposed-network-discovery-design-for-scalable-membership-and-monitoring.html

@subsection architecture Architecture
This concept has two kinds of participating entities:
 - a Centralized Monitoring Authority - monitoring the collective
 - a potentially very large number of lightweight monitoring agents

@subsection Autoconfiguration
One of the key aspects of this system is it be largely auto-configuring, and incorporates discovery into its
basic philosophy.
It is expected that a customer will drop the various nanoprobes onto the clients being
monitored, and once those are running, the systems register themselves and get automatically
configured into the system once the nanoprobes are installed and activated.

@subsection lightweight Lightweight monitoring agents
The nanoprobe code is written largely in C and minimizes use of:
 - CPU
 - memory
 - disk
 - network resources

To do this, we will follow a <i>no news is good news</i> philosophy for exception monitoring -
when nothing is wrong, nothing will be reported.
Although the server part of the code will likely be only available on POSIX systems, 
the nanoprobes  will be available on various flavors of Windows as well.

@subsection service_mon Service Monitoring
To the degree possible, we will perform exception monitoring of services on the machine they're provided on - which 
imples zero network overhead to monitor working services.  Stated another way, we follow a
<i>no news is good news</i> philosophy.

@subsection server_mon Server Monitoring
For server monitoring, we follow a ring monitoring where each memeber of a ring sends heartbeats
to the the machine ahead of it in the ring, and the machine after it, and expects heartbeats from
each in the same fashion.
There is also a hierarchy of rings, one for the local (TOR) switch, one for the switches on a subnet, and
one connecting all subnets.  No machine would need to participate in more than two of these rings - hence
will only need to directly communicate with at most four machines - with the overwhelming majority of systems
only needing to talk to two other ring members.
This is all controlled and directed by the collective monitoring authority (CMA) -
which is designed to be configured to run in an HA cluster using a product like Pacemaker.

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
