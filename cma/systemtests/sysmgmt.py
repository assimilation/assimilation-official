#!/usr/bin/env python3
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=90
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2014 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community - http://assimproj.org
# Paid support is available from Assimilation Systems Limited
# - http://assimilationsystems.com
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
"""
This file provides a basic set of classes to allow us to create a semi-realistic test
environment for testing the Assimilation project software.  We use containers
(or potentially virtual machines) to run a CMA and a bunch of nanoprobes on a system.

This file does everything to help us be able to manage these systems and the services
running on them - for the purpose of testing the Assimilation project.
"""
import tempfile, subprocess, sys, random, os, time
from logwatcher import LogWatcher


class TestSystem(object):
    "This is the base class for managing test systems for testing the Assimilation code"
    nameindex = 0
    nameformat = "%s.%05d-%05d"
    tmpprefix = ""
    tmpbasedir = "/var/tmp/"
    tmpsuffix = ".AssimTest"
    tmpdir = None
    NOTINIT = 0
    RUNNING = 1
    STOPPED = 2
    ManagedSystems = {}

    def __init__(self, imagename, imagecount=2, cmdargs=None):
        "Constructor for Abstract class TestSystem"
        self.mkname()
        TestSystem.nameindex += 1
        if TestSystem.tmpdir is None:
            TestSystem.tmpdir = tempfile.mkdtemp(
                TestSystem.tmpsuffix, TestSystem.tmpprefix, TestSystem.tmpbasedir
            )
        self.tmpfile = tempfile.mktemp(".testout", self.__class__.__name__, TestSystem.tmpdir)
        self.cmdargs = cmdargs
        self.imagename = imagename
        self.status = TestSystem.NOTINIT
        self.pid = None
        self.hostname = None
        self.ipaddr = None
        self.runningservices = []
        TestSystem.ManagedSystems[self.name] = self

    @staticmethod
    def find(name):
        "Locate the named TestSystem"
        return TestSystem.ManagedSystems[name]

    @staticmethod
    def delete(name):
        "Delete the named TestSystem"
        del TestSystem.ManagedSystems[name]

    @staticmethod
    def cleanupall():
        "Clean up all our test systems, and all their temp files"
        if TestSystem.tmpdir is None:
            return
        for mgdsys in TestSystem.ManagedSystems:
            msys = TestSystem.ManagedSystems[mgdsys]
            msys.stop()
        TestSystem.ManagedSystems = {}
        subprocess.call(("rm", "-fr", TestSystem.tmpdir))
        TestSystem.tmpdir = None
        # TestSystem.nameindex = 0

    def start(self):
        "Unimplemented start action"
        raise NotImplementedError("Abstract class - doesn't implement start")

    def stop(self):
        "Unimplemented stop action"
        raise NotImplementedError("Abstract class - doesn't implement stop")

    def destroy(self):
        "Unimplemented destroy action"
        raise NotImplementedError("Abstract class - doesn't implement destroy")

    def startservice(self, servicename, async=False):
        "start service in a container"
        if servicename in self.runningservices:
            print >>sys.stderr, (
                "WARNING: Service %s already running in system %s" % (servicename, self.name)
            )
        else:
            self.runningservices.append(servicename)
        if async:
            self.runinimage(("/bin/bash", "-c", "/etc/init.d/%s start &" % servicename))
            # self.runinimage(('/bin/bash', '-c', '/usr/sbin/service %s restart &' % servicename,))
        else:
            # self.runinimage(('/bin/bash',  ('/etc/init.d/%s' % servicename), 'start',))
            # self.runinimage(('/etc/init.d/'+servicename, 'start'))
            self.runinimage(("/usr/sbin/service", servicename, "restart"))

    def stopservice(self, servicename, async=False):
        "stop service in a container"
        if servicename in self.runningservices:
            self.runningservices.remove(servicename)
        else:
            print >>sys.stderr, (
                "WARNING: Service %s not running in system %s" % (servicename, self.name)
            )
        if async:
            self.runinimage(("/bin/sh", "-c", "/etc/init.d/%s stop &" % servicename))
        else:
            self.runinimage(("/etc/init.d/" + servicename, "stop"))

    def kill9service(self, servicename, async=False):
        "kill -9 service action"
        if servicename in self.runningservices:
            self.runningservices.remove(servicename)
        else:
            print >>sys.stderr, (
                "WARNING: Service %s not running in system %s" % (servicename, self.name)
            )
        self.runinimage(("killall", "-9", servicename))


