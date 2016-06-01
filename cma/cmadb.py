#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
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
'''
This module defines our CMAdb class and so on...
'''

import os, sys, random, subprocess
import getent
import py2neo
from store import Store
from AssimCtypes import NEO4JCREDFILENAME, CMAUSERID

DEBUG = False

# R0903: Too few public methods
# pylint: disable=R0903
class CMAdb(object):
    '''Class defining our Neo4J database.'''
    nodename = os.uname()[1]
    debug = False
    transaction = None
    log = None
    store = None
    globaldomain = 'global'
    underdocker = None
    # versions we know we can't work with...
    neo4jblacklist = ['2.0.0']

    def __init__(self, db=None):
        self.db = db
        CMAdb.store = Store(self.db, {}, {})
        self.dbversion = self.db.neo4j_version
        vers = ""
        dot = ""
        for elem in self.dbversion:
            if str(elem) == '':
                continue
            vers += '%s%s' % (dot, str(elem))
            dot = '.'
        self.dbversstring = vers
        if self.dbversstring in CMAdb.neo4jblacklist:
            print >> sys.stderr, ("The Assimilation CMA isn't compatible with Neo4j version %s"
            %   self.dbversstring)
            sys.exit(1)
        self.nextlabelid = 0
        if CMAdb.debug:
            CMAdb.log.debug('Neo4j version: %s' % str(self.dbversion))
            print >> sys.stderr, ('HELP Neo4j version: %s' % str(self.dbversion))

    @staticmethod
    def running_under_docker():
        "Return True if we're running under docker - must be root the first time we're called"
        if CMAdb.underdocker is None:
            try:
                initcmd = os.readlink("/proc/1/exe")
                CMAdb.underdocker =  (os.path.basename(initcmd) != 'init')
            except OSError:
                print >> sys.stderr, ('Assimilation needs to run --privileged under docker')
                CMAdb.underdocker =  True
        return CMAdb.underdocker

class Neo4jCreds(object):
    'Neo4j credentials object'
    default_name = 'neo4j'      # Default "login" name
    default_auth = 'neo4j'      # built-in default password
    default_length = 16         # default length of a randomly-generated password
    passchange = 'neoauth'      # Program to change passwords

    def __init__(self, filename=None):
        '''Neoj4Creds constructor

        :arg filename location of where to find/stash the credentials (optional)
        '''
        if filename is None:
            filename = NEO4JCREDFILENAME
        self.filename = filename
        self.dirname = os.path.dirname(self.filename)
        self.isdefault = True
        if (not os.access(self.dirname, os.W_OK|os.R_OK)):
            raise IOError('Directory %s not accessible (are you root?)' % self.dirname)
        try:
            with open(self.filename) as f:
                self.name=f.readline().strip()
                self.auth=f.readline().strip()
                self.isdefault = False
        except IOError:
            self.name = Neo4jCreds.default_name
            self.auth = Neo4jCreds.default_auth

    @staticmethod
    def randpass(length):
        '''
        Generate a random password from letters, digits and punctuation

        :param length: length of the password to generate
        :return: password string
        '''
        chars = r'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789' \
                r'!@#$%^&*()_-+=|\~`{[}]:;,.<>/?'
        ret = ''.join((random.choice(chars)) for _ in range(length))
        return str(ret)

    def update(self, newauth=None, length=None):
        '''Update credentials from the new authorization info we've been given.
        '''
        if length is None or length < 1:
            length = Neo4jCreds.default_length
        if (not os.access(self.dirname, os.W_OK)):
            raise IOError('Directory %s not writable (are you root?)' % self.dirname)
        if newauth is None:
            newauth = Neo4jCreds.randpass(length)
        if DEBUG:
            print >> sys.stderr, 'Calling %s' % Neo4jCreds.passchange
        rc = subprocess.check_call([Neo4jCreds.passchange, self.name, self.auth, newauth])
        if rc != 0:
            raise IOError('Cannot update neo4j credentials.')
        self.auth = newauth
        if DEBUG:
            print >> sys.stderr, '%s "%s:%s" successful' % \
                    (Neo4jCreds.passchange, self.name, self.auth)
        userinfo = getent.passwd(CMAUSERID)
        if userinfo is None:
            raise OSError('CMA user id "%s" is unknown' % CMAUSERID)
        with open(self.filename, 'w') as f:
            self.auth = newauth
            os.chmod(self.filename, 0600)
            # pylint is confused about getent.passwd...
            # pylint: disable=E1101
            os.chown(self.filename, userinfo.uid, userinfo.gid)
            f.write('%s\n%s\n' % (self.name, self.auth))
        print >> sys.stderr, 'Updated Neo4j credentials cached in %s.' % self.filename

    def authenticate(self, uri='localhost:7474'):
        '''
        Authenticate ourselves to the neo4j database using our credentials
        '''
        if self.isdefault:
            self.update()
        if DEBUG:
            print >> sys.stderr, 'AUTH WITH ("%s")' % str(self)
        py2neo.authenticate(uri, self.name, self.auth)

    def __str__(self, filename=None):
        '''We return the current assimilation Neo4j credentials (login, password) as a string
        :return: credentials tuple (login, password)
        '''
        return '%s:%s' % (self.name, self.auth)


if __name__ == '__main__':
    # pylint: disable=C0413
    from cmainit import CMAinit
    print >> sys.stderr, 'Starting'
    CMAinit(None, cleanoutdb=True, debug=True)
    print >> sys.stderr, 'Init done'
