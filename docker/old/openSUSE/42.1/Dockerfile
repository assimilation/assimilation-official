FROM opensuse:42.1
# Tag in "FROM" will be replaced by "dockit" script
MAINTAINER Alan Robertson <alanr@assimilationsystems.com>
ENV ZYPPER zypper --non-interactive
ENV NEOROOT /usr/share/neo4j
ENV NEOPARENT /usr/share/
ENV NEOCONF /etc/neo4j
ENV NEODATA /var/lib/neo4j/data
ENV NEOVERS 3.0.1
ENV NEOSERVFILE /usr/lib/systemd/system/neo4j.service
ENV GITREPOSITORY assimilation-official
ENV GITVERSION master
ENV GITHUB https://github.com/assimilation/$GITREPOSITORY
ENV GITTARZAN $GITHUB/tarball/$GITVERSION
ENV GITHASH 3dc4128
ENV GITPATH assimilation-${GITREPOSITORY}-${GITHASH}
ENV CERT https://debian.neo4j.org/neotechnology.gpg.key
ENV RPMDIR /usr/src/packages
RUN $ZYPPER install pkg-config || true
RUN $ZYPPER install deltarpm glib2 libpcap zlib-devel python			\
	python-devel python-flask which java-1_8_0-openjdk-headless lsof				\
	'libsodium-devel' gcc cmake make glib2-devel valgrind resource-agents 	\
	wget libpcap-devel python3-pylint rpm-build iproute python-pytest
COPY dummy.spec /tmp/
RUN mkdir -p $RPMDIR/SOURCES $RPMDIR/RPMS $RPMDIR/RPMS/x86_64
RUN ls -l /tmp
RUN rpmbuild -bb /tmp/dummy.spec
RUN find $RPMDIR -print | xargs ls -ld
RUN $ZYPPER install $RPMDIR/RPMS/x86_64/java*openjdk*.rpm
RUN $ZYPPER install doxygen graphviz python-pip ca-certificates-mozilla ca-certificates-cacert
RUN pip install 'py2neo==2.0.8' getent netaddr && pip install ctypesgen --pre
ENV BROKENDNS true
RUN $ZYPPER install rsyslog
RUN $ZYPPER install jq
#RUN wget -q -O - $CERT > neotechnology.gpg.key; rpm --import neotechnology.gpg.key; rm neotechnology.gpg.key
#RUN $ZYPPER ar -f http://yum.neo4j.org neo4j
#RUN $ZYPPER refresh-services
#RUN $ZYPPER -n --no-gpg-checks install neo4j=$NEOVERS
########################################################################
# This is where we roll our own installer because Neo4j doesn't have one
#
# Install the 3.0.1 of Neo4j community edition
RUN wget -q "https://neo4j.com/artifact.php?name=neo4j-community-3.0.1-unix.tar.gz" -O /tmp/neo4j-community-3.0.1-unix.tar.gz
RUN tar -C $NEOPARENT -xzf /tmp/neo4j-community-3.0.1-unix.tar.gz
RUN rm -f $NEOROOT
RUN ln -s $NEOPARENT/neo4j-community-3.0.1/ $NEOROOT
RUN useradd -c 'Neo4j Graph database' -d ${NEOROOT} --user-group --no-create-home --system --shell /bin/false neo4j
RUN chown -R neo4j:neo4j  $NEOROOT-community-3.0.1/
RUN mkdir -p $NEODATA/databases
RUN chown -R neo4j:neo4j $NEODATA
RUN rm -fr $NEOROOT/data
RUN ln -s $NEODATA $NEOROOT/data
RUN printf '[Unit]\nDescription = Neo4j Graph Database\nAfter = network.target\n\n' > $NEOSERVFILE
RUN printf '[Service]\nType = simple\n' >> $NEOSERVFILE
RUN printf 'ExecStart = %s/bin/neo4j console\n' "$NEOROOT" >> $NEOSERVFILE
RUN printf 'TimeoutStartSec = 120\nTimeoutStopSec = 30\nuser=neo4j\ngroup=neo4j\n' >> $NEOSERVFILE
RUN printf 'LimitNOFILE=40000\n\n' >> $NEOSERVFILE
RUN printf '[Install]\nWantedBy = multi-user.target\n' >> $NEOSERVFILE
RUN echo $NEOSERVFILE; cat $NEOSERVFILE
#
# End of our home-brew Neo4j installer...
#
########################################################################
RUN echo "Sat Jun 11 22:26:01 MDT 2016"
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
WORKDIR $RPMDIR/RPMS/x86_64/
RUN pwd
RUN $ZYPPER install assimilation-nanoprobe*.rpm assimilation-cma*.rpm
RUN echo "/usr/lib*/assimilation" > /etc/ld.so.conf.d/assimilation.conf && ldconfig /usr/lib*/assimilation
WORKDIR /root/assimilation/src/cma
RUN sed /etc/rsyslog.conf -e 's%^$.*imjournal%#&%' -e 's%.*$OmitLocalLogging.*%$OmitLocalLogging off%' > /tmp/foo
RUN printf "%s\n%s\n" '$ModLoad imuxsock' '$SystemLogSocketName /dev/log' >> /tmp/foo
RUN  cp /tmp/foo /etc/rsyslog.conf; rm /tmp/foo
RUN /usr/sbin/assimcli genkeys
RUN pip install demjson
RUN mkdir -p /var/lib/heartbeat/lrm
RUN rsyslogd && $NEOROOT/bin/neo4j console&  sleep 20; py.test -rw -v tests
RUN mkdir -p /root/assimilation/packages && cp $RPMDIR/RPMS/x86_64/*.rpm /root/assimilation/packages
RUN echo "GOOD BUILD: opensuse:42.1" # Will be updated by "dockit" script
###  Our RPMs
RUN echo "GOODBUILD=$(echo "$(lsb_release -i -s)_$(lsb_release -r -s)-$(uname -m)" | tr '[A-Z]' '[a-z]')"
RUN echo "ASSIMVERSION=$(cma --version)"
