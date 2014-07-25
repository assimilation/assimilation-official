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
import tempfile, subprocess, sys, itertools, random
class TestSystem(object):
    'This is the base class for managing test systems for testing the Assimilation code'
    nameindex = 0
    nameformat = '%s.%05d'
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
        self.name = TestSystem.nameformat % (self.__class__.__name__, TestSystem.nameindex)
        TestSystem.nameindex += 1
        if TestSystem.tmpdir is None:
            TestSystem.tmpdir = tempfile.mkdtemp(TestSystem.tmpsuffix
            ,       TestSystem.tmpprefix, TestSystem.tmpbasedir)
        self.tmpfile = tempfile.mktemp('.testout', self.__class__.__name__, TestSystem.tmpdir)
        self.cmdargs = cmdargs
        self.imagename = imagename
        self.status = TestSystem.NOTINIT
        self.pid = None
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
        TestSystem.nameindex = 0

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
        if self.status == TestSystem.NOTINIT:
            runargs = ['run', '--detach=true', '--name=%s' % self.name, self.imagename]
            if self.cmdargs != None:
                runargs.extend(self.cmdargs)
            DockerSystem.run(*runargs)
            self.status = TestSystem.RUNNING
            #FIXME: Need to do this!
            #PID=$(docker inspect --format {{.State.Pid}} <container_name_or_ID>)
            fd = os.popen('%s %s %s %s %s'
            %   (DockerSystem.dockercmd , 'inspect', '--format', '{{.State.Pid}}', self.name))
            self.pid = int(fd.readline())
            fd.close()
        elif self.status == TestSystem.STOPPED:
            DockerSystem.run('restart', self.name)
            self.status = TestSystem.RUNNING
        elif self.status == TestSystem.RUNNING:
            self.stop()
            self.start()

    def stop(self):
        'Stop a docker instance'
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
        print >> sys.stderr, 'RUNNING nsenter cmd:', cmd
        rc = subprocess.check_call(args)


    def start(self):
        'Start a docker instance'
        if self.status == TestSystem.NOTINIT:
            runargs = ['run', '--detach=true', '--name=%s' % self.name, self.imagename]
            if self.cmdargs != None:
                runargs.extend(self.cmdargs)
            DockerSystem.run(*runargs)
            self.status = TestSystem.RUNNING

    def startservice(self, servicename):
        'nsenter-based start service action for docker'
        self._nsenter((DockerSystem.servicecmd, servicename, 'start'))

    def stopservice(self):
        'nsenter-based stop service action for docker'
        self._nsenter((DockerSystem.servicecmd, servicename, 'stop'))


class SystemTestEnvironment(object):
    'A basic system test environment'
    CMASERVICE = 'cma'
    NANOSERVICE = 'nanoprobe'
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
        for child in itertools.repeat(lambda: self._spawnnanoprobe(), nanocount):
            self.nanoprobes.append(child)

    def _spawnsystem(self, imagename):
        system = self.sysclass(imagename, ('/bin/sleep', '1000000000'))
        system.start()
        return system

    def _spawncma(self):
        'Spawn a CMA instance'
        os = self._spawnsystem(self.cmaimage)
        os.startservice(SystemTestEnvironment.CMASERVICE)
        time.sleep(5)
        os.startservice(SystemTestEnvironment.NANOSERVICE)
        self.cma = os

    def _spawnnanoprobe(self):
        'Spawn a nanoprobe instance randomly chosen from our set of possible nanoprobes'
        image = random.choice(self.nanoprobes)
        os = self._spawnsystem(image)
        os.startservice(SystemTestEnvironment.NANOSERVICE)

    def stop(self):
        for nano in self.nanoprobes():
            nano.stop()
        self.cma.stop()


# A little test code...
if __name__ == '__main__':
    print >> sys.stderr, 'Initializing:'
    env = SystemTestEnvironment(5)
    os.sleep(10)
    env.stop()
    env = None
    TestSystem.cleanupall()
    for count in range(0, 5):
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
    env = SystemTestEnvironment(5)
    os.sleep(10)
    env.stop()
    env = None
    TestSystem.cleanupall()
    print >> sys.stderr, 'All systems after deletion:', TestSystem.ManagedSystems
