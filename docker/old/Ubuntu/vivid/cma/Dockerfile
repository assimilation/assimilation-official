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
FROM assimilation/nanoprobe-vivid:latest
MAINTAINER Alan Robertson <alanr@assimilationsystems.com>
ENV TERM linux
ENV DEBIAN_FRONTEND noninteractive
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
RUN apt-get -y update
RUN apt-get -y install --no-install-recommends wget python-pip python-flask lsof python-netaddr
RUN pip install 'py2neo==2.0.8' getent

###############################################################
#   Neo4j installation
###############################################################
# Skip java ppa repo setup for vivid
RUN apt-get install -y --no-install-recommends openjdk-8-jre
# Import the Neo4j signing key
RUN wget -O - http://debian.neo4j.org/neotechnology.gpg.key | apt-key add - 
# Create an Apt sources.list file for neo4j.
RUN neoversion=stable; echo "deb http://debian.neo4j.org/repo ${neoversion}/" > /etc/apt/sources.list.d/neo4j.list
RUN apt-get -y update
RUN apt-get -y install --no-install-recommends neo4j
#
RUN mkdir -p /tmp/pkgs
COPY assimilation-cma-1.1.7.1465707477-all.deb /tmp/pkgs/
COPY cmaStart /usr/bin/
RUN chmod 755 /usr/bin/cmaStart
#   Install Assimilation CMA package
RUN dpkg --install /tmp/pkgs/assimilation-cma-1.1.7.1465707477-all.deb
RUN rm -fr /tmp/pkgs/
#   Set up Assimilation encryption keys
RUN mkdir -p /usr/share/assimilation/crypto.d  /tmp/cores # putting --mode 0700 on mkdir screws up security attributes
RUN chown assimilation -R /usr/share/assimilation/crypto.d/ && chmod 0700 /usr/share/assimilation/crypto.d && /usr/sbin/assimcli genkeys
ENTRYPOINT ["/usr/bin/cmaStart"]
