VOLS="/var/lib/assimilation
/var/run/assimilation
/usr/share/assimilation
/var/run/docker.sock
/dev/log
/var/log/assim_neo4j
"
VFLAGS=""
for vol in $VOLS
do
  VFLAGS="$VFLAGS -v $vol:$vol"
done
uid=$(grep '^assimilation:' /etc/passwd | cut -d: -f3)
gid=$(grep '^assimilation:' /etc/passwd | cut -d: -f4)
dockergid=$(grep '^docker:' /etc/group | cut -d: -f3)
EFLAGS=" -e ASSIM_UID=${uid} -e ASSIM_GID=${gid} -e DOCKER_GID=${dockergid}"

sudo killall -9 nanoprobe
sudo ../nanoprobe/nanoprobe --debug 4 --dynamic
sudo rm -fr /var/lib/assimilation/assim_json.sqlite*
sudo touch /var/lib/assimilation/assim_json.sqlite
docker kill assim_neo4j ; sudo rm -fr /var/lib/assimilation/neo4j/data/databases/graph.db/*
docker run -t -i --privileged --pid=host --net=host $VFLAGS $EFLAGS assimilationproject/cma:1.99.0 /bin/bash -i -o vi
