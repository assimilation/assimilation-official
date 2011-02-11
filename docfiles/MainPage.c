/**
@mainpage The Assimilation Monitoring Project (or whatever we wind up calling it)
@section intro Introduction
Welcome to the Assimilation monitoring project.
This is a new project designed to to monitor servers and services on a network of potentially unlimited size,
without significant growth in centralized resources.  The work of monitoring is delegated in tiny pieces to
the various machines being monitored in a network-aware topology.

The general idea is to distribute the monitoring task out as broadly as possible, and in a network-aware fashion,
and to auto-configure as much as possible.
The original idea was outlined in two different articles
 -# http://techthoughts.typepad.com/managing_computers/2010/10/big-clusters-scalable-membership-proposal.html
 -# http://techthoughts.typepad.com/managing_computers/2010/11/a-proposed-network-discovery-design-for-scalable-membership-and-monitoring.html

@subsection architecture Architecture
This concept has two kinds of participating entities:
 - a Centralized Monitoring Entity
 - a potentially very large number of lightweight monitoring agents

@subsection Autoconfiguration
One of the key aspects of this system is it be largely auto-configuring - at least for host monitoring.
It is expected that a customer will drop the various client packages onto the clients being
monitored, and once those are running, the systems register themselves and get automatically
configured into the system once the client packages are installed and activated.
It will initially be necessary to configure services like web servers and so on, until autodetection
of these services is implemented.

@subsection lightweight Lightweight monitoring agents
The client code will be written largely in C and will minimize use of:
 - CPU
 - memory
 - disk
 - network resources

To do this, we will follow a <i>no news is good news</i> philosophy for exception monitoring -
when nothing is wrong, nothing will be reported.
Although the server part of the code will likely be only available on POSIX systems, 
the lightweight client portion will be available on various flavors of Windows as well.

@subsection service_mon Service Monitoring
To the degree possible, we will monitor services (exception monitoring) on the machine they're provided on - which 
imples zero network overhead to monitor working services.  Stated another way, we follow a
no news is good news philosophy.

@subsection server_mon Server Monitoring
For server monitoring, we follow a ring monitoring where each memeber of a ring sends heartbeats
to the the machine ahead of it in the ring, and the machine after it, and expects heartbeats from
each in the same fashion.
There is also a hierarchy of rings, one for the local (TOR) switch, one for the switches on a subnet, and
one connecting all subnets.  No machine would need to participate in more than two of these rings - hence
will only need to directly communicate with at most four machines - with the overwhelming majority of systems
only needing to talk to two other ring members.
This is all controlled and directed by the centralized entity - which is expected to typically be configured to run
in an HA cluster using a product like Pacemaker.

@section AutoconfigurationStrategy Autoconfiguration Strategy
@subsection Discovery System Discovery
Initially there will be no automatic discovery of new entities to monitor,
and no automatic installation of monitoring software on these machines.
It is currently planned that subsequent releases will include these capabilities.
Initial releases will provide a tool for easy packaging of client software and local configuration
so that it can be easily distributed by the system administrator.

@subsubsection DiscoveryThoughts Thoughts about Discovery
If the client monitors and captures contents of the local ARP cache and periodically announces
the appearance of new IP and/or MAC addresses, then this could be valuable to the discovery
process.
Presumably having the central server monitor DHCP address assignment could also be interesting.
I would assume that the probing of OS and so on would be performed by the central monitoring
authority.

@subsection lldp_cdp The role of LLDP and CDP in the configuration process.
In order to be as topology sensitive as we would like to be, it is necessary to know some things
about the network topology.  These include:
 - subnet connectivity - that is, which subnets is each machine on
 - switch connectivity - that is, which switch is each machine connected to

The first item is easily extracted from the local network configuration.  The second item (switch
connectivity) is more difficult.  What we want to know here is which
machines are connected to which switches.  In general, this kind of layer 2 topology information is
hidden from the hosts.  However, there are a couple of protocols which make this kind
of information available - IEEE's 801.2AB (LLDP) protocol and Cisco's - Cisco Discovery Protocol (CDP).
Both of these provide a unique identifier of which switch a server is connected to.
So, we collect this information and send it up to the central monitoring entity when it is available.

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
