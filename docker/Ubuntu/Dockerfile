# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# Dockerfile to build Libsodium and Assimilation packages
#   All the packages we create are conveniently copied to /root/assimilation/packages
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2014 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community - http://assimproj.org
# Paid support is available from Assimilation Systems Limited - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
######################################################
#   Install required base packages
######################################################
FROM ubuntu:latest
MAINTAINER Alan Robertson <alanr@assimilationsystems.com>
ENV TERM linux
ENV DEBIAN_FRONTEND noninteractive
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
RUN apt-get -y update && apt-get -y install --no-install-recommends gcc cmake make pkg-config libglib2.0-dev resource-agents wget libpcap0.8-dev rsyslog 
RUN apt-get -y install --no-install-recommends python-pip python-flask debianutils lsof python-netaddr valgrind python-dev lsb-release
RUN apt-get -y install --no-install-recommends bind9 host           # So we have some services to monitor in system testing
RUN apt-get -y install --no-install-recommends strace gdb tcpdump   # For debugging...
RUN pip install ctypesgen 'py2neo<2.0' getent

###############################################################
#   Neo4j installation
###############################################################
RUN apt-get -y install --no-install-recommends openjdk-7-jre
# Import the Neo4j signing key
RUN wget -O - http://debian.neo4j.org/neotechnology.gpg.key | apt-key add - 
# Create an Apt sources.list file for neo4j.
RUN neoversion=stable; echo "deb http://debian.neo4j.org/repo ${neoversion}/" > /etc/apt/sources.list.d/neo4j.list
#RUN ls -l /etc/apt/sources.list.d && cat /etc/apt/sources.list.d/neo4j.list
RUN apt-get update && apt-get -y install --no-install-recommends neo4j
#

###############################################################
#   Create libsodium packages
###############################################################
RUN cd /root && mkdir -p assimilation/bin/buildtools assimilation/bin/libsodium assimilation/packages
#   Import our script for building libsodium...
ADD http://hg.linux-ha.org/assimilation/raw-file/tip/buildtools/libsodium.mkdeb.sh /root/assimilation/bin/buildtools/
RUN cd /root/assimilation/bin/libsodium && bash ../buildtools/libsodium.mkdeb.sh &&  dpkg --install *.deb && cp *.deb /root/assimilation/packages

###############################################################
#   Build and install Packages from Assimilation Source
###############################################################
ADD http://hg.linux-ha.org/assimilation/archive/tip.tar.gz /root/assimilation/
RUN cd /root/assimilation/ && tar xzf tip.tar.gz && mv Assimilation-* src
RUN cd /root/assimilation/bin; cmake ../src && make install && cpack
#   Set up Assimilation encryption keys
RUN mkdir -p /usr/share/assimilation/crypto.d  /tmp/cores # putting --mode 0700 on mkdir screws up security attributes (don't do it!)
RUN chown assimilation -R /usr/share/assimilation/crypto.d/ && chmod 0700 /usr/share/assimilation/crypto.d && /usr/sbin/assimcli genkeys && chmod a+w /tmp/cores
#   Set up syslog to log to host
RUN PARENT=$(/sbin/route | grep '^default' | cut -c17-32); PARENT=$(echo $PARENT); echo '*.*   @@'"${PARENT}:514" > /etc/rsyslog.d/99-remote.conf
#   Install Assimilation packages
RUN lsb_release -a
RUN cd /root/assimilation/bin && dpkg --install assimilation-*.deb && cp assimilation-*.deb /root/assimilation/packages
###############################################################
#   Run Assimilation unit tests
###############################################################
RUN apt-get -y install --no-install-recommends jq || true
RUN pip install testify
RUN /usr/sbin/rsyslogd&  service neo4j-service start; sleep 5; cd /root/assimilation/src && testify -v cma.tests

###############################################################
#   Clean out the database and prepare for running system tests
###############################################################
RUN rm -fr /opt/neo4j/data/graph.db/* /opt/neo4j/data/graph.db/keystore /opt/neo4j/data/log/* /opt/neo4j/data/rrd /opt/neo4j/data/neo4j-service.pid
RUN service neo4j-service start && service neo4j-service stop # Make a lovely empty database...
# Install be a copy of host's /etc/timezone - so logs will have right TZ
COPY timezone /etc/
RUN dpkg-reconfigure --frontend noninteractive tzdata
