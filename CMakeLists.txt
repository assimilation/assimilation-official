if(WIN32)
  set(CMAKE_C_COMPILER,"cl")
else(WIN32)
  set(CMAKE_C_COMPILER,"/usr/bin/clang")
endif(WIN32)

cmake_minimum_required(VERSION 2.8)
project(assimilation C)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR}/include)
include(FindPkgConfig)
pkg_check_modules(GLIB2 REQUIRED glib-2.0)
if (PKG_CONFIG_FOUND)
    include_directories(${GLIB2_INCLUDE_DIRS})
else (PKG_CONFIG_FOUND)
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
      INCLUDE_DIRECTORIES( ${CMAKE_INCLUDE_PATH})
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
