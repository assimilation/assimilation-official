#!/usr/bin/env python
# coding=utf-8
#
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2017 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community
#   - http://assimproj.org
# Paid support may be available from Assimilation Systems Limited
#   - http://assimilationsystems.com
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
"""
This file provides secret management for the Assimilation project.
"""
import stat
import os.path
import pwd
import grp
import json
from AssimCtypes import CRYPTKEYDIR


class AssimSecret(object):
    """
    This class is for providing secrets for the Assimilation code.
    These things include credentials for Neo4j, and other credentials the software might need to
    do its work.
    """

    secret_subclasses = {}
    _secret_info_map = {}

    def __init__(self, secret_name, secret_parameters):
        """
        Base class initialization for the AssimSecret base class
        :param secret_name: str: the name of this secret
        :param secret_parameters: list(str): - parameters for this subclass initializer
        """

        self.secret_name = secret_name
        self._secret_parameters = secret_parameters
        self._update_functions = []

    @classmethod
    def register(cls, subclass):
        """
        Register this class as a subclass of AssimSecret - used as a decorator
        :param subclass: class: The subclass of AssimSecret we want to register as a constructor
        :return: the constructed object
        """
        assert issubclass(subclass, cls)
        cls.secret_subclasses[subclass.__name__.lower()] = subclass
        return subclass

    @staticmethod
    def factory(secret_name, **keywords):
        """
        Implements the factory pattern for our secret types
        :param secret_name: str: name of the secret we want to instantiate
        :return: AssimSecret: (actually a subclass of AssimSecret)
        """

        secret_info = AssimSecret._secret_info_map[secret_name]
        secret_type = secret_info.get("type", "file").lower()
        if secret_type not in AssimSecret.secret_subclasses:
            secret_type += "secret"
        return AssimSecret.secret_subclasses[secret_type](secret_name, secret_info, **keywords)

    def get(self):
        """
        Retrieve the value of our secret
        :return: Union(str, unicode, bytes)
        """
        raise NotImplementedError("%s.get() is an abstract method" % self.__class__.__name__)

    def set(self, new_value):
        """
        Update the value of our secret

        :param new_value: The new value to set the secret to.
        :return: None
        """
        raise NotImplementedError("%s.set() is an abstract method" % self.__class__.__name__)

    def add_update_function(self, update_function):
        """
        Add a new update function to an AssimSecret object.
        :param update_function: callable(secret_name, secret_parameters): function to add
        :return: None
        """
        self._update_functions.append(update_function)

    def _perform_external_update(self):
        """
        Utility function to perform all corresponding external updates when a secret is
        (about to be) updated. This is intended to do things like propagate such a
        change to Neo4j or other secret owners.
        These functions are supplied through _add_update_function.

        :return: bool: True if the external update process succeeded.
        """
        if self._update_functions:
            for fun in self._update_functions:
                if not fun(self.secret_name, self._secret_parameters):
                    return False
        else:
            return True

    @staticmethod
    def set_secret_info_map(info_map):
        """
        Set the secret info map for our secrets classes
        :param info_map: dict(str: dict)
        :return: None
        """
        for secret_name in info_map:
            parameters = info_map[secret_name]
            if "type" not in parameters:
                raise ValueError(
                    "Secret %s has no secret type in secret information map." % secret_name
                )
            if parameters["type"].lower() not in AssimSecret.secret_subclasses:
                secret_type = parameters["type"].lower() + "secret"
                if secret_type not in AssimSecret.secret_subclasses:
                    raise ValueError(
                        "Secret %s has an invalid secret type [%s] in secret information map."
                        % (secret_name, parameters["type"])
                    )
        # Must be OK - or at least no egregious errors ;-)
        AssimSecret._secret_info_map = info_map

    @staticmethod
    def set_secret_info_map_filename(file_name):
        """
        Set our secret map info from a JSON-structured filename
        :param file_name: Name of the file to read the JSON secret map from
        :return: None
        """
        with open(file_name) as map_fd:
            AssimSecret.set_secret_info_map(json.loads(map_fd.read()))


