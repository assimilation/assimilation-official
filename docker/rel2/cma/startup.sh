#!/bin/sh -eu
: ${CMADEBUG=1}

critical() {
    echo "CRITICAL: $*" >&2
    result='BAD'
}
OWNERSHIP=assimilation:assimilation
DEFAULT_MODE=0755
shares="/dev/log /var/run/docker.sock /var/lib/assimilation /var/run/assimilation"

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
}

fix_install
exec python ./cma.py --debug ${CMADEBUG} --foreground