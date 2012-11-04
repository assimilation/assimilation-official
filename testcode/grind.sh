HERE=$(dirname $0)
REPCOUNT=20
GEN=--gen-suppressions=all
GEN="--gen-suppressions=no --num-callers=50 --read-var-info=yes"
GEN="--gen-suppressions=no --num-callers=50"
sudo valgrind -q --sim-hints=lax-ioctls --leak-check=full --show-reachable=yes --suppressions=$HERE/valgrind-msgs.supp $GEN --error-exitcode=100 --trace-children=no --child-silent-after-fork=yes ./mainlooptest $REPCOUNT
