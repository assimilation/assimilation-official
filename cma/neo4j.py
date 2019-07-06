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
"""
Software for managing a Neo4j instance...
Currently that only means a docker image of Neo4j...
"""
from __future__ import print_function
import os
import sys
from sys import stderr
import docker
import docker.errors
import time
import shutil


class NeoServer(object):
    """
    Abstract Neo4j server class
    """

    # What volumes does Neo4j export, and what kind of permissions are required for each?
    neo_volumes = {
        "/conf": "ro",
        "/data": "rw",
        "/import": "ro",
        "/logs": "rw",
        "/metrics": "rw",
        "/plugins": "ro",
        "/ssl": "ro",
    }

    # Names and in-container values of ports that Neo4j exports...
    neo_ports = {"http": 7474, "https": 7473, "bolt": 7687}

    def start(self):
        """Abstract method to start a server"""
        raise NotImplementedError("Abstract method start")

    def stop(self):
        """Abstract method to stop a server"""
        raise NotImplementedError("Abstract method stop")

    def set_initial_password(self, initial_password):
        """Abstract method to supply the initial password"""
        raise NotImplementedError("Abstract method set_initial_password")

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

    edition_map = {"community": "", "enterprise": "-enterprise"}
    good_versions = {"3"}

    initial_password_command = ["neo4j-admin", "set-initial-password"]

    def __init__(
        self,
        edition="community",
        version="latest",
        host="assim_neo4j",
        exposed_ports=None,
        environment_map=None,
        accept_license=False,
        root_directory="/var/lib/assimilation/neo4j",
        log_directory="/var/log/assim_neo4j",
        docker_client=None,
        debug=False,
    ):
        """
        Create a Neo4j server...

        :param edition:str: Which Neo4j edition? (community or enterprise)
        :param version:str: Which Neo4j version? (default: latest)
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
            exposed_ports = {"bolt": None, "http": None}

        self.version_info = version.split(".")
        if version != "latest":
            assert self.version_info[0] in self.good_versions
        self.image_name = "neo4j"

        edition_suffix = self.edition_map[edition]
        if edition == "enterprise" and version == "latest":
            self.image_name += ":" + edition
        else:
            if edition_suffix:
                self.image_name += ":" + version + edition_suffix
        if edition == "enterprise":
            self.environment_map["NEO4J_ACCEPT_LICENSE_AGREEMENT"] = (
                "yes" if accept_license else "no"
            )
            assert accept_license

        self.host = host
        self.root_directory = root_directory
        self.port_map = {}
        for port_name, external_port in exposed_ports.items():
            external_port = (
                external_port if external_port else self.neo_ports[port_name]
            )
            self.port_map[self.neo_ports[port_name]] = int(external_port)
        self.volume_map = {}
        writable_owners = set()
        writable_groups = set()
        for volume, mode in self.neo_volumes.items():
            if log_directory and "log" in volume:
                external_dir = log_directory
            else:
                external_dir = os.path.join(root_directory, volume[1:])
            self.volume_map[external_dir] = {"bind": volume, "mode": mode}
            if mode == "rw":
                writable_stat = os.stat(external_dir)
                writable_owners.add(writable_stat.st_uid)
                writable_groups.add(writable_stat.st_gid)
        if len(writable_owners) > 1:
            raise TypeError(
                "Neo4j writable volumes owned by multiple owners: %s" % writable_owners
            )
        if len(writable_groups) > 1:
            print(
                "Neo4j writable volumes grouped to multiple groups: %s"
                % writable_groups,
                file=stderr,
            )

        self.docker_client = docker_client if docker_client else docker.from_env()
        self.container = None
        # We need to run neo4j as the owner of its writable volumes...
        self.uid = list(writable_owners)[0]
        self.gid = list(writable_groups)[0]
        self.uid_flag = "%d:%d" % (self.uid, self.gid)

        if self.debug:
            self.debug_msg(self)

    def __str__(self):
        return (
            self.__class__.__name__
            + "("
            + self.image_name
            + "("
            + 'name="%s"' % self.host
            + ", "
            + "ports=%s" % self.port_map
            + ", "
            + "env=%s" % self.environment_map
            + ", "
            + 'user="%s"' % self.uid_flag
            + ", "
            + "volumes=%s" % self.volume_map
            + "))"
        )

    @property
    def auth_file_name(self):
        """Return the name of the Neo4j 'auth' file"""
        return os.path.join(self.root_directory, "data", "dbms", "auth")

    @property
    def roles_file_name(self):
        """Return the name of the Neo4j 'roles' file"""
        return os.path.join(self.root_directory, "data", "dbms", "roles")

    @property
    def databases_directory(self):
        """Return the name of the Neo4j 'databases' directory"""
        return os.path.join(self.root_directory, "data", "databases")

    def attributes(self):
        """
        Return a set of attributes of our container (from the container itself)
        :return: dict
        """
        if not self.is_running():
            return {}
        assert self.container

        image = self.container.attrs["Config"]["Image"]
        if image.startswith("sha"):
            for tag in self.container.image.tags:
                if "neo4j" in tag:
                    image = tag
                    break

        net_settings = self.container.attrs["NetworkSettings"]
        attrs = {
            "image": image,
            "ipaddress": net_settings["IPAddress"],
            "edition": "enterprise" if "enterprise" in image else "community",
            "mounts": self.container.attrs["Mounts"],
            "ports": net_settings["Ports"],
            # 'networks': self.container.attrs['Networks'],
        }
        if net_settings.get("LinkLocalIPv6Address"):
            attrs["link_local_ipv6_address"] = net_settings["LinkLocalIPv6Address"]
        if net_settings.get("GlobalIPv6Address"):
            attrs["global_ipv6_address"] = net_settings["GlobalIPv6Address"]
        return attrs

    def start(self, restart_if_running=False):
        """

        :param restart_if_running:bool: False => return existing container
        :return:docker.container.Container: Container that's running Neo4j
        We run this container with the permissions of the owner of its various
        read/write directories
        """

        if self.is_running():
            if restart_if_running:
                self.stop()
            else:
                return self.container
        self.container = self.docker_client.containers.run(
            self.image_name,
            auto_remove=True,
            detach=True,
            name=self.host,
            ports=self.port_map,
            user=self.uid_flag,
            volumes=self.volume_map,
            environment=self.environment_map,
        )
        time.sleep(5)
        # @FIXME: This should be a loop waiting for services to become available...
        print('Neo4j container %s started.' % self.container.short_id, file=stderr)
        return self.container

    def is_running(self):
        """
        Return True if this container is running
        Side effect: set self.container to the docker container object
        :return:bool: True if the container is running
        """
        try:
            self.container = self.docker_client.containers.get(self.host)
            return True
        except docker.errors.NotFound:
            self.container = None
            return False

    def stop(self):
        """
        Stop our docker container - if it's running...
        :return: None
        """
        container_s = str(self.container.short_id)
        while self.is_running():
            try:
                self.container.kill(15)
            except docker.errors.APIError as oops:
                if "404" not in str(oops) and "409" not in str(oops):
                    raise
            time.sleep(0.25)
        print('Neo4j container %s now stopped.' % container_s, file=stderr)

    def _getpass(self, name="neo4j"):
        """
        Return the tuple (username, authentication string, extra stuff) from
        the docker container's authentication file
        :param name: username we're looking for
        :return: Tuple[str, str, str]: name, auth string, extra
        """
        bad_return = None, None, None
        try:
            with open(self.auth_file_name) as auth_fd:
                while True:
                    line = auth_fd.readline()
                    if not line:
                        return bad_return
                    fields = line.split(":", 2)
                    if fields[0] == name:
                        return fields
        except (IOError, ValueError):
            return bad_return

    def is_password_set(self):
        """
        Return True if the password is already set
        :return:bool: True if password already set
        """
        name, _, extra = self._getpass()
        return name is not None and not extra

    def set_initial_password(self, initial_password, force=False):
        """
       Set the initial password

        :param initial_password: str: new/initial password
        :param force: bool: True if we want to force it to be changed anyway
                            Force causes the database to be restarted
        :return: bool: True if it succeeded, False if not...
        """

        name, auth, extra = self._getpass()
        if extra is not None:
            extra = extra.strip()
            name = None
        if extra or force:
            try:
                # Do we need to stop Neo4j before doing this?
                os.unlink(self.auth_file_name)
                os.unlink(self.roles_file_name)
                print('Previous neo4j authorization information deleted.', file=stderr)
            except OSError:
                pass

        if name is not None and not extra:
            raise TypeError("Initial password already set.")
        command = self.initial_password_command
        command.append(initial_password)
        rc, output = self.container.exec_run(command, user=self.uid_flag)
        output = output.strip()
        print(output)
        if rc != 0:
            raise RuntimeError('Could not set initial password: %s' % output)
        if force:
            self.start(restart_if_running=True)
        result = rc == 0
        print('Initial Neo4j password %sset.' % '' if result else 'NOT ', file=stderr)
        return result

    def clean_db(self):
        """
        Clean out the database...
        This is nice because it cleans out _everything_ - not just nodes and relationships...
        It leaves authentication and other things untouched...
        """
        print('Emptying out Neo4j database @%s.' % self.container.short_id, file=stderr)
        self.stop()
        shutil.rmtree(self.databases_directory)
        self.start()


if __name__ == "__main__":

    def stupid_docker_test():
        """This is a stupid Neo4j/Docker test..."""
        sys.stdout = sys.stderr  # Good for testing...
        print(NeoDockerServer())
        print(NeoDockerServer(edition="enterprise", accept_license=True))
        print(
            NeoDockerServer(edition="enterprise", version="3.5.0", accept_license=True)
        )
        neo4j = NeoDockerServer(edition="enterprise", version='3.5.6', accept_license=True)
        print("Now RUNNING:", neo4j)
        neo4j.start(restart_if_running=False)
        print('Is Neo4j running?', neo4j.is_running())
        neo4j.set_initial_password("passw0rd", force=True)
        neo4j.clean_db()

    stupid_docker_test()
