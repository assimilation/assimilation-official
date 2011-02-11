add_library (clientlib SHARED proj_classes.c cdp_min.c lldp_min.c pcap_min.c generic_tlv_min.c pcap_GSource.c tlvhelper.c frameset.c frame.c intframe.c addrframe.c cstringframe.c signframe.c)
target_link_libraries (clientlib -lpcap -lglib-2.0)
