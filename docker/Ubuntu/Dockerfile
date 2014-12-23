FROM nanoprobe.ubuntu:latest
RUN apt-get update
RUN apt-get -y install --no-install-recommends python-pip python-flask debianutils lsof python-netaddr valgrind python-dev
RUN apt-get install -y --no-install-recommends openjdk-7-jre
RUN pip install 'py2neo<2.0' testify getent
# Import the Neo4j signing key
RUN wget -O - http://debian.neo4j.org/neotechnology.gpg.key | apt-key add - 
# Create an Apt sources.list file
RUN neoversion=stable; echo "deb http://debian.neo4j.org/repo ${neoversion}/" > /etc/apt/sources.list.d/neo4j.list
RUN apt-get -y update
RUN apt-get -y install --no-install-recommends neo4j
RUN echo /usr/lib/*linux-gnu/assimilation > /etc/ld.so.conf.d/assimilation.conf
RUN ldconfig /usr/lib/*linux-gnu/assimilation
#RUN service rsyslog start && service neo4j-service start  && cd /root/assimilation/src && testify -v cma.tests && service rsyslog stop
RUN cd /root/assimilation/bin && dpkg --install assimilation-cma-*-all.deb
RUN rm -fr /opt/neo4j/data/graph.db/* /opt/neo4j/data/graph.db/keystore /opt/neo4j/data/log/* /opt/neo4j/data/rrd /opt/neo4j/data/neo4j-service.pid
RUN service neo4j-service start && service neo4j-service stop # To make a lovely empty database...
ADD #CMA#00001.secret /usr/share/assimilation/crypto.d/#CMA#00001.secret
RUN chown assimilation -R /usr/share/assimilation/crypto.d/ && chmod 600 '/usr/share/assimilation/crypto.d//#CMA#00001.secret'
