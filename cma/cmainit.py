#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2011, 2012 - Alan Robertson <alanr@unix.sh>
#
#  The Assimilation software is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  The Assimilation software is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
"""
This module provides a class which initializes the CMA.
"""

import sys
import time
import os
import logging
import logging.handlers
import random
import getent
import inject
import py2neo
import neokit
from store import Store
from cmadb import CMAdb
from AssimCtypes import NEO4JCREDFILENAME, CMAUSERID


class Neo4jCreds(object):
    """Neo4j credentials object.
    We own the login name and password for getting at our instance of Neo4j.
    This includes caching the login and password.
    If we're invoked and there is no cached password, we generate a random
    password and tell Neo4j that's the one it should use.
    We also own the authentication process.
    Our object is suitable for injection...
    """
    default_name = 'neo4j'  # Default "login" name
    default_auth = 'neo4j'  # built-in default password
    default_length = 16     # default length of a randomly-generated password
    passchange = 'neoauth'  # Program to change passwords
    DEBUG = False

    @inject.params(log='logging.Logger')
    def __init__(self, log=None, filename=None, neologin=None, neopass=None, install_dir=None):
        """Neoj4Creds constructor

        :arg filename location of where to find/stash the credentials (optional)
        """
        self.install_dir = install_dir or '/usr/share/neo4j'

        # print("Calling Neo4jCreds.__init__(log=%s)" % log)
        # log.warning("Calling Neo4jCreds.__init__()")
        if neologin is not None and neopass is not None:
            self.isdefault = False
            self.name = neologin
            self.auth = neopass
            return
        if filename is None:
            filename = NEO4JCREDFILENAME
        self.filename = filename
        self.dirname = os.path.dirname(self.filename)
        self.isdefault = True
        if not os.access(self.dirname, os.W_OK | os.R_OK):
            raise IOError('Directory %s not accessible (are you root?)' % self.dirname)
        try:
            with open(self.filename) as f:
                self.name = f.readline().strip()
                self.auth = f.readline().strip()
                self.isdefault = False
        except IOError:
            self.name = Neo4jCreds.default_name
            self.auth = Neo4jCreds.default_auth
        self._log = log

    @staticmethod
    def randpass(length):
        """
        Generate a random password from letters, digits and punctuation

        :param length: length of the password to generate
        :return: password string
        """
        chars = r'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789' \
                r'!@#$%^&*()_-+=|\~`{[}]:;,.<>/?'
        ret = ''.join((random.choice(chars)) for _ in range(length))
        return str(ret)

    def update(self, newauth=None, length=None):
        """Update credentials from the new authorization info we've been given.
        """
        if length is None or length < 1:
            length = Neo4jCreds.default_length
        if not os.access(self.dirname, os.W_OK):
            raise IOError('Directory %s not writable (are you root?)' % self.dirname)
        if newauth is None:
            newauth = Neo4jCreds.randpass(length)
        if self.DEBUG:
            self._log.debug('Calling %s' % Neo4jCreds.passchange)
        # /var/lib/neo4j # bin/neo4j-admin
        # usage: neo4j-admin <command>
        #     set-initial-password
        server = neokit.GraphServer(home=self.install_dir)
        print('self.name, self.auth, newauth', self.name, self.auth, newauth)
        rc = server.update_password(self.name, self.auth, newauth)

        if rc is not None and rc != 0:
            raise IOError('Cannot update neo4j credentials.')
        self.auth = newauth
        if self.DEBUG:
            print >> sys.stderr, ('%s "%s:%s" successful.'
                                  % (Neo4jCreds.passchange, self.name, self.auth))
        userinfo = getent.passwd(CMAUSERID)
        if userinfo is None:
            raise OSError('CMA user id "%s" is unknown.' % CMAUSERID)
        with open(self.filename, 'w') as f:
            self.auth = newauth
            os.chmod(self.filename, 0o600)
            # pylint is confused about getent.passwd...
            # pylint: disable=E1101
            os.chown(self.filename, userinfo.uid, userinfo.gid)
            f.write('%s\n%s\n' % (self.name, self.auth))
        self._log.info('Updated Neo4j credentials cached in %s.' % self.filename)

    def authenticate(self, uri='localhost:7474'):
        """
        Authenticate ourselves to the neo4j database using our credentials
        """
        if self.isdefault:
            self.update()
        if True or self.DEBUG:
            print >> sys.stderr, 'AUTH against %s WITH ("%s")' % (str(uri), self)
        py2neo.authenticate(uri, user=self.name, password=self.auth)

    def __str__(self, filename=None):
        """We return the current assimilation Neo4j credentials (login, password) as a string
        :return: credentials tuple (login, password)
        """
        return '%s:%s' % (self.name, self.auth)


