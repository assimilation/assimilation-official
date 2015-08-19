FROM centos:centos6
# Would prefer headless, but not available in CentOS6
RUN yum -y install wget java-1.7.0-openjdk scl-utils redhat-lsb-core
RUN wget -qO- http://dev.centos.org/centos/6/SCL/scl.repo >> /etc/yum.repos.d/centos.scl.repo
RUN yum -y install python27-python python27-python-setuptools
###  Neo4j RPM
RUN wget http://debian.neo4j.org/neotechnology.gpg.key -O /tmp/neo4j.key  && rpm --import /tmp/neo4j.key && rm -f /tmp/neo4j.key
RUN echo '[neo4j]' > /etc/yum.repos.d/neo4j.repo && echo 'name=Neo4j Yum Repo' >> /etc/yum.repos.d/neo4j.repo && echo 'baseurl=http://yum.neo4j.org' >> /etc/yum.repos.d/neo4j.repo && echo 'enabled=1' >> /etc/yum.repos.d/neo4j.repo && echo 'gpgcheck=1' >> /etc/yum.repos.d/neo4j.repo && yum -y install neo4j
RUN scl enable python27 'easy_install pip'
RUN scl enable python27 'pip install py2neo'
RUN echo "Pulling Assimilation project source (v2)"
RUN mkdir /tmp/neotest && cd /tmp/neotest && wget -q http://hg.linux-ha.org/assimilation/raw-file/tip/cma/store.py  && wget -q http://hg.linux-ha.org/assimilation/raw-file/tip/cma/assimevent.py 
RUN NEO=neo4j; cd /tmp/neotest && /etc/init.d/${NEO} start && sleep 15 && scl enable python27 '/usr/bin/env python --version; (python store.py; true)'