@AssimSecret.register
class FileSecret(AssimSecret):
    """
    A subclass for storing secrets in files
    """

    DEFAULT_SECRET_DIR = CRYPTKEYDIR
    uids = set()
    gids = set()

    def __init__(self, secret_name, secret_parameters):
        """
        :param secret_name: str: name of this secret
        :param secret_parameters: parameters for this secret
        """
        AssimSecret.__init__(self, secret_name, secret_parameters)
        self._temp_ok = secret_parameters.get("temp_ok", False)

    @staticmethod
    def set_uids_and_gids(uids=None, gids=None):
        """
        Set the globally permissible set of user ids and group ids for files
        that we check the permissions of
        :param uids: a list of user ids - either numeric or strings
        :param gids: a list of group ids - either numeric or strings
        :return:
        """
        FileSecret.uids = FileSecret.make_uids(uids) if uids else set()
        FileSecret.gids = FileSecret.make_gids(gids) if gids else set()
        print("UIDS: %s" % FileSecret.uids)

    @staticmethod
    def _check_full_path_permissions(file_name, file_read_only=True, temp_ok=False):
        """
        Validate the file permissions of the file and all its parent directories.
        :param file_name: str: name of the file we want to check the permissions of
        :return: None
        :raises: OSError: If permissions look wrong
        """
        FileSecret._check_path_perms(file_name, read_only=file_read_only, temp_ok=temp_ok)
        read_only = file_read_only
        while True:
            FileSecret._check_path_perms(file_name, read_only=read_only)
            read_only = False
            parent = os.path.dirname(file_name)
            if parent == "" or parent == file_name:
                break
            file_name = parent

    @staticmethod
    def _check_path_perms(path_name, read_only=True, temp_ok=False):
        """
        Check the permissions of this particular pathname
        We enforce the following rules:
            Must not be writable by group or other
            if read_only: Must not be readable by group or other

        :param path_name: str: the pathname we've been asked about
        :param read_only: bool: True if the file must be read-only to everyone but owner
                                files must are always readable only by owner
        :return: None
        :raises: OSError: If the file doesn't exist or permissions look wrong
        """

        stat_buffer = os.stat(path_name)
        mode = stat_buffer.st_mode
        if stat.S_ISLNK(mode):
            link_path = os.readlink(path_name)
            if not link_path.startswith("/"):
                link_directory = os.path.dirname(path_name)
                link_path = os.path.join(link_directory, link_path)
            FileSecret._check_full_path_permissions(file_name=link_path)
            return
        if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise OSError('"%s" is not a file, directory or link' % path_name)
        if not (temp_ok and path_name == "/tmp" or path_name == "/var/tmp" and mode & stat.S_ISVTX):
            # That combination looks to see if it's under a temp dir which is marked sticky...
            # this is useful for testing...
            if mode & (stat.S_IWOTH | stat.S_IWGRP):
                raise OSError('"%s" is writable by other or group' % path_name)
            if read_only or stat.S_ISREG(mode):
                if mode & (stat.S_IROTH | stat.S_IRGRP):
                    raise OSError('"%s" is readable by other or group' % path_name)
        if FileSecret.uids and stat_buffer.st_uid not in FileSecret.uids:
            raise OSError(
                'user id %s is not a permissible owner for "%s". %s'
                % (stat_buffer.st_uid, path_name, str(list(FileSecret.uids)))
            )
        if FileSecret.gids and stat_buffer.st_uid not in FileSecret.gids:
            raise OSError(
                'group id %s is not a permissible owner for "%s". %s'
                % (stat_buffer.st_uid, path_name, str(list(FileSecret.gids)))
            )
            # Well, if we got this far, it must be OK :-)

    @staticmethod
    def make_uids(uids):
        """
        Convert the arguments from user names to user ids
        :param uids: list(union(str, int))
        :return: list(int)
        """
        ret_uids = []
        for uid in uids:
            if isinstance(uid, int):
                ret_uids.append(uid)
            else:
                try:
                    ret_uids.append(pwd.getpwnam(uid).pw_uid)
                except KeyError:
                    pass
        return set(ret_uids)

    @staticmethod
    def make_gids(gids):
        """
        Convert the arguments from group names to group ids
        :param gids: list(union(str, int))
        :return: list(int)
        """
        ret_gids = []
        for gid in gids:
            if isinstance(gid, int):
                ret_gids.append(gid)
            else:
                try:
                    ret_gids.append(grp.getgrnam(gid.gr_gid))
                except KeyError:
                    pass
        return set(ret_gids)

    def get(self):
        """
        Get the value of the secret

        :return: str: value of secret [or other appropriate value ;-)]
        :raises OSError: For a variety of reasons.
        """
        file_name = self._secret_parameters.get("filename", self.secret_name)
        if not file_name.startswith("/"):
            file_name = os.path.join(self.DEFAULT_SECRET_DIR, file_name)
        try:
            self._check_full_path_permissions(file_name)
            with open(file_name) as secret_fd:
                return secret_fd.read()
        except OSError as error:
            raise OSError('FileSecret("%s"): %s.' % (self.secret_name, str(error)))

    def set(self, new_value):
        """
        Set the value of the file-stored secret...
        :param new_value:
        :return: None
        """
        file_name = self._secret_parameters.get("filename", self.secret_name)
        if not file_name.startswith("/"):
            file_name = os.path.join(self.DEFAULT_SECRET_DIR, file_name)
        try:
            self._check_full_path_permissions(file_name)
            with open(file_name, "w") as secret_fd:
                if self._perform_external_update():
                    return secret_fd.write(new_value)
                else:
                    raise RuntimeError(
                        'External secret update failed. Secret "%s" unchanged' % self.secret_name
                    )
        except OSError as error:
            raise OSError('FileSecret("%s"): %s.' % (self.secret_name, str(error)))


