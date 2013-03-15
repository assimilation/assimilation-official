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

SET (CTYPESRC ${CMAKE_CURRENT_SOURCE_DIR}/AssimCtypes.py)
SET (CTYPEBIN ${CMAKE_CURRENT_SOURCE_DIR}/AssimCtypes.py-install)

ADD_CUSTOM_COMMAND(
   OUTPUT ${CTYPESRC}
   COMMAND python ${BUILDTOOLS}/genpybindings.py ${CTYPESRC} ${SRCROOT} ${BINROOT} ${SRCROOT}/clientlib
   DEPENDS ../include/*.h
   )

ADD_CUSTOM_COMMAND(
   OUTPUT ${CTYPEBIN}
   COMMAND python ${BUILDTOOLS}/genpybindings.py ${CTYPEBIN} ${SRCROOT} ${BINROOT} ${InstallLIBS} 
   DEPENDS ../include/*.h
   )

ADD_CUSTOM_TARGET(generate_ctypes_src DEPENDS ${CTYPESRC})
ADD_CUSTOM_TARGET(generate_ctypes_bin DEPENDS ${CTYPEBIN})
ADD_DEPENDENCIES(${CLIENTLIB} generate_ctypes_src generate_ctypes_bin)

SET_SOURCE_FILES_PROPERTIES(${CMAKE_CURRENT_BINARY_DIR}/AssimCtypes.py PROPERTIES GENERATED 1)
SET_SOURCE_FILES_PROPERTIES(${CMAKE_CURRENT_SOURCE_DIR}/AssimCtypes.py PROPERTIES GENERATED 1)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/cma.in ${CMAKE_CURRENT_BINARY_DIR}/cma @ONLY)
install(PROGRAMS AssimCclasses.py 
	cmadb.py cma.py dispatchtarget.py droneinfo.py frameinfo.py hbring.py
	messagedispatcher.py packetlistener.py
        COMPONENT cma-component DESTINATION ${PYINSTALL})

install(FILES __init__.py 
        COMPONENT cma-component DESTINATION ${PYINSTALL}
        PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ
	)
install(FILES ${CTYPESRC}-install
        COMPONENT cma-component DESTINATION ${PYINSTALL}
        PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ
	RENAME AssimCtypes.py
	)

install (PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/cma COMPONENT cma-component DESTINATION ${CMAKE_INSTALL_PREFIX}/sbin)

install(DIRECTORY tests 
        COMPONENT cma-component DESTINATION ${PYINSTALL} FILES_MATCHING PATTERN "*.py")
