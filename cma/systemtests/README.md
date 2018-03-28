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

	$ sh runtests.sh -l /var/log/assim.log -m vagrant -C cma -N drone 20

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
are in the vagrant directory. The base box is Debian Stretch. We
used this one:

https://app.vagrantup.com/debian/boxes/stretch64

The provider to use is libvirt, so install the vagrant-libvirt
plugin.

To run the tests as a regular user, add yourself to the following
groups: kvm libvirt libvirt-qemu.

Before running the tests, copy the cma, nanoprobe, and libsodium
debian packages to the vagrant directory. They are going to be
installed in VMs from that directory.

The VMs are going to be "cma" (for the cma) and "drone%n"
(for drones) where "%n" stands for a drone number (a
small integer). The drone VMs count starts at 1.

The Vagrantfile contains also configuration for the
apt-cacher-ng. It is not strictly required, but reduces runtime
considerably.

To use other boxes/distributions please modify the Vagrantfile
and the provisioning scripts accordingly. For other Debian based
distributions such as Ubuntu, it _should_ be enough just to
modify the base box name. Best to make copies in another
directory and then use the "-D" option. It is out of scope for
this document to describe vagrant, but it should not be very
difficult.

Vagrant ssh command is quite slow. To access VMs with ssh or pdsh
do the following:

$ cd vagrant
$ . mksshconf.sh
$ ssh -F ssh_config <hostname>

To run commands on all VMs, install pdsh:

$ pdsh date
drone1: Wed Mar 28 15:30:30 UTC 2018
cma: Wed Mar 28 15:30:30 UTC 2018
drone2: Wed Mar 28 15:30:30 UTC 2018

