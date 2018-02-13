#!/usr/bin/env python
# coding=utf-8
#
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2018 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community
#   - http://assimproj.org
# Paid support is available from Assimilation Systems Limited
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

from __future__ import print_function
from sys import stderr
import os
import errno
import hashlib
import json

if hasattr(os, 'syncfs'):
    syncfs = os.syncfs
else:
    import ctypes
    libc = ctypes.CDLL("libc.so.6")

    def syncfs(fd):
        libc.syncfs(fd)


class PersistentInvariantJSON(object):
    """
    An abstract base class which implements several methods of providing persistent invariant
    data.
    """
    def __init__(self, data_type, **initial_args):
        """
        Abstract class constructor

        :param initial_args: a collection of initial arguments for this class or any subclasses
        """
        self._constructor_args = initial_args
        self.debug = initial_args.get('debug', False)
        self.audit = initial_args.get('audit', False)
        self.query_root = initial_args.get('query_root', 'data')
        self.json_load = initial_args.get('json_load', json.loads)
        self.data_type = data_type
        self.sync_all = bool(initial_args.get('sync_all', True))

        if initial_args.get('autosync_on_delete', False):
            self.__del__ = self.sync

    def get(self, key, default=None):
        """
        Return the value associated with this key, or the default if the key is not found

        :param key: Key to retrieve
        :param default: value to return if key not found
        :return: str: previously-stored value
        """
        raise NotImplementedError("Abstract class PersistentInvariantData.get() [%s, %s]"
                                  % (key, default))

    def __getitem__(self, key):
        """
        Standard dict-like __getitem__ - get the value that goes with this key
        :param key:
        :return:
        """
        result = self.get(key, None)
        if result is None:
            raise KeyError("No such key: %s" % key)

    def put(self, value, key=None):
        """
        Put the given value into our collection.
        If the key is not given, then we will compute it using our hash function...

        :param value: Value to stash away in our collection
        :param key: Key of value to put - will be computed from the value if not specified
        :return: str: key of item we stashed away
        """
        raise NotImplementedError("Abstract class PersistentInvariantData.put() [%s, %s]"
                                  % (key, value))

    def __setitem__(self, key, value):
        """
        Standard dict-like __setitem__ - set the value that goes with this key

        :param key: str: key to stash away
        :param value: str: Value to associate with 'key'
        :return: None
        """
        return self.put(value, key=key)

    def __contains__(self, key):
        """
        Return True if the given key is this container

        :param key: Key to retrieve
        :return: bool: True if this key exists in our collection
        """
        raise NotImplementedError("Abstract class PersistentInvariantData.__contains__() [%s]"
                                  % key)

    def delete(self, key):
        """
        Remove this item from the Collection
        :param key: Key to delete
        :return:
        """
        raise NotImplementedError("Abstract class PersistentInvariantData.del() [%s]" % key)

    def __delitem__(self, key):
        """
        Remove this item from the Collection - standard __delitem__ semantics
        :param key: Key to delete
        :return:
        """
        self.delete(key)

    def viewkeys(self):
        """
        Return iterator which walks through all the data items
        :return:
        """
        raise NotImplementedError("Abstract class PersistentInvariantData.viewitems()")

    def viewitems(self):
        """
        Should be a generator which yields each dict-from-JSON item in turn...
        :return:
        """
        raise NotImplementedError("Abstract class PersistentInvariantData.viewitems()")

    def viewvalues(self):
        """

        :return:
        """
        for key, value in self.viewitems():
            yield value

    def __iter__(self):
        """

        :return:
        """
        return self.viewkeys()

    @staticmethod
    def _equal_item_compare(equal_item, dict_obj):
        """
        See if the dict_obj matches the equal item comparison criteria we've been given


        :param equal_item: (str, []): (field description, comparison description)
        :param dict_obj: dict: (or dict-like) implements deepget or get
        :return: True if the given field is in the list of possible values
        """
        # FIXME: This implementation is SIGNIFICANTLY inadequate: need something supporting '*', etc

        field, value_list = equal_item
        if isinstance(value_list, (str, unicode, int, float)):
            value_list = list(value_list)

        if hasattr(dict_obj, 'deepget'):
            field_value = dict_obj.deepget(field)
        else:
            field_value = dict_obj.get(field)
        if field_value is None:
                return False
        return field_value in value_list

    def _equal_set_compare_and(self, equal_sets, dict_obj):
        """

        :param equal_sets:
        :param dict_obj:
        :return:
        """
        for item in equal_sets:
            if not self._equal_item_compare(item, dict_obj):
                return False
        return True

    def _equal_set_compare_or(self, equal_sets, dict_obj):
        """

        :param equal_sets:
        :param dict_obj:
        :return:
        """
        for item in equal_sets:
            if self._equal_item_compare(item, dict_obj):
                return True
        return False

    def equality_query(self, equal_sets, ctype='and'):
        """

        :param equal_sets: sets to perform equality operation on...
        :param ctype: str: 'and' for and comparision, 'or' otherwise
        :return:
        """
        comparator = self._equal_set_compare_and if type == 'and' else self._equal_set_compare_or
        for item in self.viewitems():
            item = item.get(self.query_root)
            if comparator(equal_sets, item):
                yield item

    def sync(self):
        """
        Sync any outstanding data to disk...
        The logical equivalent to COMMITting a transaction

        :return: None
        """
        raise NotImplementedError("Abstract class PersistentInvariantData.sync()")


