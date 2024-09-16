# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [1.99.1-pre] - Oct 30, 2020
- Testing release automation

## [1.1.7] - Jun 12, 2016 - the "From The Heart" release
### New Features
- Added two subgraph queries to assimcli
- Changed <i>drawwithdot</i> to use subgraph queries - much faster results
- Added support for Docker containers
- Added support for Vagrant VMs
- Updated to Neo4j 3.0.1
- Updated to Py2neo 2.0.8

### Bug Fixes

- Fixed an obscure bug in the fileattrs discovery script

### Caveats
- Neo4j 3.x requires Java 1.8 - this eliminates some platforms
- Not compatible with database formats before 1.1.0
- No alerting, or interface to existing alerting beyond a sample email script. (hooks to build your own interface are included)
- high availability option for the CMA is roll-your-own using Pacemaker or similar
- queries could benefit from more indexes for larger installations.
- The CMA will suffer performance problems when discovering IP addresses when large numbers of nanoprobes are on a subnet.
- no GUI
- Our current process only allows us to create 64-bit binaries. Feel free to build 32-bit binaries yourself. They still work for Ubuntu, and Debian, SuSE and 7.0 and later versions of CentOS.

## [1.1.6] - Apr 20, 2016 - the DevOpsDaysRox (Rockies) release
###  New Features
- Added several <a href="https://trello.com/c/G1DSBE6U">queries for installed packages</a>
- <a href="https://trello.com/c/s4vLO6Cv">Incorporate severities</a> into best practice score calculations.
- Added <a href="https://trello.com/c/9NxqFAGG">OUIs to some MAC queries</a>
- Added <a href="https://trello.com/c/10HLSbEP">DNS/hosts names to some IP queries</a>
- Added a <a href="https://trello.com/c/IPIE00rw">query for MAC addresses without OUIs</a>
- Added a <a href="https://trello.com/c/qeEpY0wY">query for IP addresses without DNS/hosts names</a>
- Collect file ownership, permissions for system files
- Added <a href="https://trello.com/c/py1Eo7RT">security rules for password, group and shadow file permissions.</a>
- Added an <a href="https://trello.com/c/ceIgGgZI">/etc/sudoers best practice rule</a>
- Added <a href="https://trello.com/c/K6c0Qevr">security notifications to our sample email tool.</a>
- Added <a href="https://trello.com/c/KsGkBqTz">capability to make python queries be usable the same way as pure Cypher queries.</a>
- Moved test infrastructure <a href="https://trello.com/c/oXM25X6e">from Testify to py.test</a>

### Bug Fixes
- <tt>assimcli loadqueries</tt> <a href="https://trello.com/c/cXc5wweQ">accepted bad JSON</a>
- Neo4j OCF monitoring agent now <a href="https://trello.com/c/ItD29HS0">works with Neo4j database with authentication enabled</a>.
- fixed "<a href="https://trello.com/c/tDQI98Au">Unterminated quoted string"</a> in <i>installme</i> installer
- fixed the numbering of a NIST/DISA best practice.
- worked around a bug in <i>pip list</i> where it throws an exception and causes all package discovery to get hosed (bad JSON). It now deals with the fact that pip might throw an exception, and salvages everything it can.

### Caveats
- a few options were shuffled for <i>assimcli query</i> score reporting queries.
- Not compatible with database formats before 1.1.0
- No alerting, or interface to existing alerting beyond a sample email script. (hooks to build your own interface are included)
- high availability option for the CMA is roll-your-own using Pacemaker or similar
- queries could benefit from more indexes for larger installations.
- The CMA will suffer performance problems when discovering IP addresses when large numbers of nanoprobes are on a subnet.
- no GUI
- Our current process only allows us to create 64-bit binaries. Feel free to build 32-bit binaries yourself. They still work for Ubuntu, and Debian, SuSE and 7.0 and later versions of CentOS.

## [1.1.4] - Apr 1, 2016 - the April Fools Release (not a joke)
So the joke is that it's not a joke ;-)

### New Features
- Recognize and automatically monitor Oracle
- Added new argmatch() function for returning a portion of a string matching a () regex
- Added support for IPv4-only systems (whether disabled by either known method)
- Added support for systems which create pidfile directories for us
- README updates
- Updated documentation to reflect use of GitHub instead of Mercurial (hurray!)
- Updated basic coding standards documentation
- Added yet-another-RedHat clone to the installer (and made that process easier)

