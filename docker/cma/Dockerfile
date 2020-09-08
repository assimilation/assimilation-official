# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#   Container to be used to build static binary images using Meson+Ninja
#   As far as OS versions, the older the better (as long as security bugs are still patched)
#
# 3.6.10 is the latest version of 3.6. Later releases broke ctypes :-( -- then fixed it :-D
from python:3.8.5-buster
ENV PYVERS 3.8.5
ENV PYCMD python3.8
ENV LIBSODIUM_VERSION=1.0.18
#
# Compile libsodium - because we want a recent version - ideally same as nanoprobe
# @TODO: Validate the source tar ball signature
#
ENV SRCDIR /usr/src/assimilation
ADD src/getsigningkey.py src/hashes.csv lib*.so* frame*types.h ${SRCDIR}/
WORKDIR ${SRCDIR}
# Compile and install libsodium - trusting as little as possible ;-)
ENV LIBSODIUM_BASEURL=https://download.libsodium.org/libsodium/releases/libsodium-
ENV LIBSODIUM_URL=${LIBSODIUM_BASEURL}${LIBSODIUM_VERSION}.tar.gz
ENV TARFILE libsodium-${LIBSODIUM_VERSION}.tar.gz
ENV LIBSODIUM_SIG=${LIBSODIUM_URL}.sig
ENV SIGFILE ${TARFILE}.sig
ENV LIBSODIUM_SIGNING_KEY https://download.libsodium.org/jedi.gpg.asc
RUN pip3 install requests                               # Needed for getsigningkey.py
RUN ${PYCMD} getsigningkey.py ${LIBSODIUM_SIGNING_KEY}  # Fetch and validate signing key...
RUN gpg --import $(basename $LIBSODIUM_SIGNING_KEY)     # Import validated signing key
# RUN wget --quiet ${LIBSODIUM_URL} ${LIBSODIUM_SIG}      # Get libsodium and its signature
RUN curl -s ${LIBSODIUM_URL} -o ${TARFILE} # Get libsodium tar file
RUN curl -s ${LIBSODIUM_SIG} -o ${SIGFILE} # Get libsodium signature
RUN gpg $(basename ${LIBSODIUM_SIG})                    # Validate libsodium tar ballDD
# NOTE: This will give a warning about not knowing if this is a trusted signature. That's OK...
RUN tar xzf $(basename ${LIBSODIUM_URL})                # untar and install...
WORKDIR libsodium-${LIBSODIUM_VERSION}
RUN ./configure prefix=/usr && bash -c "time make && time make check && make install"
# Install other packages that
RUN apt-get update && apt-get install -y libglib2.0-dev libpcap-dev dbus docker.io vim # vim is only for testing and development
#
# Now get ready to build our libraries, etc...
#
ADD src/meson.build src/genpybindings.py src/toolrequirements.txt ${SRCDIR}/
ADD src/include/ ${SRCDIR}/include/
RUN rm -f ${SRCDIR}/include/projectcommon.h
ADD src/clientlib/ ${SRCDIR}/clientlib/
ADD src/serverlib/ ${SRCDIR}/serverlib/
ADD src/nanoprobe/  ${SRCDIR}/nanoprobe/
ENV LIBDIR /usr/lib/
ADD libpcap.* libsodium.* libassimilationclient.* ${LIBDIR}
ENV BINDIR /root/bin
WORKDIR ${SRCDIR}
ADD src/cma/requirements.txt ${SRCDIR}/cma/
RUN $PYCMD -m pip install -r toolrequirements.txt -r cma/requirements.txt
RUN $PYCMD -m pip freeze --all | tee cma/frozen.txt
ADD src/cma/frameinfo.py ${SRCDIR}/cma/
RUN bash -c "time meson ${BINDIR}"
WORKDIR ${BINDIR}
# RUN bash -c "time ninja install"
# RUN cp -a libassimilationclient.so ${LIBDIR}/
ENV ASSIMLIB ${LIBDIR}/libassimilationclient.so
RUN cp ${BINDIR}/*.h ${SRCDIR}/include/
RUN mv ${SRCDIR}/frame*types.h ${SRCDIR}/include/
# genpybindings.py outfile sourceroot buildroot libdir libfile ...
#   outfile     name of file to put output into
#   sourceroot  root of source directory tree
#   buildroot   root of build (binary) directory tree
#   libdir      where the runtime libraries are located
#   libfiles    list of library files that we might want to bind to (just one today)
ENV ASSIMCTYPES ${SRCDIR}/cma/AssimCtypes.py
ENV GENBIND ${PYCMD} ${SRCDIR}/genpybindings.py ${ASSIMCTYPES}
ENV GENCMD $GENBIND $SRCDIR $SRCDIR $BINDIR libassimilationclient libsodium libpcap libglib-2.0
RUN echo ${GENCMD}
RUN ${GENCMD} 2>&1 | egrep -v '/usr/include/|Undef "NULL"'
WORKDIR ${SRCDIR}/cma
RUN mkdir -p /var/run /usr/share/assimilation/notification.d
RUN echo '/root/startup.sh "$@"' > /usr/local/bin/s; chmod 755 /usr/local/bin/s
CMD ["/root/startup.sh"]
ADD startup.sh /root/startup.sh
ADD src/cma/ ${SRCDIR}/cma/
