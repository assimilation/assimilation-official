FROM nanoprobe.ubuntu:latest
RUN apt-get update
RUN apt-get -y install --no-install-recommends python-pip python-flask debianutils lsof python-netaddr valgrind
RUN apt-get install -y --no-install-recommends openjdk-7-jre
RUN pip install py2neo testify getent
# Import the Neo4j signing key
RUN wget -O - http://debian.neo4j.org/neotechnology.gpg.key | apt-key add - 
# Create an Apt sources.list file
RUN neoversion=stable; echo "deb http://debian.neo4j.org/repo ${neoversion}/" > /etc/apt/sources.list.d/neo4j.list
RUN apt-get -y update
RUN apt-get -y install --no-install-recommends neo4j
RUN echo /usr/lib/*linux-gnu/assimilation > /etc/ld.so.conf.d/assimilation.conf
RUN ldconfig /usr/lib/*linux-gnu/assimilation
RUN service rsyslog start && service neo4j-service start  && cd /root/assimilation/src && testify -v cma.tests
RUN rm -fr /opt/neo4j/data/graph.db/* /opt/neo4j/data/graph.db/keystore /opt/neo4j/data/log/* /opt/neo4j/data/rrd /opt/neo4j/data/neo4j-service.pid
RUN cd /root/assimilation/bin && dpkg --install assimilation-cma-*-all.deb
RUN service neo4j-service start # To make a lovely empty database...
