FROM centos:centos6
# Created by ./CentOS6-directions --format=dockerfile docker
# enable_repos: Enable the CentOS 6 EPEL and SCL repos
RUN yum -y install wget epel-release centos-release-scl
RUN yum -y update

# install_libsodium: Pull in and install prebuilt RPMs of libsodium
RUN wget -q ftp://mandril.creatis.insa-lyon.fr/linux/remi/enterprise/6/remi/x86_64/libsodium-last-1.0.10-1.el6.remi.x86_64.rpm -O /tmp/libsodium-last-1.0.10-1.el6.remi.x86_64.rpm
RUN wget -q ftp://mandril.creatis.insa-lyon.fr/linux/remi/enterprise/6/remi/x86_64/libsodium-last-devel-1.0.10-1.el6.remi.x86_64.rpm -O /tmp/libsodium-last-devel-1.0.10-1.el6.remi.x86_64.rpm
RUN yum -y install          /tmp/libsodium-last-1.0.10-1.el6.remi.x86_64.rpm /tmp/libsodium-last-devel-1.0.10-1.el6.remi.x86_64.rpm

# java_install: Install JAVA from java-1.8.0-openjdk-headless
RUN yum -y install java-1.8.0-openjdk-headless

# neo4j_install: Install the community edition of Neo4j version 3.0.1
RUN yum -y install which lsof tar
RUN wget -q "https://neo4j.com/artifact.php?name=neo4j-community-3.0.1-unix.tar.gz" -O /tmp/neo4j-community-3.0.1-unix.tar.gz
RUN tar -C /usr/share -xzf /tmp/neo4j-community-3.0.1-unix.tar.gz
RUN rm -f /usr/share/neo4j
RUN ln -s /usr/share/neo4j-community-3.0.1/ /usr/share/neo4j
RUN useradd -c 'Neo4j Graph database' -d /usr/share/neo4j --user-group --no-create-home --system --shell /bin/false neo4j
RUN chown -R neo4j:neo4j  /usr/share/neo4j-community-3.0.1/
RUN mkdir -p /etc/neo4j
RUN cp -R /usr/share/neo4j/conf/* /etc/neo4j
RUN chown -R neo4j:neo4j /etc/neo4j
RUN printf 'NEO4J_CONF=%s su --shell /bin/sh -m -c "%s $@" neo4j\n' "/etc/neo4j" "/usr/share/neo4j/bin/neo4j" > /etc/init.d/neo4j
RUN cat /etc/init.d/neo4j
RUN chmod 755 /etc/init.d/neo4j
RUN mkdir -p /var/lib/neo4j/data/databases
RUN chown -R neo4j:neo4j /var/lib/neo4j/data
RUN rm -fr /usr/share/neo4j/data
RUN ln -s /var/lib/neo4j/data /usr/share/neo4j/data

# download_tarball: Download the Assimilation tarball "master" from project source control
RUN set -x
RUN mkdir -p /root/rpmbuild/SOURCES
RUN echo Sat Jun 11 21:54:31 MDT 2016
RUN wget -q https://github.com/assimilation/assimilation-official/tarball/master -O /root/rpmbuild/SOURCES/master.tar.gz; : assimilation-assimilation-official-3dc4128

# rpm_build: Build the Assimilation RPMs for x86_64 from the project tarball
RUN set -x
RUN yum -y install rpm-build tar scl-utils-build glib2-devel libpcap-devel zlib-devel gcc scl-utils python27-python python27-python-devel cmake28 python27-python-setuptools python-demjson
WORKDIR /root/rpmbuild/SOURCES
ENV ASSIMVERSION assimilation-assimilation-official-3dc4128
RUN echo "Downloaded Assimilation version ${ASSIMVERSION}"
RUN echo TAR VERSION IS $(tar tzf /root/rpmbuild/SOURCES/master.tar.gz 2>/dev/null | head -n 1 | sed 's%/.*%%')
RUN mkdir /tmp/assim-rpm
WORKDIR /tmp/assim-rpm
RUN tar xvf /root/rpmbuild/SOURCES/master.tar.gz ${ASSIMVERSION}/docker/CentOS6/assimilation-cma.spec
RUN rm -f /root/rpmbuild/RPMS/x86_64/assimilation-*.rpm
RUN mv /root/rpmbuild/SOURCES/master.tar.gz /root/rpmbuild/SOURCES/${ASSIMVERSION}.tgz
RUN scl enable python27 'easy_install pip'
RUN scl enable python27 'pip install ctypesgen'
RUN rpmbuild -ba /tmp/assim-rpm/${ASSIMVERSION}/docker/CentOS6/assimilation-cma.spec --define="assimversion ${ASSIMVERSION}" --define="libsodium libsodium-last"
WORKDIR /
RUN rm -fr /tmp/assim-rpm

# nanoprobe_rpm_install: Install the CentOS 6 Assimilation nanoprobe RPM
WORKDIR /root/rpmbuild/RPMS/x86_64/ 
RUN yum -y install assimilation-nanoprobe*.x86_64.rpm

# cma_rpm_install: Install the CentOS 6 Assimilation CMA RPM
RUN yum -y install python27-python-setuptools
RUN scl enable python27 'easy_install pip'
RUN scl enable python27 'pip install netaddr getent flask py2neo==2.0.8 demjson'
RUN yum -y install assimilation-cma*.x86_64.rpm
RUN echo "ASSIMVERSION=$(cma --version)"

# logger_install: Install rsyslog logger
RUN yum -y install rsyslog

# build_for_test: (re-)Build the Assimilation software for testing
RUN mkdir /tmp/assimilation-test /tmp/assimilation-test/bin
WORKDIR /tmp/assimilation-test
RUN tar xzf /root/rpmbuild/SOURCES/${ASSIMVERSION}.tgz
RUN mv ${ASSIMVERSION} src
WORKDIR /tmp/assimilation-test/bin
RUN /usr/bin/cmake28 ../src
RUN scl enable python27 make

# run_assimilation_tests: Run the Assimilation unit tests
RUN yum -y install valgrind
RUN scl enable python27 'pip install pylint pytest'
RUN mkdir -p /var/lib/heartbeat/lrm
WORKDIR /tmp/assimilation-test/src/cma
RUN service rsyslog start & /usr/share/neo4j/bin/neo4j console & sleep 20 && scl enable python27 'assimcli genkeys && py.test -rw -v tests'

# copy_packages: Copy the packages into a single directory for Docker extraction
RUN mkdir -p /tmp/assimilation-test/packages
RUN cp /root/rpmbuild/RPMS/x86_64/assim*.rpm /tmp/assimilation-test/packages
RUN cp /root/rpmbuild/SRPMS/assim*.src.rpm  /tmp/assimilation-test/packages

RUN echo "GOODBUILD=$(echo "$(lsb_release -i -s)_$(lsb_release -r -s)-$(uname -m)" | tr '[A-Z]' '[a-z]')"
