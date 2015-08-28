/**
@page CMAArch Centralized Monitoring Authority (CMA) Software Architecture

@section CMAArch_overview CMA Overview
There are a number of considerations for the CMA architecture.  The first of these is probably robustness.
It needs to be able to fail over and recover while maintaining system state, and continuing to respond
to client input <i>without losing any important messages</i>.

A simple and relatively-proven architecture for this kind of thing is to have a front end process which
reads messages bound for the CMA, and puts them in a persistent queue - using a tool similar to Qpid or Websphere MQ.
It is worth noting that Qpid doesn't solve all possible failover-type problems, but it reduces the number of
cases to take care of, and significantly reduces the probabilities of these corner cases.

This then puts the structure into two sets of components:
 - packet readers - which are queue writers
 - queue readers - which are decision makers, action takers and packet writers

This architecture allows the packet readers to be multiple instances.
It is unclear how the queue reader/packet writer job should be structured, nor how many queues there should be, and so on...

@section CMAArch_packet_readers
The CMA packet reader architecture is very simple.  It performs these functions:
- Wait for packets to arrive
- Classify packets
- Take appropriate action(s) - which depending on the classification might include:
 - Copying the packet into the queue selected by the classification stage
 - Sending an acknowledgement to the sender of the packet
 - Acting directly on the packet

In my original thoughts on this subject, I had thought that all the CMA software would be in Python.
However, it probably makes sense to do this one module in 'C' - since it is very simple, and the GSource code
is well-suited to this kind of task.  But, I haven't thought out all the details yet...

@section CMAArch_queue_readers CMA Queue reader architecture
This code is more complex than the clients, or the packet reader above.
It makes sense for this code to be in a higher-level language with garbage collection.
I currently think of this as a good thing to write in Python. Java is also a reasonable candidate language for this
task - particularly since the native interfaces for Qpid are Java interfaces.

@section CMAArch_client_messages CMA messages that a client might send
There are several kinds of messages that might be received from clients
- Hello, I'm alive - here's my basic network configuration
- I'm going away (shutdown/suspend)
- I have new/updated network configuration data for you
- I have observed a heartbeat timeout from another client
- Here is the list of nodes I expect to receive heartbeats from and their status
- Here is the list of nodes I am sending heartbeats to
- Here is an ACK for set of actions you asked me to perform.
- Here is an NACK for set of actions you asked me to perform (hopefully not!)
- Here is a collection of statistical data (future)
- Here is my current ARP table (future)

@section CMAArch_queue_actions
For the first four types of packets, the actions are pretty similar
- Decide what actions to take to update the ring structures
- Send messages to cause the actions to take place
- update a database with the information from the packet
- update a database with the information from the packet
- remove the entry from the queue

@todo Need to think more about and document what my remaining concerns for closing the failure/failover holes for the CMA are.
The possibility of a crash during this process is the one place where we need to be very careful that nothing gets lost
and that we <i>know</i> that any actions which might get repeated are harmless (idempotent).

The occurrence of a heartbeat timeout will eventually invoke a finite state machine to disambiguate the failure.
That is, if machine B is being monitored by machines A and C, then when A reports that B is down,
it is expected that machine C should soon (within two heartbeats time) make a similar report.
If it does not, then something funky is going on here and further investigation is likely in order.

When a machine is a member of a higher level ring and the machine making the report is not connected to the same switch,
then active probes are in order to see whether network components (switches or routers) might be implicated.

*/
