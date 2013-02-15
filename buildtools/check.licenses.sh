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
HERE=$(dirname $0)
if
  [ "$HERE" = '.' ]
then
  TOP=..
else
  TOP=$(dirname $HERE)
fi
HERE=$(dirname $0)
excludelist=/tmp/$$.exclude
trap 'rm -f $excludelist $includelist' 0
cat <<-!EXCLUDE > $excludelist
	cma/AssimCtypes.py
	docfiles/
	CMakeFiles/
	pcap/oui.txt
	pcap/shortoui.txt
	CMakeCache.txt
	cma/__init__.py
	cma/tests/__init__.py
	testcode/filetest.ref.txt
	testcode/mainloop.ref.txt
	_CPack_Packages/
	install_manifest
	!EXCLUDE
includelist=/tmp/$$.included
find "$TOP"  \( -name '.hg' -prune \) -o \( -name '*.[ch]' -o -name '*.[ch].in' -o -name '*.py' -o -name '*.txt' -o -name '*.sh' \) -a -print | grep -v -F -f $excludelist  | sort -u -o $includelist
while
  read file
do
  if
    grep -i 'GNU General Public License' "$file" >/dev/null 2>&1 &&
    grep -i 'version 3 of the License, or' "$file" >/dev/null 2>&1 &&
    egrep -i 'Copyright.*201[12].*Alan *Robertson *<alanr@unix.sh>' "$file" >/dev/null 2>&1
  then
    : OK
  else
    echo "$file"
  fi
done <$includelist
