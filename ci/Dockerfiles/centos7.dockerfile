FROM centos:7
RUN yum -y install epel-release
RUN yum -y groupinstall "Development Tools" "Development Libraries"
RUN yum -y install \
  cmake \
  pkgconfig \
  python36-pip \
  glib2-devel \
  libpcap-devel \
  libsodium-devel \
  git
RUN pip36 install -e git+https://github.com/Alan-R/ctypesgen#egg=ctypesgen
WORKDIR /root/assimilation/bin
