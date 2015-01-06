#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2014 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community - http://assimproj.org
# Paid support is available from Assimilation Systems Limited - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
'''
This file provides a basic set of classes to allow us to create a semi-realistic test environment
for testing the Assimilation project software.  We use containers (or potentially virtual machines)
to run a CMA and a bunch of nanoprobes on a system.

This file does everything to help us be able to manage these systems and the services
running on them - for the purpose of testing the Assimilation project.
'''
import tempfile, subprocess, sys, itertools, random, os, time
from logwatcher import LogWatcher
class TestSystem(object):
    'This is the base class for managing test systems for testing the Assimilation code'
    nameindex = 0
    nameformat = '%s.%05d-%05d'
    tmpprefix = ''
    tmpbasedir = '/var/tmp/'
    tmpsuffix = '.AssimTest'
    tmpdir = None
    NOTINIT = 0
    RUNNING = 1
    STOPPED = 2
    ManagedSystems = {}

    def __init__(self, imagename, cmdargs=None):
        'Constructor for Abstract class TestSystem'
        self.name = TestSystem.nameformat % (self.__class__.__name__, os.getpid()
        ,   TestSystem.nameindex)
        TestSystem.nameindex += 1
        if TestSystem.tmpdir is None:
            TestSystem.tmpdir = tempfile.mkdtemp(TestSystem.tmpsuffix
            ,       TestSystem.tmpprefix, TestSystem.tmpbasedir)
        self.tmpfile = tempfile.mktemp('.testout', self.__class__.__name__, TestSystem.tmpdir)
        self.cmdargs = cmdargs
        self.imagename = imagename
        self.status = TestSystem.NOTINIT
        self.pid = None
        self.hostname = None
        self.ipaddr = None
        TestSystem.ManagedSystems[self.name] = self

    @staticmethod
    def find(name):
        'Locate the named TestSystem'
        return TestSystem.ManagedSystems[name]

    @staticmethod
    def delete(name):
        'Delete the named TestSystem'
        del TestSystem.ManagedSystems[name]

    @staticmethod
    def cleanupall():
        'Clean up all our test systems, and all their temp files'
        if TestSystem.tmpdir is None:
            return
        for mgdsys in TestSystem.ManagedSystems:
            msys = TestSystem.ManagedSystems[mgdsys]
            msys.stop()
        TestSystem.ManagedSystems = {}
        subprocess.call(('rm', '-fr', TestSystem.tmpdir))
        TestSystem.tmpdir = None
        #TestSystem.nameindex = 0

    def start(self):
        'Unimplemented start action'
        raise NotImplementedError("Abstract class - doesn't implement start")

    def stop(self):
        'Unimplemented stop action'
        raise NotImplementedError("Abstract class - doesn't implement stop")

    def destroy(self):
        'Unimplemented destroy action'
        raise NotImplementedError("Abstract class - doesn't implement destroy")

    def __del__(self):
        "Invoke our destroy operation when we're deleted"
        #self.destroy()

    def startservice(self, servicename, async=False):
        'Unimplemented start service action'
        raise NotImplementedError("Abstract class - doesn't implement startservice")

    def stopservice(self, servicename, async=False):
        'Unimplemented stop service action'
        raise NotImplementedError("Abstract class - doesn't implement stopservice")


