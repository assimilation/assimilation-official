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
add_library(${SERVERLIB} SHARED dump.c lldp.c cdp.c)
if (WIN32)
  target_link_libraries(${SERVERLIB} ${CLIENTLIB})
else (WIN32)
install (TARGETS ${SERVERLIB} COMPONENT nanoprobe-component LIBRARY DESTINATION ${DESTDIR}${InstallLIBS})
endif (WIN32)
