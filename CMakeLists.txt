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
cmake_minimum_required(VERSION 2.8.5)
project(assimilation C)
set (BUILDTOOLS ${CMAKE_CURRENT_SOURCE_DIR}/buildtools)
#
#	Definitions that packaging systems like to see...
#
set (CPACK_PACKAGE_CONTACT Assimilation Mailing List <assimilation@lists.community.tummy.com>)
set (CPACK_PACKAGE_DESCRIPTION_SUMMARY Hyperscale Discovery-Driven Monitoring System)
set (CPACK_PACKAGE_DESCRIPTION_FILE ${CMAKE_CURRENT_BINARY_DIR}/doxygen/html/_r_e_a_d_m_e.html)
set (CPACK_PACKAGE_RESOURCE_FILE_README ${CMAKE_CURRENT_SOURCE_DIR}/docfiles/README.c)
set (CPACK_PACKAGE_VENDOR_NAME Assimilation Systems Limited - a Colorado Limited Liability Company)
set (CPACK_RPM_PACKAGE_LICENSE "GPLv3")
set(CPACK_DEB_COMPONENT_INSTALL ON)
set(CPACK_RPM_COMPONENT_INSTALL ON)
execute_process (OUTPUT_VARIABLE CPACK_GENERATOR OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND python ${BUILDTOOLS}/select-cpack.py)

#
#
set (CPACK_COMPONENT_CMA-COMPONENT_GROUP "cma")
set (CPACK_COMPONENT_NANOPROBE-COMPONENT_GROUP "nanoprobe")
#
#	Important project-specific variables we set:
#	LIB_DIRNAME		either lib or lib64 -- as appropriate
#	InstallLIBS		where we install our libraries
#	CLIENTLIB		the name of our client-side (nanoprobe) library - also used by the CMA
#	SERVERLIB		the name of our server-side library
#	PYINSTALL		Where we install our python files
#	USRSHARE		Our subdirectory under /usr/share
#	DAGENTS			the relative directory name we source discovery agents from
#	DISCOVERYINSTALL	Where we install our discovery scripts
#	CMAADDR			Default address and port of the CMA - defaults to 224.0.2.5:1984
#	NANOLISTENADDR		Default listen address/port for nanoprobes - defaults to 0.0.0.0:1984
#	
set(CMAKE_BUILD_TYPE debug)
set(CMAKE_INSTALL_PREFIX /usr)
set (LIB_DIRNAME lib${LIB_SUFFIX})
set (InstallLIBS ${CMAKE_INSTALL_PREFIX}/${LIB_DIRNAME})
set (CLIENTLIB ${PROJECT_NAME}clientlib)
set (SERVERLIB ${PROJECT_NAME}serverlib)
# Figure out where to install our python code
# This isn't perfect, but it should be good enough for us to get things going...
execute_process (OUTPUT_VARIABLE PYTHON_PKGDIR OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND python ${BUILDTOOLS}/install-path.py)
set (PYINSTALL ${PYTHON_PKGDIR}/${PROJECT_NAME})
set (USRSHARE ${CMAKE_INSTALL_PREFIX}/share/${PROJECT_NAME})
set (DAGENTS discovery_agents)
set (DISCOVERYINSTALL ${USRSHARE}/${DAGENTS})
#
# CMAADDR is the address where the nanoprobes should go to initially find the CMA.
# 224.0.2.5 is a multicast address which I reseved from IANA for the Assimilation project.
# Port 1984 UDP and TCP is reserved from IANA for the Big Brother monitoring system which
# is in turn owned by Sean MacGuire.  Big Brother reserved both TCP and UDP ports but only
# uses the TCP port.  Sean MacGuire gave us permission to use port 1984/UDP for the
# Assimilation Project.
# So this is why we default to 224.0.2.5:1984 for all our UDP communication.
# Ephemeral ports are NOT OK for the CMA.
#
if (NOT CMAADDR) 
  set(CMAADDR "224.0.2.5:1984")
endif (NOT CMAADDR) 
# Probably don't want to override NANOLISTENADDR at compile time - better to override it
# at run time, or let it grab an ephemeral port (which it will do if the 
# requested port is not available).  Ephemeral ports are fine for nanoprobes.
# But if you need to change the default port to something else - feel free...
if (NOT NANOLISTENADDR) 
  set(NANOLISTENADDR "0.0.0.0:1984")
endif (NOT NANOLISTENADDR) 
#####################################################################################

include (CheckSymbolExists)

if(WIN32)
  set(CMAKE_C_COMPILER,"cl")
else(WIN32)
  set(CMAKE_C_COMPILER,"/usr/bin/clang")
endif(WIN32)


include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR}/include)

#
#	Get options for glib2 from pkg-config (for both Linux and Windows)
#
include(FindPkgConfig)
pkg_check_modules(GLIB2 REQUIRED glib-2.0)
if (PKG_CONFIG_FOUND)
    include_directories(${GLIB2_INCLUDE_DIRS})
else (PKG_CONFIG_FOUND)
  # Hopefully this isn't needed any more...
  if(WIN32)
      include_directories("C:/Glib/Glib-2-28-8-1/include/glib-2.0")
      include_directories("C:/Glib/Glib-2-28-8-1/lib/glib-2.0/include")
  else(WIN32)
      include_directories("/usr/lib/glib-2.0/include")
      include_directories("/usr/include/glib-2.0")
      include_directories("/usr/lib/i386-linux-gnu/glib-2.0/include")
      include_directories("/usr/include/i386-linux-gnu")
      include_directories(${CMAKE_CURRENT_BINARY_DIR}/include)
  ENDIF(WIN32)
endif (PKG_CONFIG_FOUND)

