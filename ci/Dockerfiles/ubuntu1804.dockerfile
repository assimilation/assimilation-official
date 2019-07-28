FROM ubuntu:18.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update && apt-get -y install software-properties-common && \
  add-apt-repository -y ppa:deadsnakes/ppa && apt-get -y update && apt-get -y install \
  build-essential \
  cmake \
  pkg-config \
  python3.7 \
  libglib2.0-dev \
  libpcap-dev \
  libsodium-dev \
  git \
  curl \
  && rm -rf /var/lib/apt/lists/*
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
RUN python3.7 get-pip.py
RUN pip3.7 install -e git+https://github.com/Alan-R/ctypesgen#egg=ctypesgen
WORKDIR /root/assimilation/bin
