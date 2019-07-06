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
WORKDIR /root/assimilation/bin
