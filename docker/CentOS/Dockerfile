FROM centos:latest
#FROM xdrum/centos64-base
RUN yum -y install glib2 libpcap zlib-devel rpm-build
# Can't use sudo from within a docker build - it needs a tty.  Some tests need to run as root. Good thing we run as root here...
# An alternative to providing syslog would be to mount /dev/log from the host - but you can't do that in a Dockerfile :-(
RUN yum -y install gcc cmake28 cpack make pkg-config glib2-devel valgrind resource-agents mercurial wget libpcap-devel rsyslog which tar redhat-lsb-core
RUN yum -y install java-1.7.0-openjdk lsof
RUN wget -q http://mirror-fpt-telecom.fpt.net/fedora/epel/6/i386/epel-release-6-8.noarch.rpm -O /tmp/epel-release-6-8.noarch.rpm
RUN yum -y install /tmp/epel-release-6-8.noarch.rpm
RUN wget -q http://dist.neo4j.org/neo4j-community-2.0.1-unix.tar.gz -O /tmp/neo4j-community-2.0.1-unix.tar.gz && tar -C /opt -xzf /tmp/neo4j-community-2.0.1-unix.tar.gz && ln -s /opt/neo4j-community-2.0.1/ /opt/neo4j && (echo ''; echo '') | /opt/neo4j/bin/neo4j-installer install && mkdir -p /var/lib/heartbeat/lrm
RUN yum -y install scl-utils
RUN wget -qO- http://dev.centos.org/centos/6/SCL/scl.repo >> /etc/yum.repos.d/centos.scl.repo
RUN yum -y install python27 # python27-python-devel
RUN scl enable python27 'easy_install pip'
RUN scl enable python27 'pip install ctypesgen'
RUN echo "about to build another new version (v24)"
RUN mkdir -p /root/assimilation/src /root/assimilation/bin && hg clone http://hg.linux-ha.org/assimilation /root/assimilation/src && cd /root/assimilation/bin; cmake ../src && scl enable python27 "make install"
#EXPOSE 55604 7473 7474 1984 1337
ENV BROKENDNS true
RUN scl enable python27 'pip install py2neo netaddr flask getent testify pylint'
RUN adduser --shell /bin/false assimilation
RUN echo '/usr/lib64/assimilation' > /etc/ld.so.conf.d/assimilation && ldconfig /usr/lib64/assimilation

# An alternative to starting syslog would be to mount /dev/log from the host - but you can't do that in a Dockerfile :-(
RUN cd /root/assimilation/src/cma && (rsyslogd&  /etc/init.d/neo4j-service start) && scl enable python27 'python --version; /usr/bin/env python --version; testify -v tests'
RUN cd /root/assimilation/src && id=$(hg id --id .) && mkdir -p /rpmbuild/SOURCES && hg archive --type tgz /rpmbuild/SOURCES/${id}.tgz && rpmbuild -ba /root/assimilation/src/docker/CentOS/assimilation-cma.spec --define="assimversion ${id}"