class FilesystemJSON(PersistentInvariantJSON):
    """
    A class which implements storing each object in its own file
    """
    def __init__(self, data_type, **initial_args):

        """
        FilesystemPersistentInvariantData constructor...
        :param initial_args: a collection of initial arguments for this class or any subclasses
        :exceptions: OSError: if we can't make the root directory or it's not writable...
        """

        PersistentInvariantJSON.__init__(self, data_type, **initial_args)
        root_directory = initial_args['root_directory']
        self.root_directory = os.path.join(root_directory, data_type)
        self.data_hash = initial_args.get('data_hash', 'sha224')
        self.hash = getattr(hashlib, self.data_hash)
        self.levels = 1
        self.filename_length = self.hash().digest_size * 2   # hex => 2 chars per hash byte
        self.hash_chars = int(initial_args.get('hash_chars', 3))
        self.dirmode = int(initial_args.get('dirmode', 0o755))
        self.filemode = int(initial_args.get('filemode', 0o644))
        self.delayed_sync = bool(initial_args.get('delayed_sync', True))
        self.sync_all = bool(initial_args.get('sync_all', False))
        if not os.access(self.root_directory, os.W_OK):
            os.mkdir(self.root_directory, self.dirmode)

    def _pathname(self, key):
        """
        Return the pathname of a file in our collection
        :param key:
        :return:
        """
        return os.path.join(self.root_directory, key[:self.hash_chars], key).lower()

    def is_valid_key(self, key):
        """

        :param key: str: Key to validate
        :return: bool: True if the filename is a valid key
        """
        return (len(key) == self.filename_length
                and len(key.lower().strip("0123456789abcdef")) == 0)

    def __contains__(self, key):
        """
        Return True if the given key exists -- standard __contains__() API

        :param key: Key to look for in this container
        :return: True if data for this key exists
        """
        return os.access(self._pathname(key), os.R_OK)

    def get(self, key, default=None):
        """
        Return the value we were asked for...
        :param key: Value to retrieve
        :param default: value to return if missing
        :return: str
        :exceptions: OSError: if we can't read the data but it's there...
        """
        try:
            with open(self._pathname(key)) as file_obj:
                result = file_obj.read()
                if self.audit:
                    self._doaudit(key, result)
                return result
        except OSError as oopsie:
            if oopsie.errno == errno.ENOENT:  # Already exists
                return default
            raise oopsie

    def put(self, value, key=None):
        """
        Write data using this key
        :param key: str: key to write - or computed if not supplied...
        :param value: value to write into this key
        :exceptions: OSError:
        :return: Key for this data
        """
        if key is None:
            key = self.hash(value).hexdigest()
        if self.audit:
            self._doaudit(key, value)
        pathname = self._pathname(key)
        if not self.is_valid_key(key):
            raise ValueError('key is not valid: %s' % key)

        try:
            os_openmode = os.O_EXCL+os.O_CREAT+os.O_WRONLY
            with os.fdopen(os.open(pathname, os_openmode, self.filemode), 'w') as file_obj:
                file_obj.write(value)
                file_obj.flush()
                if not self.delayed_sync:
                    os.fsync(file_obj.fileno())  # Make sure the bits get saved for real...
        except OSError as oopsie:
            if oopsie.errno == errno.EEXIST:  # Already exists
                pass
            elif oopsie.errno == errno.ENOENT:  # Directory is missing...
                self._create_missing_directories(os.path.join(self.root_directory,
                                                              key[:self.hash_chars]))
                # Try again (recursively)...
                self.put(value, key)
            else:
                raise oopsie
        return key

    def delete(self, key):
        """
        Remove this item from the Collection
        :param key: Key to delete - OK if it doesn't exist
        :raises: OSError: If something goes wrong deleting it
        :return:
        """
        try:
            os.unlink(os.path.join(self.root_directory, key[:self.hash_chars], key))
        except OSError as oopsie:
            if oopsie.errno == errno.ENOENT:
                return
            raise oopsie

    def viewitems(self):
        """
        A generator which yields each (key, dict-from-JSON) pair in turn...
        :return: generator(str, dict): Generator returning (str, dict) on each next() call...
        """
        for root, dirs, files in os.walk(self.root_directory, followlinks=False):
            for filename in files:
                if not self.is_valid_key(filename):
                    print("WARNING: Ignoring file %s." % os.path.join(root, filename), file=stderr)
                    continue
                try:
                    with open(os.path.join(root, filename)) as open_file:
                        contents = open_file.read()
                        if self.audit:
                            self._doaudit(filename, contents)
                        yield filename, self.json_load(contents)
                except OSError as oops:
                    print("ERROR: cannot open file %s: %s."
                          % (os.path.join(root, filename), oops), file=stderr)

    def viewkeys(self):
        """
        A generator which yields each key in turn
        :return: generator(str)
        """
        for root, dirs, files in os.walk(self.root_directory, followlinks=True):
            for filename in files:
                if self.is_valid_key(filename):
                    yield filename
                else:
                    print("WARNING: Ignoring file %s." % os.path.join(root, filename), file=stderr)

    def _create_missing_directories(self, path):
        """
        Create any missing directories (only one at the moment...)
        :param path: Path we want to exist
        :return: None
        :exceptions: OSError: If we can't create a directory
        """
        os.mkdir(path, self.dirmode)

    def _doaudit(self, key, data):
        """

        :param key: key - assumed to be the hash of the data
        :param data: data that goes with the key
        :return: None
        :raises: AssertionError: if it fails the audit
        """
        assert key == self.hash(data).hexdigest()

    def sync(self):
        """
        Sync underlying filesystem
        The logical equivalent to COMMITting a transaction
        :return:
        """
        for key in self:
            try:
                fd = os.open(self._pathname(key), os.O_RDONLY)
                try:
                    syncfs(fd)
                except OSError as oopsie:
                    print('ERROR: Cannot sync data in %s' % self._pathname(key), file=stderr)
                os.close(fd)
                return
            except OSError as oopsie:
                # This shouldn't happen unless permissions are screwed up...
                print('ERROR: Cannot open data in %s' % self._pathname(key), file=stderr)


