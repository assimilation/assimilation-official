/**
@page DesignDecisions Design Decisions
@section Choice_HeartbeatCommProtocol Choice of Heartbeat Communication Protocol
I have decided to use UDP for heartbeats between nodes.
By their nature, heartbeats don't require reliable delivery, and do not require flow control
especially with our low-stress architecture.
The packets should be short (less than the MTU) and relatively infrequent (only a few received
or sent per second).
Although many of our heartbeats won't require routing, some will - so sitting on top of IP makes sense.
UDP-IP seems like the obvious choice.


@section Choice_CMA_Client_CommProtocol Choice of Client<->CMA Communication protocol
My original thoughts on the base protocol were to use a reliable protocol like RDP for the base protocol.
However, this reliability isn't sufficient to allow for reliable operation in the presence of a CMA failover.
This implies that we need application-level acknowledgements and retransmission on the protocols, to distinguish
the "the OS has received the packet" from "the CMA will not lose the data" case.

Given that this is the case, and we our application is not trying to do high-bandwidth communication - but control communication,
and we need application-level acks and retransmission, UDP is probably the best choice.

@section Choice_Heartbeat_CMA_CommPortChoices Choice of Same vs. Different Ports for CMA and Heartbeat communication
The nature of the heartbeat communication is quite different from the CMA<->client communication.
From this perspective, it initially seems like a good idea to use different ports for the different kinds of communication - so that the
two kinds of communication don't get intermingled, and thereby confused.

There are some non-simple considerations which are worth explaining which in my opinion weigh against this approach.
One of the jobs of the CMA is to disambiguate failure reports from the clients.  For any given client failure, there are at least two nodes
which one would expect to observe the failure via the heartbeat mechanism, and of course, the CMA itself can also perform a check via the 
CMA link.
Because there are three possible paths to discover the problem, it is possible to get disagreement between
the two observer clients, and/or the CMA itself.

One of the most common causes of heartbeat style failure is erroneously configured firewalls.  If one has two ports which have to be open
in order to monitor clients from the two kinds of sources, then there is more possibility for ambiguity in response due to firewall
misconfiguration - complicating the diagnosis and management.  
In addition, having multiple ports complicates adoption of the software.

As a result, I believe that both kinds of messages should go over the same UDP port.

@section NextSteps What needs to happen next
 - create python code to talk to the libraries from the CMA side
 - decide on a persistence method for packets sent to CMA - 
 - create code to send packets persistently until they're ACKed - in C or python?
 - add the capability to ACK packets that are marked as needing an ACK when they've been "acted on"
 - integrate the two capabilities above
 -

*/
