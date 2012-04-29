REPCOUNT=20
GEN=--gen-suppressions=all
GEN="--gen-suppressions=no --num-callers=50 --read-var-info=yes"
GEN="--gen-suppressions=no --num-callers=50"
sudo valgrind -q --sim-hints=lax-ioctls --leak-check=full --show-reachable=yes --suppressions=../../src/testcode/valgrind-msgs.supp $GEN --error-exitcode=100 ./mainlooptest $REPCOUNT
