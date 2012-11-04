add_library(${SERVERLIB} SHARED dump.c lldp.c cdp.c)
if(WIN32)
  target_link_libraries(${SERVERLIB} ${CLIENTLIB})
endif(WIN32)
