# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2011, 2012, 2013, 2014 - Alan Robertson <alanr@unix.sh>
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
cmake_minimum_required(VERSION 2.6.4)
project(assimilation C)
execute_process (OUTPUT_VARIABLE BUILDTIME OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND date +%s)
set (BASEVERSION "0.5")
set (PROJVERS "${BASEVERSION}.${BUILDTIME}")
set (SRCROOT ${CMAKE_CURRENT_SOURCE_DIR})
set (BINROOT ${CMAKE_CURRENT_BINARY_DIR})

set (INITDIR "/etc/init.d")
set (CMAKE_BUILD_TYPE debug)

set (BUILDTOOLS ${CMAKE_CURRENT_SOURCE_DIR}/buildtools)
set (DESCRIPTION_FILE "${BUILDTOOLS}/short_description.txt")
file (READ ${BUILDTOOLS}/short_license.txt LICENSE_SHORT)
file (READ ${BUILDTOOLS}/long_license.txt LICENSE_LONG)
string(STRIP "${LICENSE_SHORT}" LICENSE_SHORT)
string(STRIP "${LICENSE_LONG}" LICENSE_LONG)

execute_process (OUTPUT_VARIABLE CPACK_GENERATOR OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND python ${BUILDTOOLS}/select-cpack.py)

#set (CPACK_COMPONENTS_ALL_IN_ONE_PACKAGE 0)
#############################################################
# Figure out our package architecture (and system type)
# Would this be better done by another simple python program?
#############################################################

if (EXISTS "/bin/uname")
  execute_process (OUTPUT_VARIABLE SYSTYPE OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND uname -s)

  if (SYSTYPE STREQUAL "AIX")
    set(PROJARCH aix)
  elseif (SYSTYPE STREQUAL "Darwin" OR SYSTYPE STREQUAL FreeBSD)
    # Try uname -m ...
    execute_process (OUTPUT_VARIABLE PROJARCH OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND uname -m)
  else (SYSTYPE STREQUAL "Darwin" OR SYSTYPE STREQUAL "FreeBSD")
    # Now we hope uname -i gives a good answer...
    execute_process (OUTPUT_VARIABLE PROJARCH OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND uname -i)
  endif (SYSTYPE STREQUAL "AIX")
else (COMMAND uname)
    message(STATUS "Package architecture _assumed_ to be i386")
  set(PROJARCH i386)
endif (EXISTS "/bin/uname")

if (SYSTYPE STREQUAL "Linux" OR SYSTYPE STREQUAL "linux")
  if("${CMAKE_C_COMPILER}" MATCHES ".*/cc")
    set (CMAKE_C_COMPILER "/usr/bin/gcc")
  endif("${CMAKE_C_COMPILER}" MATCHES ".*/cc")
endif (SYSTYPE STREQUAL "Linux" OR SYSTYPE STREQUAL "linux")



if (CPACK_GENERATOR STREQUAL "DEB")
    set (NOARCH all)
    execute_process (OUTPUT_VARIABLE PROJARCH OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND dpkg --print-architecture)
    set (LIBPCAP libpcap0.8)
    set (LIBGLIB libglib2.0-0)
else (CPACK_GENERATOR STREQUAL "DEB")
    set (NOARCH noarch)
    set (LIBPCAP libpcap)
    set (LIBGLIB libglib2.0)
