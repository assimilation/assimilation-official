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
SET (FST_H ${CMAKE_CURRENT_BINARY_DIR}/../include/framesettypes.h)
SET (FT_H ${CMAKE_CURRENT_BINARY_DIR}/../include/frametypes.h)
SET (GENCMD ${CMAKE_CURRENT_SOURCE_DIR}/../cma/frameinfo.py)

ADD_CUSTOM_COMMAND(
   OUTPUT ${FST_H}
   COMMAND python ${GENCMD} framesettypes ${FST_H}
   DEPENDS ${GENCMD}
   )
ADD_CUSTOM_TARGET(generate_framesettypes DEPENDS ${FST_H})

ADD_CUSTOM_COMMAND(
   OUTPUT ${FT_H}
   COMMAND python ${GENCMD} frametypes ${FT_H}
   DEPENDS ${GENCMD}
   )
ADD_CUSTOM_TARGET(generate_frametypes DEPENDS ${FT_H})

add_library (${CLIENTLIB} SHARED proj_classes.c cdp_min.c lldp_min.c pcap_min.c generic_tlv_min.c pcap_GSource.c tlvhelper.c frameset.c frame.c intframe.c addrframe.c cstringframe.c signframe.c unknownframe.c seqnoframe.c packetdecoder.c discovery.c switchdiscovery.c netio.c netioudp.c netgsource.c netaddr.c hblistener.c hbsender.c cryptframe.c compressframe.c nvpairframe.c listener.c configcontext.c assimobj.c authlistener.c jsondiscovery.c nanoprobe.c cmalib.c ipportframe.c misc.c fsqueue.c fsprotocol.c reliableudp.c replacement_funs.c)
SET_SOURCE_FILES_PROPERTIES(${FST_H} PROPERTIES GENERATED 1)
SET_SOURCE_FILES_PROPERTIES(${FT_H} PROPERTIES GENERATED 1)
ADD_DEPENDENCIES(${CLIENTLIB} generate_framesettypes generate_frametypes)

IF(WIN32)
  find_library (PCAP_LIB wpcap PATHS "C:/winpcap/lib")
  find_library (GLIB_LIB glib-2.0 PATHS "C:/Glib/Glib-2-28-8-1/lib") 
  find_library (WS2_LIB ws2_32 )
  target_link_libraries(${CLIENTLIB} ${PCAP_LIB})
  target_link_libraries(${CLIENTLIB} ${GLIB_LIB})
  target_link_libraries(${CLIENTLIB} ${WS2_LIB})
ELSE(WIN32)
  target_link_libraries (${CLIENTLIB} -lpcap -lglib-2.0)
ENDIF(WIN32)
install(TARGETS ${CLIENTLIB} COMPONENT nanoprobe-component LIBRARY DESTINATION ${InstallLIBS})