@AssimSecret.register
class Neo4jSecret(FileSecret):
    """
    Class for the Neo4j password and so on as secrets...
    """

    def __init__(self, secret_name, secret_parameters):

        if secret_parameters is None:
            secret_parameters = {}
        if "filename" not in secret_parameters:
            secret_parameters["filename"] = "neo4j.creds"
        FileSecret.__init__(self, secret_name, secret_parameters)
        self.add_update_function(Neo4jSecret._update_neo4j)

    @staticmethod
    def _update_neo4j(_secret_name, _secret_parameters):
        """
        Tell neo4j to change their password.

        FIXME: Actually do this work! :-D

        :param _secret_name: str: not used
        :param _secret_parameters: dict: not used
        :return: bool
        """
        # foo = secret_name + str(secret_parameters)
        # return foo is foo
        return True

    def get(self):
        """
        The Neo4j secret object returns a list of [login, password]

        Since the last character in the file is a newline, it would like to
        return a list of three items with the last one being an empty string.
        We exclude the empty string from the return value, so you only
        get two of them.

        :return: [str, str] : [login-string, password-string]
        """
        return [line for line in FileSecret.get(self).split("\n") if line]


if __name__ == "__main__":
    print("doing stuff")
    AssimSecret.set_secret_info_map(
        {
            "secret": {"type": "file", "filename": "/home/alanr/secret/secret"},
            "not_secret": {"type": "file", "filename": "/home/alanr/secret/not_secret"},
            "foobar": {"type": "file", "filename": "/home/alanr/secret/foobar"},
        }
    )
    uid_list = ["alanr", "root", "sys", "bin", "adm"]
    FileSecret.set_uids_and_gids(uid_list)
    secret = AssimSecret.factory("secret")
    print("GET: %s" % secret.get())
    secret = AssimSecret.factory("not_secret")
    try:
        print("GET: %s" % secret.get())
    except OSError as os_err:
        if "is readable by" not in str(os_err):
            print("Wrong error raised (%s)" % (str(os_err)))
    else:
        print("No error raised for not_secret file")
    secret = AssimSecret.factory("foobar")
    try:
        print("GET: %s" % secret.get())
    except OSError as os_err:
        if "No such file or directory" not in str(os_err):
            print("Wrong error raised (%s)" % (str(os_err)))
    else:
        print("No error raised for foobar file")

    FileSecret.set_uids_and_gids(uids=("root", "bin", "adm"))
    print("UIDS: %s" % FileSecret.uids)
    secret = AssimSecret.factory("secret")
    try:
        print("GET: %s" % secret.get())
    except OSError as os_err:
        if "not a permissible owner" not in str(os_err):
            print("Wrong error raised (%s)" % (str(os_err)))
    else:
        print("No owner error raised for secret file")