endif (CPACK_GENERATOR STREQUAL "DEB")
#############################################################
#
#	Definitions that Cpack likes to see...
#
#	For some cases, it will take *two* invocations of cpack for changes to take effect.
#	This is *very* confusing until you come to expect it".
#
#############################################################
set (CPACK_PACKAGE_CONTACT "Assimilation Mailing List <assimilation@lists.community.tummy.com>")
file (READ ${DESCRIPTION_FILE} CPACK_PACKAGE_DESCRIPTION_SUMMARY)
string(STRIP "${CPACK_PACKAGE_DESCRIPTION_SUMMARY}" CPACK_PACKAGE_DESCRIPTION_SUMMARY)
set (SUMMARY ${CPACK_PACKAGE_DESCRIPTION_SUMMARY})
set (CPACK_PACKAGE_DESCRIPTION_SUMMARY "${SUMMARY}")
set (CPACK_PACKAGE_DESCRIPTION_FILE ${DESCRIPTION_FILE})
set (CPACK_PACKAGE_RESOURCE_FILE_README ${CMAKE_CURRENT_SOURCE_DIR}/README)
set (CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA ${CMAKE_CURRENT_BINARY_DIR}/buildtools/debian/postinst)
set (CPACK_PACKAGE_VENDOR_NAME "The Assimilation Project - assimmon.org // Assimilation Systems Limited - assimilationsystems.com")
set (CPACK_DEBIAN_PACKAGE_SECTION "contrib/admin")
set (CPACK_DEBIAN_PACKAGE_ARCHITECTURE ${PROJARCH})
# The CPACK_NANOPROBE_PACKAGE_DEPENDS only works with patched versions of cpack - so I repeat the nanoprobe ones below
# I can't do that for the CMA dependencies, or the nanoprobe will pick up those dependencies too - which it doesn't need.
# So, without this patch, these CMA dependencies will be missing :-(
set (CPACK_DEB_NANOPROBE_PACKAGE_DEPENDS "libc6, resource-agents, iproute, ${LIBPCAP}, ${LIBGLIB}")
set (CPACK_DEBIAN_PACKAGE_DEPENDS        "libc6, resource-agents, iproute, ${LIBPCAP}, ${LIBGLIB}")
set (CPACK_DEB_CMA_PACKAGE_DEPENDS "python, python-netaddr, python-flask")
#When I turn on SHLIBDEPS, I get this error...
#CPackDeb: dpkg-shlibdeps: dpkg-shlibdeps: need at least one executable
#set (CPACK_DEBIAN_PACKAGE_SHLIBDEPS ON)	# autogenerate dependency information
set (CPACK_RESOURCE_FILE_LICENSE "${CMAKE_CURRENT_SOURCE_DIR}/legal/COPYING")
set (CPACK_COMPONENT_CMA-COMPONENT_DEPENDS NANOPROBE-COMPONENT)
set (CPACK_RPM_PACKAGE_LICENSE "${LICENSE_SHORT}")
set (CPACK_DEB_COMPONENT_INSTALL ON)
set (CPACK_RPM_COMPONENT_INSTALL ON)

set (CPACK_PACKAGE_FILE_NAME "assimilation")
set (CPACK_PACKAGE_VERSION "${PROJVERS}")


# Fool Cpack into generating conventional package names
if (${CPACK_GENERATOR} STREQUAL "DEB")
  set(CMANAME cma-${PROJVERS}-${NOARCH})
  set(NANOPROBENAME nanoprobe-${PROJVERS}-${PROJARCH})
elseif (${CPACK_GENERATOR} STREQUAL "RPM")
else (${CPACK_GENERATOR} STREQUAL "RPM")
  set(CMANAME cma-${PROJVERS}-${NOARCH})
  set(NANOPROBENAME nanoprobe-${PROJVERS}-${PROJARCH})
endif (${CPACK_GENERATOR} STREQUAL "DEB")

#
#
set (CPACK_COMPONENT_CMA-COMPONENT_GROUP "${CMANAME}")
set (CPACK_COMPONENT_NANOPROBE-COMPONENT_GROUP "${NANOPROBENAME}")
#
#	Important project-specific variables we set:
#	InstallLIBS		where we install our libraries
#	CLIENTLIB		the name of our client-side (nanoprobe) library - also used by the CMA
#	SERVERLIB		the name of our server-side library
#	PYINSTALL		Where we install our python files
#	USRSHARE		Our nanoprobe subdirectory under /usr/share
#	USRSHARECMA		Our CMA subdirectory under /usr/share
#	DAGENTS			the relative directory name we source discovery agents from
#	DISCOVERYINSTALL	Where we install our discovery scripts
#	QUERYSUBDIR		the relative directory where we store the flat files we make query nodes from
#	QUERYINSTALL		Where we install our query flat files
#	MONRULESUBDIR		the relative directory where we store the flat files containing our monitoring rules
#	MONRULEINSTALL		Where we install our monitoring rule flat files
#	CRYPTKEYDIR		Where we keep our encryption/signature keys
#	OCFINSTALL		Where we install our OCF resource agents
#	CMAADDR			Default address and port of the CMA - defaults to 224.0.2.5:1984
#	CMAINITFILE		Name of initialization file for the CMA - defaults to /etc/cma.conf
#	NANOLISTENADDR		Default listen address/port for nanoprobes - defaults to 0.0.0.0:1984
#	CMAUSERID		The user id to run the CMA as - defaults to 'assimilation'
#	

