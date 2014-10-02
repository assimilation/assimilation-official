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

@section DiscoveryInformationFormat Nanoprobe discovery agent output format
Most discovery information will be represented as JSON objects.
That is, the run-of-the-mill discovery agents (plugins, whathaveyou) will produce
their discovery data in JSON in a particular format according to the type of information
being discovered.  The only exception to this rule planned at the current time
is to transmit CDP and LLDP packets in binary - to avoid putting full decoding CDP and LLDP
decoding information into the nanoprobes.
Below is sample JSON data for documenting discovered network configuration.
@code
{
  "discovertype": "netconfig",
  "description": "IP Network Configuration",
  "source": "discover_netconfig",
  "host": "paul",
  "data": {
    "eth0": {
        "address": "6c:62:6d:84:98:a3",
        "carrier": 1,
        "mtu": 1500,
        "speed": 100,
        "ipaddrs": [ {"inet": "10.10.10.16/24", "brd": "10.10.10.255", "scope": "global", "name": "eth0"}, {"inet": "10.10.10.21/32", "brd": "10.10.10.149", "scope": "global", "name": "eth0:home"}, {"inet6": "fe80::6e62:6dff:fe84:98a3/64", "scope": "link"}]
    }, 
    "eth1": {
        "address": "00:03:47:23:da:2c",
        "carrier": 1,
        "mtu": 1500,
        "speed": 1000,
        "ipaddrs": [ {"inet": "10.1.1.31/24", "brd": "10.1.1.255", "scope": "global", "name": "eth1"}, {"inet6": "fe80::203:47ff:fe23:da2c/64", "scope": "link"}]
    }, 
    "lo": {
        "address": "00:00:00:00:00:00",
        "carrier": 1,
        "mtu": 16436,
        "ipaddrs": [ {"inet": "127.0.0.1/8", "scope": "host"}, {"inet6": "::1/128", "scope": "host"}]
    }
  }
}
@endcode


@subsection DiscoveringServers Discovering Systems
There are at least two ways in which other systems can be discovered without sending out any packets.
These are:
- Examining the ARP cache
- Examining the output of netstat -ntup

@subsection DiscoveringServices Discovering Services
For UNIX systems, there is a set of directories and files which describe all the services which
are installed (for example, /etc/init.d).  In addition the netstat commands can also produce details on which services
are being provided on listening ports (netstat -utnlp).

@subsection DiscoveringServiceDependencies Discovering Service Dependencies

*/
