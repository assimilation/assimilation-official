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
"""
   Design outline:

   All incoming network messages come in and get sent to a client who is a dispatcher.

   The dispatcher looks at the message type and computes which queue to send the
   message to based on the message type and contents.

       For death notices, the dispatcher forwards the message to the worker
       assigned to the switch the system is on - if known, or the worker
       assigned to the subnet.

   Each worker handles one or more rings - probably handling the per-switch rings
   for a subnet and the subnet ring as well.  It is important to ensure that a ring
   is handled by only one worker.  This eliminates locking concerns.  When a given
   worker receives a death notice for a drone that is also in higher-level rings,
   it does its at its level and also forwards the request to the worker handling
   the higher level ring as well.  The first subnet worker will also handle the work
   for the top-level (global) ring.

   Packets are ACKed by workers after all work has been completed.  In the case of
   a drone on multiple rings, it is only ACKed after both rings have been fully
   repaired.

   The reason for this is that until it is fully repaired, the system might crash
   before completing its work.  Retransmission timeouts will need to be set
   accordingly...

   Although congestion is normally very unlikely, this is not true for full
   datacenter powerons - where it is reasonably likely - depending on how
   quickly one can power on the servers and not pop circuit breakers or
   damage UPSes
       (it would be good to know how fast hosts can come up worst case).


   Misc Workers with well-known-names
   Request-To-Create-Ring


   Mappings:

   Drone-related information-------------------------
   NetAddr-to-drone-name
   drone-name to NetAddr
   (drone-name,ifname) to interface-info (including switch info)
   drone-neighbor-info:
       drone-name-to-neighbor-info (drone-name, NetAddr, ring-name)

   Ring-related information--------------------------
   drone-name to ring-name(s)
   ring-names to ring-information (level, #members, etc)
   ring-links-info ??
   Subnet-to-ring-name
   Switch-to-ring-name
   Global-ring-name [TheOneRing]

   Discovery-related information---------------------
   (drone-name, Interface-name) to LLDP/CDP packet
   (drone-name, discovery-type) to JSON info


   Misc Info-----------------------------------------
   NetAddr(MAC)-to-NetAddr(IP)


   Dispatcher logic:
   For now sends all requests to TheOneRing because we need to write more code ;-)


################################################################################
#
# It is readily observable that the code is headed that way, but is a long
# way from that structure...
#
################################################################################
"""
from __future__ import print_function
import os

# This works around a bug in the glib library...
os.environ["G_SLICE"] = "always-malloc"
# This works around a stupidity in the glib library...
os.environ["G_MESSAGES_DEBUG"] = "all"
# The environment assignments above *must* come before the imports below.
# It *might* be sufficient to put them before AssimCtypes, but that would also make pylint bitch...
# pylint: disable=C0413
import sys
import signal
import optparse
import traceback
import importlib

# import atexit
import grp
import pwd
import py2neo
import cmainit
from assimeventobserver import ForkExecObserver
from AssimCtypes import NOTIFICATION_SCRIPT_DIR, CMAINITFILE, CMAUSERID, CRYPTKEYDIR, CMA_KEY_PREFIX
import AssimCtypes
from AssimCclasses import pyCompressFrame, pyCryptCurve25519, pyCryptFrame
from cmaconfig import ConfigFile
from bestpractices import BestPractices

sys.stdout = sys.stderr

SUPPORTED_PYTHON_VERSIONS = ("3.6","3.7", "3.8")
SUPPORTED_PY2NEO_VERSIONS = (4,)

PYTHON_VERSION = "%s.%s" % sys.version_info[0:2]
if PYTHON_VERSION not in SUPPORTED_PYTHON_VERSIONS:
    raise EnvironmentError("Python Version %s not supported" % PYTHON_VERSION)