if (WIN32)
set(CMAKE_INSTALL_PREFIX ${PROJECT_SOURCE_DIR})
set (LIB_DIRNAME ${LIB_SUFFIX})
set (InstallLIBS ${CMAKE_INSTALL_PREFIX}/nanoprobe/${CMAKE_BUILD_TYPE})
set (USRSHARE ${CMAKE_INSTALL_PREFIX}/nanoprobe)
set (DIRDELIM \\ )
else (WIN32)
set (DIRDELIM /)
set(CMAKE_INSTALL_PREFIX /usr)
if (NOT LIBDIR)
  # This next command depends on the assumption that libc is in /something and that
  # we want to put our library in ${CMAKE_INSTALL_PREFIX}/something
  execute_process (OUTPUT_VARIABLE LIBSUFFIX OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND sh -c "dirname \$(ldd /bin/sh | grep libc | sed -e 's%.*=> *%%' -e 's% .*%%')")
  set (LIBDIR ${CMAKE_INSTALL_PREFIX}${LIBSUFFIX})
endif (NOT LIBDIR)
set (InstallLIBS ${LIBDIR}/${PROJECT_NAME})
set (USRSHARE ${CMAKE_INSTALL_PREFIX}/share/${PROJECT_NAME})
endif (WIN32)
MESSAGE ("Project LIBDIR IS ${InstallLIBS}")

set (CLIENTLIB ${PROJECT_NAME}clientlib)
set (SERVERLIB ${PROJECT_NAME}serverlib)
# Figure out where to install our python code
# This isn't perfect, but it should be good enough for us to get things going...
execute_process (OUTPUT_VARIABLE PYTHON_PKGDIR OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND python ${BUILDTOOLS}/install-path.py)
set (PYINSTALL ${PYTHON_PKGDIR}/${PROJECT_NAME})

set (DAGENTS discovery_agents)
set (DISCOVERYINSTALL ${USRSHARE}/${DAGENTS})
set (QUERYSUBDIR queries)
set (QUERYINSTALL ${USRSHARE}/${QUERYSUBDIR})
set (MONRULESUBDIR monrules)
set (MONRULEINSTALL ${USRSHARE}/${MONRULESUBDIR})
set (NOTIFICATIONDIR notification.d)
set (NOTIFICATION_SCRIPT_DIR ${USRSHARE}/${NOTIFICATIONDIR})
set (CRYPTKEYDIR ${USRSHARE}/crypto.d)
set (PUBKEYSUFFIX .pub)
set (PRIVATEKEYSUFFIX .secret)
set (OCFINSTALL /usr/lib/ocf/resource.d/assimilation)
#	OCFINSTALL		Where we install our OCF resource agents
configure_file(${BUILDTOOLS}/debian/postinst.in ${CMAKE_CURRENT_BINARY_DIR}/buildtools/debian/postinst @ONLY)
configure_file(${BUILDTOOLS}/debian/postrm.in ${CMAKE_CURRENT_BINARY_DIR}/buildtools/debian/postrm @ONLY)
#
# CMAADDR is the address where the nanoprobes should go to initially find the CMA.
# 224.0.2.5 is a multicast address which we reseved from IANA for the Assimilation project.
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
if (NOT CMAINITFILE) 
  set (CMAINITFILE "/etc/cma.conf")
endif (NOT CMAINITFILE) 

if (NOT CMAUSERID)
  set(CMAUSERID "assimilation")
endif (NOT CMAUSERID)
  
#####################################################################################


if(WIN32)
  set(CMAKE_C_COMPILER,"cl")
else(WIN32)
  set(CMAKE_C_COMPILER,"/usr/bin/clang")
endif(WIN32)


include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR}/include)

#
#	Get options for glib2 from pkg-config (for both Linux and Windows)
#	Sometimes it's called glib-2.0 and sometimes libglib-2.0 - Sigh...
#
include(FindPkgConfig)

if (PKG_CONFIG_FOUND OR PKGCONFIG_FOUND)
    #pkg_check_modules(GLIB2 QUIET glib-2.0)
    pkg_check_modules(GLIB2 glib-2.0)
    if (NOT GLIB2_FOUND)
        pkg_check_modules(GLIB2 REQUIRED libglib-2.0)
        if (NOT GLIB2_FOUND)
            message(SEND_ERROR "Cannot find development package for glib2.0")
        endif (NOT GLIB2_FOUND)
    endif (NOT GLIB2_FOUND)
    
    include_directories(${GLIB2_INCLUDE_DIRS})
    #set(CMAKE_REQUIRED_FLAGS ${GLIB2_LDFLAGS})
