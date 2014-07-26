#!/bin/sh
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
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
NEOSERVICE="neo4j-service"
NEO=/opt/neo4j
NEODATA=$NEO/data
cleanneo() {
    service $NEOSERVICE stop
    rm -fr $NEODATA/graph.db/* $NEODATA/graph.db/keystore $NEODATA/log/* $NEODATA/rrd $NEODATA/neo4j-service.pid
}

set -e
neoversion=stable
neoversion=testing
apt-get update
apt-get -y install python-pip python-flask debianutils lsof python-netaddr valgrind
#apt-get -y install openjdk-7-jre-headless
apt-get install -y --no-install-recommends openjdk-7-jdk-headless
pip install py2neo testify getent
# Import the Neo4j signing key
wget -O - http://debian.neo4j.org/neotechnology.gpg.key | apt-key add - 
# Create an Apt sources.list file
echo "deb http://debian.neo4j.org/repo ${neoversion}/" > /etc/apt/sources.list.d/neo4j.list
apt-get -y update
apt-get -y install neo4j
echo /usr/lib/*gnu-linux/assimilation > /etc/ld.so.conf.d/assimilation.conf
ldconfig /usr/lib/*linux-gnu/assimilation
service $NEOSERVICE start
cd /root/assimilation/src
testify -v cma.tests
cleanneo
cd /root/assimilation/bin
dpkg --install assimilation-cma-*-all.deb
service $NEOSERVICE start
cma --foreground # don't need to erase the database...