optional_modules = [
    "discoverylistener",  # NOT OPTIONAL(!)
    "linkdiscovery",
    "checksumdiscovery",
    "monitoringdiscovery",
    "arpdiscovery",
]
PY2NEO_VERSION = py2neo.__version__
#
#   "Main" program starts below...
#   It is a the real CMA intended to run with some real nanoprobes running
#   somewhere out there...
#
# 912: Too many branches, 914: too many local variables, 915: too many statements
# pylint: disable=R0912,R0914,R0915
def main():
    "Main program for the CMA (Collective Management Authority)"
    py2neo_major_version = int(PY2NEO_VERSION.partition(".")[0])
    if py2neo_major_version not in SUPPORTED_PY2NEO_VERSIONS:
        raise EnvironmentError("py2neo version %s not supported" % PY2NEO_VERSION)
    DefaultPort = 1984
    # VERY Linux-specific - but useful and apparently correct ;-)
    PrimaryIPcmd = "ip address show primary scope global | grep '^ *inet' | sed -e 's%^ *inet *%%' -e 's%/.*%%'"
    ipfd = os.popen(PrimaryIPcmd, "r")
    OurAddrStr = "%s:%d" % (ipfd.readline().rstrip(), DefaultPort)
    ipfd.close()

    parser = optparse.OptionParser(
        prog="CMA",
        version=AssimCtypes.VERSION_STRING,
        description="Collective Management Authority for the Assimilation System",
        usage="cma.py [--bind address:port]",
    )

    parser.add_option(
        "-b",
        "--bind",
        action="store",
        default=None,
        dest="bind",
        metavar="address:port-to-bind-to",
        help="Address:port to listen to - for nanoprobes to connect to",
    )

    parser.add_option(
        "-d",
        "--debug",
        action="store",
        default=0,
        dest="debug",
        help="enable debug for CMA and libraries - value is debug level for C libraries.",
    )

    parser.add_option(
        "-s",
        "--status",
        action="store_true",
        default=False,
        dest="status",
        help="Return status of running CMA",
    )

    parser.add_option(
        "-k",
        "--kill",
        action="store_true",
        default=False,
        dest="kill",
        help="Shut down running CMA.",
    )

    parser.add_option(
        "-e",
        "--erasedb",
        action="store_true",
        default=False,
        dest="erasedb",
        help="Erase Neo4J before starting",
    )

    parser.add_option(
        "-f",
        "--foreground",
        action="store_true",
        default=False,
        dest="foreground",
        help="keep the CMA from going into the background",
    )

    parser.add_option(
        "-p",
        "--pidfile",
        action="store",
        default="/var/run/assimilation/cma",
        dest="pidfile",
        metavar="pidfile-pathname",
        help="full pathname of where to locate our pid file",
    )

    parser.add_option(
        "-T",
        "--trace",
        action="store_true",
        default=False,
        dest="doTrace",
        help="Trace CMA execution",
    )

    parser.add_option(
        "-u",
        "--user",
        action="store",
        default=CMAUSERID,
        dest="userid",
        metavar="userid",
        help="userid to run the CMA as",
    )

    opt = parser.parse_args()[0]

    from AssimCtypes import (
        daemonize_me,
        assimilation_openlog,
        are_we_already_running,
        kill_pid_service,
        pidrunningstat_to_status,
        remove_pid_file,
        rmpid_and_exit_on_signal,
    )

    if opt.status:
        rc = pidrunningstat_to_status(are_we_already_running(opt.pidfile, None))
        return rc

    if opt.kill:
        if kill_pid_service(opt.pidfile, 15) < 0:
            print("Unable to stop CMA.", file=sys.stderr)
            return 1
        return 0

    opt.debug = int(opt.debug)

    # This doesn't seem to work no matter where I invoke it...
    # But if we don't fork in daemonize_me() ('C' code), it works great...
    #    def cleanup():
    #        remove_pid_file(opt.pidfile)
    #    atexit.register(cleanup)
    #    signal.signal(signal.SIGTERM, lambda sig, stack: sys.exit(0))
    #    signal.signal(signal.SIGINT, lambda sig, stack: sys.exit(0))

    from cmadb import CMAdb

    CMAdb.running_under_docker()
    make_pid_dir(opt.pidfile, opt.userid)
    make_key_dir(CRYPTKEYDIR, opt.userid)
    cryptwarnings = pyCryptCurve25519.initkeys()
    for warn in cryptwarnings:
        print("WARNING: %s" % warn, file=sys.stderr)
    # print('All known key ids:', file=sys.stderr)
    keyids = pyCryptFrame.get_key_ids()
    keyids.sort()
    for keyid in keyids:
        if not keyid.startswith(CMA_KEY_PREFIX):
            try:
                # @FIXME This is not an ideal way to associate identities with hosts
                # in a multi-tenant environment
                # @FIXME - don't think I need to do the associate_identity at all any more...
                hostname, notused_post = keyid.split("@@", 1)
                notused_post = notused_post
                pyCryptFrame.associate_identity(hostname, keyid)
            except ValueError:
                pass
        # print('>    %s/%s' % (keyid, pyCryptFrame.get_identity(keyid)), file=sys.stderr)

    daemonize_me(opt.foreground, "/", opt.pidfile, 20)

    rmpid_and_exit_on_signal(opt.pidfile, signal.SIGTERM)

    # Next statement can't appear before daemonize_me() or bind() fails -- not quite sure why...
    assimilation_openlog("cma")
    from packetlistener import PacketListener
    from messagedispatcher import MessageDispatcher
    from dispatchtarget import DispatchTarget
    from monitoring import MonitoringRule
    from AssimCclasses import pyNetAddr, pySignFrame, pyReliableUDP, pyPacketDecoder
    from AssimCtypes import (
        CONFIGNAME_CMAINIT,
        CONFIGNAME_CMAADDR,
        CONFIGNAME_CMADISCOVER,
        CONFIGNAME_CMAFAIL,
        CONFIGNAME_CMAPORT,
        CONFIGNAME_OUTSIG,
        CONFIGNAME_COMPRESSTYPE,
        CONFIGNAME_COMPRESS,
        proj_class_incr_debug,
        LONG_LICENSE_STRING,
        MONRULEINSTALL_DIR,
    )

    if opt.debug:
        print("Setting debug to %s" % opt.debug, file=sys.stderr)

    for debug in range(opt.debug):
        debug = debug
        print("Incrementing C-level debug by one.", file=sys.stderr)
        proj_class_incr_debug(None)

    #   Input our monitoring rule templates
    #   They only exist in flat files and in memory - they aren't in the database
    print(f"Loading monitoring rules from '{MONRULEINSTALL_DIR}'", file=sys.stderr)
    MonitoringRule.load_tree(MONRULEINSTALL_DIR)

    execobserver_constraints = {
        "nodetype": ["Drone", "IPaddrNode", "MonitorAction", "NICNode", "ProcessNode", "SystemNode"]
    }
    ForkExecObserver(constraints=execobserver_constraints, scriptdir=NOTIFICATION_SCRIPT_DIR)
    print("Fork/Event observer dispatching from %s" % NOTIFICATION_SCRIPT_DIR, file=sys.stderr)

    if opt.bind is not None:
        OurAddrStr = opt.bind

    OurAddr = pyNetAddr(OurAddrStr)
    if OurAddr.port() == 0:
        OurAddr.setport(DefaultPort)

    try:
        configinfo = ConfigFile(filename=CMAINITFILE)
    except IOError:
        configinfo = ConfigFile()
    if opt.bind is not None:
        bindaddr = pyNetAddr(opt.bind)
        if bindaddr.port() == 0:
            bindaddr.setport(ConfigFile[CONFIGNAME_CMAPORT])
        configinfo[CONFIGNAME_CMAINIT] = bindaddr
    configinfo[CONFIGNAME_CMADISCOVER] = OurAddr
    configinfo[CONFIGNAME_CMAFAIL] = OurAddr
    configinfo[CONFIGNAME_CMAADDR] = OurAddr
    if CONFIGNAME_COMPRESSTYPE in configinfo:
        configinfo[CONFIGNAME_COMPRESS] = pyCompressFrame(
            compression_method=configinfo[CONFIGNAME_COMPRESSTYPE]
        )
    configinfo[CONFIGNAME_OUTSIG] = pySignFrame(1)
    config = configinfo.complete_config()

    addr = config[CONFIGNAME_CMAINIT]
    # pylint is confused: addr is a pyNetAddr, not a pyConfigContext
    # pylint: disable=E1101
    if addr.port() == 0:
        addr.setport(DefaultPort)
    ourport = addr.port()
    for elem in (
        CONFIGNAME_CMAINIT,
        CONFIGNAME_CMAADDR,
        CONFIGNAME_CMADISCOVER,
        CONFIGNAME_CMAFAIL,
    ):
        if elem in config:
            config[elem] = pyNetAddr(str(config[elem]), port=ourport)
    io = pyReliableUDP(config, pyPacketDecoder())
    io.setrcvbufsize(10 * 1024 * 1024)  # No harm in asking - it will get us the best we can get...
    io.setsendbufsize(1024 * 1024)  # Most of the traffic volume is inbound from discovery
    cmainit.CMAInjectables.set_config(configinfo)
    cmainit.CMAInjectables.default_cma_injection_configuration()
    userinfo = pwd.getpwnam(opt.userid)
    try:
        os.chown(config.get("SQLiteFile"), userinfo.pw_uid, userinfo.pw_gid)
    except FileNotFoundError:
        pass
    try:
        os.chown(config.get("SQLiteFile") + '-journal', userinfo.pw_uid, userinfo.pw_gid)
    except FileNotFoundError:
        pass
    drop_privileges_permanently(opt.userid)
    try:
        cmainit.CMAinit(io, cleanoutdb=opt.erasedb, debug=(opt.debug > 0))
    except RuntimeError:
        remove_pid_file(opt.pidfile)
        raise
    for warn in cryptwarnings:
        CMAdb.log.warning(warn)
    cmadb = CMAdb()
    CMAdb.log.info("Listening on: %s" % str(config[CONFIGNAME_CMAINIT]))
    CMAdb.log.info("Requesting return packets sent to: %s" % str(OurAddr))
    CMAdb.log.info("Socket input buffer size:  %d" % io.getrcvbufsize())
    CMAdb.log.info("Socket output buffer size: %d" % io.getsendbufsize())
    keyids = pyCryptFrame.get_key_ids()
    keyids.sort()
    for keyid in keyids:
        CMAdb.log.info("KeyId %s Identity %s" % (keyid, pyCryptFrame.get_identity(keyid)))
    if CMAdb.debug:
        CMAdb.log.debug("C-library Debug was set to %s" % opt.debug)
        CMAdb.log.debug("TheOneRing created - id = %s" % CMAdb.TheOneRing)
        CMAdb.log.debug("Config Object sent to nanoprobes: %s" % config)

    jvmfd = os.popen("java -version 2>&1")
    jvers = jvmfd.readline()
    jvmfd.close()
    disp = MessageDispatcher(DispatchTarget.dispatchtable)
    neoversstring = py2neo.__version__

    CMAdb.log.info(
        "Starting CMA version %s - licensed under %s"
        % (AssimCtypes.VERSION_STRING, LONG_LICENSE_STRING)
    )
    CMAdb.log.info(
        "Neo4j version %s // py2neo version %s // Python version %s // %s"
        % (
            cmadb.db.database.kernel_version,
            str(py2neo.__version__),
            ("%s.%s.%s" % sys.version_info[0:3]),
            jvers,
        )
    )
    if opt.foreground:
        print(
            "Starting CMA version %s - licensed under %s"
            % (AssimCtypes.VERSION_STRING, LONG_LICENSE_STRING),
            file=sys.stderr,
        )
        print(
            "Neo4j version %s // py2neo version %s // Python version %s // %s"
            % (neoversstring, PY2NEO_VERSION, ("%s.%s.%s" % sys.version_info[0:3]), jvers),
            file=sys.stderr,
        )

    # Important to note that we don't want PacketListener to create its own 'io' object
    # or it will screw up the ReliableUDP protocol...
    listener = PacketListener(config, disp, io=io)
    mandatory_modules = ["discoverylistener"]
    for mandatory in mandatory_modules:
        importlib.import_module(mandatory)
    # pylint is confused here...
    # pylint: disable=E1133
    for optional in config["optional_modules"]:
        importlib.import_module(optional)
    if opt.doTrace:
        import trace

        tracer = trace.Trace(count=False, trace=True)
        if CMAdb.debug:
            CMAdb.log.debug("Starting up traced listener.listen(); debug=%d" % opt.debug)
        if opt.foreground:
            print(
                "cma: Starting up traced listener.listen() in foreground; debug=%d" % opt.debug,
                file=sys.stderr,
            )
        tracer.runfunc(listener.listen)
    else:
        if CMAdb.debug:
            CMAdb.log.debug("Starting up untraced listener.listen(); debug=%d" % opt.debug)
        if opt.foreground:
            print(
                "cma: Starting up untraced listener.listen() in foreground; debug=%d" % opt.debug,
                file=sys.stderr,
            )

        # This is kind of a kludge, we should really look again at
        # at initializition and so on.
        # This module *ought* to be optional.
        # that would involve adding some Drone callbacks for creation of new Drones
        BestPractices(config, io, CMAdb.store, CMAdb.log, opt.debug)
        listener.listen()
    return 0


