FROM ubuntu:18.04
ARG DEBIAN_FRONTEND=noninteractive

COPY assimilation-cma*.deb /tmp
RUN apt-get -y update && apt-get -y install --no-install-recommends python python-pip /tmp/assimilation-cma*.deb && rm -rf /var/lib/apt/lists/*
RUN pip install py2neo

CMD ["/usr/sbin/cma"]
