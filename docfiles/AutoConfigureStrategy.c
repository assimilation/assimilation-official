/**
@page AutoConfigureStrategy Autoconfigure Strategy and Philosophy
@section AutoConfiguraOverview Autoconfigure Overview
The <i>current thinking</i> is that over time we will expend a good bit of energy discovering
things so that we can present them to the client for them to choose
whether they want to monitor the things we've discovered.

Simple/auto/self-configuration needs to be a hallmark of this project.  This and
scalability are its raison-d'etre.

The preferred method of discovery is to have the client be discover machines being
communicated with via our local agents (probes), then get these agents installed
on the newly discovered machines.

Once installed, these agents monitor the server and
discover services and so on as described below.
The admins would in turn be prompted to monitor the discovered services (or at
least services of types we know about).

Of course, some of the discovered systems will not be able to run our agents
(network switches, appliances, etc),
so we need the ability to do network-discovery of services on these machines
through port scanning, and similar techniques.

And lastly we will still need the ability to just add a service manually.

@section ClientDiscoveryStrategy Client-side automatic discovery
In the client code, we implement a @ref DiscoveryClass hierarchy to discover
local discovery.
As of this writing, the only thing we discover is Link-Level switch configuration stuff
via LLDP or CDP (using the @ref SwitchDiscoveryClass).
But we will eventually discover things like ARP cache partner IP and MAC addresses,
local services running, network ports in use, and so on.
Some like the SwitchDiscovery class tell us when things have changed.
Others will need to be polled for.
The @ref DiscoveryClass base class has provisions for both kinds of discovery
mechanisms.

@subsection DiscoveringServers Discovering Systems
There are at least two ways in which other systems can be discovered without sending out any packets.
These are:
- Examining the ARP cache
- Examining the output of netstat -ntup

@subsection DiscoveringServices Discovering Services
For UNIX systems, there is a set of directories and files which describe all the services which
are installed.  Examining these
These are:
@subsection DiscoveringServices Discovering Service Dependencies

*/