if(WIN32)
      include_directories("C:/winpcap/include")
      INCLUDE_DIRECTORIES(${CMAKE_INCLUDE_PATH})
endif(WIN32)

#
#	Compiler flags for various compilers and platforms...
#
set (Best_GNUCC_FLAGS "-Werror -Wall -Wformat=2 -Wmissing-prototypes -Wmissing-declarations -Wstrict-prototypes -Wdeclaration-after-statement -Wpointer-arith -Wwrite-strings -Wcast-align -Winline -Wmissing-format-attribute -Wno-strict-aliasing -funsigned-char -Wextra -Wstack-protector")
set (Lesser_GNUCC_FLAGS "-Werror -Wall -Wformat=2 -Wmissing-prototypes -Wmissing-declarations -Wstrict-prototypes -Wdeclaration-after-statement -Wpointer-arith -Wwrite-strings -Wcast-align -Winline -Wmissing-format-attribute -Wno-strict-aliasing -funsigned-char -Wextra -Wstack-protector -Wno-int-to-pointer-cast -Wno-pointer-to-int-cast-Wcast-qual")
set (Best_CLANG_FLAGS "-Werror -Wall -Wformat=2 -Wmissing-prototypes -Wmissing-declarations -Wstrict-prototypes -Wdeclaration-after-statement -Wpointer-arith -Wwrite-strings -Wcast-qual -Wcast-align -Winline -Wmissing-format-attribute -Wno-strict-aliasing -funsigned-char -Wextra -Wstack-protector")

set (Active_CLANG_FLAGS ${Best_CLANG_FLAGS})


if("${CMAKE_C_COMPILER}" MATCHES ".*/ccc-analyze")
  message(STATUS "found CLANG")
  add_definitions(${Active_CLANG_FLAGS})
  # Kludges to work around in older Clang versions
  if ("${GLIB2_INCLUDE_DIRS}" MATCHES ".*/i386-linux-gnu/.*")
    include_directories("/usr/include/i386-linux-gnu")
  endif()
  if ("${GLIB2_INCLUDE_DIRS}" MATCHES ".*/x86_64-linux-gnu/.*")
    include_directories("/usr/include/x86_64-linux-gnu")
  endif()
elseif("${CMAKE_C_COMPILER}" MATCHES ".*/gcc")
  message(STATUS "found gnu")
  IF(CMAKE_COMPILER_IS_GNUCC)
  #
  # Some versions of GCC combined with versions of glib don't like our most strict flags.
  # So we try and figure out the strictest flags we can enable and have it compile.
  #
  file (WRITE ${CMAKE_BINARY_DIR}/CmakeTmp/testflags.c
"#include <glib.h>
int main(int argc, char **argv) {
	GQuark	q = 0; (void)argc; (void)argv;
	return GUINT_TO_POINTER(q) == NULL;
}")
    TRY_COMPILE(GOOD_GCC_FLAGS_WORK
	${CMAKE_BINARY_DIR}
	${CMAKE_BINARY_DIR}/CmakeTmp/testflags.c
	COMPILE_DEFINITIONS ${GLIB2_STATIC_CFLAGS} ${Best_GNUCC_FLAGS}
	)
     execute_process (COMMAND ${CMAKE_COMMAND} -E remove_directory ${CMAKE_BINARY_DIR}/CmakeTmp)

    if (GOOD_GCC_FLAGS_WORK)
      message(STATUS "Notice: Enabling the strictest GCC flags.")
      add_definitions(${Best_GNUCC_FLAGS})
    else (GOOD_GCC_FLAGS_WORK)
      message(STATUS "WARNING: Enabling somewhat less strict GCC flags.")
      add_definitions(${Lesser_GNUCC_FLAGS})
      if (IS_DIRECTORY "/usr/lib/glib-2.0/include")
          # Sleazy -- should be unnecessary - but glibconfig seems broken for me on some older platforms...
          message(STATUS "ADDING: /usr/lib/glib-2.0/include")
          include_directories("/usr/lib/glib-2.0/include")
      endif (IS_DIRECTORY "/usr/lib/glib-2.0/include")
    endif (GOOD_GCC_FLAGS_WORK)
  ENDIF(CMAKE_COMPILER_IS_GNUCC)
endif("${CMAKE_C_COMPILER}" MATCHES ".*/ccc-analyze")

#
#	Add all our various subdirectories... Order matters...
#
add_subdirectory(clientlib)
add_subdirectory(serverlib)
add_subdirectory(testcode)
add_subdirectory(nanoprobe)
add_subdirectory(include)
add_subdirectory(cma)
#
# Doxygen documentation stuff...
#
find_package(Doxygen)
if(DOXYGEN_FOUND)
  configure_file(${CMAKE_CURRENT_SOURCE_DIR}/Doxyfile.in ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile @ONLY)
  add_custom_target(doc # ALL
  ${DOXYGEN_EXECUTABLE} ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile
  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
  COMMENT "Generating API documentation with Doxygen" VERBATIM
  )
endif(DOXYGEN_FOUND)
#
#	Create a header file with some of our project (install) directories defined
#
configure_file(${PROJECT_SOURCE_DIR}/include/projectcommon.h.in ${PROJECT_BINARY_DIR}/include/projectcommon.h)
#
#	Install our discovery agents under /usr/share/assimilation.  Retain permissions from source control.
#
install (DIRECTORY ${DAGENTS} COMPONENT nanoprobe-component DESTINATION ${USRSHARE} USE_SOURCE_PERMISSIONS
	PATTERN ".nfs*" EXCLUDE PATTERN "*.out" EXCLUDE PATTERN "*.txt" EXCLUDE)

#
#	This has to be the last command in the file
#
include(CPack)
