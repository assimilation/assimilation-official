# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#   Container to be used to build static binary images using Meson+Ninja
#   As far as OS versions, the older the better (as long as security bugs are still patched)
#
from centos:6.10
# A vintage version of CentOS
ENV PYVERS 3.6.10
ENV PYCMD python3.6
# Ned Deily's OpenPGP public key id from https://www.python.org/downloads/
ENV PGPKEYID 2D347EA6AA65421D
# 3.6.10 is the latest version of 3.6, which is sufficient to run meson
RUN yum -y update
RUN yum -y install epel-release
RUN yum -y groupinstall "Development Tools"
RUN yum -y install clang
RUN yum -y install glibc-static zlib-devel zlib-static openssl-devel xz-devel xz wget
# It would be nice to use the latest version, but then you have SSL versions (or so it seems...)
# --with-openssl=/usr/lib64/libssl.so.10 ## Or whatever...
RUN echo Using $PYCMD
ENV PYTAR Python-${PYVERS}.tgz
ENV PYASC Python-${PYVERS}.tgz.asc
WORKDIR /tmp
#
#   Compile python ${PYVERS} from source
#
RUN wget --quiet http://www.python.org/ftp/python/${PYVERS}/${PYTAR} http://www.python.org/ftp/python/${PYVERS}/${PYASC}
#   start validate Python tarball
#   https://serverfault.com/questions/896228/how-to-verify-a-file-using-an-asc-signature-file
#   1. download maintainer's OpenPGP public key
RUN curl -s https://keybase.io/nad/pgp_keys.asc?fingerprint=0d96df4d4110e5c43fbfb17f2d347ea6aa65421d -o pgp_keys.asc
#   2. verify the keyid matches and import if correct
RUN [[ ${PGPKEYID} == $(gpg --keyid-format long --list-options show-keyring pgp_keys.asc | awk '/pub/ {print $2}' | awk -F/ '{print $2}') ]] && gpg --import pgp_keys.asc
#   3. verify Python tarball
RUN gpg --verify ${PYASC}
#   end validate Python tarball
RUN tar xf /tmp/${PYTAR}
RUN cd /tmp/Python-${PYVERS} && ./configure --prefix=/usr/local --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib" && make altinstall && make install
RUN echo "Getting pip" && curl --silent https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
RUN ${PYCMD} /tmp/get-pip.py # Install Pip
# Install meson and ninja
RUN ${PYCMD} -m pip install pip meson ninja --upgrade
