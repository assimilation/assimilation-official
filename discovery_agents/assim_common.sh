#!/bin/sh
# vim: smartindent tabstop=4 shiftwidth=4 number expandtab colorcolumn=100
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2016 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community - http://assimproj.org
# Paid support is available from Assimilation Systems Limited - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
#   Initial setup of Assimilation Proxy environment for proxied discovery (and monitoring?)
#   Code currently only supports one level of proxying - even though you might think
#   otherwise from reading the code...
#
#   Multiple-levels are either a thought experiment or a work-in-progress - take your pick...
#
#export ASSIM_PROXY_PATH=vagrant/9e6e7ec
#export ASSIM_PROXY_PATH=docker/4249d41de074


#
#   Set up for our other functions
#
_assim_get_proxy_paths() {
    : ${ASSIM_PROXY_PATH:=local/local}
    _assim_local_path=$(echo "$ASSIM_PROXY_PATH" | sed 's%:.*%%')
    case $ASSIM_PROXY_PATH in
        *:*)    ASSIM_REMOTE_PROXY_PATH=$(echo "$ASSIM_PROXY_PATH" | sed 's%^[^:]*:%%');;
        *)      ASSIM_REMOTE_PROXY_PATH='local/local';;
    esac
    ASSIM_LOCAL_PROXY_METHOD=$(echo "${_assim_local_path}" | sed 's%/.*%%')
    ASSIM_LOCAL_PROXY_DEST=$(echo "${_assim_local_path}" | sed 's%^[^/]*/%%')
}
_assim_get_proxy_paths

# For future multi-level proxying...
_assim_quote_string() {
    echo "$1" | sed -e "s%'%'\\\\''%g" -e "s%^%\\'%" -e "s%$%\'%" 
}

# Also for future multi-level proxying...
_assim_quote_command() {
    (
        space=''
        for arg in "$@"
        do
            printf '%s%s' "$space" "$(_assim_quote_string "$arg")"
            space=' '
        done
    )
}


# Run a command in the requested ($ASSIM_LOCAL_PROXY_DEST) Vagrant VM
_assim_vagrant_run_() {
    (
        set -e
        assim_vagrant_dir=$(vagrant global-status | grep "^${ASSIM_LOCAL_PROXY_DEST} " |
                sed 's%^[^/]*/%/%')
                cd ${assim_vagrant_dir} 2>/dev/null && vagrant ssh -- $(_assim_quote_command "$@")
        exit $?
    )
}

# Enumerate running vagrant images
# Not sure if we should include non-running images or not...
assim_vagrant_enumerate() {
    (
        set -e
        vagrant global-status 2>/dev/null | grep ' /' | sort -u |
        while
            read id name provider state directory
        do
            STATUS=$(cd "$directory" 2>/dev/null && vagrant status || true)
            case $STATUS in
                *' running ('*)     echo $id;;
            esac
        done
    )
}

# Enumerate running docker images
assim_docker_enumerate() {
    docker ps 2>/dev/null | cut -d' ' -f1 | egrep '^[0-9a-f]+' | sort -u
}


# Run a command in the requested ($ASSIM_LOCAL_PROXY_DEST) docker image
_assim_docker_run_() {
    docker exec "$ASSIM_LOCAL_PROXY_DEST" "$@"
    return $?
}


#
#   Run the given command in the given context
#   A context consists of a $ASSIM_LOCAL_PROXY_DEST in a type of $ASSIM_LOCAL_PROXY_METHOD
#   Currently the only environments we support are:
#       docker          - run inside a docker container
#       local (default) - run locally
#
#
assim_run_in_context() {
    case $ASSIM_LOCAL_PROXY_METHOD in
        docker)     _assim_docker_run_ "$@"     ;;
        vagrant)    _assim_vagrant_run_ "$@"    ;;
        *)          "$@"                        ;;
    esac
}

#
#   Not sure if this simple environment enumeration is useful or not...
# 
assim_environ_enumerate() {
    (
        outercomma=''
        printf '{\n '
        for env in docker vagrant
        do
            if
                ENUM_OUT=$("assim_${env}_enumerate") && test ! -z "$ENUM_OUT"
            then
                printf '%s"%s": [' "$outercomma" "$env"
                innercomma=''
                for container in ${ENUM_OUT}
                do
                    printf '%s"%s"' "$innercomma" "$container"
                    innercomma=','
                done
                printf ']'
            fi
            outercomma=',
 '
        done
        printf '\n}\n'
    )
}
