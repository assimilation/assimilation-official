mk_ssh_config() {
	for c in $vms; do
		vagrant ssh-config $c | sed 's/User vagrant/User root/'
	done
}

which pdsh >/dev/null || {
	echo install pdsh!
	exit 1
}

vms=`vagrant status | grep -w running | awk '{print $1}'`
mk_ssh_config > ssh_config
echo $vms > vmlist
export PDSH_RCMD_TYPE=ssh
export PDSH_SSH_ARGS="-F ssh_config"
export WCOLL="vmlist"
