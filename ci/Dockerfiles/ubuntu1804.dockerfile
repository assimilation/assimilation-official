FROM ubuntu:18.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get -y update && apt-get -y install --no-install-recommends ca-certificates
RUN echo deb https://dl.bintray.com/assimproj/ubuntu bionic unstable | sudo tee -a /etc/apt/sources.list
# add bintrays public gpg key
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 379CE192D401AB61
RUN apt-get -y update
