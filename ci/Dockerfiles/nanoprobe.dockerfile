FROM ubuntu:18.04
ARG DEBIAN_FRONTEND=noninteractive

COPY assimilation-nanoprobe*.deb /tmp
RUN apt-get -y update && apt-get -y install --no-install-recommends libsodium-dev /tmp/assimilation-nanoprobe*.deb && rm -rf /var/lib/apt/lists/*
#RUN dpkg -i /tmp/assimilation-nanoprobe*.deb

CMD ["/usr/sbin/nanoprobe","-f"]
