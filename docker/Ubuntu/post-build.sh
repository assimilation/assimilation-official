apt-get -y install openjdk-7-jre
wget -q http://dist.neo4j.org/neo4j-community-2.0.1-unix.tar.gz -O /tmp/neo4j-community-2.0.1-unix.tar.gz && tar -C /opt -xzf /tmp/neo4j-community-2.0.1-unix.tar.gz && ln -s /opt/neo4j-community-2.0.1/ /opt/neo4j && (echo ''; echo '') | /opt/neo4j/bin/neo4j-installer install && rm -fr /tmp/neo4j-community-*.tar.gz && mkdir -p /var/lib/heartbeat/lrm
# The next command hangs - have no idea why...
/etc/init.d/neo4j-service start &
sleep 30
kill $!
/etc/init.d/neo4j-service status
cd /root/assimilation/src
testify cma.tests
