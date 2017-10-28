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

	if $fromhost-ip startswith '172.17.' or $HOSTNAME == 'cma' or $HOSTNAME startswith 'nanoprobe' then {
		/var/log/assim.log
		stop
	}

Just put that in /etc/rsyslog.d/assim.conf and you should be OK.
Make sure that the user with which you run tests have read access
to the log file. Or just do this:

	$ sudo chmod 644 /var/log/assim.log

The script to start the tests is runtests.sh. Example use for
vagrant:

	$ sh runtests.sh -l /var/log/assim.log -m vagrant -C cma -N nanoprobe 20

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
are in the vagrant directory. The base box is Debian stretch. We
used this one:

https://app.vagrantup.com/debian/boxes/stretch64

Before running the tests, copy the cma, nanoprobe, and libsodium
debian packages to the vagrant directory. They are going to be
installed in VMs from that directory. By default, vagrant shares
it with the VMs.

The VMs are going to be "cma" (for the cma) and "nanoprobe%n"
(for nanoprobes) where "%n" stands for a nanoprobe number (a
small integer). The nanoprobe VMs count starts at 1.

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
