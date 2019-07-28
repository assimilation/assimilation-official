FROM ubuntu:18.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update && apt-get -y install software-properties-common && \
  add-apt-repository -y ppa:deadsnakes/ppa && apt-get -y update && apt-get -y install \
  build-essential \
  cmake \
  pkg-config \
  python \
  python3.7 \
  python3-pip \
  libglib2.0-dev \
  libpcap-dev \
  libsodium-dev \
  git \
  && rm -rf /var/lib/apt/lists/*
RUN pip3 install -e git+https://github.com/Alan-R/ctypesgen#egg=ctypesgen
WORKDIR /root/assimilation/bin
