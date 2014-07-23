FROM ubuntu:latest
RUN apt-get -y update
RUN apt-get -y install libglib2.0 libpcap0.8 wget resource-agents
RUN apt-get -y install mercurial cmake gcc libpcap0.8-dev libglib2.0-dev
#RUN apt-get -y install python python-flask debianutils lsof python-gi python-netaddr python-pip valgrind
RUN echo "about to build another new version (v6)"
RUN pip install python ctypesgen
RUN mkdir -p /root/assimilation/src /root/assimilation/bin /root/assimilation/src && hg clone http://hg.linux-ha.org/assimilation /root/assimilation/src
RUN cd /root/assimilation/bin; cmake ../src && make install && echo /usr/lib/*linux-gnu/assimilation > /etc/ld.so.conf.d/assimilation.conf && ldconfig /usr/lib/*linux-gnu/assimilation
#ENV BROKENDNS true