class DockerSystem(TestSystem):
    "This class implements managing local Docker-based test systems"
    dockercmd = "/usr/bin/docker"
    nsentercmd = "/usr/bin/nsenter"

    def __init__(
        self, imagename, imagecount=2, cmdargs=None, dockerargs=None, cleanupwhendone=False
    ):
        "Constructor for DockerSystem class"
        if dockerargs is None:
            dockerargs = []
        self.dockerargs = dockerargs
        self.hostname = "unknown"
        self.ipaddr = "unknown"
        self.pid = "unknown"
        self.debug = 0
        self.cleanupwhendone = cleanupwhendone
        TestSystem.__init__(self, imagename, cmdargs=cmdargs)

    def __del__(self):
        "Invoke our destroy operation when we're deleted"
        # self.destroy()

    def mkname(self):
        self.name = TestSystem.nameformat % (
            self.__class__.__name__,
            os.getpid(),
            TestSystem.nameindex,
        )

    @staticmethod
    def run(*dockerargs):
        "Runs the docker command given by dockerargs"
        cmd = [DockerSystem.dockercmd]
        cmd.extend(dockerargs)
        # print >> sys.stderr, 'RUNNING cmd:', cmd
        rc = subprocess.check_call(cmd)
        return rc == 0

    def start(self):
        "Start a docker instance"
        if self.status == TestSystem.NOTINIT:
            runargs = [
                "run",
                "--detach=true",
                "-v",
                "/dev/urandom:/dev/random",
                "--privileged",
                "--name=%s" % self.name,
            ]
            if self.dockerargs is not None:
                runargs.extend(self.dockerargs)
            runargs.append(self.imagename)
            if self.cmdargs is not None:
                runargs.extend(self.cmdargs)
            DockerSystem.run(*runargs)
            self.status = TestSystem.RUNNING
            fd = os.popen(
                "%s %s %s %s %s"
                % (DockerSystem.dockercmd, "inspect", "--format", "{{.Config.Hostname}}", self.name)
            )
            self.hostname = fd.readline().rstrip()
            fd.close()
            fd = os.popen(
                "%s %s %s %s %s"
                % (
                    DockerSystem.dockercmd,
                    "inspect",
                    "--format",
                    "{{.NetworkSettings.IPAddress}}",
                    self.name,
                )
            )
            self.ipaddr = fd.readline().rstrip()
            fd.close()
            self.pid = self._get_docker_pid()
        elif self.status == TestSystem.STOPPED:
            DockerSystem.run("start", self.name)
            self.status = TestSystem.RUNNING
        elif self.status == TestSystem.RUNNING:
            self.stop()
            self.start()

    def _get_docker_pid(self):
        "Return the PID of a docker instance - retrying in case of error"
        j = 0
        while j < 10:
            fd = os.popen(
                "%s %s %s %s %s"
                % (DockerSystem.dockercmd, "inspect", "--format", "{{.State.Pid}}", self.name)
            )
            line = fd.readline().rstrip()
            pid = int(line)
            fd.close()
            if pid > 0:
                return pid
            print >>sys.stderr, (
                ".State.Pid is currently zero for instance %s/%s [%s]"
                % (self.name, self.hostname, line)
            )
            time.sleep(0.1)
            j += 1
        raise RuntimeError(
            ".State.Pid is zero for instance %s/%s [%s]" % (self.name, self.hostname, line)
        )

    def stop(self):
        "Stop a docker instance"
        if self.status != TestSystem.RUNNING:
            return
        os.system("logger -s 'Running services in %s: %s'" % (self.name, str(self.runningservices)))
        # self.runinimage(('/bin/echo', 'THIS IS', '/tmp/cores/*',), detached=False)
        # DockerSystem.run('top', self.name)
        DockerSystem.run("stop", self.name)
        self.status = TestSystem.STOPPED

    def destroy(self):
        "Destroy a docker instance (after stopping it if necessary)"
        if self.status == TestSystem.RUNNING:
            os.system(
                "logger -s 'Running services in %s: %s'" % (self.name, str(self.runningservices))
            )
            # self.runinimage(('/bin/echo', 'THIS IS', '/tmp/cores/*',), detached=False)
            # DockerSystem.run('top', self.name)
        DockerSystem.run("rm", "-f", self.name)
        self.status = TestSystem.NOTINIT

    def runinimage(self, cmdargs, detached=True):
        "Runs the given command on our running docker image"
        detached = detached
        if self.status != TestSystem.RUNNING:
            raise RuntimeError(
                "Docker Container %s is not running - docker exec not possible" % self.name
            )
        # self.docker_nsenter(cmdargs, detached)
        self.docker_exec(cmdargs, detached)

    def docker_nsenter(self, cmdargs, detached=True):
        "Runs the given command on our running docker image using nseneter"
        detached = detached
        args = [
            DockerSystem.nsentercmd,
            "--target",
            str(self.pid),
            "--mount",
            "--uts",
            "--ipc",
            "--pid",
            "--net",
            "--",
        ]
        args.extend(cmdargs)
        # print >> sys.stderr, 'RUNNING nsenter cmd:', args
        subprocess.check_call(args)

    def docker_exec(self, cmdargs, detached=True):
        "Runs the given command on our running docker image using docker exec"
        if self.status != TestSystem.RUNNING:
            raise RuntimeError(
                "Docker Container %s is not running - docker exec not possible" % self.name
            )
        if detached:
            args = [DockerSystem.dockercmd, "exec", "-d", str(self.name)]
        else:
            args = [DockerSystem.dockercmd, "exec", str(self.name)]
        args.extend(cmdargs)
        print >>sys.stderr, ("%s: RUNNING docker exec cmd: %s" % (time.asctime(), str(args)))
        subprocess.check_call(args)