if (WIN32)
    set(CMAKE_REQUIRED_LIBRARIES ${CMAKE_REQUIRED_LIBRARIES} ${GLIB2_LIBDIR}/glib-2.0.lib)
    include_directories("C:/winpcap/include")
    include_directories("C:/winpcap/src/wpcap/libpcap")
    INCLUDE_DIRECTORIES(${CMAKE_INCLUDE_PATH})
else (WIN32)
	set(CMAKE_REQUIRED_LIBRARIES c ${CMAKE_REQUIRED_LIBRARIES} ${GLIB2_LIBRARIES})
endif (WIN32)

else (PKG_CONFIG_FOUND OR PKGCONFIG_FOUND)
    message(SEND_ERROR "Cannot find pkg-config utility")
endif (PKG_CONFIG_FOUND OR PKGCONFIG_FOUND)

#
#	Checking for various system functions and header files...
#
include(CheckIncludeFile)
CHECK_INCLUDE_FILE(unistd.h HAVE_UNISTD_H)
CHECK_INCLUDE_FILE(sys/utsname.h HAVE_SYS_UTSNAME_H)
CHECK_INCLUDE_FILE(fcntl.h HAVE_FCNTL_H)
CHECK_INCLUDE_FILE(mcheck.h HAVE_MCHECK_H)
CHECK_INCLUDE_FILE(sys/types.h HAVE_SYS_TYPES_H)
CHECK_INCLUDE_FILE(sys/socket.h HAVE_SYS_SOCKET_H)
CHECK_INCLUDE_FILE(netdb.h HAVE_NETDB_H)
CHECK_INCLUDE_FILE(zlib.h HAVE_ZLIB_H)
CHECK_INCLUDE_FILE(sodium.h HAVE_SODIUM_H)
include(CheckFunctionExists)
include(CheckSymbolExists)
CHECK_FUNCTION_EXISTS(clock_gettime  HAVE_CLOCK_GETTIME)
CHECK_FUNCTION_EXISTS(endprotoent  HAVE_ENDPROTOENT)
CHECK_FUNCTION_EXISTS(fcntl HAVE_FCNTL)
CHECK_FUNCTION_EXISTS(g_get_real_time HAVE_G_GET_REAL_TIME)
CHECK_FUNCTION_EXISTS(g_get_monotonic_time HAVE_G_GET_MONOTONIC_TIME)
CHECK_FUNCTION_EXISTS(g_get_environ HAVE_G_GET_ENVIRON)
CHECK_FUNCTION_EXISTS(getaddrinfo HAVE_GETADDRINFO)
CHECK_FUNCTION_EXISTS(geteuid HAVE_GETEUID)
CHECK_FUNCTION_EXISTS(kill HAVE_KILL)
CHECK_FUNCTION_EXISTS(mcheck HAVE_MCHECK)
CHECK_FUNCTION_EXISTS(mcheck_pedantic HAVE_MCHECK_PEDANTIC)
CHECK_FUNCTION_EXISTS(setpgid  HAVE_SETPGID)
CHECK_FUNCTION_EXISTS(sigaction HAVE_SIGACTION)
CHECK_FUNCTION_EXISTS(uname HAVE_UNAME)

CHECK_SYMBOL_EXISTS(GetComputerNameA "Windows.h" HAVE_GETCOMPUTERNAME) 

#
#	Compiler flags for various compilers and platforms...
#
set (Best_GNUCC_FLAGS "-g -O2 -Werror -Wall -Wformat=2 -Wmissing-prototypes -Wmissing-declarations -Wstrict-prototypes -Wdeclaration-after-statement -Wpointer-arith -Wwrite-strings -Wcast-align -Winline -Wmissing-format-attribute -Wno-strict-aliasing -funsigned-char -Wextra -Wstack-protector -Wformat-security -D_FORTIFY_SOURCE=2")

