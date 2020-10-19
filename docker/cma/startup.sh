#!/bin/sh -eu
: ${CMADEBUG=3}

set -e

critical() {
    echo "CRITICAL: $*" >&2
    result='BAD'
}
OWNERSHIP=assimilation:assimilation
DEFAULT_MODE=0755
shares="/dev/log /var/run/docker.sock /var/lib/assimilation /var/run/assimilation"

make_user() {
  set -x
  if
    grep '^assimilation:' /etc/group >/dev/null
  then
    : OK assimilation group
  else
    addgroup --gid $ASSIM_GID assimilation
  fi
  if
    grep '^docker:' /etc/group >/dev/null
  then
    : OK docker group
  else
    addgroup --gid $DOCKER_GID docker
  fi
  if
    grep '^assimilation:' /etc/passwd >/dev/null
  then
    : COOL!
  else
    adduser --system --uid $ASSIM_UID --gid $ASSIM_GID --no-create-home assimilation
    adduser assimilation docker
    adduser root docker
  fi
}


fix_install() {
    result=OK
    for share in $shares
    do
        if
            [ ! -S "${share}" -a ! -d "${share}" ]
        then
            critical "$share must be shared as a volume: -v $share:$share"
        fi
    done

    case ${result} in
        OK) ;;
        *)  exit 1;;
    esac
    make_user

    dirs="/usr/share/assimilation $DEFAULT_MODE
    /var/lib/assimilation/neo4j $DEFAULT_MODE
    /usr/share/assimilation/ $DEFAULT_MODE
    /usr/share/assimilation/crypto.d 0700"

    echo "$dirs" | while
        read dir mode
    do
        set -eu
        if
            [ ! -d "${dir}" ]
        then
            mkdir -m "${mode}" "${dir}"
            chown "${OWNERSHIP}" "${dir}"
        fi
    done
    chown $OWNERSHIP /usr/share/assimilation
    for file in /usr/share/assimilation assim_json.sqlite assim_json.sqlite-journal
    do
        touch $file
	chmod g+w $file
    done
}

fix_install
export G_MESSAGES_DEBUG=all
export G_SLICE=always-malloc
export G_ENABLE_DIAGNOSTIC=1
export MALLOC_CHECK_=2
export PYTHONPATH=$PWD
export TRACEMALLOC=25
FLAGS="-X dev"
exec python $FLAGS ./cma.py "$@" --debug ${CMADEBUG} --foreground
