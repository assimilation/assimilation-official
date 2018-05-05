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
"""
This file implements invariant JSON storage for the Assimilation project
The JSON is content-addressible via its hash value, so it's will never change
with the exception of being deleted...
We implement a base class and a couple of subclasses for different types of invariant JSON
storage.
"""

from __future__ import print_function
from sys import stderr
import collections
import os
import subprocess
import errno
import hashlib
import json
import sqlite3
import string

if hasattr(os, 'syncfs'):
    syncfs = getattr(os, 'syncfs')
else:
    import ctypes
    libc = ctypes.CDLL("libc.so.6")

    def syncfs(fd):
        """
        Wrapper for libc.syncfs if it's not already defined in our Python OS module...
        :param fd: file descriptor
        :return: int: typical system call return code...
        """
        libc.syncfs(fd)

import dpath


def dict_merge(original_dict, merge_dict):
    """
    Recursive dict merge. Merges merge_dict into original_dict, updating keys.
    :param original_dict: dict we're merging into
    :param merge_dict: dict: dict to be merged into original_dict
    :return: None
    """
    for key, value in merge_dict.items():
        if (key in original_dict
            and isinstance(original_dict[key], dict)
                and isinstance(value, collections.Mapping)):
            dict_merge(original_dict[key], value)
        else:
            original_dict[key] = merge_dict[key]


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
        result = self.get(key)
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
        for _, value in self.viewitems():
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
                                      The field description is according to dpath format
        :param dict_obj: dict: (or dict-like) object being filtered
        :return: True if the given field is in the list of possible values
        """

        field, value_list = equal_item
        if isinstance(value_list, (str, unicode, int, float, bool)):
            value_list = (value_list,)

        def _filter_match(data):
            """Return True if data is found in our desired value_list"""
            return data in value_list

        return dpath.util.search(dict_obj, field, afilter=_filter_match)

    def _equal_set_compare_and(self, equal_sets, dict_obj):
        """

        :param equal_sets: [(str,[str])]: Query specification
        param dict_obj: dict: thing to evaluate this against
        :return:
        """
        keys = set()
        biggest_result = {}  # Not used but it makes analyzers happy :-D
        for item in equal_sets:
            comparison = self._equal_item_compare(item, dict_obj)
            new_keys = set(comparison.keys())
            if keys:
                keys.intersection_update(new_keys)
                if not keys:
                    return {}
                dict_merge(biggest_result, comparison)
            else:
                keys = new_keys
                biggest_result = comparison

        for key in biggest_result.keys():
            if key not in keys:
                del biggest_result[key]
        return biggest_result

    def _equal_set_compare_or(self, equal_sets, dict_obj):
        """

        :param equal_sets:
        :param dict_obj:
        :return:
        """
        result = []
        for item in equal_sets:
            comparison = self._equal_item_compare(item, dict_obj)
            if comparison:
                result.append(comparison)
        return result

    def equality_query(self, equal_sets, ctype='and'):
        """

        :param equal_sets: sets to perform equality operation on...
        :param ctype: str: 'and' for and comparision, 'or' otherwise
        :return:
        """
        comparator = self._equal_set_compare_and if ctype == 'and' else self._equal_set_compare_or
        for key, item in self.viewitems():
            item = item.get(self.query_root)
            result = comparator(equal_sets, item)
            if result:
                yield key, result

    def sync(self):
        """
        Sync any outstanding data to disk...
        The logical equivalent to COMMITting a transaction

        :return: None
        """
        raise NotImplementedError("Abstract class PersistentInvariantData.sync()")

    def delete_everything(self):
        """
        Delete everything from the underlying storage
        :return:
        """
        raise NotImplementedError("Abstract class PersistentInvariantData.delete_everything()")


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

    def delete_everything(self):
        """
        Delete everything for this bucket
        :return: None
        """
        try:
            subprocess.check_call(['rm', '-fr', self.root_directory])
        except OSError:
            pass

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
            if oopsie.errno == errno.ENOENT:  # Doesn't exist
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
        for root, _, files in os.walk(self.root_directory):
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
        for root, _, files in os.walk(self.root_directory, followlinks=True):
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
                    print('ERROR: Cannot sync data in %s: %s'
                          % (self._pathname(key), oopsie), file=stderr)
                os.close(fd)
                return
            except OSError as oopsie:
                # This shouldn't happen unless permissions are screwed up...
                print('ERROR: Cannot open data in %s: %s'
                      % (self._pathname(key), oopsie), file=stderr)


class SQLiteInstance(object):
    """
    An Instance of a connection to an SQLite database. Needed by SQLiteJSON
    """
    instances = {}  # Key is pathname
    BEGIN_TRANS = 'BEGIN DEFERRED TRANSACTION;'
    TABLE_PREFIX = 'HASH_'

    def __init__(self, **initial_args):
        dbpath = initial_args['pathname']
        assert dbpath not in SQLiteInstance.instances
        self.in_transaction = False
        self.cursor = None
        args_to_del = {'delayed_sync', 'pathname', 'audit', 'root_directory'}
        filtered_args = {key: initial_args[key] for key in initial_args if key not in args_to_del}
        self.connection = sqlite3.connect(dbpath, **filtered_args)
        self.json_load = initial_args.get('json_load', json.loads)
        SQLiteInstance.instances[dbpath] = self
        self.hash_tables = set(self.all_hash_tables())
        self.dbpath = dbpath
        self.filtered_args = filtered_args

    def delete_everything(self):
        """
        Delete everything for this SQLite Instance
        :return: None
        """
        self.connection = None
        try:
            os.unlink(self.dbpath)
        except OSError as oopsie:
            if oopsie.errno != errno.ENOENT:  # Doesn't exist
                raise
        self.hash_tables = set()
        self.connection = sqlite3.connect(self.dbpath, **self.filtered_args)
        self.in_transaction = False
        self.cursor = None

    @staticmethod
    def instance(**initial_args):
        """

        :param initial_args:
        :return:
        """
        dbpath = initial_args['pathname']
        if dbpath in SQLiteInstance.instances:
            return SQLiteInstance.instances[dbpath]
        return SQLiteInstance(**initial_args)

    @staticmethod
    def sanitize(inchars):
        """
        Sanitize a string

        :param inchars: str: input characters
        :return: sanitized string
        """
        sanitize_charset = string.letters + string.digits + '_'
        return ''.join(char for char in inchars if char in sanitize_charset)

    def table_name(self, name):
        """

        :param name:
        :return:
        """
        return self.TABLE_PREFIX + self.sanitize(name)

    def ensure_transaction(self):
        """
        Ensure that we're in a transaction
        :return: None
        """
        if not self.in_transaction:
            self.cursor = self.connection.cursor()
            self.cursor.execute(self.BEGIN_TRANS)
            self.in_transaction = True

    def ensure_table(self, table):
        """
        Create a table if it doesn't exist
        :param table: Table to make sure we have
        :return:
        """
        self.ensure_transaction()

        if table not in self.hash_tables:
            self.create_hash_table(table)

    def execute(self, sql_statement, *args):
        """

        :param sql_statement: str: A single SQL statement
        :param args: [str]: Arguments to the SQL statement
        :return: depends on the SQL
        """
        self.ensure_transaction()
        return self.cursor.execute(sql_statement, *args)

    def all_hash_tables(self):
        """
        Return the names of all our hash tables (SQlite relations that correspond to hash tables)
        :return: [str]: Names of all our hash tables...
        """
        self.ensure_transaction()
        sql = ("""SELECT name FROM sqlite_master
                 WHERE type='table' AND name LIKE '%s%%'
                 ORDER BY name;""" % self.TABLE_PREFIX)
        self.execute(sql)
        chopindex = len(self.TABLE_PREFIX)
        return [row[0][chopindex:] for row in self.cursor.fetchall()]

    def create_hash_table(self, table):
        """
        Create the given hash table

        :param table: Name of (hash) table to create
        :return:
        """
        self.ensure_transaction()
        sql = ('CREATE TABLE %s(hash varchar unique, data varchar, integer current default 1);'
               % self.table_name(table))
        self.execute(sql)
        self.hash_tables.add(table)

    def put(self, table, datahash, data):
        """
        Insert this data into one of our tables...
        :param table: str: table name
        :param datahash: str: hash of data
        :param data: str: (JSON) data to be inserted
        :return: whatever cursor.execute returns...
        """
        self.ensure_table(table)
        if self.table_contains(table, datahash):
            return True
        insert_command = ('INSERT INTO %s (hash, data) VALUES (?, ?);' % self.table_name(table))
        return self.execute(insert_command, (datahash, data))

    def get(self, table, datahash, default=None):
        """
        Get the given value from the given table
        :param table:
        :param datahash:
        :param default:
        :return:
        """
        self.ensure_table(table)
        command = ('SELECT data FROM %s WHERE hash = ?;' % self.table_name(table))
        self.execute(command, (datahash,))
        result = self.cursor.fetchone()
        return self.json_load(result[0]) if result else default

    def delete(self, table, datahash):
        """
        Delete the given hash entry (row) from the given table
        :param table: str: Table to delete from
        :param datahash: str: key to delete
        :return: Whatever sqlite3.cursor.execute returns...
        """
        self.ensure_table(table)
        command = ('DELETE FROM %s WHERE hash = ?;' % self.table_name(table))
        return self.execute(command, (datahash,))

    def table_contains(self, table, datahash):
        """

        :param table: str: table to check for the key
        :param datahash: str: key (hash value)
        :return: bool: True if present, False otherwise
        """
        self.ensure_table(table)
        command = ('SELECT hash FROM %s WHERE hash = ?;' % self.table_name(table))
        self.execute(command, (datahash,))
        result = self.cursor.fetchone()
        return True if result else False

    def commit(self):
        """
        Commit any pending transaction
        :return:
        """
        if not self.in_transaction:
            return
        self.in_transaction = False
        self.cursor = None
        return self.connection.commit()

    def viewtableitems(self, table):
        """
        View all the key,value pairs in this table
        :return: generator(str, dict)
        """
        self.ensure_table(table)
        command = ('SELECT hash, data FROM %s;' % self.table_name(table))
        self.execute(command)
        result = self.cursor.fetchone()
        while result:
            yield result[0], self.json_load(result[1])
            result = self.cursor.fetchone()

    def viewtablevalues(self, table):
        """
        View all the values in this table
        :return: generator(dict)
        """
        self.ensure_table(table)
        command = ('SELECT data FROM %s;' % self.table_name(table))
        self.execute(command)
        result = self.cursor.fetchone()
        while result:
            yield self.json_load(result[0])
            result = self.cursor.fetchone()

    def viewtablekeys(self, table):
        """
        View all the keys in this table

        :return: generator(str)
        """
        self.ensure_table(table)
        command = ('SELECT hash FROM %s;' % self.table_name(table))
        self.execute(command)
        result = self.cursor.fetchone()
        while result:
            yield result[0]
            result = self.cursor.fetchone()


class SQLiteJSON(PersistentInvariantJSON):
    """
    Class using SQLite to store Invariant JSON.
    """

    def __init__(self, data_type, **initial_args):

        """
        SQListeJSON constructor...
        :param initial_args: a collection of initial arguments for this class or any subclasses
        """

        PersistentInvariantJSON.__init__(self, data_type, **initial_args)
        self.delayed_sync = bool(initial_args.get('delayed_sync', True))
        self.sync_all = bool(initial_args.get('sync_all', True))
        self.instance = SQLiteInstance.instance(**initial_args)
        self.data_hash = initial_args.get('data_hash', 'sha224')
        self.hash = getattr(hashlib, self.data_hash)

    def delete_everything(self):
        """
        Delete everything for this bucket
        :return: None
        """
        self.instance.delete_everything()

    def get(self, key, default=None):
        """

        :param key:
        :param default:
        :return:
        """
        return self.instance.get(self.data_type, key)

    def put(self, value, key=None):
        """

        :param value:
        :param key:
        :return:
        """
        if key is None:
            key = self.hash(value).hexdigest()
        return self.instance.put(self.data_type, key, value)

    def delete(self, key):
        """
        Delete this item from its table
        :param key: str: hash value to delete
        :return: Whatever cursor.execute() returns...
        """
        return self.instance.delete(self.data_type, key)

    def sync(self):
        """
        Commit the transaction -- sync to disk...
        :return: None
        """
        print('COMMIT.', file=stderr)
        self.instance.commit()

    def viewitems(self):
        """

        :return:
        """
        return self.instance.viewtableitems(self.data_type)

    def viewkeys(self):
        """

        :return:
        """
        return self.instance.viewtablekeys(self.data_type)

    def __contains__(self, key):
        """

        :param key:
        :return: bool: True if this key is in the table
        """
        return self.instance.table_contains(self.data_type, key)

    def all_hash_types(self):
        """
        Return all our known SQLite hash tables...
        :return: [str] -- all our known hash types
        """
        return self.instance.all_hash_tables()


class PersistentJSON(object):
    """
    Class encapsulating our Invariant JSON objects
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
        self.queried_all = False

    def _make_bucket(self, jsontype):
        """
        Make a bucket for this JSON type if it doesn't exist
        :param jsontype: str: JSON type bucket
        :return: None
        """
        if jsontype not in self.buckets:
            thing = self.cls(jsontype, **self._initial_args)
            self.buckets[jsontype] = thing
            if not self.queried_all:
                if hasattr(thing, 'all_hash_types'):
                    for bucket in thing.all_hash_types():
                        self._make_bucket(bucket)
            self.queried_all = True

    def __contains__(self, key):
        """
        Standard __contains__ API

        :param key: (str, str): (jsontype, jsonhash) key-pair
        :return: bool: True if this key exists
        """
        jsontype, jsonhash = key
        self._make_bucket(jsontype)
        return jsonhash in self.buckets[jsontype]

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
            if not bucket.sync_all:
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

    def equality_query(self, bucket_name, query, ctype='and'):
        """

        :param bucket_name: Which bucket to search in
        :param query: [str,[]]: sets to perform equality operation on...
        :param ctype:
        :return:
        """
        self._make_bucket(bucket_name)
        bucket = self.buckets[bucket_name]
        return bucket.equality_query(query, ctype=ctype)

    def delete_everything(self):
        """
        Delete everything from the underlying database
        :return: None
        """
        for bucket in self.buckets.viewvalues():
            bucket.delete_everything()
        self.buckets = {}


if __name__ == '__main__':
    # This is a pretty crappy test - but it works when you invoke it with the right data ;-)

    def test_main():
        """
        Test main program
        :return: None
        """
        try:
            os.unlink('/tmp/sqlite')
        except OSError:
            pass
        obj = PersistentJSON(cls=SQLiteJSON, root_directory='/tmp/alanr', audit=False,
                             pathname='/tmp/sqlite',
                             delayed_sync=True)
        directory = 'pgtests/json_data'
        for name in os.listdir(directory):
            with open(os.path.join(directory, name)) as json_fd:
                print('putting %s' % name, file=stderr)
                obj.put('fileattrs', json_fd.read())
        print('Performing sync.', file=stderr)
        obj.sync()  # Make sure all our bits get written to disk...
        print('Sync done.', file=stderr)
        for item in obj.equality_query('fileattrs', (('*/perms/sticky', True),)):
            print("Found sticky bit:", item, file=stderr)
        print('Performing second query.', file=stderr)
        for item in obj.equality_query('fileattrs', (('*/perms/group/write', True),
                                                     ('*/type', ('d', '-', 'b', 'c')))):
            print("Group-Writable non-links:", item, file=stderr)

    test_main()
