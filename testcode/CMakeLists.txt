add_executable (filetest pcap_test.c)
add_executable (mainlooptest pcap+mainloop.c)
target_link_libraries (filetest clientlib serverlib -lpcap )
target_link_libraries (mainlooptest clientlib serverlib -lpcap )

