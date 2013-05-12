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
add_executable (filetest pcap_test.c)
add_executable (mainlooptest pcap+mainloop.c)
add_executable (pinger pinger.c)
add_executable (gtest01 gtest01.c)
add_executable (gtest02 gtest02.c)

IF(WIN32)
 
  find_library (PCAP_LIB wpcap PATHS "C:/winpcap/lib")
  find_library (GLIB_LIB glib-2.0 PATHS "C:/Glib/Glib-2-28-8-1/lib") 

ELSE(WIN32)
  #target_link_libraries (filetest ${CLIENTLIB} ${SERVERLIB} -lpcap -lrt)
  #target_link_libraries (mainlooptest ${CLIENTLIB} ${SERVERLIB} -lpcap -lrt)
  #target_link_libraries (pinger ${CLIENTLIB} ${GLIB_LIB})
  set (PCAP_LIB -lpcap)
ENDIF(WIN32)
target_link_libraries(filetest     ${CLIENTLIB} ${SERVERLIB} ${PCAP_LIB} ${GLIB_LIB})
target_link_libraries(mainlooptest ${CLIENTLIB} ${SERVERLIB} ${PCAP_LIB} ${GLIB_LIB})
target_link_libraries(pinger       ${CLIENTLIB} ${GLIB_LIB})
target_link_libraries(gtest01      ${CLIENTLIB} ${GLIB_LIB})
target_link_libraries(gtest02      ${CLIENTLIB} ${GLIB_LIB})

