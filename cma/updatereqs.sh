#/bin/sh
set -u
set -e
PYTHON=python3
PIP=pip3
MIN=min-requirements.txt
FULL=requirements.txt
DIR=$(mktemp -d)
trap "rm -fr ${DIR}" 0
test -r $MIN

$PYTHON -m venv $DIR/venv
. $DIR/venv/bin/activate
if
  $PIP install -r $MIN > $DIR/pip.out 2>&1
then
  $PIP freeze > $FULL
  echo "updated $FULL with $(echo $(wc -l <$FULL)) dependencies"
else
  cat $DIR/pip.out
  exit 1
fi
  