### Bug Fixes
- corrected the URL to the IT Best Practices project in syslog messages

### Caveats
- Not compatible with database formats before 1.1.0
- No alerting, or interface to existing alerting beyond a sample email script.(hooks to build your own interface are included)
- high availability option for the CMA is roll-your-own using Pacemaker or similar
- queries could benefit from more indexes for larger installations.
- The CMA will suffer performance problems when discovering IP addresses when large numbers of nanoprobes are on a subnet.
- no GUI
- Our current process only allows us to create 64-bit binaries. Feel free to build 32-bit binaries yourself. They still work for Ubuntu, and probably Debian and 7.0 and later versions of CentOS.

## [1.1.3] - Feb 26, 2016 - the Leap Day Release
### New Features
- Added the drawwithdot command - draw pictures of subsets of the graph data
- We now work with (and enable) Neo4j authentication
- Improved LLDP data capture (including LLDP-MED)
- Added test code for LLDP and CDP packet handling
- Added best practice scoring system
- Added three new canned best practice score reports (queries)
- Added discovery of the contents of /etc/auditd.conf
- Added auditd.conf best practice rules
- Added new assimcli subcommand for printing scores summarized by discovery type
- Added new assimcli subcommand for printing scores summarized by discovery type and hostname
- Added new assimcli subcommand for printing scores summarized by discovery type and ruleid
  The new subcommands and queries are great for planning security/compliance triage

### Bug Fixes
- Fixed a bug in conversion of JSON floating point numbers
- Made CDP data capture work
- Made discovery code obey timeout and warntime directives
- Fixed checksum program default configuration

### Caveats
- Not compatible with database formats before 1.1.0
- **Documentation has not been updated to reflect move to github.** No doubt other shortcomings exist as well. Sorry! Please fix and generate a pull request.
- No alerting, or interface to existing alerting beyond a sample email script.(hooks to build your own interface are included)
- high availability option for the CMA is roll-your-own using Pacemaker or similar
- queries could benefit from more indexes for larger installations.
- The CMA will suffer performance problems when discovering IP addresses when large numbers of nanoprobes are on a subnet.
- no GUI
- use with recent versions of Neo4j requires disabling authentication on Neo4j
- Our current process only allows us to create 64-bit binaries. Feel free to build 32-bit binaries yourself. They still work for Ubuntu, and probably Debian and 7.0 and later versions of CentOS.

## [1.1.2] - Jan 2, 2016 - Happy 2016 Release
### New Features
- Now produce packages and installer works on openSUSE
- best practice compliance code now issues warn and unwarn events
- new code for debugging bad key id problems
- added overview documentation of cma python files
- you can now say "make tests" to run tests
- changed libsodium RPM dependency to not be so particular about the version of libsodium available
- added support for scientific and scientificfermi linux
- enabled /etc/sudoers discovery by default

### Bug Fixes
- discovery of /proc/sys now ignores I/O errors (this happens on some newer kernels)
- linux os discovery won't issue funky messages when lsb_release is not installed
- assimcli now works with a non-empty database again
- fixed sudoers command to support += operator

### Caveats
- Not compatible with database formats before 1.1.0
- Documentation has not been updated to reflect move to github. No doubt other shortcomings exist as well. Sorry! Please fix and generate a pull request.
- No alerting, or interface to existing alerting beyond a sample email script (hooks to build your own interface are included)
- high availability option for the CMA is roll-your-own using Pacemaker or similar
- queries could benefit from more indexes for larger installations.
- The CMA will suffer performance problems when discovering IP addresses when large numbers of nanoprobes are on a subnet.
- no GUI
- use with recent versions of Neo4j requires disabling authentication on Neo4j
- Our current process only allows us to create 64-bit binaries. Feel free to build 32-bit binaries yourself. They still work for Ubuntu, and probably Debian and 7.0 and later versions of CentOS.

## [1.1.1] - Nov 26, 2011 - the Thanksgiving Release
### New Features
- Added sample notification API client code - https://trello.com/c/LmBhODaa
- Added –remote option to the installer - https://trello.com/c/P2czyw9x

### Bug Fixes
- Fixed notification API filter code - https://trello.com/c/RFpMIIhP
- Fixed switch discovery - https://trello.com/c/ZJacf7EI
- Fixed installer to not remove file that doesn't exist - https://trello.com/c/5RcOfd3H

