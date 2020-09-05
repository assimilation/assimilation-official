#!/bin/sh -eu
: ${CMADEBUG=1}

set -e

critical() {
    echo "CRITICAL: $*" >&2
    result='BAD'
}
OWNERSHIP=assimilation:assimilation
DEFAULT_MODE=0755
shares="/dev/log /var/run/docker.sock /var/lib/assimilation /var/run/assimilation"

make_user() {
  if
    grep '^assimilation:' /etc/passwd >/dev/null
  then
    : COOL!
  else
    addgroup --gid $ASSIM_GID assimilation
    adduser --system --uid $ASSIM_UID --gid $ASSIM_GID --no-create-home assimilation
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
    make_user
    chown $OWNERSHIP /usr/share/assimilation
    for file in /usr/share/assimilation assim_json.sqlite assim_json.sqlite-journal
    do
        touch $file
	chmod g+w $file
    done
}

fix_install
export PYTHONPATH=$PWD
exec python ./cma.py --debug ${CMADEBUG} --foreground
