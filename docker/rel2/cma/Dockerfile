# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#   Container to be used to build static binary images using Meson+Ninja
#   As far as OS versions, the older the better (as long as security bugs are still patched)
#
from python:3.6.10-buster
ENV PYVERS 3.6.10
ENV PYCMD python3.6
ENV LIBSODIUM_VERSION=1.0.18
# 3.6.10 is the latest version of 3.6. Later releases broke ctypes :-(
#
# Compile libsodium - because we want a recent version - ideally same as nanoprobe
# @TODO: Validate the source tar ball signature
#
ENV SRCDIR /tmp/src
ADD src/getsigningkey.py src/hashes.csv ${SRCDIR}/
WORKDIR ${SRCDIR}
# Compile and install libsodium - trusting as little as possible ;-)
ENV LIBSODIUM_BASEURL=https://download.libsodium.org/libsodium/releases/libsodium-
ENV LIBSODIUM_URL=${LIBSODIUM_BASEURL}${LIBSODIUM_VERSION}.tar.gz
ENV LIBSODIUM_SIG=${LIBSODIUM_URL}.sig
ENV LIBSODIUM_SIGNING_KEY https://download.libsodium.org/jedi.gpg.asc
RUN pip3 install requests                               # Needed for getsigningkey.py
RUN ${PYCMD} getsigningkey.py ${LIBSODIUM_SIGNING_KEY}  # Fetch and validate signing key...
RUN gpg --import $(basename $LIBSODIUM_SIGNING_KEY)     # Import validated signing key
RUN wget --quiet ${LIBSODIUM_URL} ${LIBSODIUM_SIG}      # Get libsodium and its signature
RUN gpg $(basename ${LIBSODIUM_SIG})                    # Validate libsodium tar ballDD
# NOTE: This will give a warning about not knowing if this is a trusted signature. That's OK...
RUN tar xzf $(basename ${LIBSODIUM_URL})                # untar and install...
WORKDIR libsodium-${LIBSODIUM_VERSION}
RUN ./configure prefix=/usr && bash -c "time make && time make check && make install"
# Install other packages that
RUN apt-get update >/dev/null 2>&1
RUN apt-get install -y libglib2.0-dev libpcap-dev dbus
#
# Now get ready to build our libraries, etc...
#
ADD src/meson.build ${SRCDIR}/
ADD src/genpybindings.py ${SRCDIR}/
ADD src/cma/ ${SRCDIR}/cma/
ADD src/include/ ${SRCDIR}/include/
ADD src/clientlib/ ${SRCDIR}/clientlib/
ADD src/serverlib/ ${SRCDIR}/serverlib/
ADD src/nanoprobe/  ${SRCDIR}/nanoprobe/
ENV BINDIR /tmp/bin
WORKDIR ${SRCDIR}
RUN $PYCMD -m pip install meson ninja -r cma/requirements.txt
RUN bash -c "time meson ${BINDIR}"
WORKDIR ${BINDIR}
RUN bash -c "time ninja install"
ENV LIBDIR /usr/lib/
RUN cp -a libassimilationclient.so ${LIBDIR}/
ENV ASSIMLIB ${LIBDIR}/libassimilationclient.so
RUN ls -l ${LIBDIR}/libassimilationclient.so && sha256sum ${LIBDIR}libassimilationclient.so
RUN apt-get install -y docker.io
# genpybindings.py outfile sourceroot buildroot libdir libfile ...
#   outfile     name of file to put output into
#   sourceroot  root of source directory tree
#   buildroot   root of build (binary) directory tree
#   libdir      where the runtime libraries are located
#   libfiles    list of library files that we might want to bind to (just one today)
ENV ASSIMCTYPES ${SRCDIR}/cma/AssimCtypes.py
ENV GENBIND ${PYCMD} ${SRCDIR}/genpybindings.py ${ASSIMCTYPES}
ENV GENCMD $GENBIND $SRCDIR $SRCDIR $BINDIR $LIBDIR ${LIBDIR}/libassimilationclient.so
RUN echo ${GENCMD}
RUN ${GENCMD}
