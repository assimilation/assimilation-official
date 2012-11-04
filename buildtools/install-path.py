from os.path import join, isfile, isdir
import sys
if (join(sys.path[1], 'dist-packages')) in sys.path:
  print join(sys.path[1], 'dist-packages')
  sys.exit(0)
for p in sys.path[1:]:
  if p != '' and isfile(join(p,'README')):
    print p
    sys.exit(0)
sys.exit(1)
