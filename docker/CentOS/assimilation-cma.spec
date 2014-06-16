# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Original Author: Jamie Nguyen <j@jamielinux.com>
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
#--------------------------------------------------------------------
# This file based on original work of Jamie Nguyen <j@jamielinux.com>
#
# To the extent possible under law, Jamie Nguyen waived all copyright
# and related or neighboring rights to his original work.
#
# This work is published from: United Kingdom.
#
# See https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt
#--------------------------------------------------------------------

%global enable_docs 0

%global cma_user    assimilation
%global cma_group   assimilation

%global _hardened_build 1

%if 0%{?rhel}
%global cma_rundir  %{_localstatedir}/run/assimilation
%global nano_rundir %{_localstatedir}/run/nanoprobe
%else
%global cma_rundir  /run/assimilation
%global nano_rundir /run/nanoprobe
%endif

Name:       assimilation-cma
Version:    0.1.4
Release:    0.30
Summary:    Collective Management Authority (CMA) for Assimilation

Group:      Applications/System
License:    GPLv3+
URL:        http://linux-ha.org/source-doc/assimilation/html/index.html
Source0:    assimilation.tip.tar.gz
Source20:   assimilation-cma.service
# A copy of the CC0 legal code taken from:
# https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt
# This waives all copyright for the following files:
# assimilation-nanoprobe.service
# assimilation-cma.spec
# ------------------------------
# Note that these files have been relicensed as noted at the top of the file
# ------------------------------

%if 0%{?rhel}
BuildRequires: cmake28
%else
BuildRequires: cmake
%endif

BuildRequires: glib2-devel
BuildRequires: libpcap-devel
BuildRequires: pkgconfig
BuildRequires: scl-utils
BuildRequires: python27-devel
#BuildRequires: python27-ctypesgen
#BuildRequires: python27-py2neo

Requires:         neo4j
Requires:         assimilation-nanoprobe = 0:%{version}-%{release}
#
#   The next couple things are different if we have python >= 2.7 available...
#
Requires:         scl-utils
#Requires:        python27-py2neo
Requires(pre):    shadow-utils

%if 0%{?rhel}
Requires(post):   chkconfig
Requires(preun):  chkconfig
Requires(preun):  initscripts
Requires(postun): initscripts
%else
BuildRequires:    systemd
Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd
%endif

Provides:  assimilation = 0:%{version}-%{release}

%description
This package contains the Collective Management Authority (CMA) for
the Assimilation System software.

The Assimilation System maintains a Configuration Management Data Base (CMDB)
which is used as the basis for system automation - including automated
monitoring.

The Assimilation System is designed to manage and monitor systems and services on a network of
potentially unlimited size, with minimal growth in centralized resources.
The work of discovery and monitoring is delegated uniformly in tiny pieces to
the various machines being monitored in a network-aware topology, minimizing
network overhead and being naturally geographically sensitive.

The main features include:
 - Creates and keeps up to date a detailed and extensible CMDB
 - Drives automated actions from the CMDB (including monitoring and audits)
 - Easily and massively scales
 - Monitor systems and services with near-zero overhead
 - Auto-configuration and integrated continuous low-profile discovery of
   systems, services and dependencies
 - Easy to configure and manage

A normal installation consists of one instance of a Collective Management
Authority (CMA) and n+1 nanoprobes. Only one machine runs the CMA software,
but every machine being monitored (including the CMA itself) runs a copy of
the assimilation-nanoprobe daemon.

%package -n assimilation-nanoprobe
Group:         Applications/System
Summary:       Nanoprobe distributed monitoring agent for Assimilation
Source21:      assimilation-nanoprobe.service
Source31:      assimilation-nanoprobe.init
%if 0%{?rhel}
Requires(post):   chkconfig
Requires(preun):  chkconfig
Requires(preun):  initscripts
Requires(postun): initscripts
%else
Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd
%endif
Requires:         redhat-lsb-core
Requires:         wireless-tools
Requires:         resource-agents
Requires:         libpcap
Requires:         glib2

%description -n assimilation-nanoprobe
This package contains the nanoprobe distributed monitoring agent for
Assimilation.

The Assimilation System maintains a Configuration Management Data Base (CMDB)
which is used as the basis for system automation - including automated
monitoring.

The Assimilation System is designed to manage and monitor systems and services on a network of
potentially unlimited size, with minimal growth in centralized resources.
The work of discovery and monitoring is delegated uniformly in tiny pieces to
the various machines being monitored in a network-aware topology, minimizing
network overhead and being naturally geographically sensitive.

