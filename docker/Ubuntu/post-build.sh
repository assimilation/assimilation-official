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
NEO=/opt/neo4j
NEODATA=$NEO/data
cleanneo() {
    /etc/init.d/neo4j-service stop
    rm -fr $NEODATA/graph.db/* $NEODATA/graph.db/keystore $NEODATA/log/* $NEODATA/rrd $NEODATA/neo4j-service.pid
}

set -e
neoversion=stable
neoversion=testing
apt-get -y install python-flask debianutils lsof python-gi python-netaddr python-pip valgrind
apt-get -y install openjdk-7-jre
pip install py2neo testify
# Import the Neo4j signing key
wget -O - http://debian.neo4j.org/neotechnology.gpg.key | apt-key add - 
# Create an Apt sources.list file
echo "deb http://debian.neo4j.org/repo ${neoversion}/" > /etc/apt/sources.list.d/neo4j.list
apt-get update
apt-get install neo4j
ldconfig /usr/lib/*/assimilation
neo4j start
cd /root/assimilation/src
testify -v cma.tests
cleanneo
cd /root/assimilation/bin
dpkg --install assimilation-cma-*-all.deb
neo4j start
#/usr/sbin/nanoprobe --dynamic # Don't really want this - it will clutter the database...
/usr/sbin/cma --foreground
