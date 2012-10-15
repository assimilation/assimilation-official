import os
import sys
import re
libs = ["/lib64", "/lib"]

for lib in libs:
  if os.path.isdir(lib):
      print os.path.basename(lib)
      sys.exit(0)
print "lib"
sys.exit(1)