The main features include:
 - Creates and keeps up to date a detailed and extensible CMDB
 - Drives automated actions from the CMDB (including monitoring and audits)
 - Easily and massively scales
 - Monitor systems and services with near-zero overhead
 - Auto-configuration and integrated continuous low-profile discovery of
   systems, services and dependencies
 - Easy to configure and manage

A normal installation consists of one instance of a Collective Management
Authority (CMA) and n+1 nanoprobes. Only one machine runs the CMA software,
but every machine being monitored (including the CMA itself) runs a copy of
the assimilation-nanoprobe daemon.

%prep
%setup -q -n assimilation-%{snapshot}


%build
mkdir -p build
pushd build
%if 0%{?rhel}
%cmake28 .. -DCMAKE_SKIP_BUILD_RPATH=1
%else
%cmake .. -DCMAKE_SKIP_BUILD_RPATH=1
%endif
popd

%if 0%{?enable_docs}
pushd build
make doc
popd
%endif


%install
pushd build
make install DESTDIR=%{buildroot}
popd


%if 0%{?enable_docs}
mkdir -p %{buildroot}%{_docdir}/assimilation
cp -a build/doxygen/html %{buildroot}%{_docdir}/assimilation
%endif

%if 0%{?rhel}
install -p -D -m0755 %{SOURCE30} %{buildroot}%{_initddir}/assimilation-cma
install -p -D -m0755 %{SOURCE31} %{buildroot}%{_initddir}/assimilation-nanoprobe
%else
install -p -D -m0644 %{SOURCE20} %{buildroot}%{_unitdir}/assimilation-cma.service
install -p -D -m0644 %{SOURCE21} %{buildroot}%{_unitdir}/assimilation-nanoprobe.service
%endif

mkdir -p %{buildroot}%{cma_rundir}
mkdir -p %{buildroot}%{nano_rundir}

mkdir -p %{buildroot}%{_libdir}

mkdir -p %{buildroot}%{python_sitearch}/assimilation/testcode
# These commands are binaries - should not install in the Python aera...
#for i in filetest mainlooptest pinger; do
#    install -p -D -m0755 build/testcode/"${i}" \
#        %{buildroot}%{python_sitearch}/assimilation/testcode/"${i}"
#done
#install -p -D -m0755 testcode/grind.sh \
#    %{buildroot}%{python_sitearch}/assimilation/testcode/grind.sh
#install -p -D -m0644 testcode/valgrind-msgs.supp \
#    %{buildroot}%{python_sitearch}/assimilation/testcode/valgrind-msgs.supp


%pre
getent group %{cma_group} > /dev/null || groupadd -r %{cma_group}
getent passwd %{cma_user} > /dev/null || \
    useradd -r -M -g %{cma_group} \
    -s /sbin/nologin -c "Assimilation Collective Management Authority" %{cma_user}
exit 0


%if 0%{?rhel}
%post
/sbin/chkconfig --add assimilation-cma

%preun
if [ $1 -eq 0 ] ; then
    /sbin/service assimilation-cma stop >/dev/null 2>&1
    /sbin/chkconfig --del assimilation-cma
fi

%postun
if [ $1 -ge 1 ] ; then
    /sbin/service assimilation-cma condrestart >/dev/null 2>&1 || :
fi

%post -n assimilation-nanoprobe
echo ${_libdir}/assimilation > /etc/ld.so.conf/assimilation
/sbin/ldconfig %{_libdir}/assimilation
/sbin/chkconfig --add assimilation-nanoprobe

%preun -n assimilation-nanoprobe
if [ $1 -eq 0 ] ; then
    /sbin/service assimilation-nanoprobe stop >/dev/null 2>&1
    /sbin/chkconfig --del assimilation-nanoprobe
fi

%postun -n assimilation-nanoprobe
/sbin/ldconfig %{_libdir}/assimilation
if [ $1 -ge 1 ] ; then
    /sbin/service assimilation-nanoprobe condrestart >/dev/null 2>&1 || :
fi

%else

%post
%systemd_post assimilation-cma.service

%preun
%systemd_preun assimilation-cma.service

%postun
%systemd_postun_with_restart assimilation-cma.service

%post -n assimilation-nanoprobe
/sbin/ldconfig
%systemd_post assimilation-nanoprobe.service

%preun -n assimilation-nanoprobe
%systemd_preun assimilation-nanoprobe.service

%postun -n assimilation-nanoprobe
/sbin/ldconfig
%systemd_postun_with_restart assimilation-nanoprobe.service
%endif