# Pylint wants us to have an __init__ for this pseudo-class
# pylint: disable=W0232
class CMAInjectables(object):
    """
    This class is more of a naming convention than a class ;-)
    It contains most of what you need for injecting our various objects where they're needed.
    """
    settings = {
        'LOG_NAME':         'cma',
        'LOG_FACILITY':     logging.handlers.SysLogHandler.LOG_DAEMON,
        'LOG_LEVEL':        logging.DEBUG,
        'LOG_DEVICE':       '/dev/log',
        'LOG_FORMAT':       '%(name)s %(levelname)s: %(message)s',
        'NEO4J_HTTP':       True,
        'NEO4J_HTTPS':      False,
        'NEO4J_BOLT':       False,
        'NEO4J_HOST':       'localhost',
        'NEO4J_PORT':       7474,
        'NEO4J_READONLY':   False,
        'NEO4J_RETRIES':    300,
    }
    config = {}

    @staticmethod
    def set_config(config):
        """
        Set things up so our config gets used during injection. Should be used
        before setting up injection.
        :param config: dict OR callable returning dict
        :return: None
        """
        CMAInjectables.config = config
        CMAdb.config = config

    @staticmethod
    def setup_prod_logging(name=None, address=None, facility=None, level=None):
        """Set up a perfectly wonderful logging environment for us - or at least try...
        This is perfectly well-suited for being an injector of logging.Logger"""
        name =     CMAInjectables.settings['LOG_NAME']     if name     is None else name
        address =  CMAInjectables.settings['LOG_DEVICE']   if address  is None else address
        facility = CMAInjectables.settings['LOG_FACILITY'] if facility is None else facility
        level =    CMAInjectables.settings['LOG_LEVEL']    if level    is None else level
        try:
            syslog = logging.handlers.SysLogHandler(address, facility)
        except EnvironmentError:
            # Docker doesn't really get along with logging - sigh...
            # And pylint doesn't like us assigning syslog a different type...
            # pylint: disable=R0204
            syslog = logging.StreamHandler()
        syslog.setFormatter(logging.Formatter(CMAInjectables.settings['LOG_FORMAT']))
        log = logging.getLogger(name)
        log.addHandler(syslog)
        log.setLevel(level)
        return log

    @staticmethod
    def setup_config():
        """
        Return configuration for injection
        :return:
        """
        if callable(CMAInjectables.config):
            return CMAInjectables.config()
        return CMAInjectables.config

    @staticmethod
    def setup_test_logging(_name=None, _address=None, _facility=None, _level=None):
        """Set up a wonderful logging environment for testing (stderr) - or at least try...
        This is perfectly well-suited for being an injector of logging.Logger
        """
        logger = logging.getLogger('testcode')
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter('%(name)s %(levelname)s: %(message)s'))
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)
        # print >> sys.stderr,"LOGGER IS: %s type is %s" % (logger, type(logger))
        return logger

    @staticmethod
    @inject.params(neocredentials='Neo4jCreds', log='logging.Logger')
    def setup_db(neocredentials, log, host=None, port=None, https=False, http=False, bolt=False):
        """Return a neo4j.Graph object (open channel to the Neo4j database)
        We're great as an injector for neo4j.Graph
        """
        host = host or CMAInjectables.settings['NEO4J_HOST']
        port = port or CMAInjectables.settings['NEO4J_PORT']
        http = http or CMAInjectables.settings['NEO4J_HTTP']
        https = https or CMAInjectables.settings['NEO4J_HTTPS']
        bolt = bolt or CMAInjectables.settings['NEO4J_BOLT']

        hostport = '%s:%s' % (host, port)
        protocol = 'bolt' if bolt else ('https' if https else 'http')
        url = '%s://%s/db/data/' % (protocol, hostport)

        trycount = 0
        while True:
            try:
                print >> sys.stderr, ("URI: %s" % url)
                print >> sys.stderr, ("hostport: %s" % hostport)
                neocredentials.authenticate(hostport)
                print >> sys.stderr, ('URI:%s bolt:%s, https:%s, http:%s, host:%s, port=%s'
                      % (url, bolt, https, http, host, port))
                neodb = py2neo.Graph(uri=url, bolt=bolt, https=https, http=http,
                                     host=host, port=port)
                # Neo4j started.  All is well with the world.
                break
            except (RuntimeError, IOError, py2neo.GraphError) as exc:
                print >> sys.stderr, 'TRYING AGAIN [%s]...[%s]' % (url, str(exc))
                trycount += 1
                if trycount > CMAInjectables.settings['NEO4J_RETRIES']:
                    print >> sys.stderr, ('Neo4j still not started - giving up.')
                    log.critical('Neo4j still not started - giving up.')
                    raise RuntimeError('Neo4j not running - giving up [%s]' % str(exc))
                if (trycount % 60) == 1:
                    print >> sys.stderr, ('Waiting for Neo4j [%s] to start [%s].' % (url, str(exc)))
                    log.warning('Waiting for Neo4j [%s] to start [%s].' % (url, str(exc)))
                # Let's try again in a second...
                time.sleep(10)
        return neodb

    @staticmethod
    @inject.params(config='Config')
    def setup_json_store(config):
        """
        Construct the JSON store that goes with this filename
        :param config: dict: or dict-like - configuration describing where to put jsonstorage
        :return: PersistentJSON: JSON store object
        """
        from invariant_data import (PersistentJSON, SQLiteJSON)
        store_filename = config.get('SQLiteFile', '/tmp/assimilation.sqlite')
        store_dirname = os.path.dirname(store_filename)
        if not os.path.isdir(store_dirname):
            try:
                os.mkdir(store_dirname, 0o750)
            except OSError as oops:
                print('Cannot make SQLite directory: %s' % oops)
                raise oops
        if not os.access(store_dirname, os.W_OK + os.X_OK + os.R_OK):
            raise OSError('ERROR: Directory "%s" not is not "rwx" to uid %s'
                          % (store_dirname, os.geteuid()))

        recreate_store = config.get('recreate_json_store', False)
        if recreate_store:
            try:
                os.unlink(store_filename)
            except OSError:
                pass
            try:
                os.unlink(store_filename + '-journal')
            except OSError:
                pass
        return PersistentJSON(cls=SQLiteJSON, audit=False, pathname=store_filename,
                              delayed_sync=True)

    @staticmethod
    @inject.params(db='py2neo.Graph', log='logging.Logger')
    def setup_store(db, log, readonly=None):
        """Return a Store object for mapping our objects to the database (OGM model)
        We're happy to be an injector for Store objects...
        """
        readonly = CMAInjectables.settings['NEO4J_READONLY'] if readonly is None else readonly
        store = Store(db=db, readonly=readonly, log=log)
        # print >> sys.stderr, ('RETURNING STORE: %s' % store)
        return store

    @staticmethod
    def default_config_injection(binder):
        """Perform our default injection setup
        """
        binder.bind_to_constructor('logging.Logger', CMAInjectables.setup_prod_logging)
        binder.bind_to_provider('Neo4jCreds', Neo4jCreds)  # odd, but intentional...
        binder.bind_to_constructor('py2neo.Graph', CMAInjectables.setup_db)
        binder.bind_to_constructor('Store', CMAInjectables.setup_store)
        binder.bind_to_provider('Config', CMAInjectables.setup_config)
        binder.bind_to_constructor('PersistentJSON', CMAInjectables.setup_json_store)

    @staticmethod
    def test_config_injection(binder):
        """Perform our test injection setup
        """
        binder.bind_to_constructor('logging.Logger', CMAInjectables.setup_test_logging)
        binder.bind_to_provider('Neo4jCreds', Neo4jCreds)  # odd, but intentional...
        binder.bind_to_constructor('py2neo.Graph', CMAInjectables.setup_db)
        binder.bind_to_constructor('Store', CMAInjectables.setup_store)
        binder.bind_to_provider('Config', CMAInjectables.setup_config)
        binder.bind_to_constructor('PersistentJSON', CMAInjectables.setup_json_store)
        return

    @staticmethod
    def default_cma_injection_configuration(config=None, injectable_config=None):
        """Do it all in one easy step... -- InjectItAll :-)
        The configuration parameters will be used to configure all our
        injectable objects. Only those listed in CMAInjectables.settings
        are legal keys (config names) to use in the 'config' parameter.
        """
        if injectable_config is None:
            injectable_config = CMAInjectables.default_config_injection
        if config is not None:
            for param in config:
                if param not in CMAInjectables.settings:
                    raise ValueError("%s is not a valid configuration parameter")
                CMAInjectables.settings[param] = config[param]
        if not inject.is_configured():
            inject.configure_once(injectable_config)


