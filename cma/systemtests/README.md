System testing
--------------

This is the system testing machinery, based on VM/container
systems.

Either docker or vagrant is required for VM management.

It is also necessary to configure your host's syslog for remote
logging. For instance, for rsyslog, one can use something like
this:

	module(load="imtcp")
	input(type="imtcp" port="514")

	if $fromhost-ip startswith '172.17.' or $HOSTNAME == 'cma' or $HOSTNAME startswith 'drone' then {
		/var/log/assim.log
		stop
	}

Just put that in /etc/rsyslog.d/assim.conf and you should be OK.
Make sure that the user with which you run tests have read access
to the log file. Or just do this:

	$ sudo chmod 644 /var/log/assim.log

The script to start the tests is runtests.sh. Example use for
vagrant:

	$ sh runtests.sh -l /var/log/assim.log -m vagrant -C generic/ubuntu1604 -N debian/stretch64 20

Example for docker:

	$ sh runtests.sh -l /var/log/assim.log 20

Docker
------

The tests use docker containers by default. They can be run
without any further configuration after successfully building
packages in the docker directory which is at the top of the
project.

Vagrant
-------

The vagrant's Vagrantfile as well as provisioning shell scripts
are in the vagrant directory. The scripts were developed on a
Debian Stretch release. They work for most of Ubuntu releases
such as xenial or artful. For other Debian/Ubuntu releases minor
modifications may be necessary.

The provider is libvirt, so install the vagrant-libvirt plugin.

The timezone is set with the vagrant-timezone plugin.

The Vagrantfile features also the configuration for
apt-cacher-ng. It is not strictly required, but reduces runtime
considerably.

To run the tests as a regular user, add the user to the following
groups: kvm libvirt libvirt-qemu.

Here are the commands you may have to run to setup the
environment:

$ sudo usermod -a -G kvm,libvirt,libvirt-qemu <user>
$ sudo apt-get install vagrant-libvirt apt-cacher-ng
$ vagrant plugin install vagrant-timezone

Before running the tests, copy the cma, nanoprobe, and libsodium
debian packages to a subdirectories named after test boxes
provided with "-C" and "-N" options. For instance, for
debian/stretch64:

$ cd vagrant
$ mkdir -p debian/stretch64

The VMs are going to be named "cma" (for the cma) and "drone%n"
(for drones/nanoprobes) where "%n" stands for a drone number (a
small integer). The drone VMs count starts at 1.

Vagrant ssh command is quite slow. To access VMs with ssh or pdsh
do the following:

$ cd vagrant
$ . mksshconf.sh
$ ssh -F ssh_config <hostname>

To run commands on all VMs with pdsh:

$ pdsh date
drone1: Wed Mar 28 15:30:30 UTC 2018
cma: Wed Mar 28 15:30:30 UTC 2018
drone2: Wed Mar 28 15:30:30 UTC 2018

