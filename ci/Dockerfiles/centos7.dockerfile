FROM centos:7
RUN yum -y groupinstall "Development Tools"
RUN yum -y install \
  cmake \
  pkgconfig \
  glib2-devel \
  libpcap-devel
RUN yum -y install epel-release
RUN yum -y install \
  libsodium-devel \
  python2-pip
RUN pip install ctypesgen
WORKDIR /root/assimilation/bin
