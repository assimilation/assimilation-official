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
install(PROGRAMS AssimCclasses.py assimjson.py assimevent.py assimeventobserver.py
	checksumdiscovery.py
	cmadb.py cma.py cmainit.py consts.py dispatchtarget.py discoverylistener.py droneinfo.py
	frameinfo.py graphnodes.py hbring.py linkdiscovery.py messagedispatcher.py monitoring.py
	monitoringdiscovery.py
	packetlistener.py query.py store.py transaction.py
        COMPONENT cma-component DESTINATION ${PYINSTALL})

install(FILES __init__.py 
        COMPONENT cma-component DESTINATION ${PYINSTALL}
        PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ
	)
install(FILES AssimCtypes.py-install
        COMPONENT cma-component DESTINATION ${PYINSTALL}
        PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ
	RENAME AssimCtypes.py
	)
install (PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/cma ${CMAKE_CURRENT_BINARY_DIR}/assimcli  COMPONENT cma-component DESTINATION ${CMAKE_INSTALL_PREFIX}/sbin)
install(DIRECTORY tests 
        COMPONENT cma-component DESTINATION ${PYINSTALL} FILES_MATCHING PATTERN "*.py")
install(DIRECTORY flask 
        COMPONENT cma-component DESTINATION ${PYINSTALL} FILES_MATCHING PATTERN "*.py")
