/**
@page ClientArch Client Architecture
@section PolicyFreeClient Clients are Policy-free and Mostly Passive
Clients are mostly passive, and policy-free.  They do what the central monitoring agency tells them to do.
The only things they do on their own are:
 - Announce itself when it starts (it needs to be configured where to announce itself)
 - Gather local network configuration and send it along to the CMA initially (and when it changes?)
 - Gather LLDP or CDP information and send to the CMA when it changes
 - Eventually gather ARP cache information and send it along in the same fashion
@section BasicClientCapabilities Basic Client capabilities
 - Announce its presence when starting, and after a resume operation
 - Listen to LLDP/CDP information and send it when it changes
 - Gather local network configuration, and send it when it changes
 - listen to the CMA
 - send heartbeat packets as directed
 - listen for heartbeat packets, and compute timeouts
 - Report things back to the CMA.
 - (eventually) provide proxy services for the LRM (potentially other entities)

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

@subsection ClientArchSwitchDeath Misc Linux Notes about Nic configuration
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
Some of these things there are probably are pcap functions for... (addr and addr_len perhaps).
speed and MTU and duplex and carrier are probably not known to pcap.
*/
