#!/usr/bin/env bash
set -eu

# this script attaches a file to a particular release as an asset
# usage: ./attach_asset.sh <path> <file> <tag>

# prereqs
# run this script in $TRAVIS_BUILD_DIR (hub needs to run at the root of repo)

PATH_TO_FILE=$1
FILE=$2
TAG=$3


# check if the release exists, if not, create it
set +e
RELEASE_EXISTS=$(hub release | grep v${DOCKER_TAG})
set -e
if [ "$RELEASE_EXISTS" == "" ]; then
  hub release create -d -m test "v${DOCKER_TAG}"
fi

# check if the release at <tag> already has this asset. if so we have to delete it first, then we can upload.

ASSETS=$(hub api repos/assimilation/assimilation-official/releases | jq -r --arg TAG "$TAG" --arg FILE "$FILE" '.[]|select(.tag_name==$TAG)|.assets[]|select(.name==$FILE)|[.name,.url]|@tsv')

if [ "$ASSETS" == "" ]; then
  hub release edit -a "$PATH_TO_FILE/$FILE" -m "fake release to test attaching binary" -m "test" $TAG
else
  hub api -X DELETE $(echo $ASSETS | awk '{print $2}')
  hub release edit -a "$PATH_TO_FILE/$FILE" -m "fake release to test attaching binary" -m "test" $TAG
fi
