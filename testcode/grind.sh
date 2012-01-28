sudo valgrind -q --sim-hints=lax-ioctls --leak-check=full --show-reachable=yes --suppressions=../../src/testcode/valgrind-msgs.supp --gen-suppressions=no --error-exitcode=100 ./mainlooptest 4 
