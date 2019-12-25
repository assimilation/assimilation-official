FROM ubuntu:18.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get -y update && apt-get -y install --no-install-recommends ca-certificates gnupg
RUN echo deb https://dl.bintray.com/assimproj/ubuntu bionic unstable | tee -a /etc/apt/sources.list
# add bintrays public gpg key
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 379CE192D401AB61
RUN apt-get -y update
# assimilation-cma somehow is expecting /var/lib/pacemaker directory to exist so we're assuming it wants pacemaker to be installed
# https://www.travis-ci.org/assimilation/assimilation-official/builds/629489388#L1300
RUN apt-get -y install --no-install-recommends pacemaker
# assimilation-cma also expects to have assimilation-nanoprobe installed first
# https://www.travis-ci.org/assimilation/assimilation-official/builds/629489388#L1308
RUN apt-cache search assimilation-nanoprobe | awk '{print $1}' | sort | tail -1 | xargs apt-get -y install --no-install-recommends
RUN apt-cache search assimilation-cma | awk '{print $1}' | sort | tail -1 | xargs apt-get -y install --no-install-recommends
