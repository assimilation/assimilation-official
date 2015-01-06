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
'''
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
'''


import optparse, time
import os, sys, signal
import cmainit
from assimeventobserver import ForkExecObserver
from AssimCtypes import NOTIFICATION_SCRIPT_DIR, CMAINITFILE, CMAUSERID, CRYPTKEYDIR
import AssimCtypes
from AssimCclasses import pyCompressFrame, pyCryptCurve25519
from cmaconfig import ConfigFile
import importlib
#import atexit
import getent
import py2neo


optional_modules = [    'discoverylistener' # NOT OPTIONAL(!)
    ,                   'linkdiscovery'
    ,                   'checksumdiscovery'
    ,                   'monitoringdiscovery'
    ,                   'arpdiscovery'
    ]
#
#   "Main" program starts below...
#   It is a the real CMA intended to run with some real nanoprobes running
#   somewhere out there...
#
# 912: Too many branches, 914: too many local variables, 915: too many statements
#pylint: disable=R0912,R0914,R0915
def main():
    'Main program for the CMA (Collective Management Authority)'
    DefaultPort = 1984
    # This works around a bug in the glib library...
    os.environ['G_SLICE'] = 'always-malloc'
    # This works around a stupidity in the glib library...
    os.environ['G_MESSAGES_DEBUG'] = 'all'
    # VERY Linux-specific - but useful and apparently correct ;-)
    PrimaryIPcmd =   \
    "ip address show primary scope global | grep '^ *inet' | sed -e 's%^ *inet *%%' -e 's%/.*%%'"
    ipfd = os.popen(PrimaryIPcmd, 'r')
    OurAddrStr = ('%s:%d' % (ipfd.readline().rstrip(), DefaultPort))
    ipfd.close()

    parser = optparse.OptionParser(prog='CMA', version=AssimCtypes.VERSION_STRING,
        description='Collective Management Authority for the Assimilation System',
        usage='cma.py [--bind address:port]')

    parser.add_option('-b', '--bind', action='store', default=None, dest='bind'
    ,   metavar='address:port-to-bind-to'
    ,   help='Address:port to listen to - for nanoprobes to connect to')

    parser.add_option('-d', '--debug', action='store', default=0, dest='debug'
    ,   help='enable debug for CMA and libraries - value is debug level for C libraries.')

    parser.add_option('-s', '--status', action='store_true', default=False, dest='status'
    ,   help='Return status of running CMA')

    parser.add_option('-k', '--kill', action='store_true', default=False, dest='kill'
    ,   help='Shut down running CMA.')

    parser.add_option('-e', '--erasedb', action='store_true', default=False, dest='erasedb'
    ,   help='Erase Neo4J before starting')

    parser.add_option('-f', '--foreground', action='store_true', default=False, dest='foreground'
    ,   help='keep the CMA from going into the background')

    parser.add_option('-p', '--pidfile', action='store', default='/var/run/assimilation/cma'
    ,   dest='pidfile',   metavar='pidfile-pathname'
    ,   help='full pathname of where to locate our pid file')

    parser.add_option('-T', '--trace', action='store_true', default=False, dest='doTrace'
    ,   help='Trace CMA execution')

    parser.add_option('-u', '--user', action='store', default=CMAUSERID, dest='userid'
    ,   metavar='userid'
    ,   help='userid to run the CMA as')


    opt = parser.parse_args()[0]

    from AssimCtypes import daemonize_me, assimilation_openlog, are_we_already_running, \
        kill_pid_service, pidrunningstat_to_status, remove_pid_file, rmpid_and_exit_on_signal


    if opt.status:
        rc = pidrunningstat_to_status(are_we_already_running(opt.pidfile, None))
        return rc

    if opt.kill:
        if kill_pid_service(opt.pidfile, 15) < 0:
            print >> sys.stderr, "Unable to stop CMA."
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
    drop_privileges_permanently(opt.userid)
    cryptwarnings = pyCryptCurve25519.initkeys()
    for warn in cryptwarnings:
        print >> sys.stderr, ("WARNING: %s" % warn)

    daemonize_me(opt.foreground, '/', opt.pidfile, 20)

    rmpid_and_exit_on_signal(opt.pidfile, signal.SIGTERM)


    # Next statement can't appear before daemonize_me() or bind() fails -- not quite sure why...
    assimilation_openlog("cma")
    from packetlistener import PacketListener
    from messagedispatcher import MessageDispatcher
    from dispatchtarget import DispatchTarget
    from monitoring import MonitoringRule
    from AssimCclasses import pyNetAddr, pySignFrame, pyReliableUDP, \
         pyPacketDecoder
    from AssimCtypes import CONFIGNAME_CMAINIT, CONFIGNAME_CMAADDR, CONFIGNAME_CMADISCOVER, \
        CONFIGNAME_CMAFAIL, CONFIGNAME_CMAPORT, CONFIGNAME_OUTSIG, CONFIGNAME_COMPRESSTYPE, \
        CONFIGNAME_COMPRESS, CONFIGNAME_OUTSIG,\
        proj_class_incr_debug, LONG_LICENSE_STRING, MONRULEINSTALL_DIR


    if opt.debug:
        print >> sys.stderr, ('Setting debug to %s' % opt.debug)

    for debug in range(opt.debug):
        debug = debug
        print >> sys.stderr, ('Incrementing C-level debug by one.')
        proj_class_incr_debug(None)

    #   Input our monitoring rule templates
    #   They only exist in flat files and in memory - they aren't in the database
    MonitoringRule.load_tree(MONRULEINSTALL_DIR)
    print >> sys.stderr, ('Monitoring rules loaded from %s' % MONRULEINSTALL_DIR)

    execobserver_constraints = {
        'nodetype': ['Drone', 'SystemNode', 'IPaddrNode', 'ProcessNode', 'MonitorAction']
    }
    ForkExecObserver(constraints=execobserver_constraints, scriptdir=NOTIFICATION_SCRIPT_DIR)
    print >> sys.stderr, ('Fork/Event observer dispatching from %s' % NOTIFICATION_SCRIPT_DIR)


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
    if (CONFIGNAME_COMPRESSTYPE in configinfo):
        configinfo[CONFIGNAME_COMPRESS]     \
        =   pyCompressFrame(compression_method=configinfo[CONFIGNAME_COMPRESSTYPE])
    config = configinfo.complete_config()
    config[CONFIGNAME_OUTSIG] = pySignFrame(1)

    addr = config[CONFIGNAME_CMAINIT]
    if addr.port() == 0:
        addr.setport(DefaultPort)
    ourport = addr.port()
    for elem in (CONFIGNAME_CMAINIT, CONFIGNAME_CMAADDR
    ,           CONFIGNAME_CMADISCOVER, CONFIGNAME_CMAFAIL):
        if elem in config:
            config[elem] = pyNetAddr(str(config[elem]), port=ourport)
    io = pyReliableUDP(config, pyPacketDecoder())
    trycount = 0
    while True:
        try:
            cmainit.CMAinit(io, cleanoutdb=opt.erasedb, debug=(opt.debug > 0))
        except RuntimeError:
            print >> sys.stderr, 'TRYING AGAIN...'
            trycount += 1
            if trycount > 300:
                remove_pid_file(opt.pidfile)
                print >> sys.stderr, ('Neo4j still not started - giving up.')
                CMAdb.log.critical('Neo4j still not started - giving up.')
                raise SystemExit(1)
            if (trycount % 60) == 1:
                print >> sys.stderr, ('Waiting for Neo4j to start.')
                CMAdb.log.warning('Waiting for Neo4j to start.')
            # Let's try again in a second...
            time.sleep(1)
            continue
        # Neo4j started.  All is well with the world.
        break
    for warn in cryptwarnings:
        CMAdb.log.warning(warn)

    CMAdb.log.info('Listening on: %s' % str(config[CONFIGNAME_CMAINIT]))
    CMAdb.log.info('Requesting return packets sent to: %s' % str(OurAddr))
    if CMAdb.debug:
        CMAdb.log.debug('C-library Debug was set to %s' % opt.debug)
        CMAdb.log.debug('TheOneRing created - id = %s' % CMAdb.TheOneRing)
        CMAdb.log.debug('Config Object sent to nanoprobes: %s' % config)

    jvmfd = os.popen('java -version 2>&1')
    jvers = jvmfd.readline()
    jvmfd.close()
    disp = MessageDispatcher(DispatchTarget.dispatchtable)
    CMAdb.log.info('Starting CMA version %s - licensed under %s'
    %   (AssimCtypes.VERSION_STRING, LONG_LICENSE_STRING))
    CMAdb.log.info('Neo4j version %s // py2neo version %s // Python version %s // %s'
        % (('%s.%s.%s%s' % CMAdb.cdb.db.neo4j_version)
        ,   str(py2neo.__version__)
        ,   ('%s.%s.%s' % sys.version_info[0:3])
        ,   jvers))
    if opt.foreground:
        print >> sys.stderr, ('Starting CMA version %s - licensed under %s'
        %   (AssimCtypes.VERSION_STRING, LONG_LICENSE_STRING))
        print >> sys.stderr, ('Neo4j version %s // py2neo version %s // Python version %s // %s'
            % (('%s.%s.%s%s' % CMAdb.cdb.db.neo4j_version)
            ,   str(py2neo.__version__)
            ,   ('%s.%s.%s' % sys.version_info[0:3])
            ,   jvers))
    # Important to note that we don't want PacketListener to create its own 'io' object
    # or it will screw up the ReliableUDP protocol...
    listener = PacketListener(config, disp, io=io)
    mandatory_modules = [ 'discoverylistener' ]
    for mandatory in mandatory_modules:
        importlib.import_module(mandatory)
    for optional in config['optional_modules']:
        importlib.import_module(optional)
    if opt.doTrace:
        import trace
        tracer = trace.Trace(count=False, trace=True)
        if CMAdb.debug:
            CMAdb.log.debug(
            'Starting up traced listener.listen(); debug=%d' % opt.debug)
        if opt.foreground:
            print >> sys.stderr, (
            'cma: Starting up traced listener.listen() in foreground; debug=%d' % opt.debug)
        tracer.run('listener.listen()')
    else:
        if CMAdb.debug:
            CMAdb.log.debug(
            'Starting up untraced listener.listen(); debug=%d' % opt.debug)
        if opt.foreground:
            print >> sys.stderr, (
            'cma: Starting up untraced listener.listen() in foreground; debug=%d' % opt.debug)
        listener.listen()
    return 0