set (Lesser_GNUCC_FLAGS "-Werror -Wall -Wformat=2 -Wmissing-prototypes -Wmissing-declarations -Wstrict-prototypes -Wdeclaration-after-statement -Wpointer-arith -Wwrite-strings -Wcast-align -Winline -Wmissing-format-attribute -Wno-strict-aliasing -funsigned-char -Wextra -Wstack-protector -Wno-int-to-pointer-cast -Wno-pointer-to-int-cast -Wcast-qual -D_FORTIFY_SOURCE=2")
set (Best_CLANG_FLAGS "-Werror -Wall -Wformat=2 -Wmissing-prototypes -Wmissing-declarations -Wstrict-prototypes -Wdeclaration-after-statement -Wpointer-arith -Wwrite-strings -Wcast-qual -Wcast-align -Winline -Wmissing-format-attribute -Wno-strict-aliasing -funsigned-char -Wextra -Wstack-protector")

set (Active_CLANG_FLAGS ${Best_CLANG_FLAGS})

if (NOT WIN32)
set (OUR_LINKER_FLAGS "-Wl,-Bsymbolic-functions -Wl,-z,relro -z now")
endif (NOT WIN32)

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
  set (CMAKE_EXE_LINKER_FLAGS ${OUR_LINKER_FLAGS})
  set (CMAKE_SHARED_LINKER_FLAGS ${OUR_LINKER_FLAGS})
elseif("${CMAKE_C_COMPILER}" MATCHES ".*/gcc")
  message(STATUS "Found GNU gcc")
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
  set (CMAKE_EXE_LINKER_FLAGS ${OUR_LINKER_FLAGS})
  set (CMAKE_SHARED_LINKER_FLAGS ${OUR_LINKER_FLAGS})
  ENDIF(CMAKE_COMPILER_IS_GNUCC)
else("${CMAKE_C_COMPILER}" MATCHES ".*/ccc-analyze")
  message(STATUS "Unknown compiler ${CMAKE_C_COMPILER}")
endif("${CMAKE_C_COMPILER}" MATCHES ".*/ccc-analyze")
set (CMAKE_POSITION_INDEPENDENT_CODE ON)

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
#	Install our discovery agents under /usr/share/assimilation.  Retain permissions from source control.
#
install (DIRECTORY ${DAGENTS} COMPONENT nanoprobe-component DESTINATION ${DESTDIR}${USRSHARE} USE_SOURCE_PERMISSIONS
	PATTERN ".nfs*" EXCLUDE PATTERN "*.out" EXCLUDE PATTERN "*.txt" EXCLUDE)
#
#
#	Install our query flat files under /usr/share/assimilation/${QUERYSUBDIR}
#
install (DIRECTORY ${QUERYSUBDIR} COMPONENT cma-component DESTINATION ${DESTDIR}${USRSHARE})
#
#
#	Install our monitoring rule flat files under /usr/share/assimilation/${MONRULESUBDIR}
#
install (DIRECTORY ${MONRULESUBDIR} COMPONENT cma-component DESTINATION ${DESTDIR}${USRSHARE})
#
#	Install our OCF scripts under /usr/lib/ocf/resource.d/assimilation - as part of the nanoprobe package
#
install (PROGRAMS ocf/neo4j COMPONENT nanoprobe-component DESTINATION ${DESTDIR}${OCFINSTALL})
#
#	Create an empty notification script directory under /usr/share/assimilation/notification.d
#
install (DIRECTORY COMPONENT cma-component DESTINATION ${DESTDIR}${NOTIFICATION_SCRIPT_DIR})
#
#	Install our init scripts in ${INITDIR}
#
install (PROGRAMS  ${PROJECT_SOURCE_DIR}/buildtools/nanoprobe COMPONENT nanoprobe-component DESTINATION ${DESTDIR}${INITDIR})
install (PROGRAMS  ${PROJECT_SOURCE_DIR}/buildtools/cma COMPONENT cma-component DESTINATION ${DESTDIR}${INITDIR})
#
#	Install our copyright file
#
install (FILES  ${PROJECT_SOURCE_DIR}/legal/copyright COMPONENT nanoprobe-component DESTINATION ${DESTDIR}${USRSHARE})
#install (FILES  ${PROJECT_SOURCE_DIR}/legal/copyright COMPONENT cma-component DESTINATION ${DESTDIR}${USRSHARE})

# Create the CMA user id at install time as part of the CMA component
install (CODE "execute_process ( COMMAND /bin/sh -c \"getent passwd assimilation >/dev/null || adduser --disabled-login --disabled-password --no-create-home --gecos 'Assimilation software CMA' --shell /bin/false ${CMAUSERID}\" )" COMPONENT cma-component ) 


#
#	This has to be the last command in the file
#
include(CPack)