def supplementary_groups_for_user(userid):
    """Return the list of supplementary groups to which this member
    would belong if they logged in as a tuple of (groupnamelist, gidlist)
    """
    namelist = []
    gidlist = []
    for entry in grp.getgrall():
        if userid in entry.gr_mem:
            namelist.append(entry.gr_name)
            gidlist.append(entry.gr_gid)
    return namelist, gidlist


def drop_privileges_permanently(userid):
    """
    Drop our privileges permanently and run as the given user with
    the privileges to which they would be entitled if they logged in.
    That is, the uid, gid, and supplementary group list are all set correctly.
    We are careful to make sure we have exactly the permissions we need
    as 'userid'.
    Either we need to be started as root or as 'userid' or this function
    will fail and exit the program.
    """
    return
    userinfo = pwd.getpwnam(userid)
    if userinfo is None:
        raise (OSError('Userid "%s" is unknown.' % userid))
    newuid = userinfo.pw_uid
    newgid = userinfo.pw_gid
    auxgroups = set(supplementary_groups_for_user(userid)[1])
    # Need to set supplementary groups, then group id then user id in that order.
    try:
        os.setgroups(sorted(auxgroups))
        os.setgid(newgid)
        os.setuid(newuid)
    except OSError:
        # We let this fail if it wants to and catch it below.
        # This allows this to work if we're already running as that user id...
        pass
    # Let's see if everything wound up as it should...
    if (
        os.getuid() != newuid
        or os.geteuid() != newuid
        or os.getgid() != newgid
        or os.getegid() != newgid
    ):
        raise OSError(
            'Could not set user/group ids to user "%s" [uid:%s, gid:%s].'
            % (userid, os.getuid(), os.getgid())
        )
    curgroups = set(os.getgroups())
    if curgroups != auxgroups:
        raise OSError(f'Could not set auxiliary groups for user "{userid}"'
                      f'{sorted(curgroups)} vs {sorted(auxgroups)}')
    print(f"Curent user information: {newuid}::{newgid}::{sorted(curgroups)}")
    # Hurray!  Everything worked!


