FROM ubuntu:latest
RUN apt-get -y install libglib2.0 libpcap0.8
RUN apt-get -y install python python-flask debianutils lsof python-gi python-netaddr
RUN echo "about to build another new version (v4)"
RUN mkdir -p /root/assimilation/src /root/assimilation/bin /root/assimilation/src && hg clone http://hg.linux-ha.org/assimilation /root/assimilation/src
RUN cd /root/assimilation/bin; cmake ../src && make install
#ENV BROKENDNS true
RUN cd /root/assimilation/src/cma && service syslog start && /etc/init.d/neo4j-service start && logger 'test message1' && logger 'test message 2' && tail /var/log/syslog && ldconfig -v /usr/lib/x86_64-linux-gnu/assimilation && testify -v tests
RUN pip install testify py2neo ctypesgen
