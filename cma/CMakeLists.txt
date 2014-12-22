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


configure_file(${CMAKE_CURRENT_SOURCE_DIR}/cma.in ${CMAKE_CURRENT_BINARY_DIR}/cma @ONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/assimcli.in ${CMAKE_CURRENT_BINARY_DIR}/assimcli @ONLY)
install(PROGRAMS
	arpdiscovery.py AssimCclasses.py assimcli.py assimeventobserver.py assimevent.py
	assimjson.py checksumdiscovery.py cmaconfig.py cmadb.py cmainit.py
	cma.py consts.py discoverylistener.py dispatchtarget.py droneinfo.py
	frameinfo.py glib.py graphnodeexpression.py graphnodes.py hbring.py linkdiscovery.py
	messagedispatcher.py monitoringdiscovery.py monitoring.py packetlistener.py query.py
	store.py transaction.py procsysdiscovery.py
        COMPONENT cma-component DESTINATION ${DESTDIR}${PYINSTALL})

install(FILES __init__.py 
        COMPONENT cma-component DESTINATION ${DESTDIR}${PYINSTALL}
        PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ
	)
install(FILES AssimCtypes.py-install
        COMPONENT cma-component DESTINATION ${DESTDIR}${PYINSTALL}
        PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ
	RENAME AssimCtypes.py
	)
install (PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/cma ${CMAKE_CURRENT_BINARY_DIR}/assimcli  COMPONENT cma-component DESTINATION ${DESTDIR}${CMAKE_INSTALL_PREFIX}/sbin)
install(DIRECTORY tests 
        COMPONENT cma-component DESTINATION ${DESTDIR}${PYINSTALL} FILES_MATCHING PATTERN "*.py")
install(DIRECTORY flask 
        COMPONENT cma-component DESTINATION ${DESTDIR}${PYINSTALL} FILES_MATCHING PATTERN "*.py")
