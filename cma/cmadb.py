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
"""
This module defines our CMAdb class and so on...
"""
from typing import Any
import os
import sys
from sys import stderr
import inject
import py2neo


SUPPORTED_NEO4J_VERSIONS = (4,)
DEBUG = False


# R0903: Too few public methods
# pylint: disable=R0903
class CMAdb(object):
    """Class defining our Neo4J database."""

    nodename = os.uname()[1]
    debug = True
    net_transaction = None
    log = None
    store = None
    config = {}
    TheOneRing: Any
    globaldomain = "global"
    underdocker = None
    # versions we know we can't work with...
    neo4jblacklist = []

    @inject.params(db="py2neo.Graph", store="Store")
    def __init__(self, db=None, store=None):
        self.db: py2neo.Graph = db
        self.io = None
        CMAdb.store = store
        self.dbversion = py2neo.__version__
        CMAdb.dbversion = self.dbversion
        # print(f"DBVERSION: {type(self.dbversion)}: {self.dbversion}")
        major = self.dbversion.split(".")[0]
        # print("MAJOR IS", major)
        if self.dbversion in CMAdb.neo4jblacklist or int(major) not in SUPPORTED_NEO4J_VERSIONS:
            print(
                "The Assimilation CMA isn't compatible with Neo4j version %s" % self.dbversion,
                file=stderr,
            )
            raise EnvironmentError("Neo4j version %s not supported" % self.dbversion)

        if False and db.dbms.config.get("cypher.forbid_shortestpath_common_nodes", True):
            print(
                'Neo4j must be configured with "cypher.forbid_shortestpath_common_nodes=false"',
                file=stderr,
            )
            sys.exit(1)

        if CMAdb.debug:
            CMAdb.log.debug("Neo4j version: %s" % str(self.dbversion))

    @staticmethod
    def running_under_docker():
        "Return True if we're running under docker - must be root the first time we're called"
        if CMAdb.underdocker is None:
            try:
                initcmd = os.readlink("/proc/1/exe")
                CMAdb.underdocker = os.path.basename(initcmd) != "init"
            except OSError:
                print("Assimilation needs to run --privileged under docker", file=stderr)
                CMAdb.underdocker = True
        return CMAdb.underdocker


if __name__ == "__main__":
    # pylint: disable=C0413
    from cmainit import CMAinit, CMAInjectables

    inject.configure_once(CMAInjectables.test_config_injection)
    print("Starting", file=stderr)
    CMAinit(None, cleanoutdb=True, debug=True)
    print("Init done", file=stderr)
