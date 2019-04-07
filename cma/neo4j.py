#!/usr/bin/env python
# coding=utf-8
#
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2019 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community
#   - http://assimproj.org
#
# The Assimilation software is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.
# If not, see http://www.gnu.org/licenses/
#
# Here are my thoughts about Neo4j"
#
#   - we should run it in a container, not natively...
#   - we need to export most of the volumes they define to the host
#
#
#
#
from __future__ import print_function
import os
import sys
from sys import stderr
import docker
import docker.errors
import time


class NeoServer(object):
    """
    Abstract Neo4j server class
    """
    neo_volumes = {
        '/conf': 'ro',
        '/data': 'rw',
        '/import': 'ro',
        '/logs':  'rw',
        '/metrics': 'rw',
        '/plugins': 'ro',
        '/ssl': 'ro',
    }

    neo_ports = {
        'http':  7474,
        'https': 7473,
        'bolt':  7687
    }

    def start(self):
        """Abstract method to start a server"""
        raise NotImplementedError('Abstract method start')

    def stop(self):
        """Abstract method to stop a server"""
        raise NotImplementedError('Abstract method stop')

    def set_initial_password(self, initial_password):
        """Abstract method to supply the initial password"""
        raise NotImplementedError('Abstract method set_initial_password')

    @staticmethod
    def debug_msg(*args):
        """

        :param args:
        :return:
        """
        print(args)


class NeoDockerServer(NeoServer):
    """
    Neo4j in Docker
    """
    edition_map = {
        'community':    '',
        'enterprise':   '-enterprise'
    }
    good_versions = {'3'}

    def __init__(self, edition='community',
                 version='latest',
                 host='assim_neo4j',
                 exposed_ports=None,
                 environment_map=None,
                 accept_license=False,
                 root_directory='/var/lib/assimilation/neo4j',
                 log_directory='/var/log/assim_neo4j',
                 docker_client=None,
                 debug=False):
        """

        :param edition:str: Which Neo4j edition?
        :param version:str: Which Neo4j version?
        :param host:str: host name / container name for this container
        :param exposed_ports: [str]: List of port names you want exposed
        :param environment_map:{str:str}: Environment variables to pass
        :param accept_license:bool: True if you accept the enterprise license
        :param root_directory:str: Root of where to put everything except log files
        :param log_directory:str: Root of where to store log files
        :param debug:bool: True to get debug messages (if any)
        """
        NeoServer.__init__(self)
        self.edition = edition
        self.version = version
        self.debug = debug
        self.environment_map = environment_map if environment_map else {}
        if exposed_ports is None:
            exposed_ports = {'bolt': None, 'http': None}

        self.version_info = version.split('.')
        if version != 'latest':
            assert self.version_info[0] in self.good_versions
        self.image_name = 'neo4j'

        edition_suffix = self.edition_map[edition]
        if edition == 'enterprise' and version == 'latest':
            self.image_name += ':' + edition
        else:
            if edition_suffix:
                self.image_name += ':' + version + edition_suffix
        if edition == 'enterprise':
            self.environment_map['NEO4J_ACCEPT_LICENSE_AGREEMENT'] = (
                'yes' if accept_license else 'no')
            assert accept_license

        self.host = host
        self.root_directory = root_directory
        self.port_map = {}
        for port_name, external_port in exposed_ports.items():
            external_port = external_port if external_port else self.neo_ports[port_name]
            self.port_map[self.neo_ports[port_name]] = int(external_port)
        self.volume_map = {}
        writable_owners = set()
        writable_groups = set()
        for volume, mode in self.neo_volumes.items():
            if log_directory and 'log' in volume:
                external_dir = log_directory
            else:
                external_dir = os.path.join(root_directory, volume[1:])
            self.volume_map[external_dir] = {'bind': volume, 'mode': mode}
            if mode == 'rw':
                writable_stat = os.stat(external_dir)
                writable_owners.add(writable_stat.st_uid)
                writable_groups.add(writable_stat.st_gid)
        if len(writable_owners) > 1:
            raise TypeError('Neo4j writable volumes owned by multiple owners: %s' % writable_owners)
        if len(writable_groups) > 1:
            print('Neo4j writable volumes grouped to multiple groups: %s' % writable_groups,
                  file=stderr)

        self.docker_client = docker_client if docker_client else docker.from_env()
        self.container = None
        # We need to run neo4j as the owner of its writable volumes...
        self.uid = list(writable_owners)[0]
        self.gid = list(writable_groups)[0]
        self.uid_flag = '%d:%d' % (self.uid, self.gid)

        if self.debug:
            self.debug_msg(self)

    def __str__(self):
        return (self.__class__.__name__ +
                '(' + self.image_name + '(' +
                'name="%s"' % self.host + ', ' +
                'ports=%s' % self.port_map + ', ' +
                'env=%s' % self.environment_map + ', ' +
                'user="%s"' % self.uid_flag + ', ' +
                'volumes=%s' % self.volume_map +
                '))')

    def start(self, restart_if_running=False):
        """

        :param restart_if_running:bool: False => return existing container
        :return:docker.container.Container: Container that's running Neo4j
        """

        if restart_if_running:
            self.stop()
        self.container = self.docker_client.containers.run(
            self.image_name,
            auto_remove=True,
            detach=True,
            name=self.host,
            ports=self.port_map,
            user='1001:1001',
            # group_add=[1001],
            volumes=self.volume_map,
            environment=self.environment_map
        )
        return self.container

    def stop(self):
        """
        Stop our docker container - if it's running...
        :return: None
        """
        container = self.container
        if not container:
            try:
                container = self.docker_client.containers.get(self.host)
            except docker.errors.NotFound as oops:
                print('%s not currently running.' % self.host,  file=stderr)
                return
        print('Killing %s' % container.id, file=stderr)
        container.kill()
        self.container = None


if __name__ == '__main__':
    print(NeoDockerServer())
    print(NeoDockerServer(edition='enterprise', accept_license=True))
    print(NeoDockerServer(edition='enterprise', version='3.5.2', accept_license=True))
    neo4j = NeoDockerServer(edition='enterprise', accept_license=True)
    print('RUNNING:', neo4j)
    sys.stdout.flush()
    print(neo4j.start(restart_if_running=True))
    sys.stdout.flush()