def supplementary_groups_for_user(userid):
    '''Return the list of supplementary groups to which this member
    would belong if they logged in as a tuple of (groupnamelist, gidlist)
    '''
    namelist=[]
    gidlist=[]
    for entry in getent.group():
        if userid in entry.members:
            namelist.append(entry.name)
            gidlist.append(entry.gid)
    return (namelist, gidlist)


def drop_privileges_permanently(userid):
    '''
    Drop our privileges permanently and run as the given user with
    the privileges to which they would be entitled if they logged in.
    That is, the uid, gid, and supplementary group list are all set correctly.
    We are careful to make sure we have exactly the permissions we need
    as 'userid'.
    Either we need to be started as root or as 'userid' or this function
    will fail and exit the program.
    '''
    userinfo = getent.passwd(userid)
    if userinfo is None:
        raise(OSError('Userid "%s" is unknown.' % userid))
    #pylint is confused about the getent.passwd object
    #pylint: disable=E1101
    newuid = userinfo.uid
    #pylint: disable=E1101
    newgid = userinfo.gid
    auxgroups = supplementary_groups_for_user(userid)[1]
    # Need to set supplementary groups, then group id then user id in that order.
    try:
        os.setgroups(auxgroups)
        os.setgid(newgid)
        os.setuid(newuid)
    except OSError:
        # We let this fail if it wants to and catch it below.
        # This allows this to work if we're already running as that user id...
        pass
    # Let's see if everything wound up as it should...
    if (os.getuid() != newuid or os.geteuid() != newuid
       or os.getgid() != newgid or os.getegid() != newgid):
        raise OSError('Could not set user/group ids to user "%s" [uid:%s, gid:%s].'
        %   (userid, os.getuid(), os.getgid()))
    # Checking groups is a little more complicated - order is potentially not preserved...
    # This also allows for the case where there might be dups (which shouldn't happen?)
    curgroups = os.getgroups()
    for elem in auxgroups:
        if elem not in curgroups:
            raise OSError('Could not set auxiliary groups for user "%s"' % userid)
    for elem in curgroups:
        # I don't think the default gid is supposed to be in the current group list...
        # but it is in my tests...  It should be harmless...
        if elem not in auxgroups and elem != newgid:
            raise OSError('Could not set auxiliary groups for user "%s"' % userid)
    # Hurray!  Everything worked!