%files
%doc legal/COPYING README
%{python_sitearch}/assimilation
%{_sbindir}/cma
%attr(0755,%{cma_user},%{cma_group}) %dir %{cma_rundir}

%if 0%{?rhel}
%{_initddir}/cma
%else
%{_unitdir}/assimilation-cma.service
%endif
%{_sbindir}/cma
%{_sbindir}/assimcli
%{_datadir}/assimilation/queries/hostswitchports
%{_datadir}/assimilation/queries/allipports
%{_datadir}/assimilation/queries/shutdown
%{_datadir}/assimilation/queries/hostservicestatus
%{_datadir}/assimilation/queries/downservices
%{_datadir}/assimilation/queries/crashed
%{_datadir}/assimilation/queries/list
%{_datadir}/assimilation/queries/allips
%{_datadir}/assimilation/queries/down
%{_datadir}/assimilation/queries/findip
%{_datadir}/assimilation/queries/allswitchports
%{_datadir}/assimilation/queries/unknownips
%{_datadir}/assimilation/queries/allservicestatus
%{_datadir}/assimilation/queries/hostdependencies
%{_datadir}/assimilation/queries/findmac
%{_datadir}/assimilation/queries/allservers
%{_datadir}/assimilation/queries/hostipports
%{_datadir}/assimilation/queries/unmonitored
%{_datadir}/assimilation/monrules/assimilation/bacula-director-lsb.mrule
%{_datadir}/assimilation/monrules/assimilation/munin-node-lsb.mrule
%{_datadir}/assimilation/monrules/assimilation/tprintdaemon-nomon.mrule
%{_datadir}/assimilation/monrules/assimilation/ssh-lsb.mrule
%{_datadir}/assimilation/monrules/assimilation/bacula-sd-lsb.mrule
%{_datadir}/assimilation/monrules/assimilation/dropbox-nomon.mrule
%{_datadir}/assimilation/monrules/assimilation/rpcbind-lsb.mrule
%{_datadir}/assimilation/monrules/assimilation/named.mrule
%{_datadir}/assimilation/monrules/assimilation/pidgin-nomon.mrule
%{_datadir}/assimilation/monrules/assimilation/skype-nomon.mrule
%{_datadir}/assimilation/monrules/assimilation/neo4j.mrule
%attr(0755,root,root) %dir %{python_sitearch/assimilation}
%{_python_sitearch}/assimilation/arpdiscovery.py
%{_python_sitearch}/assimilation/AssimCclasses.py
%{_python_sitearch}/assimilation/assimcli.py
%{_python_sitearch}/assimilation/assimeventobserver.py
%{_python_sitearch}/assimilation/assimevent.py
%{_python_sitearch}/assimilation/assimjson.py
%{_python_sitearch}/assimilation/checksumdiscovery.py
%{_python_sitearch}/assimilation/cmaconfig.py
%{_python_sitearch}/assimilation/cmadb.py
%{_python_sitearch}/assimilation/cmainit.py
%{_python_sitearch}/assimilation/cma.py
%{_python_sitearch}/assimilation/consts.py
%{_python_sitearch}/assimilation/discoverylistener.py
%{_python_sitearch}/assimilation/dispatchtarget.py
%{_python_sitearch}/assimilation/droneinfo.py
%{_python_sitearch}/assimilation/frameinfo.py
%{_python_sitearch}/assimilation/glib.py
%{_python_sitearch}/assimilation/graphnodeexpression.py
%{_python_sitearch}/assimilation/graphnodes.py
%{_python_sitearch}/assimilation/hbring.py
%{_python_sitearch}/assimilation/linkdiscovery.py
%{_python_sitearch}/assimilation/messagedispatcher.py
%{_python_sitearch}/assimilation/monitoringdiscovery.py
%{_python_sitearch}/assimilation/monitoring.py
%{_python_sitearch}/assimilation/packetlistener.py
%{_python_sitearch}/assimilation/query.py
%{_python_sitearch}/assimilation/store.py
%{_python_sitearch}/assimilation/transaction.py
%{_python_sitearch}/assimilation/__init__.py
%{_python_sitearch}/assimilation/AssimCtypes.py
%{_python_sitearch}/assimilation/tests/__init__.py
%{_python_sitearch}/assimilation/tests/store_test.py
%{_python_sitearch}/assimilation/tests/assimevent_test.py
%{_python_sitearch}/assimilation/tests/cclass_wrappers_test.py
%{_python_sitearch}/assimilation/tests/cma_test.py
%{_python_sitearch}/assimilation/tests/zexternaltests.py
%{_python_sitearch}/assimilation/flask/hello.py

