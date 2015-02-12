FROM fedora:21
RUN yum -y install deltarpm glib2 libpcap zlib-devel epel-release python python-devel python-flask which java-1.8.0-openjdk lsof libsodium-devel
RUN yum -y install gcc cmake make pkg-config glib2-devel valgrind resource-agents mercurial wget libpcap-devel pylint rpm-build iproute
RUN yum -y remove vim-minimal && yum -y install doxygen graphviz
RUN yum -y install python-pip
RUN pip install testify 'py2neo<2.0' getent netaddr && pip install ctypesgen --pre
RUN wget -q http://dist.neo4j.org/neo4j-community-2.0.1-unix.tar.gz -O /tmp/neo4j-community-2.0.1-unix.tar.gz && tar -C /opt -xzf /tmp/neo4j-community-2.0.1-unix.tar.gz && ln -s /opt/neo4j-community-2.0.1/ /opt/neo4j && (echo ''; echo '') | /opt/neo4j/bin/neo4j-installer install && rm -fr /tmp/neo4j-community-*.tar.gz && mkdir -p /var/lib/heartbeat/lrm
RUN echo "about to build another new version (v14)"
RUN mkdir -p /root/assimilation/src /root/assimilation/bin /root/assimilation/src /run/systemd/journal && hg clone http://hg.linux-ha.org/assimilation /root/assimilation/src
WORKDIR /root/assimilation/src
RUN id=$(hg id --id .) && mkdir -p /root/rpmbuild/SOURCES && hg archive --type tgz /root/rpmbuild/SOURCES/${id}.tgz && rpmbuild -ba /root/assimilation/src/docker/CentOS/assimilation-cma.spec --define="assimversion ${id}"
WORKDIR /root/assimilation/bin
RUN cmake ../src && make install
#EXPOSE 55604 7473 7474 1984 1337
ENV BROKENDNS true
RUN yum -y install rsyslog
WORKDIR /root/rpmbuild/RPMS/x86_64/
RUN yum -y install assimilation-nanoprobe*.rpm assimilation-cma*.rpm
RUN echo "/usr/lib*/assimilation" > /etc/ld.so.conf.d/assimilation.conf && ldconfig /usr/lib*/assimilation
WORKDIR /root/assimilation/src/cma
RUN sed /etc/rsyslog.conf -e 's%^$.*imjournal%#&%' -e 's%.*$OmitLocalLogging.*%$OmitLocalLogging off%' > /tmp/foo
RUN  cp /tmp/foo /etc/rsyslog.conf; rm /tmp/foo
RUN /usr/sbin/assimcli genkeys
RUN rsyslogd && /etc/init.d/neo4j-service start&  sleep 15; ps -ef; ls -l /dev/*log*; testify -v tests
###  Our RPMs
