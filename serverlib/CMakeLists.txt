add_library(serverlib SHARED dump.c lldp.c cdp.c)


if(WIN32)


find_library (CLIENT_LIB clientlib PATHS "${CMAKE_BINARY_DIR}/clientlib/Debug")

find_library (CLIENT_LIB clientlib PATHS "${CMAKE_BINARY_DIR}/clientlib/Debug")

target_link_libraries(serverlib ${CLIENT_LIB})
endif(WIN32)
