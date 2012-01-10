add_executable (filetest pcap_test.c)
add_executable (mainlooptest pcap+mainloop.c)

IF(WIN32)
 
find_library (PCAP_LIB wpcap PATHS "C:/winpcap/lib")
find_library (GLIB_LIB glib-2.0 PATHS "C:/Glib/Glib-2-28-8-1/lib") 

target_link_libraries(filetest  clientlib serverlib ${PCAP_LIB} ${GLIB_LIB})
target_link_libraries(mainlooptest clientlib serverlib ${PCAP_LIB} ${GLIB_LIB})


ELSE(WIN32)
target_link_libraries (filetest clientlib serverlib -lpcap )
target_link_libraries (mainlooptest clientlib serverlib -lpcap )

ENDIF(WIN32)

