FROM centos:latest
# Tag in "FROM" will be replaced by "dockit" script
MAINTAINER Alan Robertson <alanr@assimilationsystems.com>
ENV YUM @YUM@
ENV GITREPOSITORY assimilation-official
ENV GITVERSION master
ENV GITHUB https://github.com/assimilation/$GITREPOSITORY
ENV GITTARZAN $GITHUB/tarball/$GITVERSION
ENV GITHASH 5e5971a # Will be updated by "dockit" script
ENV GITPATH assimilation-${GITREPOSITORY}-${GITHASH}
RUN $YUM install epel-release pkg-config || true
RUN $YUM install deltarpm glib2 libpcap zlib-devel python	\
	python-devel python-flask which java-1.8.0-openjdk lsof	\
	libsodium-devel gcc cmake make glib2-devel valgrind resource-agents \
	wget libpcap-devel pylint rpm-build iproute
RUN $YUM remove vim-minimal && $YUM install doxygen graphviz
RUN $YUM install python-pip
RUN pip install testify 'py2neo>2.0' getent netaddr && pip install ctypesgen --pre
RUN wget -q http://dist.neo4j.org/neo4j-community-2.0.1-unix.tar.gz -O /tmp/neo4j-community-2.0.1-unix.tar.gz && tar -C /opt -xzf /tmp/neo4j-community-2.0.1-unix.tar.gz && ln -s /opt/neo4j-community-2.0.1/ /opt/neo4j && (echo ''; echo '') | /opt/neo4j/bin/neo4j-installer install && rm -fr /tmp/neo4j-community-*.tar.gz && mkdir -p /var/lib/heartbeat/lrm
RUN echo "@OURDATE@"
RUN mkdir -p /root/assimilation/bin /root/assimilation/packages /run/systemd/journal /root/rpmbuild/SOURCES 
ADD $GITTARZAN /root/assimilation/
WORKDIR /root/assimilation
RUN tar xzf $GITVERSION && mv [Aa]ssimilation-* src
RUN cp $GITVERSION /root/rpmbuild/SOURCES/${GITPATH}.tgz
# Build the RPM
WORKDIR /root/rpmbuild/SOURCES
RUN rpmbuild -ba /root/assimilation/src/docker/CentOS6/assimilation-cma.spec --define="assimversion $GITPATH"
WORKDIR /root/assimilation/bin
# Now build separately to test installing the packages and run our tests...
RUN cmake ../src && make install
ENV BROKENDNS true
RUN $YUM install rsyslog
RUN $YUM install jq
WORKDIR /root/rpmbuild/RPMS/x86_64/
RUN pwd; ls -l
RUN $YUM install assimilation-nanoprobe*.rpm assimilation-cma*.rpm
RUN echo "/usr/lib*/assimilation" > /etc/ld.so.conf.d/assimilation.conf && ldconfig /usr/lib*/assimilation
WORKDIR /root/assimilation/src/cma
RUN sed /etc/rsyslog.conf -e 's%^$.*imjournal%#&%' -e 's%.*$OmitLocalLogging.*%$OmitLocalLogging off%' > /tmp/foo
RUN printf "%s\n%s\n" '$ModLoad imuxsock' '$SystemLogSocketName /dev/log' >> /tmp/foo
RUN  cp /tmp/foo /etc/rsyslog.conf; rm /tmp/foo
RUN /usr/sbin/assimcli genkeys
RUN $YUM install python-demjson
#RUN rsyslogd && /etc/init.d/neo4j-service start&  sleep 15; ps -ef; ls -l /dev/*log*; testify -v tests
RUN /usr/sbin/rsyslogd&  /opt/neo4j/bin/neo4j console & sleep 20; testify -v tests
RUN cp /root/rpmbuild/RPMS/x86_64/* /root/assimilation/packages
RUN echo "GOOD BUILD: fedora:latest" # Will be updated by "dockit" script
###  Our RPMs