def make_pid_dir(pidfile, userid):
    "Make a suitable directory for the pidfile"
    piddir = os.path.dirname(pidfile)
    if os.path.isdir(piddir):
        # Assume it's been set up suitably
        return
    os.mkdir(piddir, 0o755)
    userinfo = pwd.getpwnam(userid)
    if userinfo is None:
        raise (OSError('Userid "%s" is unknown.' % userid))
    os.chown(piddir, userinfo.pw_uid, userinfo.pw_gid)


def make_key_dir(keydir, userid):
    "Make a suitable directory for us to store our keys in "
    if os.path.isdir(keydir):
        # Assume it's been set up suitably
        return
    os.mkdir(keydir, 0o700)
    userinfo = pwd.getpwnam(userid)
    if userinfo is None:
        raise (OSError('Userid "%s" is unknown.' % userid))
    os.chown(keydir, userinfo.pw_uid, userinfo.pw_gid)


def logger(msg):
    "Log a message to syslog using logger"
    os.system("logger -s '%s'" % msg)


def process_main_exception(ex):
    "Process an uncaught exception outside our event loop"
    trace = sys.exc_info()[2]
    tblist = traceback.extract_tb(trace, 20)
    # Put our traceback into the logs in a legible way
    logger(f"Got a {type(ex).__name__} exception in Main [{str(ex)})]")
    logger(f"======== Begin Main {type(ex).__name__} Exception Traceback ========")
    for tb in tblist:
        (filename, line, funcname, text) = tb
        filename = os.path.basename(filename)
        logger("%s.%s:%s: %s" % (filename, line, funcname, text))
    logger(f"======== End Main {type(ex).__name__} Exception Traceback ========")
    raise ex


if __name__ == "__main__":
    pyversion = sys.version_info
    if pyversion[0] != 3 or pyversion[1] < 6:
        raise RuntimeError("Must be run using python 3.x where x >= 7")
    exitrc = 1
    # W0703 == Too general exception catching...
    # pylint: disable=W0703
    try:
        exitrc = main()
    except Exception as e:
        process_main_exception(e)

    sys.exit(int(exitrc))
