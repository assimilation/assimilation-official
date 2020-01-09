FROM ubuntu:wily
ENV WORK /tmp/workdir
RUN mkdir /tmp/workdir
WORKDIR /tmp/workdir
RUN : "Version Sun Jun 12 08:20:16 MDT 2016"
ADD installme /tmp/workdir/
RUN chmod 755 installme
RUN ls -l $WORK
RUN /bin/sh -ex installme --nolog  --prerel=1.1.7 nanoprobe
    RUN sed 's%^%LOG: %' < /tmp/assimilation-install.txt