class DockerSystem(TestSystem):
    'This class implements managing local Docker-based test systems'
    dockercmd = '/usr/bin/docker.io'
    servicecmd = '/usr/bin/service'

    def __init__(self, imagename, cmdargs=None, dockerargs=None):
        'Constructor for Abstract class TestSystem'
        if dockerargs is None:
            dockerargs = []
        self.dockerargs = dockerargs
        self.runningservices = []
        self.hostname = 'unknown'
        self.ipaddr = 'unknown'
        self.pid = 'unknown'
        self.debug = 0
        TestSystem.__init__(self, imagename, cmdargs=cmdargs)

    @staticmethod
    def run(*dockerargs):
        'Runs the docker command given by dockerargs'
        cmd = [DockerSystem.dockercmd,]
        cmd.extend(dockerargs)
        print >> sys.stderr, 'RUNNING cmd:', cmd
        rc = subprocess.check_call(cmd)
        return rc == 0


    def start(self):
        'Start a docker instance'
        if self.status == TestSystem.NOTINIT:
            runargs = ['run', '--detach=true', '-v', '/dev/urandom:/dev/random', '--privileged'
            ,       '--name=%s' % self.name]
            if self.dockerargs is not None:
                runargs.extend(self.dockerargs)
            runargs.append(self.imagename)
            if self.cmdargs is not None:
                runargs.extend(self.cmdargs)
            DockerSystem.run(*runargs)
            self.status = TestSystem.RUNNING
            fd = os.popen('%s %s %s %s %s'
            %   (DockerSystem.dockercmd , 'inspect', '--format', '{{.Config.Hostname}}', self.name))
            self.hostname = fd.readline().rstrip()
            fd.close()
            fd = os.popen('%s %s %s %s %s'
            %   (DockerSystem.dockercmd , 'inspect', '--format', '{{.NetworkSettings.IPAddress}}'
            ,       self.name))
            self.ipaddr = fd.readline().rstrip()
            fd.close()
            self.pid = self._get_docker_pid()
        elif self.status == TestSystem.STOPPED:
            DockerSystem.run('start', self.name)
            self.status = TestSystem.RUNNING
        elif self.status == TestSystem.RUNNING:
            self.stop()
            self.start()

    def _get_docker_pid(self):
        'Return the PID of a docker instance - retrying in case of error'
        j=0
        while j < 10:
            fd = os.popen('%s %s %s %s %s'
            %   (DockerSystem.dockercmd , 'inspect', '--format', '{{.State.Pid}}', self.name))
            line = fd.readline().rstrip()
            pid = int(line)
            fd.close()
            if pid > 0:
                return pid
            print >> sys.stderr, ('.State.Pid is currently zero for instance %s/%s [%s]'
            %   (self.name, self.hostname, line))
            time.sleep(.1)
            j += 1
        raise RuntimeError('.State.Pid is zero for instance %s/%s [%s]'
        %   (self.name, self.hostname, line))

    def stop(self):
        'Stop a docker instance'
        if self.status != TestSystem.RUNNING:
            return
        DockerSystem.run('stop', self.name)
        self.status = TestSystem.STOPPED
        self.pid = None

    def destroy(self):
        'Destroy a docker instance (after stopping it if necessary)'
        DockerSystem.run('rm', '-f', self.name)
        self.status = TestSystem.NOTINIT


    def runinimage(self, cmdargs, detached=True):
        'Runs the given command on our running docker image'
        if self.status != TestSystem.RUNNING:
            raise RuntimeError('Docker Container %s is not running - docker exec not possible'
            %   self.name)
        if detached:
            args = [DockerSystem.dockercmd, 'exec', '-d', str(self.name) ]
        else:
            args = [DockerSystem.dockercmd, 'exec', str(self.name) ]
        args.extend(cmdargs)
        #print >> sys.stderr, 'RUNNING docker exec cmd:', args
        subprocess.check_call(args)

    def startservice(self, servicename, async=False):
        'docker-exec-based start service action for docker'
        if servicename in self.runningservices:
            print >> sys.stderr, ('WARNING: Service %s already running in docker system %s'
            %       (servicename, self.name))
        else:
            self.runningservices.append(servicename)
        if async:
            self.runinimage(('/bin/sh', '-c', '/etc/init.d/%s start &' % servicename,))
        else:
            self.runinimage(('/etc/init.d/'+servicename, 'start'))

    def stopservice(self, servicename, async=False):
        'docker-exec-based stop service action for docker'
        if servicename in self.runningservices:
            self.runningservices.remove(servicename)
        else:
            print >> sys.stderr, ('WARNING: Service %s not running in docker system %s'
            %       (servicename, self.name))
        if async:
            self.runinimage(('/bin/sh', '-c', '/etc/init.d/%s stop &' % servicename,))
        else:
            self.runinimage(('/etc/init.d/'+servicename, 'stop'))