try:
    import fabric.api
except ImportError:
    fabric = None


class VagrantSystem(TestSystem):
    "This class implements managing local Vagrant-based test systems"
    vagrantcmd = "vagrant"

    def __init__(self, imagename, imagecount=2, cmdargs=None, cleanupwhendone=False):
        "Constructor for VagrantSystem class"
        import vagrant

        assert fabric.api
        self.imagecount = imagecount
        # need to pass the number of nanoprobe VMs to Vagrant
        os_env = os.environ.copy()
        os_env["NUM_DRONES"] = str(imagecount)
        os_env["ASSIM_TEST_BOX"] = imagename
        self.v = vagrant.Vagrant(env=os_env, quiet_stdout=False, quiet_stderr=False)
        self.hostname = "unknown"
        self.ipaddr = "unknown"
        self.debug = 0
        self.cleanupwhendone = cleanupwhendone
        TestSystem.__init__(self, imagename)

    def __del__(self):
        "Invoke our destroy operation when we're deleted"
        # self.destroy()

    def mkname(self):
        if TestSystem.nameindex > 0:
            self.name = "drone%d" % TestSystem.nameindex
        else:
            self.name = "cma"

    def start(self):
        "Start a vagrant instance"
        if self.status == TestSystem.NOTINIT:
            self.v.up(vm_name=self.name)
            self.status = TestSystem.RUNNING
            fabric.api.env.host_string = self.v.user_hostname_port(vm_name=self.name).replace(
                "vagrant@", "root@"
            )
            fabric.api.env.key_filename = self.v.keyfile(vm_name=self.name)
            self.hostname = fabric.api.run("hostname")
            for l in fabric.api.run("ip address show scope global").splitlines():
                if l.find("inet") > 0 and l.find("10.0.2") == -1:
                    addr_net = l.partition("inet")[2].split()[0]
                    self.ipaddr = addr_net[0 : addr_net.index("/")]
                    break
            # there's an issue with syncing shared directory
            # at least during the provisioning
            if self.hostname == "cma":
                fabric.api.run("tar -cf cma_pubkeys.tar /usr/share/assimilation/crypto.d/*CMA*.pub")
                fabric.api.get("cma_pubkeys.tar", ".")
            # and at other times too
            else:
                fabric.api.put("cma_pubkeys.tar", ".")
                fabric.api.run("tar -C / -xf cma_pubkeys.tar")
        elif self.status == TestSystem.STOPPED:
            self.v.up(vm_name=self.name)
            self.status = TestSystem.RUNNING
        elif self.status == TestSystem.RUNNING:
            self.v.reload(vm_name=self.name)

    def stop(self):
        "Stop a vagrant instance"
        if self.status != TestSystem.RUNNING:
            return
        os.system("logger -s 'Running services in %s: %s'" % (self.name, str(self.runningservices)))
        # self.runinimage(('/bin/echo', 'THIS IS', '/tmp/cores/*',), detached=False)
        # VagrantSystem.run('top', self.name)
        self.v.halt(vm_name=self.name)
        self.status = TestSystem.STOPPED

    def destroy(self):
        "Destroy a vagrant instance (after stopping it if necessary)"
        if self.status == TestSystem.RUNNING:
            os.system(
                "logger -s 'Running services in %s: %s'" % (self.name, str(self.runningservices))
            )
            # self.runinimage(('/bin/echo', 'THIS IS', '/tmp/cores/*',), detached=False)
            # VagrantSystem.run('top', self.name)
        self.v.destroy(vm_name=self.name, force=True)
        self.status = TestSystem.NOTINIT

    def runinimage(self, cmdargs, detached=True):
        "Runs the given command on our running vm using fabric.api"
        if self.status != TestSystem.RUNNING:
            raise RuntimeError("Vagrant vm %s is not running" % self.name)
        if cmdargs[0] == "/bin/bash":
            cmd = " ".join(cmdargs[2:])
        else:
            cmd = " ".join(cmdargs)
        #        if detached:
        #            cmd = "%s &" % cmd
        fabric.api.run(cmd, shell=False)