def make_pid_dir(pidfile, userid):
    'Make a suitable directory for the pidfile'
    piddir = os.path.dirname(pidfile)
    if os.path.isdir(piddir):
        # Assume it's been set up suitably
        return
    os.mkdir(piddir, 0755)
    userinfo = getent.passwd(userid)
    if userinfo is None:
        raise(OSError('Userid "%s" is unknown.' % userid))
    # pylint doesn't understand about getent...
    # pylint: disable=E1101
    os.chown(piddir, userinfo.uid, userinfo.gid)

def make_key_dir(keydir, userid):
    'Make a suitable directory for us to store our keys in '
    if os.path.isdir(keydir):
        # Assume it's been set up suitably
        return
    os.mkdir(keydir, 0700)
    userinfo = getent.passwd(userid)
    if userinfo is None:
        raise(OSError('Userid "%s" is unknown.' % userid))
    # pylint doesn't understand about getent...
    # pylint: disable=E1101
    os.chown(keydir, userinfo.uid, userinfo.gid)

def logger(msg):
    'Log a message to syslog using logger'
    system("logger -s '%s'" % msg)

def process_main_exception(e):
    'Process an uncaught exception outside our event loop'
    trace = sys.exc_info()[2]
    tblist = traceback.extract_tb(trace, 20)
    # Put our traceback into the logs in a legible way
    logger('Got an exception in Main [%s]' % str(e))
    logger('======== Begin Main Exception Traceback ========')
    for tb in tblist:
        (filename, line, funcname, text) = tb
        filename = os.path.basename(filename)
        logger('%s.%s:%s: %s'% (filename, line, funcname, text))
    logger('======== End Main Exception Traceback ========')

if __name__ == '__main__':
    pyversion = sys.version_info
    if pyversion[0] != 2 or pyversion[1] < 7:
        raise RuntimeError('Must be run using python 2.x where x >= 7')
    # W0703 == Too general exception catching...
    # pylint: disable=W0703
    try:
        exitrc = main()
    except Exception as e:
        process_main_exception(e)

    sys.exit(int(exitrc))
