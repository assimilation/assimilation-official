cmake_minimum_required(VERSION 2.8)
project(assimilation C)
include_directories("include")
include_directories("/usr/lib/glib-2.0/include")
include_directories("/usr/include/glib-2.0")
IF(CMAKE_COMPILER_IS_GNUCC)

  add_definitions("-Wall -Werror -ggdb3 -Wformat=2 -Wstack-protector -Wmissing-prototypes -Wmissing-declarations -Wstrict-prototypes -Wdeclaration-after-statement -Wpointer-arith -Wwrite-strings -Wcast-qual -Wcast-align -Winline -Wmissing-format-attribute -Wno-strict-aliasing -funsigned-char")

ENDIF(CMAKE_COMPILER_IS_GNUCC)

IF(CMAKE_COMPILER_IS_GNUCXX)
  add_definitions("-Wall -Werror -ggdb3 -Wformat=2 -Wstack-protector")
ENDIF(CMAKE_COMPILER_IS_GNUCXX)

add_subdirectory(clientlib)
add_subdirectory(serverlib)
add_subdirectory(testcode)

# Doxygen documentation stuff...
find_package(Doxygen)
if(DOXYGEN_FOUND)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/Doxyfile.in ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile @ONLY)
add_custom_target(doc # ALL
${DOXYGEN_EXECUTABLE} ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile >/dev/null
WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
COMMENT "Generating API documentation with Doxygen" VERBATIM
)
endif(DOXYGEN_FOUND)
