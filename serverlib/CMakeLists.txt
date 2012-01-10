add_library(serverlib SHARED dump.c lldp.c cdp.c)


if(WIN32)


target_link_libraries(serverlib clientlib)
endif(WIN32)
