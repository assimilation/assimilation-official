VOLS="/var/lib/assimilation
/var/run/assimilation
/var/run/docker.sock
/dev/log
"
VFLAGS=""
for vol in $VOLS
do
  VFLAGS="$VFLAGS -v $vol:$vol"
done
uid=$(grep '^assimilation:' /etc/passwd | cut -d: -f3)
gid=$(grep '^assimilation:' /etc/passwd | cut -d: -f4)
EFLAGS=" -e ASSIM_UID=${uid} -e ASSIM_GID=${gid}"

  
docker run -t -i $VFLAGS $EFLAGS assimilationproject/cma:1.99.0 /bin/bash
