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
REPCOUNT=20
GEN=--gen-suppressions=all
GEN="--gen-suppressions=no --num-callers=50 --read-var-info=yes"
GEN="--gen-suppressions=no --num-callers=50"
sudo valgrind -q --sim-hints=lax-ioctls --leak-check=full --show-reachable=yes --suppressions=$HERE/valgrind-msgs.supp $GEN --error-exitcode=100 --trace-children=no --child-silent-after-fork=yes ./mainlooptest $REPCOUNT
