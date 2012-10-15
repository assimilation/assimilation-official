cmake_minimum_required(VERSION 2.8)
project(assimilation C)
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
#	
#
#
set(CMAKE_INSTALL_PREFIX /usr)
#Supposedly this isn't necessary...
#execute_process (OUTPUT_VARIABLE LIB_DIRNAME OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND python buildtools/determinelibdir.py)
set(LIB_DIRNAME lib${LIB_SUFFIX})
set(InstallLIBS ${CMAKE_INSTALL_PREFIX}/${LIB_DIRNAME})
set (CLIENTLIB ${PROJECT_NAME}clientlib)
set (SERVERLIB ${PROJECT_NAME}serverlib)
# Figure out where to install our python code
# This isn't perfect, but it should get things going...
execute_process (OUTPUT_VARIABLE PYTHON_PKGDIR OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND python buildtools/install-path.py)
set (PYINSTALL ${PYTHON_PKGDIR}/${PROJECT_NAME})
set (USRSHARE ${CMAKE_INSTALL_PREFIX}/share/${PROJECT_NAME})
set (DAGENTS discovery_agents)
set (DISCOVERYINSTALL ${USRSHARE}/${DAGENTS})
#####################################################################################

include (CheckSymbolExists)

if(WIN32)
  set(CMAKE_C_COMPILER,"cl")
else(WIN32)
  set(CMAKE_C_COMPILER,"/usr/bin/clang")
endif(WIN32)


include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR}/include)
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


if("${CMAKE_C_COMPILER}" MATCHES ".*/ccc-analyze")
  add_definitions("-Werror -Wall -Wformat=2 -Wmissing-prototypes -Wmissing-declarations -Wstrict-prototypes -Wdeclaration-after-statement -Wpointer-arith -Wwrite-strings -Wcast-qual -Wcast-align -Winline -Wmissing-format-attribute -Wno-strict-aliasing -funsigned-char -Wextra -Wstack-protector")
  # Kludges to work around in older Clang versions
  if ("${GLIB2_INCLUDE_DIRS}" MATCHES ".*/i386-linux-gnu/.*")
    include_directories("/usr/include/i386-linux-gnu")
  endif()
  if ("${GLIB2_INCLUDE_DIRS}" MATCHES ".*/x86_64-linux-gnu/.*")
    include_directories("/usr/include/x86_64-linux-gnu")
  endif()
elseif("${CMAKE_C_COMPILER}" MATCHES ".*/gcc")
  message(STATUS "found gnu")
endif()
#
#	For some older versions of gcc and/or glib (not sure quite which versions)
#	Add -Wno-int-to-pointer-cast -Wno-pointer-to-int-cast
#	Remove -Wcast-qual
#
IF(CMAKE_COMPILER_IS_GNUCC)
  add_definitions("-Wall -Werror -ggdb3 -Wformat=2 -Wstack-protector -Wmissing-prototypes -Wmissing-declarations -Wstrict-prototypes -Wdeclaration-after-statement -Wpointer-arith -Wwrite-strings -Wcast-qual -Wcast-align -Winline -Wmissing-format-attribute -Wno-strict-aliasing -funsigned-char -Wextra")

ENDIF(CMAKE_COMPILER_IS_GNUCC)

IF(CMAKE_COMPILER_IS_GNUCXX)
  add_definitions("-Wall -Werror -ggdb3 -Wformat=2 -Wstack-protector")
ENDIF(CMAKE_COMPILER_IS_GNUCXX)

add_subdirectory(clientlib)
add_subdirectory(serverlib)
add_subdirectory(testcode)
add_subdirectory(nanoprobe)
add_subdirectory(include)
add_subdirectory(cma)
#add_subdirectory(pyclasswrappers)
# Doxygen documentation stuff...
find_package(Doxygen)
if(DOXYGEN_FOUND)
  configure_file(${CMAKE_CURRENT_SOURCE_DIR}/Doxyfile.in ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile @ONLY)
  add_custom_target(doc # ALL
  ${DOXYGEN_EXECUTABLE} ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile
  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
  COMMENT "Generating API documentation with Doxygen" VERBATIM
  )
endif(DOXYGEN_FOUND)
configure_file(${PROJECT_SOURCE_DIR}/include/projectcommon.h.in ${PROJECT_BINARY_DIR}/include/projectcommon.h)
install (DIRECTORY ${DAGENTS} DESTINATION ${USRSHARE} PATTERN ".nfs*" EXCLUDE PATTERN "*.out" EXCLUDE PATTERN "*.txt" EXCLUDE)
