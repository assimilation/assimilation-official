FROM centos:latest
# Tag in "FROM" will be replaced by "dockit" script
MAINTAINER Alan Robertson <alanr@assimilationsystems.com>
ENV YUM @YUM@
ENV NEOPARENT /usr/share
ENV NEOROOT $NEOPARENT/neo4j
ENV NEODATA /var/lib/neo4j/data
ENV NEOSERVFILE /lib/systemd/system/neo4j.service
ENV CERT https://debian.neo4j.org/neotechnology.gpg.key
ENV GITREPOSITORY assimilation-official
ENV GITVERSION master
ENV GITHUB https://github.com/assimilation/$GITREPOSITORY
ENV GITTARZAN $GITHUB/tarball/$GITVERSION
ENV GITHASH 5e5971a # Will be updated by "dockit" script
ENV GITPATH assimilation-${GITREPOSITORY}-${GITHASH}
RUN $YUM install epel-release pkg-config || true
RUN $YUM install deltarpm glib2 libpcap zlib-devel python	\
	python-devel python-flask which @JRE@ lsof	\
	libsodium-devel gcc cmake make glib2-devel valgrind resource-agents \
	wget libpcap-devel pylint rpm-build iproute
RUN $YUM remove vim-minimal && $YUM install doxygen graphviz
RUN $YUM install python-pip
RUN pip install 'py2neo==@PY2NEOVERS@' getent netaddr pytest && pip install ctypesgen --pre
#Can't do this - their RPM process is broken...
#RUN wget -q -O - $CERT > neotechnology.gpg.key; rpm --import neotechnology.gpg.key; rm neotechnology.gpg.key
#RUN printf '[neo4j]\nname=Neo4j Yum Repo\nbaseurl=http://yum.neo4j.org\nenabled=1\ngpgcheck=1' > /etc/yum.repos.d/neo4j.repo
#RUN $YUM install neo4j-${NEOVERS}
########################################################################
# This is where we roll our own installer because Neo4j doesn't have one
#
# Install the @NEOVERS@ of Neo4j @NEOEDITION@ edition
RUN wget -q "https://neo4j.com/artifact.php?name=neo4j-@NEOEDITION@-@NEOVERS@-unix.tar.gz" -O /tmp/neo4j-@NEOEDITION@-@NEOVERS@-unix.tar.gz
RUN tar -C $NEOPARENT -xzf /tmp/neo4j-@NEOEDITION@-@NEOVERS@-unix.tar.gz
RUN rm -f $NEOROOT
RUN ln -s $NEOPARENT/neo4j-@NEOEDITION@-@NEOVERS@/ $NEOROOT
RUN useradd -c 'Neo4j Graph database' -d ${NEOROOT} --user-group --no-create-home --system --shell /bin/false neo4j
RUN chown -R neo4j:neo4j  $NEOROOT-@NEOEDITION@-@NEOVERS@/
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
RUN echo "@OURDATE@"
RUN mkdir -p /root/assimilation/bin /root/assimilation/packages /run/systemd/journal /root/rpmbuild/SOURCES /var/lib/heartbeat/lrm
RUN echo RUNNING "ADD $GITTARZAN /root/assimilation"
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
RUN $YUM install rsyslog || /bin/true
RUN $YUM install jq
WORKDIR /root/rpmbuild/RPMS/@ARCH@/
RUN pwd; ls -l
RUN $YUM install assimilation-nanoprobe*.rpm assimilation-cma*.rpm
RUN echo "/usr/lib*/assimilation" > /etc/ld.so.conf.d/assimilation.conf && ldconfig /usr/lib*/assimilation
WORKDIR /root/assimilation/src/cma
RUN if test -f /etc/rsyslog.conf; then  sed /etc/rsyslog.conf -e 's%^$.*imjournal%#&%' -e 's%.*$OmitLocalLogging.*%$OmitLocalLogging off%' > /tmp/foo; fi
RUN printf "%s\n%s\n" '$ModLoad imuxsock' '$SystemLogSocketName /dev/log' >> /tmp/foo
RUN  cp /tmp/foo /etc/rsyslog.conf; rm /tmp/foo
RUN /usr/sbin/assimcli genkeys
RUN $YUM install python-demjson
RUN /usr/sbin/rsyslogd&  $NEOROOT/bin/neo4j console & sleep 20; py.test -rw -v tests
RUN cp /root/rpmbuild/RPMS/@ARCH@/* /root/assimilation/packages
RUN echo "GOOD BUILD: centos:latest" # Will be updated by "dockit" script
RUN echo "GOODBUILD=$(echo "$(lsb_release -i -s)_$(lsb_release -r -s)-$(uname -m)" | tr '[A-Z]' '[a-z]')"
RUN echo "ASSIMVERSION=$(cma --version)"
###  Our RPMs