# R0903: too few public methods
# pylint: disable=R0903
class CMAinit(object):
    """
    The CMAinit class
    """
    # cmainit.py:43: [R0913:CMAinit.__init__] Too many arguments (9/7)
    # cmainit.py:43: [R0914:CMAinit.__init__] Too many local variables (17/15)
    # pylint: disable=R0914,R0913
    @inject.params(log='logging.Logger', store='Store', db='py2neo.Graph')
    def __init__(self, io, db=None, store=None, log=None, cleanoutdb=False, debug=False,
                 encryption_required=False, use_network=True):
        """Initialize and construct a global database instance
        """
        # print >> sys.stderr, 'CALLING NEW initglobal'
        CMAdb.log = log
        CMAdb.debug = debug
        CMAdb.io = io
        CMAdb.store = store
        self.db = db
        self.store = store
        self.io = io
        self.debug = debug

        if cleanoutdb:
            CMAdb.log.info('Re-initializing the NEO4j database')
            self.delete_all()

        CMAdb.use_network = use_network
        if not store.readonly:
            from hbring import HbRing
            from transaction import NetTransaction
            CMAdb.net_transaction = NetTransaction(io=io, encryption_required=encryption_required)
            # print >> sys.stderr,  'CMAdb:', CMAdb
            # print >> sys.stderr,  'CMAdb.store(cmadb.py):', CMAdb.store
            store.db_transaction = db.begin(autocommit=False)
            CMAdb.TheOneRing = CMAdb.store.load_or_create(HbRing, name='The_One_Ring',
                                                          ringtype=HbRing.THEONERING)
            print >> sys.stderr, ('Created TheOneRing: %s' % CMAdb.TheOneRing)
            if CMAdb.use_network:
                CMAdb.net_transaction.commit_trans()
            print >> sys.stderr, 'COMMITTING Store'
            print >> sys.stderr, 'NetTransaction Commit results:', CMAdb.store.commit()
            if CMAdb.store.db_transaction and not CMAdb.store.db_transaction.finished():
                CMAdb.store.commit()
            CMAdb.net_transaction = NetTransaction(io=io, encryption_required=encryption_required)
        else:
            CMAdb.net_transaction = None

    @staticmethod
    def uninit():
        """Undo initialization to make sure we aren't hanging onto any objects
        """
        CMAdb.cdb = None
        CMAdb.net_transaction = None
        CMAdb.TheOneRing = None
        CMAdb.store = None
        CMAdb.io = None

    @inject.params(json='PersistentJSON')
    def delete_all(self, json=None):
        """Empty everything out of our database - start over!
        """
        qstring = 'match (n) optional match (n)-[r]-() delete n,r'

        result = self.db.run(qstring)
        if CMAdb.debug:
            CMAdb.log.debug('Cypher query to delete all relationships'
                ' and nonzero nodes executing: %s' % qstring)
            CMAdb.log.debug('Execution results: %s' % str(result))
        json.delete_everything()



if __name__ == '__main__':
    inject.configure_once(CMAInjectables.test_config_injection)
    print >> sys.stderr, 'Starting'
    CMAinit(None, cleanoutdb=True, debug=True)
    print >> sys.stderr, 'Init done'
