FROM centos:latest
#FROM xdrum/centos64-base
RUN yum -y install glib2 libpcap zlib-devel
# Can't use sudo from within a docker build - it needs a tty.  Some tests need to run as root. Good thing we run as root here...
RUN yum -y install gcc cmake cpack make pkg-config glib2-devel valgrind resource-agents mercurial wget libpcap-devel rsyslog which tar
RUN yum -y install doxygen graphviz RUN yum -y install scl-utils
RUN yum -y install java-1.7.0-openjdk lsof
RUN wget -q http://mirror-fpt-telecom.fpt.net/fedora/epel/6/i386/epel-release-6-8.noarch.rpm -O /tmp/epel-release-6-8.noarch.rpm
RUN yum -y install /tmp/epel-release-6-8.noarch.rpm
RUN wget -q http://dist.neo4j.org/neo4j-community-2.0.1-unix.tar.gz -O /tmp/neo4j-community-2.0.1-unix.tar.gz && tar -C /opt -xzf /tmp/neo4j-community-2.0.1-unix.tar.gz && ln -s /opt/neo4j-community-2.0.1/ /opt/neo4j && (echo ''; echo '') | /opt/neo4j/bin/neo4j-installer install && mkdir -p /var/lib/heartbeat/lrm
RUN yum -y install python-pip
RUN pip install ctypesgen
RUN echo "about to build another new version (v8)"
RUN mkdir -p /root/assimilation/src /root/assimilation/bin && hg clone http://hg.linux-ha.org/assimilation /root/assimilation/src && cd /root/assimilation/bin; cmake ../src && make install
#EXPOSE 55604 7473 7474 1984 1337
ENV BROKENDNS true
RUN wget -qO- http://dev.centos.org/centos/6/SCL/scl.repo >> /etc/yum.repos.d/centos.scl.repo
RUN yum -y install python27 python27-python-devel
RUN scl enable python27 'yum -y install pygobject2'
RUN scl enable python27 'easy_install pip'
RUN scl enable python27 'pip install testify py2neo netaddr flask pylint'
RUN echo '/usr/lib64/assimilation' > /etc/ld.so.conf.d/assimilation
RUN ldconfig /usr/lib64/assimilation

RUN cd /root/assimilation/src/cma && (rsyslogd&  /etc/init.d/neo4j-service start) && logger 'test message1'&& logger 'test message 2'&& tail -100 /var/log/messages; scl enable python27 'python --version; /usr/bin/python --version; /usr/bin/env python --version; testify -v tests'
