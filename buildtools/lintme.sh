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
  
if
  [ $# = 0 ]
then
  LIST='AssimCclasses.py assimjson.py cmadb.py cma.py cmainit.py consts.py dispatchtarget.py droneinfo.py frameinfo.py hbring.py messagedispatcher.py packetlistener.py query.py store.py transaction.py'
  LIST='AssimCclasses.py assimjson.py cmadb.py cmainit.py cma.py consts.py dispatchtarget.py droneinfo.py frameinfo.py graphnodes.py hbring.py messagedispatcher.py packetlistener.py query.py store.py transaction.py flask/hello.py'
else
  LIST="$@"
fi
pylint $FLAGS --rcfile pylint.cfg $LIST