class PersistentJSON(object):
    """
    Class encapsulating all our Filesystem JSON objects
    """

    def __init__(self, cls, **initial_args):
        """
        Constructor for PersistentJSON objects...
        :param cls: Our underlying class that persists JSON somewhere appropriate...
        :param initial_args: dict: arguments to give to our 'cls' constructor
        """
        self.cls = cls
        assert issubclass(cls, PersistentInvariantJSON)
        self._initial_args = initial_args
        self.buckets = {}

    def _make_bucket(self, jsontype):
        """
        Make a bucket for this JSON type if it doesn't exist
        :param jsontype: str: JSON type bucket
        :return: None
        """
        if jsontype not in self.buckets:
            self.buckets[jsontype] = self.cls(jsontype, **self._initial_args)

    def get(self, jsontype, jsonhash, default=None):
        """
        Return the value associated with our (jsontype, jsonhash)
        :param jsontype: str: Type of JSON blob desired
        :param jsonhash: str: hash of JSON blob desired
        :param default: default return value
        :return:
        """
        self._make_bucket(jsontype)
        return self.buckets[jsontype].get(jsonhash, default)

    def put(self, jsontype, value, key=None):
        """
        Set the value associated with our (jsontype, jsonhash)
        :param jsontype: str: Type of JSON blob to be written
        :param value: str: JSON string to write
        :param key: str: hash of JSON blob - or None
        :return: str: key of the given JSON blob
        """
        self._make_bucket(jsontype)
        return self.buckets[jsontype].put(value, key)

    def delete(self, jsontype, key):
        """
        Set the value associated with our (jsontype, jsonhash)
        :param jsontype: str: Type of JSON blob to be written
        :param key: str: hash of JSON blob - or None
        :return: None
        """
        self._make_bucket(jsontype)
        return self.buckets[jsontype].delete(key)

    def sync(self):
        """
        Sync all our data out to disk...
        The logical equivalent to COMMITting a transaction
        :return: None
        """
        for bucket in self.buckets.viewvalues():
            bucket.sync()
            if not self.sync_all:
                # In this case, we assume that all our buckets can be synced at once...
                return

    def __getitem__(self, key):
        """
        Return the
        :param key: (str, str): json-type, json-hash
        :return: dict
        """
        result = self.get(key[0], key[1])
        if result is None:
            raise KeyError("No such key: %s" % key)

    def __setitem__(self, key, value):
        """
        Return the
        :param key: (str, str): json-type, json-hash
        :param value: str: JSON string
        :return: None
        """
        self.put(key[0], value, key[1])

    def __delitem__(self, key):
        """
        Delete this item...
        :param key: (str, str): json-type, json-hash
        :return: dict
        """
        self.delete(key[0], key[1])

    def viewkeys(self):
        """
        Standard viewkeys API - keys are tuple(str, str)
        :return: Generator(str, str)
        """
        for bucket_name, bucket in self.buckets.viewitems():
            for key in bucket.viewkeys():
                yield (bucket_name, key)

    def viewvalues(self):
        """
        Standard viewvalues API
        :return: Generator(dict)
        """
        for bucket in self.buckets.viewvalues():
            for value in bucket.viewvalues():
                yield value

    def viewitems(self):
        """
        Standard viewitems API - keys are tuple(str, str)

        :return: Generator((str, str), dict)
        """
        for bucket_name, bucket in self.buckets.viewitems():
            for key, json_blob in bucket.viewitems():
                yield (bucket_name, key), json_blob


if __name__ == '__main__':
    # This is a pretty crappy test - but it works when you invoke it with the right data ;-)

    def test_main():
        obj = PersistentJSON(cls=FilesystemJSON, root_directory='/tmp/alanr', audit=False,
                             delayed_sync=True)
        directory = 'pgtests/json_data'
        for name in os.listdir(directory):
            with open(os.path.join(directory, name)) as json_fd:
                obj.put('fileattrs', json_fd.read())
        obj.sync()  # Make sure all our bits get written to disk...

    test_main()
