FROM ubuntu:18.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update && apt-get install -y \
  build-essential \
  cmake \
  pkg-config \
  python3-pip \
  libglib2.0-dev \
  libpcap-dev \
  libsodium-dev \
  git \
  && rm -rf /var/lib/apt/lists/*
#RUN pip3 install -e git+https://github.com/olsonse/ctypesgen@python-3#egg=ctypesgen
RUN pip3 install -e git+https://github.com/olsonse/ctypesgen#egg=ctypesgen
WORKDIR /root/assimilation/bin
