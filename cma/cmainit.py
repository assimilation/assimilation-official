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
import subprocess
import getent
import inject
import py2neo
import neokit
from store import Store
from consts import CMAconsts
from graphnodes import GraphNode
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

        print("Calling Neo4jCreds.__init__(log=%s)" % log)
        log.warning("Calling Neo4jCreds.__init__()")
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
        server = neokit.GraphServer(home=self.install_dir)
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

    def authenticate(self, uri='http://localhost:7474'):
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
        'NEO4J_HTTPS':      True,
        'NEO4J_HOST':       'localhost',
        'NEO4J_PORT':       7474,
        'NEO4J_READONLY':   False,
        'NEO4J_RETRIES':    300,
    }


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
    def setup_test_logging(name=None, address=None, facility=None, level=None):
        """Set up a perfectly wonderful logging environment for testing (stderr) - or at least try...
        This is perfectly well-suited for being an injector of logging.Logger
        """
        logger = logging.getLogger('testcode')
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter('%(name)s %(levelname)s: %(message)s'))
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)
        print >> sys.stderr,"LOGGER IS: %s type is %s" % (logger, type(logger))
        return logger

    @staticmethod
    @inject.params(neocredentials='Neo4jCreds', log='logging.Logger')
    def setup_db(neocredentials, log, host=None, port=None, https=None):
        """Return a neo4j.Graph object (open channel to the Neo4j database)
        We're great as an injector for neo4j.Graph
        """
        host = host or CMAInjectables.settings['NEO4J_HOST']
        port = port or CMAInjectables.settings['NEO4J_PORT']
        https = https or CMAInjectables.settings['NEO4J_HTTPS']
        https = False

        hostport = '%s:%s' % (host, port)
        url = '%s://%s/db/data/' % ('https' if https else 'http', hostport)
        print >> sys.stderr, ("URL: %s" % url)

        trycount = 0
        while True:
            try:
                neocredentials.authenticate(hostport)
                neodb = py2neo.Graph(uri=url, bolt=False, https=False, http=True, host=host, port=7474)
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
    @inject.params(db='py2neo.Graph', log='logging.Logger')
    def setup_store(db, log, readonly=None):
        """Return a Store object for mapping our objects to the database (OGM model)
        We're happy to be an injector for Store objects...
        """
        readonly = CMAInjectables.settings['NEO4J_READONLY'] if readonly is None else readonly
        store = Store(db=db, readonly=readonly, log=log)
        print >> sys.stderr, ('RETURNING STORE: %s' % store)
        return store

    @staticmethod
    def default_config_injection(binder):
        """Perform our default injection setup
        """
        binder.bind_to_constructor('logging.Logger', CMAInjectables.setup_prod_logging)
        binder.bind_to_provider('Neo4jCreds', Neo4jCreds)  # odd, but intentional...
        binder.bind_to_constructor('py2neo.Graph', CMAInjectables.setup_db)
        binder.bind_to_constructor('Store', CMAInjectables.setup_store)

    @staticmethod
    def test_config_injection(binder):
        """Perform our test injection setup
        """
        binder.bind_to_constructor('logging.Logger', CMAInjectables.setup_test_logging)
        binder.bind_to_provider('Neo4jCreds', Neo4jCreds)  # odd, but intentional...
        binder.bind_to_constructor('py2neo.Graph', CMAInjectables.setup_db)
        binder.bind_to_constructor('Store', CMAInjectables.setup_store)
        return

    @staticmethod
    def default_CMA_injection_configuration(config=None, injectable_config=None):
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
    #cmainit.py:43: [R0913:CMAinit.__init__] Too many arguments (9/7)
    #cmainit.py:43: [R0914:CMAinit.__init__] Too many local variables (17/15)
    # pylint: disable=R0914,R0913
    @inject.params(log='logging.Logger', store='Store', db='py2neo.Graph')
    def __init__(self, io, db, store, log, cleanoutdb=False, debug=False,
                 encryption_required=False, use_network=True):
        """Initialize and construct a global database instance
        """
        #print >> sys.stderr, 'CALLING NEW initglobal'
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
            for classname in GraphNode.classmap:
                GraphNode.initclasstypeobj(CMAdb.store, classname)
            from transaction import NetTransaction
            CMAdb.net_transaction = NetTransaction(encryption_required=encryption_required)
            #print >> sys.stderr,  'CMAdb:', CMAdb
            #print >> sys.stderr,  'CMAdb.store(cmadb.py):', CMAdb.store
            CMAdb.TheOneRing = CMAdb.store.load_or_create(HbRing, name='The_One_Ring'
            ,           ringtype=HbRing.THEONERING)
            CMAdb.net_transaction.commit_trans(io)
            #print >> sys.stderr, 'COMMITTING Store'
            #print >> sys.stderr, 'NetTransaction Commit results:', CMAdb.store.commit()
            CMAdb.store.commit()
            #print >> sys.stderr, 'Store COMMITTED'
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


    def delete_all(self):
        """Empty everything out of our database - start over!
        """
        dbvers = self.db.neo4j_version
        if dbvers[0] >= 2:
            qstring = 'match (n) optional match (n)-[r]-() delete n,r'
        else:
            qstring = 'start n=node(*) match n-[r?]-() delete n,r'

        result = self.db.cypher.execute(qstring)
        if CMAdb.debug:
            CMAdb.log.debug('Cypher query to delete all relationships'
                ' and nonzero nodes executing: %s' % qstring)
            CMAdb.log.debug('Execution results: %s' % str(result))
        indexes = self.db.legacy.get_indexes(py2neo.Node)
        for index in indexes.keys():
            if CMAdb.debug:
                CMAdb.log.debug('Deleting index %s' % str(index))
            self.db.legacy.delete_index(py2neo.Node, index)



if __name__ == '__main__':
    print >> sys.stderr, 'Starting'
    CMAinit(None, cleanoutdb=True, debug=True)
    if CMAdb.store.transaction_pending:
        print >> sys.stderr, 'NetTransaction pending in:', CMAdb.store
        print >> sys.stderr, 'Results:', CMAdb.store.commit()
    print >> sys.stderr, 'Init done'
