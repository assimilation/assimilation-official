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
  LIST='AssimCclasses.py assimjson.py cmadb.py cma.py cmainit.py consts.py dispatchtarget.py droneinfo.py frameinfo.py hbring.py messagedispatcher.py packetlistener.py query.py store.py transaction.py'
  LIST='AssimCclasses.py assimcli.py assimevent.py assimeventobserver.py assimjson.py bestpractices.py checksumdiscovery.py cmadb.py cmainit.py cma.py cmaconfig.py consts.py discoverylistener.py dispatchtarget.py droneinfo.py frameinfo.py graphnodes.py hbring.py linkdiscovery.py messagedispatcher.py monitoring.py monitoringdiscovery.py packetlistener.py query.py store.py transaction.py flask/hello.py'
 LIST="$LIST $(echo systemtests/*.py)"
else
  LIST="$@"
fi
case $vers in
 1.1)	pylint --init-hook="sys.path.append('systemtests')" --msg-template='{path}:{line}: [{msg_id}:{obj}] {msg}' $FLAGS --rcfile pylint${vers}.cfg $LIST;;
 *)	pylint --init-hook="sys.path.append('systemtests')" $FLAGS --rcfile pylint${vers}.cfg $LIST;;
esac
