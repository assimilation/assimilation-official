SET (FST_H ${CMAKE_CURRENT_BINARY_DIR}/../include/framesettypes.h)
SET (FT_H ${CMAKE_CURRENT_BINARY_DIR}/../include/frametypes.h)
SET (GENCMD ${CMAKE_CURRENT_SOURCE_DIR}/../pyclasswrappers/frameinfo.py)

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

add_library (clientlib SHARED proj_classes.c cdp_min.c lldp_min.c pcap_min.c generic_tlv_min.c pcap_GSource.c tlvhelper.c frameset.c frame.c intframe.c addrframe.c cstringframe.c signframe.c unknownframe.c seqnoframe.c packetdecoder.c discovery.c switchdiscovery.c netio.c netioudp.c netgsource.c netaddr.c hblistener.c hbsender.c cryptframe.c compressframe.c nvpairframe.c listener.c configcontext.c assimobj.c authlistener.c jsondiscovery.c nanoprobe.c cmalib.c ipportframe.c)
SET_SOURCE_FILES_PROPERTIES(${FST_H} PROPERTIES GENERATED 1)
SET_SOURCE_FILES_PROPERTIES(${FT_H} PROPERTIES GENERATED 1)
ADD_DEPENDENCIES(clientlib generate_framesettypes generate_frametypes)

IF(WIN32)
find_library (PCAP_LIB wpcap PATHS "C:/winpcap/lib")
find_library (GLIB_LIB glib-2.0 PATHS "C:/Glib/Glib-2-28-8-1/lib") 
find_library (WS2_LIB ws2_32 )
target_link_libraries(clientlib ${PCAP_LIB})
target_link_libraries(clientlib ${GLIB_LIB})
target_link_libraries(clientlib ${WS2_LIB})
ELSE(WIN32)
target_link_libraries (clientlib -lpcap -lglib-2.0)
ENDIF(WIN32)
