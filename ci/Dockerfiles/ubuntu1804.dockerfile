FROM ubuntu:18.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update && apt-get install -y \
  build-essential \
  cmake \
  pkg-config \
  python-pip \
  libglib2.0-dev \
  libpcap-dev \
  libsodium-dev \
  git \
  && rm -rf /var/lib/apt/lists/*
RUN pip install -e git+https://github.com/Alan-R/ctypesgen#egg=ctypesgen
WORKDIR /root/assimilation/bin
