FROM centos:7
RUN yum -y install epel-release
RUN yum -y groupinstall "Development Tools" "Development Libraries"
RUN yum -y install \
  cmake \
  pkgconfig \
  python-pip
WORKDIR /root/assimilation/bin



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