class SystemTestEnvironment(object):
    "A basic system test environment"
    CMASERVICE = "cma"
    NANOSERVICE = "nanoprobe"
    NEO4JSERVICE = "neo4j"
    LOGGINGSERVICE = "rsyslog"
    NEO4JPASS = "neo4j2"
    NEO4JLOGIN = "neo4j"
    # pylint - too many arguments
    # pylint: disable=R0913
    def __init__(
        self,
        logname,
        nanocount,
        mgmtsystem,
        cmaimage=None,
        nanoimages=[],
        cleanupwhendone=False,
        nanodebug=0,
        cmadebug=0,
        chunksize=20,
    ):
        "Init/constructor for our SystemTestEnvironment"
        self.sysclass = DockerSystem
        if mgmtsystem.startswith("vagrant:"):
            self.sysclass = VagrantSystem
            os.chdir(mgmtsystem.split(":")[-1])
        self.cmaimage = cmaimage
        self.nanoimages = nanoimages
        self.nanocount = nanocount
        self.nanoprobes = []
        self.cma = None
        self.debug = 0
        self.cleanupwhendone = cleanupwhendone
        self.logname = logname
        watch = LogWatcher(logname, [])
        watch.setwatch()
        self.nanodebug = nanodebug
        self.cmadebug = cmadebug
        self.spawncma(nanodebug=nanodebug, cmadebug=cmadebug)
        regex = (
            " %s .* INFO: Neo4j version .* // py2neo version .*"
            " // Python version .* // (java|openjdk) version.*"
        ) % self.cma.hostname
        watch.setregexes((regex,))
        if watch.lookforall(timeout=120) is None:
            os.system("logger -s 'CMA did not start!! [[%s]]'" % (regex))
            print >>sys.stderr, "CMA did not start!! %s" % regex
            raise RuntimeError("CMA did not start: %s" % regex)
        print >>sys.stderr, "nanocount is", nanocount
        print >>sys.stderr, "self.nanoimages is", self.nanoimages
        # We do this in chunks to manage stress on our test environment
        children_left = range(0, nanocount)
        while len(children_left) > 0:
            self._create_nano_chunk(children_left[0:chunksize])
            del children_left[0:chunksize]

    def _create_nano_chunk(self, childnos):
        "Create a chunk of nanoprobes"
        watch = LogWatcher(self.logname, [], debug=0)
        watch.setwatch()
        regexes = []
        for childcount in childnos:
            childcount = childcount  # Make pylint happy...
            nano = self.spawnnanoprobe(debug=self.nanodebug)
            regexes.extend(
                [
                    r" %s nanoprobe\[.*]: NOTICE: Connected to CMA.  Happiness :-D"
                    % (nano.hostname),
                    r" %s cma INFO: Drone %s registered from address \[::ffff:%s]"
                    % (self.cma.hostname, nano.hostname, nano.ipaddr),
                    r" %s cma INFO: Processed u?n?changed tcpdiscovery"
                    r" JSON data from %s into graph." % (self.cma.hostname, nano.hostname),
                ]
            )
            self.nanoprobes.append(nano)
        print >>sys.stderr, len(regexes), "NANOPROBE REGEXES ARE:", (regexes)
        watch.setregexes(regexes)
        if watch.lookforall(timeout=120) is None:
            raise RuntimeError("Nanoprobes did not start - missing %s" % (str(watch.unmatched)))

    @staticmethod
    def _waitforloadavg(maxloadavg, maxwait=30):
        "Wait for the load average to drop below our maximum - not currently used..."
        fd = open("/proc/loadavg", "r")
        for waittry in range(0, maxwait):
            waittry = waittry  # Make pylint happy
            fd.seek(0)
            loadavg = float(fd.readline().split(" ")[0])
            if loadavg < maxloadavg:
                break
            time.sleep(1)
        fd.close()

    def _spawnsystem(self, imagename):
        "Spawn a system image"
        while True:
            try:
                # Docker has a bug where it will screw up and give us
                system = self.sysclass(
                    imagename,
                    imagecount=self.nanocount,
                    cmdargs=("/bin/bash", "-c", "while sleep 10; do wait -n; done"),
                )
                system.start()
                break
            except RuntimeError:
                # So, let's try that again...
                # This will leave some gaps in the system names, but we don't use them for anything.
                print >>sys.stderr, ("Destroying system %s and trying again..." % (system.name))
                system.destroy()
                system = None

        # And of course, start logging...
        system.startservice(SystemTestEnvironment.LOGGINGSERVICE)
        system.runinimage(("/bin/bash", "-c", "logger STARTING"))
        return system

    def set_nanoconfig(self, nano, debug=0, tcpdump=True):
        "Set up our nanoprobe configuration file"
        lines = (
            ("NANOPROBE_DYNAMIC=%d" % (1 if nano is self.cma else 0)),
            ("NANOPROBE_DEBUG=%d" % (debug)),
            ("NANOPROBE_CORELIMIT=unlimited"),
            ("NANOPROBE_CMAADDR=%s:1984" % self.cma.ipaddr),
        )

        if tcpdump:
            nano.runinimage(
                (
                    "dtach -n tcpdump.sock /usr/sbin/tcpdump -C 10 -U -s 1024 "
                    "-w /tmp/tcpdump udp port 1984 >/dev/null </dev/null 2>&1",
                )
            )
        print >>sys.stderr, ("NANOPROBE CONFIG [%s] %s" % (nano.hostname, nano.name))
        nano.runinimage(("rm", "-f", "/etc/default/nanoprobe"))
        for j in range(0, len(lines)):
            nano.runinimage(("/bin/bash", "-c", "echo '%s' >>/etc/default/nanoprobe" % lines[j]))
            # print >> sys.stderr, ('NANOPROBE [%s]' % lines[j])

    def set_cmaconfig(self, debug=0):
        "Set up our CMA configuration file"
        lines = (
            ("CMA_DEBUG=%d" % (debug)),
            ("CMA_CORELIMIT=unlimited"),
            # ('CMA_STRACEFILE=/tmp/cma.strace')
        )
        print >>sys.stderr, ("CMA CONFIG [%s]" % self.cma.hostname)
        self.cma.runinimage(("rm", "-f", "/etc/default/cma"))
        for j in range(0, len(lines)):
            self.cma.runinimage(("/bin/bash", "-c", "echo '%s' >>/etc/default/cma" % lines[j]))
            print >>sys.stderr, ("CMA [%s]" % lines[j])

    def spawncma(self, nanodebug=0, cmadebug=0):
        "Spawn a CMA instance"
        self.cma = self._spawnsystem(self.cmaimage)
        # make sure that neo4j owns its stuff
        self.cma.runinimage(("chown", "-R", "neo4j", "/var/lib/neo4j", "/var/log/neo4j"))
        self.cma.startservice(SystemTestEnvironment.NEO4JSERVICE)
        time.sleep(20)
        self.set_cmaconfig(debug=cmadebug)
        self.cma.startservice(SystemTestEnvironment.CMASERVICE)
        self.set_nanoconfig(self.cma, debug=nanodebug)
        if self.nanocount > 1:
            self.cma.startservice(SystemTestEnvironment.NANOSERVICE)
        return self.cma

    def spawnnanoprobe(self, debug=0):
        "Spawn a nanoprobe instance randomly chosen from our set of possible nanoprobes"
        image = random.choice(self.nanoimages)
        system = self._spawnsystem(image)
        system.debug = debug
        self.set_nanoconfig(system, debug=debug)
        system.startservice(SystemTestEnvironment.NANOSERVICE)
        return system

    def up_nanoprobes(self):
        "Return the set of nanoprobe systems which are currently running"
        return [nano for nano in self.nanoprobes if nano.status == TestSystem.RUNNING]

    def down_nanoprobes(self):
        "Return the set of nanoprobe systems which are currently down"
        return [nano for nano in self.nanoprobes if nano.status != TestSystem.RUNNING]

    def select_nanoprobe(self, count=1):
        "Select a system at random"
        result = []
        while len(self.nanoprobes) > 0:
            nano = random.choice(self.nanoprobes)
            if nano not in result:
                result.append(nano)
                if len(result) == count:
                    break
        return result

    def select_up_nanoprobe(self, count=1):
        "Select a nanoprobe system at random which is currently up"
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
        "Select a nanoprobe system at random which is currently down"
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
        "Select a system currently running the given service"
        result = []
        servlist = [
            nano
            for nano in self.nanoprobes
            if nano.status == TestSystem.RUNNING and service in nano.runningservices
        ]
        while len(servlist) > 0:
            nano = random.choice(servlist)
            if nano not in result:
                result.append(nano)
                servlist.remove(nano)
            if len(result) == count or len(servlist) == 0:
                break
        return result

    def select_nano_noservice(self, service=NANOSERVICE, count=1):
        "Select a system NOT currently running the given service"
        result = []
        servlist = [
            nano
            for nano in self.nanoprobes
            if nano.status == TestSystem.RUNNING and service not in nano.runningservices
        ]
        while len(servlist) > 0:
            nano = random.choice(servlist)
            if nano not in result:
                result.append(nano)
                servlist.remove(nano)
            if len(result) == count or len(servlist) == 0:
                break
        return result

    def stop(self):
        "Stop our entire SystemTestEnvironment"
        for onenano in self.nanoprobes:
            onenano.stop()
        self.cma.stop()

    def __del__(self):
        "Clean up any images we created"
        if self.cleanupwhendone:
            for nano in self.nanoprobes:
                if nano.cleanupwhendone:
                    nano.destroy()
            self.nanoprobes = []
            if self.cma is not None:
                if self.cma.cleanupwhendone:
                    self.cma.destroy()
                    self.cma = None


# A little test code...
if __name__ == "__main__":

    def testmain(logname):
        "A simple test main program"
        print >>sys.stderr, "Initializing:"
        env = SystemTestEnvironment(logname, 3)
        print >>sys.stderr, "Systems all up and running!"
        for j in range(0, len(env.nanoprobes)):
            nano = env.nanoprobes[j]
            print >>sys.stderr, "Stopping nanoprobe on the %d one [%s]!" % (j, nano.name)
            nano.stopservice(SystemTestEnvironment.NANOSERVICE)
        env.stop()
        env = None
        print >>sys.stderr, "All systems after deletion:", TestSystem.ManagedSystems

    testmain("/var/log/syslog")
