#!/usr/bin/env bash
set -euo pipefail

if [[ "$BUILD_ENV" == "ubuntu:18.04" ]]; then
  apt-get -y update && apt-get -y install python3 python3-pip && pip3 install testify && find /packages -type f -name *.deb -exec apt-get -y install {} \; && cd /root/assimilation/src/cma && testify tests
elif [[ "$BUILD_ENV" == "centos:7" ]]; then
  # this is not finished yet
  rpm install -y python36 python36-pip && pip36 install testify
fi

