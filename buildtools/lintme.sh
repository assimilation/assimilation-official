#!/bin/sh -eu
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
#
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2013 - Assimilation Systems Limited
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

#AssimCclasses.py AssimCtypes.py cmadb.py cma.py dispatchtarget.py droneinfo.py frameinfo.py hbring.py __init__.py messagedispatcher.py obsolete_cma.py packetlistener.py
#	AssimCtypes.py is generated
#	__init__.py is empty
#	obsolete_cma.py is obsolete
FLAGS=""
while
  [ $# -gt 0 ]
do
  case $1 in
    -*)	FLAGS="$FLAGS $1"
	shift
	;;
    *)	break;
  esac
done
version=$(pylint --version 2>/dev/null | grep pylint | (read foo version; echo $version))
case $version in
 0.*|1.0)	vers="";;
 *)		vers=1.1;;
esac
 
  
if
  [ $# = 0 ]
then
  LIST=$(echo *.py systemtests/*.py)
else
  LIST="$@"
fi

NLIST=''
for file in $LIST
do
    case $file in
        *AssimCtypes*|*SAVE*|*OLD*) ;;
        *)                          NLIST="$NLIST $file"
    esac
done

case $vers in
 1.1)	pylint --init-hook="sys.path.append('systemtests')"                 \
            --msg-template='{path}:{line}: [{msg_id}:{obj}] {msg}' $FLAGS   \
            --rcfile pylint${vers}.cfg $NLIST
        ;;
 *)     pylint --init-hook="sys.path.append('systemtests')" $FLAGS --rcfile \
                pylint${vers}.cfg $NLIST
        ;;
esac
