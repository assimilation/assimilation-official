# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#   Container to be used to build static binary images using Meson+Ninja
#   As far as OS versions, the older the better (as long as security bugs are still patched)
#
from centos:6.10
# A vintage version of CentOS
ENV PYVERS 3.6.11
ENV PYCMD python3.6
# 3.6.11 is the latest version of 3.6, which is sufficient to run meson
# The reason why I stuck to 3.6 was because of a Python bug which left us dead in the water.
# However, that's fixed now.
RUN yum -y update
RUN yum -y install epel-release
RUN yum -y groupinstall "Development Tools"
RUN yum -y install clang
RUN yum -y install glibc-static zlib-devel zlib-static openssl-devel xz-devel xz wget
# It would be nice to use the latest version, but then you have SSL versions (or so it seems...)
# --with-openssl=/usr/lib64/libssl.so.10 ## Or whatever...
RUN echo Using $PYCMD
ENV PYTAR Python-${PYVERS}.tgz
WORKDIR /tmp
#
#   Compile python ${PYVERS} from source
#
RUN wget --quiet http://www.python.org/ftp/python/${PYVERS}/${PYTAR}
#   @TODO: validate our Python tar ball
RUN tar xf /tmp/${PYTAR}
RUN cd /tmp/Python-${PYVERS} && ./configure --prefix=/usr/local --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib" && make altinstall && make install
RUN echo "Getting pip" && curl --silent https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
RUN ${PYCMD} /tmp/get-pip.py # Install Pip
# Install meson and ninja
ADD toolrequirements.txt .
RUN ${PYCMD} -m pip install pip --upgrade && ${PYCMD} -m pip install -r toolrequirements.txt