### Caveats
- Not compatible with database formats before 1.1.0
- Sudoers discovery is disabled for this release - will reappear later on
- Documentation has not been updated to reflect move to github. No doubt other shortcomings exist as well. -Sorry! Please fix and generate a pull request.
- No alerting, or interface to existing alerting - _sample code to send emails_ **is** _included_
- high availability option for the CMA is roll-your-own using Pacemaker or similar
- queries could benefit from more indexes for larger installations.
- The CMA will suffer performance problems when discovering IP addresses when large numbers of nanoprobes are on a subnet.
- no GUI
- use with recent versions of Neo4j requires disabling authentication on Neo4j
- Best practices alerts currently only come out in syslog - not as events. Sorry!
- Our current process only allows us to create 64-bit binaries. Feel free to build 32-bit binaries yourself. They still work for Ubuntu, and probably Debian and 7.0 and later versions of CentOS.
- The magic installer can't install CMAs onto Fedora due to Neo4j dependency issues.

## [1.1.0] - Nov 4, 2015 - the MCH release

**Special Note** This release cannot make use of older databases.

The workaround is to start the CMA one time with the –cleandb flag, and restart all your nanoprobes. Sorry about that.

This release is named after my Father-in-law - whose 94th birthday was 1 November 2015. Happy Birthday!

### Bug Fixes
- Installer now locks down the version of Neo4j RPMs it installs. https://trello.com/c/o2KPR0aB
- Made the code stop barfing on Neo4j beta release version numbers https://trello.com/c/eTwkkWMI
- Ensured that built releases have the right version number everywhere https://trello.com/c/cc8k892c
- Changing MAC/IP association no longer makes the CMA sick https://trello.com/c/ySlAkWJC
- README.md fixes

### New Features
- Significant performance improvement for accessing Drone (server) nodes in the database. https://trello.com/c/p19w7Jyn
- Added a best practice rule to discourage tunnelled ssh passwords.
- Verified operation against Neo4j 2.3.0 - and changed installer to favor that release. https://trello.com/c/nHUuTNUT
- Register installations via Google forms https://trello.com/c/jGsV4dt4

### Caveats
- Not compatible with previous database formats.
- Sudoers discovery is disabled for this release - will reappear later on
- Documentation has not been fully updated to reflect move to github. No doubt other shortcomings exist as well. Sorry! Please fix and generate a pull request.
- No alerting, or interface to existing alerting (hooks to build your own interface are included)
  high availability option for the CMA is roll-your-own using Pacemaker or similar
  queries could benefit from more indexes for larger installations.
- The CMA will suffer performance problems when discovering IP addresses when large numbers of nanoprobes are on a subnet.
- no GUI
- use with recent versions of Neo4j requires disabling authentication on Neo4j
- Best practices alerts currently only come out in syslog - not as events. Sorry!
- Our current process only allows us to distribute 64-bit binaries. Feel free to build 32-bit binaries yourself. They still work for Ubuntu, and probably Debian and 7.0 and later versions of CentOS.
- The magic installer can't install CMAs onto Fedora.

## [1.0.2] - Oct 8, 2015 - Pre-Columbus-day release (bug fix only)
This is a bug-fix-only release of things discovered once we got more people to install it with the easy-installer in 1.0.1.

### Bug Fixes
- Added net-tools dependency for CentOS >= 7
- Worked around brain-dead-bug in systemd
- Fixed bug around iterable Drone objects which caused some discovery to be ignored.
- Fixed broken links on the web site
- Created directories for nanoprobe pid file
- Fixed ldconfig typo in RPM packages
- Added '.' character as permissible system name
- Increased maximum system name length
- Disabled sudoers discovery to avoid periodic errors

### New Features

_none_

### Caveats
- Sudoers discovery is disabled for this release - will reappear later on
- No alerting, or interface to existing alerting (hooks to build your own interface are included)
- high availability option for the CMA is roll-your-own using Pacemaker or similar
- queries could benefit from more indexes for larger installations.
- The CMA will suffer performance problems when discovering IP addresses when large numbers of nanoprobes are on a subnet.
- no GUI
- use with recent versions of Neo4j requires disabling authentication on Neo4j
- performance with Neo4j is poor. Strangely, it's not a scalability problem. Fixes will be in a future release.
- Best practices alerts currently only come out in syslog - not as events. Sorry!
- Our current process only allows us to distribute 64-bit binaries. Feel free to build 32-bit binaries yourself. They still work for Ubuntu, and probably Debian and 7.0 and later versions of CentOS.
- The magic installer can't install CMAs onto Fedora.
