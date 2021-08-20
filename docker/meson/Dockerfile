# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#   Container to be used to build static binary images using Meson+Ninja
#   As far as OS versions, the older the better (as long as security bugs are still patched)
#
from centos:7
SHELL ["/bin/bash",  "-c"]
# A vintage version of CentOS
ENV PYVERS 3.9.6
ENV PYCMD python3
RUN yum -y update
RUN yum -y install epel-release
RUN yum -y groupinstall "Development Tools"
RUN yum -y install clang
RUN yum -y install glibc-static zlib-devel zlib-static openssl-devel xz-devel xz wget bzip2-devel readline-devel sqlite-devel libffi-devel
# It would be nice to use the latest version, but then you have SSL versions (or so it seems...)
# --with-openssl=/usr/lib64/libssl.so.10 ## Or whatever...
RUN echo Using $PYCMD
ENV PYTAR Python-${PYVERS}.tgz
WORKDIR /tmp
#
#   Compile python ${PYVERS} from source
#
RUN wget --quiet https://www.python.org/ftp/python/${PYVERS}/${PYTAR}
#   @TODO: validate our Python tar ball
#   @TODO: switch to using pyenv??
RUN tar xf /tmp/${PYTAR}
RUN cd /tmp/Python-${PYVERS} && ./configure --prefix=/usr/local --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib" && make altinstall && make install
## COPY pyenv.bash /tmp/pyenv.bash
## RUN bash -x /tmp/pyenv.bash
env HOME=/root
## env PYENV_ROOT="$HOME/.pyenv"
## env PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"
## RUN echo $PATH && ls -l $HOME/.pyenv/bin $HOME/.pyenv/libexec
## RUN eval "$(pyenv init -)" && pyenv install ${PYVERS}
# Install meson and ninja
ADD toolrequirements.txt .

# RUN eval "$(pyenv init -)" && pyenv global ${PYVERS} && eval "$(pyenv virtualenv-init -)" && echo $PATH && type python && python -V && python -m pip install pip --upgrade && python -m pip install -r toolrequirements.txt
RUN $PYCMD -V && $PYCMD -m pip install pip --upgrade && $PYCMD -m pip install -r toolrequirements.txt
