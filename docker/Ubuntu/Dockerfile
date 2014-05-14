FROM ubuntu:latest
RUN apt-get -y install libglib2.0 libpcap0.8
RUN apt-get -y install python python-flask debianutils openjdk-7-jre lsof python-gi, python-netaddr
# Can't use sudo from within a docker build - it needs a tty.  Some tests need to run as root. Good thing we run as root here...
RUN apt-get -y install gcc cmake make pkg-config libglib2.0-dev valgrind resource-agents mercurial wget libpcap0.8-dev pylint
RUN apt-get -y install doxygen graphviz
RUN apt-get -y install python-pip
RUN pip install testify py2neo ctypesgen
RUN wget -q http://dist.neo4j.org/neo4j-community-2.0.1-unix.tar.gz -O /tmp/neo4j-community-2.0.1-unix.tar.gz && tar -C /opt -xzf /tmp/neo4j-community-2.0.1-unix.tar.gz && ln -s /opt/neo4j-community-2.0.1/ /opt/neo4j && (echo ''; echo '') | /opt/neo4j/bin/neo4j-installer install && rm -fr /tmp/neo4j-community-*.tar.gz && mkdir -p /var/lib/heartbeat/lrm
RUN echo "about to build another new version (v4)"
RUN mkdir -p /root/assimilation/src /root/assimilation/bin /root/assimilation/src && hg clone http://hg.linux-ha.org/assimilation /root/assimilation/src
RUN cd /root/assimilation/bin; cmake ../src && make install
#EXPOSE 55604 7473 7474 1984 1337
ENV BROKENDNS true
RUN apt-get -y install syslog-ng
RUN cd /root/assimilation/src/cma && syslog-ng && /etc/init.d/neo4j-service start && logger 'test message1' && logger 'test message 2' && tail /var/log/messages && ldconfig -v /usr/lib/x86_64-linux-gnu/assimilation && testify -v tests
