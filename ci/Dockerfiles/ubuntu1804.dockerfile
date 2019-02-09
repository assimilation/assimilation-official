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
  && rm -rf /var/lib/apt/lists/*
RUN pip install ctypesgen
WORKDIR /root/assimilation/bin
