#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab
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

import os
import sys
from store import Store


# R0903: Too few public methods
# pylint: disable=R0903
class CMAdb:
    '''Class defining our Neo4J database.'''
    nodename = os.uname()[1]
    debug = True
    transaction = None
    log = None
    store = None
    globaldomain = 'global'
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

if __name__ == '__main__':
    from cmainit import CMAinit
    print >> sys.stderr, 'Starting'
    CMAinit(None, cleanoutdb=True, debug=True)
    print >> sys.stderr, 'Init done'
