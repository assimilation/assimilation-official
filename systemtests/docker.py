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
for testing the Assimilation project software.  We use containers (or potentially virtual machines) to
run a CMA and a bunch of nanoprobes on a system.
'''
import tempfile, subprocess, sys, itertools, random, os, time
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
        self.name = TestSystem.nameformat % (self.__class__.__name__, os.getpid(), TestSystem.nameindex)
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
        self.destroy()

    def startservice(self):
        'Unimplemented start service action'
        raise NotImplementedError("Abstract class - doesn't implement startservice")

    def stopservice(self):
        'Unimplemented stop service action'
        raise NotImplementedError("Abstract class - doesn't implement stopservice")


class DockerSystem(TestSystem):
    'This class implements managing local Docker-based test systems'
    dockercmd = '/usr/bin/docker.io'
    nsentercmd = '/usr/local/bin/nsenter'
    servicecmd = '/usr/bin/service'

    def __init__(self, imagename, cmdargs=None, dockerargs=None):
        'Constructor for Abstract class TestSystem'
        if dockerargs is None:
            dockerargs = ('-v', '/dev/log:/dev/log')
        self.dockerargs = dockerargs
        self.runningservices = []
        print 'SELF.DOCKERARGS = ', self.dockerargs
        TestSystem.__init__(self, imagename, cmdargs=cmdargs)

    @staticmethod
    def run(*dockerargs):
        'Runs the docker command given by dockerargs'
        cmd = [DockerSystem.dockercmd,]
        cmd.extend(dockerargs)
        # @FIXME: Or should this be subprocess.check_call()?
        # @FIXME: Or even subprocess.popen?
        #rc = subprocess.call(cmd)
        print >> sys.stderr, 'RUNNING cmd:', cmd
        rc = subprocess.check_call(cmd)
        return rc == 0


    def start(self):
        'Start a docker instance'
        print 'Looking in Start: SELF.DOCKERARGS = ', self.dockerargs
        if self.status == TestSystem.NOTINIT:
            runargs = ['run', '--detach=true', '--name=%s' % self.name]
            print 'Looking: SELF.DOCKERARGS = ', self.dockerargs
            if self.dockerargs is not None:
                runargs.extend(self.dockerargs)
            runargs.append(self.imagename)
            if self.cmdargs is not None:
                runargs.extend(self.cmdargs)
            DockerSystem.run(*runargs)
            self.status = TestSystem.RUNNING
            fd = os.popen('%s %s %s %s %s'
            %   (DockerSystem.dockercmd , 'inspect', '--format', '{{.State.Pid}}', self.name))
            self.pid = int(fd.readline())
            fd.close()
            fd = os.popen('%s %s %s %s %s'
            %   (DockerSystem.dockercmd , 'inspect', '--format', '{{.Config.Hostname}}', self.name))
            self.hostname = fd.readline()
            fd.close()
        elif self.status == TestSystem.STOPPED:
            DockerSystem.run('restart', self.name)
            self.status = TestSystem.RUNNING
        elif self.status == TestSystem.RUNNING:
            self.stop()
            self.start()

    def stop(self):
        'Stop a docker instance'
        if self.status != TestSystem.RUNNING:
            return
        DockerSystem.run('stop', self.name)
        self.status = TestSystem.STOPPED
        self.pid = None

    def destroy(self):
        'Destroy a docker instance (after stopping it if necessary)'
        if self.status == TestSystem.RUNNING:
            self.stop()
        DockerSystem.run('rm', self.name)
        self.status = TestSystem.NOTINIT


    def _nsenter(self, nsenterargs):
        'Runs the given command on our running docker image'
        if self.status != TestSystem.RUNNING:
            raise RuntimeError('Docker Container %s is not running - nsenter not possible' % self.name)
        args = [DockerSystem.nsentercmd, '--target', str(self.pid)
        , '--mount', '--uts',  '--ipc', '--net', '--pid', '--']
        args.extend(nsenterargs)
        print >> sys.stderr, 'RUNNING nsenter cmd:', args
        rc = subprocess.check_call(args)

    def startservice(self, servicename):
        'nsenter-based start service action for docker'
        if servicename in self.runningservices:
            print >> sys.stderr, ('WARNING: Service %s already running in docker system %s'
            %       (servicename, self.name))
        else:
            self.runningservices.append(servicename)
        self._nsenter(('/etc/init.d/'+servicename, 'start'))

    def stopservice(self, servicename):
        'nsenter-based stop service action for docker'
        if servicename in self.runningservices:
            self.runningservices.remove(servicename)
        else:
            print >> sys.stderr, ('WARNING: Service %s not running in docker system %s'
            %       (servicename, self.name))
        self._nsenter(('/etc/init.d/'+servicename, 'stop'))


class SystemTestEnvironment(object):
    'A basic system test environment'
    CMASERVICE      = 'cma'
    NANOSERVICE     = 'nanoprobe'
    NEO4JSERVICE    = 'neo4j-service'
    LOGGINGSERVICE  = 'rsyslogd'
    def __init__(self, nanocount=10
    ,       cmaimage='cma.ubuntu', nanoimages=('nanoprobe.ubuntu',)
    ,       sysclass=DockerSystem):
        'Init/constructor for our SystemTestEnvironment'
        self.sysclass = sysclass
        self.cmaimage = cmaimage
        self.nanoimages = nanoimages
        self.nanoprobes = []
        self.cma = None

        cma = self._spawncma()
        print >> sys.stderr, 'nanocount is', nanocount
        print >> sys.stderr, 'self.nanoimages is', self.nanoprobes
        for child in itertools.repeat(lambda: self._spawnnanoprobe(), nanocount):
            self.nanoprobes.append(child())

    def _spawnsystem(self, imagename):
        system = self.sysclass(imagename, ('/bin/sleep', '1000000000'))
        system.start()
        # Set up logging to be forwarded to our parent logger
        os._nsenter(self, '/bin/bash', '-c'
        ,   '''PARENT=$(/sbin/route | grep '^default' | cut -c17-32); PARENT=$(echo $PARENT);'''
        +   ''' echo '*.*   @@'"${PARENT}:514" > /etc/rsyslog.d/99-remote.conf''')
        # And of course, start logging...
        system.startservice(SystemTestEnvironment.LOGGINGSERVICE)
        return system

    def _spawncma(self):
        'Spawn a CMA instance'
        os = self._spawnsystem(self.cmaimage)
        os._nsenter(self, '/bin/bash', '-c'
        ,           'echo NANOPROBE_DYNAMIC=1 >/etc/default/assimilation'):
        os.startservice(SystemTestEnvironment.NEO4JSERVICE)
        os.startservice(SystemTestEnvironment.CMASERVICE)
        os.startservice(SystemTestEnvironment.NANOSERVICE)
        self.cma = os
        #os._nsenter(('ps', '-efl'))
        return os

    def _spawnnanoprobe(self):
        'Spawn a nanoprobe instance randomly chosen from our set of possible nanoprobes'
        image = random.choice(self.nanoimages)
        os = self._spawnsystem(image)
        os.startservice(SystemTestEnvironment.LOGGINGSERVICE)
        os.startservice(SystemTestEnvironment.NANOSERVICE)
        return os

    def stop(self):
        for nano in self.nanoprobes:
            nano.stop()
        self.cma.stop()


# A little test code...
if __name__ == '__main__':
    print >> sys.stderr, 'Initializing:'
    #env = SystemTestEnvironment(5)
    #s.sleep(10)
    #nv.stop()
    #nv = None
    #TestSystem.cleanupall()
    for count in range(0, 5):
        continue
        onesys = DockerSystem('nanoprobe.ubuntu', ('/usr/bin/nanoprobe', '--foreground'))
        print >> sys.stderr, 'Started:'
        onesys.start()
        print >> sys.stderr, 'Stopped:'
        onesys.stop()
        print >> sys.stderr, '(re)-started:'
        onesys.start()
        print >> sys.stderr, 'FIND result:', TestSystem.find(onesys.name)
    print >> sys.stderr, 'All systems:', TestSystem.ManagedSystems
    TestSystem.cleanupall()
    print >> sys.stderr, 'All systems after deletion:', TestSystem.ManagedSystems
    env = SystemTestEnvironment(3)
    time.sleep(90)
    env.stop()
    env = None
    TestSystem.cleanupall()
    print >> sys.stderr, 'All systems after deletion:', TestSystem.ManagedSystems