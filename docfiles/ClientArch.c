/**
@page ClientArch Nanoprobe Architecture
@section PolicyFreeClient Nanoprobes are Policy-free and Mostly Passive
Nanoprobes are mostly policy-free.  They do what the central monitoring agency tells them to do.
The only things they do on their own are:
 - Announce itself and request configuration when it starts (it needs to "know" where to announce itself to)
 - Gather local network configuration and send it along to the CMA initially (and when it changes?)
 - Gather LLDP or CDP information and send to the CMA when it changes
 - Eventually gather ARP cache information and send it along in the same fashion
@section BasicClientCapabilities Basic Nanoprobe capabilities
 - Announce its presence when starting, and after a resume operation
 - listen to the CMA - and do what it says ;-)
   - send heartbeat packets as directed by the CMA
   - listen for heartbeat packets as directed by the CMA, and compute timeouts
   - Perform prescribed discovery operations
     - Listen to LLDP/CDP information and send it when it changes
     - Gather local network configuration, and send it when it changes
     - Other discovery operations as requested by the CMA
   - (eventually) provide proxy services from the CMA to the LRM
 - Report failures and changes back to the CMA.

@section NanoprobeStartupProcess Nanoprobe Startup Process
The process that the nanoprobes go through when booting/rejoining/starting up looks like this:
 -# <b>nanoprobe:</b> Submit a network discovery request from an idle task, which will poll until the discovery completes (a small fraction of a second). When the data is available, it is written into the config structure.
 -# <b>nanoprobe:</b> Send out a <b>STARTUP</b> packet once the discovery data shows up in the config structure.
 -# <b>CMA:</b> When the CMA receives this request, it sends out a <b>SETCONFIG</b> packet and a series of <b><SENDEXPECTHB</b> heartbeat packets.
 -# <b>nanoprobe:</b> When the <b>SETCONFIG</b> packet is received, it enables the sending of discovery data from all (JSON and switch (LLDP/CDP)) sources.
 -# <b>nanoprobe:</b> When the <b>SENDEXPECTHB</b> packet is receivedit starts sending heartbeats and timing heartbeats to flag "dead" machines.
 -# <b>All:</b> Now everything is running in "normal" mode.

Step 1 above will be configured to default to a multicast operation - to our <i>reserved multicast address</i>.
This address is <tt>224.0.2.5</tt> - and officially belongs to the Assimilation project.

@section ClientArchSpecialCases Some Special Cases for the client to consider
@subsection ClientArchSwitchDeath When A Switch Dies
If a client discovers that one of its peers is dead, and it has not received an ACK from the CMA
for this, then there will be a notification outstanding in a queue which will keep getting retransmitted
until it gets an ack.  If this happens, and the client hears from its peer before getting an ACK from the CMA,
then the client will remove this notification request from the queue - treating it as though an ACK had been received.

One of the ways this can happen is if a switch dies - leaving clients unable to communicate with the CMA
about dead machines.  This <i>might</i> slow down a cascade of errors...  It would be nice if the
client could tell that the link status had gone away on its own NIC (see below) - so that it could also cancel
the event and keep letting timers pop until the NIC comes back - or it starts hearing heartbeats.
In fact, it should probably cancel it until the NIC comes back.

@subsection LinuxNotesAboutNICConfiguration Misc Linux Notes about NIC configuration
This command:
<PRE>
    $ for j in address addr_len  duplex mtu speed  carrier; do printf '%%s: ' $j; cat /sys/class/net/eth0/$j; done
</PRE>
Produces this output:
<PRE>
    address: 00:1b:fc:1b:a8:73
    addr_len: 6
    duplex: full
    mtu: 1500
    speed: 100
    carrier: 1
</PRE>
There are LLDP functions for the MTU, and duplex.
Watching for carrier changes on links should eventually be a special case, since it would tell us
that we have the problem, not the other guy...
*/
