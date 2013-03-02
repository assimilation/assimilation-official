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
install(PROGRAMS AssimCclasses.py 
	cmadb.py cma.py dispatchtarget.py droneinfo.py frameinfo.py hbring.py
	messagedispatcher.py packetlistener.py
        COMPONENT cma-component DESTINATION ${PYINSTALL})
install(FILES AssimCtypes.py __init__.py 
        COMPONENT cma-component DESTINATION ${PYINSTALL}
        PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ
	)

install (PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/cma COMPONENT cma-component DESTINATION ${CMAKE_INSTALL_PREFIX}/sbin)

install(DIRECTORY tests 
        COMPONENT cma-component DESTINATION ${PYINSTALL} FILES_MATCHING PATTERN "*.py")
