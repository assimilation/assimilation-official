FROM centos:latest
RUN yum -y install glib2 libpcap
RUN yum -y install python python-flask which java-1.7.0-openjdk lsof pygobject2
RUN yum -y install gcc cmake cpack make pkg-config glib2-devel valgrind resource-agents mercurial wget libpcap-devel pylint rsyslog sudo
RUN yum -y install doxygen graphviz
RUN wget -q http://mirror-fpt-telecom.fpt.net/fedora/epel/6/i386/epel-release-6-8.noarch.rpm -O /tmp/epel-release-6-8.noarch.rpm
RUN yum -y install /tmp/epel-release-6-8.noarch.rpm
RUN yum -y install python-pip
RUN pip install testify py2neo ctypesgen
RUN wget -q http://dist.neo4j.org/neo4j-community-2.0.1-unix.tar.gz -O /tmp/neo4j-community-2.0.1-unix.tar.gz && tar -C /opt -xzf /tmp/neo4j-community-2.0.1-unix.tar.gz && ln -s /opt/neo4j-community-2.0.1/ /opt/neo4j && (echo ''; echo '') | /opt/neo4j/bin/neo4j-installer install
RUN mkdir -p /root/assimilation/src /root/assimilation/bin && hg clone http://hg.linux-ha.org/assimilation /root/assimilation/src
RUN cd /root/assimilation/bin; cmake ../src && make install && ldconfig /usr/lib64/assimilation
EXPOSE 55604 7473 7474 1984 1337
RUN cd /root/assimilation/src/cma; service rsyslog start; service neo4j-service start; testify -v tests
