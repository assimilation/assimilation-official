FROM ubuntu:18.04
ARG DEBIAN_FRONTEND=noninteractive

RUN echo "deb https://dl.bintray.com/assimproj/deb bionic main" | tee -a /etc/apt/sources.list
RUN apt-get -y update && apt-get -y install --no-install-recommends ca-certificates
