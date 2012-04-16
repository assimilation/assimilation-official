REPCOUNT=20
GEN=--gen-suppressions=no
GEN=--gen-suppressions=all
sudo valgrind -q --sim-hints=lax-ioctls --leak-check=full --show-reachable=yes --suppressions=../../src/testcode/valgrind-msgs.supp $GEN --error-exitcode=100 ./mainlooptest $REPCOUNT
