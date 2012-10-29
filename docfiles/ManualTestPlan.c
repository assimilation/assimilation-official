/**
@page ManualTestPlan Preliminary System Test Plan
This document represents the "current thinking" on what we ought to be testing for the next (first!) release.  It should get better.  Of course, the planned automated test system will be even better ;-).

@section ManualTestFeaturesIncluded Features Included
 - System “liveness” monitoring
 - Discovery
  - LLDP
  - Service
  - Dependency
@section ManualTestFeaturesExcluded Features Excluded (known limitations)
 - Service monitoring
 - CDP switch discovery
 - UDP peer discovery
 - Incorporating (processing) ARP, OS or CPU discovery into Neo4j beyond JSON
 - No live ARP listening
 - Pacemaker?
  - would be nice to discover (at least) resource configuration
  - what resources exist
  - which are being monitored
  - but probably not for this first release
@section ManualTestSpecifics Specific tests
 - Node joining
 - Node graceful shutdown
 - Node/nanoprobe crashing  (reboot -f / kill -9)
 - Initial discovery
  - LLDP switch port
  - OS
  - listening / connecting TCP ports
  - ARP cache
  - network configuration
   - multiple active interfaces on the same network (for example my laptop with both wired and wireless active)
   - Virtual IPs
  - Updated discovery data – some candidate examples are shown below
  - LLDP data (change switch port, or add data, for example)
  - Network data
   - activate and deactivate wireless interface
   - Add and delete network interface – USB NIC?
   - Add / delete Virtual IP
  - OS data – perform an upgrade?
  - Dependency data
   - start an application
   - stop an application
   - Migrate an application with Pacemaker
*/