class SystemTestEnvironment(object):
    'A basic system test environment'
    CMASERVICE      = 'cma'
    NANOSERVICE     = 'nanoprobe'
    NEO4JSERVICE    = 'neo4j-service'
    LOGGINGSERVICE  = 'rsyslog'
    # pylint - too many arguments
    # pylint: disable=R0913
    def __init__(self, logname, nanocount=10
    ,       cmaimage='cma.ubuntu', nanoimages=('cma.ubuntu',)
    ,       sysclass=DockerSystem, cleanupwhendone=True, nanodebug=0, cmadebug=0):
        'Init/constructor for our SystemTestEnvironment'
        self.sysclass = sysclass
        self.cmaimage = cmaimage
        self.nanoimages = nanoimages
        self.nanoprobes = []
        self.cma = None
        self.debug = 0
        self.cleanupwhendone = cleanupwhendone
        watch = LogWatcher(logname, [])
        watch.setwatch()
        self.spawncma(nanodebug=nanodebug, cmadebug=cmadebug)
        regex = (' %s .* INFO: Neo4j version .* // py2neo version .*'
                ' // Python version .* // java version.*') % self.cma.hostname
        watch.setregexes((regex,))
        if watch.lookforall(timeout=60) is None:
            raise RuntimeError('CMA did not start')
        print >> sys.stderr, 'nanocount is', nanocount
        print >> sys.stderr, 'self.nanoimages is', self.nanoimages
        # pylint doesn't think we need a lambda: function here.  I'm pretty sure it's wrong.
        # this is because we return a different nanoprobe each time we call spawnnanoprobe()
        # pylint: disable=W0108
        for child in itertools.repeat(lambda: self.spawnnanoprobe(debug=4), nanocount):
            self.nanoprobes.append(child())
            os.system('logger "Load Avg: $(cat /proc/loadavg)"')
            os.system('logger "$(grep MemFree: /proc/meminfo)"')
            self._waitforloadavg(8, 120)

    @staticmethod
    def _waitforloadavg(maxloadavg, maxwait=30):
        'Wait for the load average to drop below our maximum'
        fd = open('/proc/loadavg', 'r')
        for waittry in range(0, maxwait):
            waittry = waittry # Make pylint happy
            fd.seek(0)
            loadavg = float(fd.readline().split(' ')[0])
            if loadavg < maxloadavg:
                break
            time.sleep(1)
        fd.close()



    def _spawnsystem(self, imagename):
        'Spawn a system image'
        while True:
            try:
                # Docker has a bug where it will screw up and give us
                system = self.sysclass(imagename
                ,   ('/bin/bash', '-c', 'while sleep 10; do wait -n; done'))
                system.start()
                break
            except RuntimeError:
                # So, let's try that again...
                # This will leave some gaps in the system names, but we don't use them for anything.
                print  >> sys.stderr, ('Destroying system %s and trying again...' % (system.name))
                system.destroy()
                system = None

        system.runinimage(('/bin/bash', '-c', 'mkdir /tmp/cores'))
        #system.runinimage(('/bin/bash', '-c'
        #,                  'echo "/tmp/cores/core.%e.%p" > /proc/sys/kernel/core_pattern'))
        # Set up logging to be forwarded to our parent logger
        system.runinimage(('/bin/bash', '-c'
        ,   '''PARENT=$(/sbin/route | grep '^default' | cut -c17-32); PARENT=$(echo $PARENT);'''
        +   ''' echo '*.*   @@'"${PARENT}:514" > /etc/rsyslog.d/99-remote.conf'''))
        # And of course, start logging...
        system.startservice(SystemTestEnvironment.LOGGINGSERVICE)
        return system

    def set_nanoconfig(self, nano, debug=3, CMApubkey=None):
        'Set up our nanoprobe configuration file'
        lines = (
            ('NANOPROBE_DYNAMIC=%d' % (1 if nano is self.cma else 0)),
            ('NANOPROBE_DEBUG=%d' % (debug)),
            ('NANOPROBE_CORELIMIT=unlimited'),
            ('NANOPROBE_CMAADDR=%s:1984' % self.cma.ipaddr)
        )
        nano.runinimage(('/bin/bash', '-c'
        ,           "echo '%s' >/etc/default/nanoprobe" % lines[0]))
        print >> sys.stderr, ('NANOPROBE CONFIG [%s]' % nano.hostname)
        for j in range(1, len(lines)):
            nano.runinimage(('/bin/bash', '-c'
            ,           "echo '%s' >>/etc/default/nanoprobe" % lines[j]))
            print >> sys.stderr, ('NANOPROBE [%s]' % lines[j])

    def set_cmaconfig(self, debug=5):
        'Set up our CMA configuration file'
        lines = ( ('CMA_DEBUG=%d' % (debug)),
                  ('CMA_CORELIMIT=unlimited'),
                  #('CMA_STRACEFILE=/tmp/cma.strace')
        )
        self.cma.runinimage(('/bin/bash', '-c'
        ,           "echo '%s' >/etc/default/cma" % lines[0]))
        print >> sys.stderr, ('CMA CONFIG [%s]' % self.cma.hostname)
        print >> sys.stderr, ('CMA [%s]' % lines[0])
        for j in range(1, len(lines)):
            self.cma.runinimage(('/bin/bash', '-c'
            ,           "echo '%s' >>/etc/default/cma" % lines[j]))
            print >> sys.stderr, ('CMA [%s]' % lines[j])



    def spawncma(self, nanodebug=0, cmadebug=0):
        'Spawn a CMA instance'
        self.cma = self._spawnsystem(self.cmaimage)
        self.cma.runinimage(('/bin/bash', '-c'
        ,           'echo CMA_DEBUG=0 >/etc/default/cma'))
        self.cma.runinimage(('/bin/bash', '-c'
        ,   'echo "org.neo4j.server.webserver.address=0.0.0.0" '
            '>> /var/lib/neo4j/conf/neo4j-server.properties'))
        self.cma.startservice(SystemTestEnvironment.NEO4JSERVICE)
        self.set_cmaconfig(debug=cmadebug)
        self.cma.startservice(SystemTestEnvironment.CMASERVICE)
        self.set_nanoconfig(self.cma, debug=nanodebug)
        self.cma.startservice(SystemTestEnvironment.NANOSERVICE)
        time.sleep(5)
        return self.cma

    def spawnnanoprobe(self, debug=0):
        'Spawn a nanoprobe instance randomly chosen from our set of possible nanoprobes'
        image = random.choice(self.nanoimages)
        system = self._spawnsystem(image)
        system.debug = debug
        self.set_nanoconfig(system, debug=debug, CMApubkey='/tmp/#CMA#00000.pub')
        system.startservice(SystemTestEnvironment.NANOSERVICE)
        return system

    def up_nanoprobes(self):
        'Return the set of nanoprobe systems which are currently running'
        return [nano for nano in self.nanoprobes if nano.status == TestSystem.RUNNING]

    def down_nanoprobes(self):
        'Return the set of nanoprobe systems which are currently down'
        return [nano for nano in self.nanoprobes if nano.status != TestSystem.RUNNING]

    def select_nanoprobe(self, count=1):
        'Select a system at random'
        result = []
        while len(self.nanoprobes) > 0:
            nano = random.choice(self.nanoprobes)
            if nano not in result:
                result.append(nano)
                if len(result) == count:
                    break
        return result

    def select_up_nanoprobe(self, count=1):
        'Select a nanoprobe system at random which is currently up'
        result = []
        uplist = self.up_nanoprobes()
        while len(uplist) > 0:
            nano = random.choice(uplist)
            if nano not in result:
                result.append(nano)
                uplist.remove(nano)
            if len(result) == count or len(uplist) == 0:
                break
        return result

    def select_down_nanoprobe(self, count=1):
        'Select a nanoprobe system at random which is currently down'
        result = []
        downlist = self.down_nanoprobes()
        while True:
            nano = random.choice(downlist)
            if nano not in result:
                result.append(nano)
                downlist.remove(nano)
            if len(result) == count or len(downlist) == 0:
                break
        return result

    def select_nano_service(self, service=NANOSERVICE, count=1):
        'Select a system currently running the given service'
        result = []
        servlist = [nano for nano in self.nanoprobes
            if nano.status == TestSystem.RUNNING and service in nano.runningservices]
        while len(servlist) > 0:
            nano = random.choice(servlist)
            if nano not in result:
                result.append(nano)
                servlist.remove(nano)
            if len(result) == count or len(servlist) == 0:
                break
        return result

    def select_nano_noservice(self, service=NANOSERVICE, count=1):
        'Select a system NOT currently running the given service'
        result = []
        servlist = [nano for nano in self.nanoprobes
            if nano.status == TestSystem.RUNNING and service not in nano.runningservices]
        while len(servlist) > 0:
            nano = random.choice(servlist)
            if nano not in result:
                result.append(nano)
                servlist.remove(nano)
            if len(result) == count or len(servlist) == 0:
                break
        return result


    def stop(self):
        'Stop our entire SystemTestEnvironment'
        for onenano in self.nanoprobes:
            onenano.stop()
        self.cma.stop()

    def __del__(self):
        'Clean up any images we created'
        if self.cleanupwhendone:
            for nano in self.nanoprobes:
                nano.destroy()
            self.nanoprobes = []
            if self.cma is not None:
                self.cma.destroy()
                self.cma = None


# A little test code...
if __name__ == '__main__':
    def testmain(logname):
        'A simple test main program'
        print >> sys.stderr, 'Initializing:'
        env = SystemTestEnvironment(logname, 5)
        print >> sys.stderr, 'Systems all up and running!'
        time.sleep(5)
        for j in range(0,len(env.nanoprobes)):
            print >> sys.stderr, 'Stopping nanoprobe on the %d one!' % j
            nano = env.nanoprobes[j]
            nano.stopservice(SystemTestEnvironment.NANOSERVICE)
            time.sleep(20)
        time.sleep(120)
        env.stop()
        env = None
        print >> sys.stderr, 'All systems after deletion:', TestSystem.ManagedSystems
    testmain('/var/log/syslog')
