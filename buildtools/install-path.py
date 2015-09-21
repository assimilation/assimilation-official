#
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2011, 2012, 2013 - Alan Robertson <alanr@unix.sh>
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
'''
Program to output where we should locate our installed python code for the system.
It is known to work for at least some Ubuntu versions.  Hope it works elsewhere ;-)

There is no doubt a more wonderful pythonic way to do it.  If you read this and
know of this better way, please let us know, and we'll fix it.
'''
from os.path import join, isfile, isdir
import sys
#print sys.path
if (join(sys.path[1], 'dist-packages')) in sys.path:
  print join(sys.path[1], 'dist-packages')
  sys.exit(0)
for p in sys.path[1:]:
  if p != '' and isfile(join(p,'README.md')):
    print p
    sys.exit(0)
sys.exit(1)
