FROM opensuse:latest
# Tag in "FROM" will be replaced by "dockit" script
MAINTAINER Alan Robertson <alanr@assimilationsystems.com>
ENV ZYPPER @ZYPPER@
ENV NEOROOT /opt/neo4j
ENV NEOVERS 2.2.5
ENV GITREPOSITORY assimilation-official
ENV GITVERSION master
ENV GITHUB https://github.com/assimilation/$GITREPOSITORY
ENV GITTARZAN $GITHUB/tarball/$GITVERSION
ENV GITHASH 5e5971a # Will be updated by "dockit" script
ENV GITPATH assimilation-${GITREPOSITORY}-${GITHASH}
ENV RPMDIR /usr/src/packages
RUN $ZYPPER install pkg-config || true
RUN $ZYPPER install deltarpm glib2 libpcap zlib-devel python	\
	python-devel python-flask which java-1.7.0-openjdk lsof	\
	'libsodium-devel>=1.0.1' gcc cmake make glib2-devel valgrind resource-agents \
	wget libpcap-devel python3-pylint rpm-build iproute
RUN $ZYPPER install doxygen graphviz python-pip ca-certificates-mozilla ca-certificates-cacert
RUN pip install 'py2neo>2.0.7' testify getent netaddr && pip install ctypesgen --pre
RUN wget -q http://dist.neo4j.org/neo4j-community-$NEOVERS-unix.tar.gz -O /tmp/neo4j-community-$NEOVERS-unix.tar.gz && tar -C $(dirname $NEOROOT) -xzf /tmp/neo4j-community-$NEOVERS-unix.tar.gz && ln -s $(dirname $NEOROOT)/neo4j-community-$NEOVERS/ $NEOROOT && (echo ''; echo '') | $NEOROOT/bin/neo4j-installer install && rm -fr /tmp/neo4j-community-*.tar.gz && mkdir -p /var/lib/heartbeat/lrm
RUN echo "@OURDATE@"
RUN mkdir -p /root/assimilation/bin $RPMDIR /run/systemd/journal $RPMDIR/SOURCES 
ADD $GITTARZAN /root/assimilation/
WORKDIR /root/assimilation
RUN tar xzf $GITVERSION && mv [Aa]ssimilation-* src
RUN set -x; cp $GITVERSION $RPMDIR/SOURCES/${GITPATH}.tgz
# Build the RPM
WORKDIR $RPMDIR/SOURCES
RUN rpmbuild -ba /root/assimilation/src/docker/CentOS6/assimilation-cma.spec --define="assimversion $GITPATH"
WORKDIR /root/assimilation/bin
# Now build separately to test installing the packages and run our tests...
RUN cmake ../src && make install
ENV BROKENDNS true
RUN $ZYPPER install rsyslog
RUN $ZYPPER install jq
WORKDIR $RPMDIR/RPMS/@ARCH@/
RUN pwd
RUN $ZYPPER install assimilation-nanoprobe*.rpm assimilation-cma*.rpm
RUN echo "/usr/lib*/assimilation" > /etc/ld.so.conf.d/assimilation.conf && ldconfig /usr/lib*/assimilation
WORKDIR /root/assimilation/src/cma
RUN sed /etc/rsyslog.conf -e 's%^$.*imjournal%#&%' -e 's%.*$OmitLocalLogging.*%$OmitLocalLogging off%' > /tmp/foo
RUN printf "%s\n%s\n" '$ModLoad imuxsock' '$SystemLogSocketName /dev/log' >> /tmp/foo
RUN  cp /tmp/foo /etc/rsyslog.conf; rm /tmp/foo
RUN /usr/sbin/assimcli genkeys
RUN pip install demjson
RUN echo 'dbms.security.auth_enabled=false' >> $NEOROOT/conf/neo4j-server.properties
RUN rsyslogd && $NEOROOT/bin/neo4j console&  sleep 20; testify -v tests
RUN mkdir -p /root/assimilation/packages && cp $RPMDIR/RPMS/@ARCH@/*.rpm /root/assimilation/packages
RUN echo "GOOD BUILD: opensuse:latest" # Will be updated by "dockit" script
###  Our RPMs
RUN echo "GOODBUILD=$(echo "$(lsb_release -i -s)_$(lsb_release -r -s)-$(uname -m)" | tr '[A-Z]' '[a-z]')"
RUN echo "ASSIMVERSION=$(cma --version)"
