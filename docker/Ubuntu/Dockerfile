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
FROM ubuntu:latest
ENV TERM linux
ENV DEBIAN_FRONTEND noninteractive
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
RUN apt-get -y update
RUN apt-get -y install --no-install-recommends gcc cmake make pkg-config libglib2.0-dev resource-agents mercurial wget libpcap0.8-dev rsyslog
RUN apt-get -y install --no-install-recommends libglib2.0 libpcap0.8 python-pip
RUN apt-get -y install --no-install-recommends python-pip python-flask debianutils lsof python-netaddr valgrind python-dev
RUN apt-get install -y --no-install-recommends openjdk-7-jre
# Import the Neo4j signing key
RUN wget -O - http://debian.neo4j.org/neotechnology.gpg.key | apt-key add - 
# Create an Apt sources.list file
RUN neoversion=stable; echo "deb http://debian.neo4j.org/repo ${neoversion}/" > /etc/apt/sources.list.d/neo4j.list
RUN ls -l /etc/apt/sources.list.d && cat /etc/apt/sources.list.d/neo4j.list
RUN apt-get -y update
RUN apt-get -y install --no-install-recommends neo4j
# Just so we have some services to monitor...
RUN apt-get -y install --no-install-recommends bind9 host
# For debugging...
RUN apt-get -y install --no-install-recommends strace gdb
RUN pip install ctypesgen 'py2neo<2.0' testify getent
#libsodium
RUN cd /root && mkdir -p assimilation/bin/buildtools assimilation/bin/libsodium && cd /root/assimilation/bin/libsodium
ADD http://hg.linux-ha.org/assimilation/raw-file/tip/buildtools/libsodium.mkdeb.sh /root/assimilation/bin/buildtools/
RUN cd /root/assimilation/bin/libsodium && pwd  && ls -l ../.. >&2 && bash ../buildtools/libsodium.mkdeb.sh &&  dpkg --install *.deb && echo Installed *.deb
RUN mkdir -p /usr/share/assimilation/crypto.d
ADD #CMA#00001.pub /usr/share/assimilation/crypto.d/
ADD #CMA#00001.secret /usr/share/assimilation/crypto.d/
#
#   Assimilation Source
#
#RUN cd /root && hg clone -r @VERSION@ http://hg.linux-ha.org/assimilation assimilation/src
ADD http://hg.linux-ha.org/assimilation/archive/tip.tar.gz /root/assimilation/
RUN cd /root/assimilation/ && tar xvzf tip.tar.gz && mv Assimilation-* src
RUN cd /root/assimilation/bin; cmake ../src && make install
RUN cd /root/assimilation/bin; cpack
RUN cd /root/assimilation/bin; dpkg --install assimilation-nanoprobe-*-*.deb
RUN chown assimilation -R /usr/share/assimilation/crypto.d/ && chmod 600 /usr/share/assimilation/crypto.d/#CMA#00001.*
RUN PARENT=$(/sbin/route | grep '^default' | cut -c17-32); PARENT=$(echo $PARENT); echo '*.*   @@'"${PARENT}:514" > /etc/rsyslog.d/99-remote.conf
RUN echo '@TIMEZONE@' | tee /etc/timezone; dpkg-reconfigure --frontend noninteractive tzdata
EXPOSE 1984

RUN echo /usr/lib/*linux-gnu/assimilation > /etc/ld.so.conf.d/assimilation.conf
RUN ldconfig /usr/lib/*linux-gnu/assimilation
#RUN service rsyslog start && service neo4j-service start  && cd /root/assimilation/src && testify -v cma.tests && service rsyslog stop
RUN cd /root/assimilation/bin && dpkg --install assimilation-cma-*-all.deb
RUN rm -fr /opt/neo4j/data/graph.db/* /opt/neo4j/data/graph.db/keystore /opt/neo4j/data/log/* /opt/neo4j/data/rrd /opt/neo4j/data/neo4j-service.pid
RUN service neo4j-service start && service neo4j-service stop # To make a lovely empty database...
