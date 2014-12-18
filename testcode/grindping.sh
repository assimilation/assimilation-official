#!/bin/sh
#
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2011, 2012 - Alan Robertson <alanr@unix.sh>
#
#  The Assimilation software is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  The Assimilation software is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
HERE=$(dirname $0)
ARGLIST="-c 30 ::1"
G_MESSAGES_DEBUG=all
G_SLICE=always-malloc
export G_MESSAGES_DEBUG G_SLICE
GEN=--gen-suppressions=all
GEN="--gen-suppressions=no --num-callers=50 --read-var-info=yes"
GEN="--gen-suppressions=all --num-callers=50"
OPTS="--show-reachable=yes"

dosudo() {
  case $(id -u) in
    0)	"$@";;
    *)	sudo "$@";;
  esac
}

dir=$(dirname $0)
cmd=pinger

placestolook=". testcode .. ../testcode bin bin/testcode ../bin ../bin/testcode root_of_binary_tree/testcode ../root_of_binary_tree/testcode ../../root_of_binary_tree/testcode ../../bin/testcode"
for place in $placestolook
do
  filename="$place/$cmd"
  if
    [ -f "$filename" -a -x "$filename" ]
  then
    cmd="$filename"
    break
  fi
done

suppressions="--suppressions=$HERE/pinger-msgs.supp"

valgrind -q --leak-check=full $GEN --error-exitcode=100 --trace-children=no --child-silent-after-fork=yes $suppressions $cmd $ARGLIST
