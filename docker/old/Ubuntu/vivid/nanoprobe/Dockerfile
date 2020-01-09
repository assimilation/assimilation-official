# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# Dockerfile to create a usable nanoprobe-only docker instance
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
FROM ubuntu:vivid
MAINTAINER Alan Robertson <alanr@assimilationsystems.com>
ENV TERM linux
ENV DEBIAN_FRONTEND noninteractive
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
WORKDIR /root
RUN apt-get update && apt-get install -y --no-install-recommends libpcap0.8 libglib2.0-0 rsyslog resource-agents lsb-release iproute2
RUN mkdir /tmp/pkgs
COPY assimilation-nanoprobe-1.1.7.1465707477-amd64.deb /tmp/pkgs/
COPY libsodium_1.0.10-1_amd64.deb /tmp/pkgs/
RUN dpkg --install /tmp/pkgs/*.deb
RUN rm -fr /tmp/pkgs/
# Make sure library dependencies are met
RUN /usr/sbin/nanoprobe && sleep 2 && /usr/sbin/nanoprobe -k
