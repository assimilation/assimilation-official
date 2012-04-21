IF(WIN32)
 
find_library (PCAP_LIB wpcap PATHS "C:/winpcap/lib")
find_library (GLIB_LIB glib-2.0 PATHS "C:/Glib/Glib-2-28-8-1/lib") 

ELSE(WIN32)
set (PCAP_LIB -lpcap)
set (GLIB_LIB )

ENDIF(WIN32)

add_executable (nanoprobe nanoprobe.c)
target_link_libraries(nanoprobe  clientlib serverlib ${PCAP_LIB} ${GLIB_LIB})