%files -n assimilation-nanoprobe
%doc legal/COPYING
/usr/lib/ocf/resource.d/assimilation/neo4j
%attr(0755,root,root) %dir %{_libdir}/assimilation
%{_libdir}/assimilation/libassimilationclientlib.so
%{_libdir}/assimilation/libassimilationserverlib.so
%{_sbindir}/nanoprobe
%attr(0755,root,root) %dir %{_datadir}/assimilation
%attr(0755,root,root) %dir %{_datadir}/assimilation/discovery_agents
%{_datadir}/assimilation/discovery_agents/checksums
%{_datadir}/assimilation/discovery_agents/cpu
%{_datadir}/assimilation/discovery_agents/monitoringagents
%{_datadir}/assimilation/discovery_agents/netconfig
%{_datadir}/assimilation/discovery_agents/os
%{_datadir}/assimilation/discovery_agents/packages
%{_datadir}/assimilation/discovery_agents/tcpdiscovery
%{_datadir}/assimilation/discovery_agents/ulimit
%{_datadir}/assimilation/copyright
%attr(0755,root,root) %dir %{nano_rundir}
%{_libdir}/libassimilationclientlib.so
%{_libdir}/libassimilationserverlib.so

%if 0%{?rhel}
${_initddir}/nanoprobe
%else
%{_unitdir}/assimilation-nanoprobe.service
%endif

%if 0%{?enable_docs}
%files -n assimilation-doc
%doc legal/COPYING
%{_docdir}/assimilation
%endif


%changelog
* Mon Jun 16 2014 Alan Robertson <alanr@unix.sh>
- First attempt at having it build for RHEL6 with python27 and new dependencies...
* Tue Jul 16 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.25.20130707hgae4553edf8c9
- update to hgae4553edf8c9
- add a missing BR

* Fri Jul 05 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.24.20130623hge529aa0d0e98
- Requires neo4j < 1.5

* Thu Jul 04 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.23.20130623hge529aa0d0e98
- do not start services by default
- add missing Short-Description to initscripts
- build with -DCMAKE_SKIP_BUILD_RPATH
- add missing shebang for testcode/grind.sh

* Tue Jul 02 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.22.20130623hge529aa0d0e98
- update to hge529aa0d0e98

* Fri Jun 21 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.21.20130610hga4584d5ba190
- update to hga4584d5ba190

* Mon Apr 15 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.20.20130415hgb175c7a2ecd3
- update to hgb175c7a2ecd3

* Mon Apr 15 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.19.20130414hg953f5c3a4e4b
- update to hg953f5c3a4e4b (v0.1.0-RC4)

* Sat Apr 06 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.18.20130405hg9923c7650d14
- update to hg9923c7650d14

* Sun Mar 31 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.17.20130329hg55163bd21d7c
- update to hg55163bd21d7c

* Wed Mar 27 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.16.20130323hg36236b3560f2
- fix a typo in clientlib/CMakeLists.txt
- make sure the headerfiles are sorted consistently when running
  genpybindings.py

* Tue Mar 26 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.15.20130323hg36236b3560f2
- update to hg36236b3560f2 (0.1.0-RC2)

* Sat Mar 23 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.14.20130323hg20185cf5bcb7
- update to hg20185cf5bcb7
- remove patches for building on RHEL 6 that have now been implemented upstream

* Thu Mar 21 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.13.20130319hg80cec7a7e666
- move assimilation-cma-tests files to assimilation-cma package

* Tue Mar 19 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.12.20130319hg80cec7a7e666
- add assimilation-cma-tests subpackage

* Tue Mar 19 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.11.20130319hg80cec7a7e666
- update to hg80cec7a7e666

* Mon Mar 18 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.10.20130318hg541
- update to hg541

* Sun Mar 17 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.9.RC1
- add redhat-lsb-core to assimilation-nanoprobe Requires

* Sun Mar 17 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.8.RC1
- fix scriptlets

* Sun Mar 17 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.7.RC1
- some more minor fixes to service files and initscripts

* Sun Mar 17 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.6.RC1
- minor fixes to service files and initscripts

* Sun Mar 17 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.5.RC1
- add missing ldconfig commands when building for EPEL

* Sun Mar 17 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.4.RC1
- update to upstream release 0.1.0-RC1

* Sat Mar 16 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.3.20130316hg532
- update to hg532
- fix ldconfig scriptlets
- add wireless-tools to assimilation-nanoprobe Requires

* Wed Mar 13 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.2.20130303hg514
- rename assimilation to assimilation-cma to match upstream

* Tue Mar 12 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 0.1.0-0.1.20130303hg514
- initial package
