FROM ubuntu:18.04

ARG DEBIAN_FRONTEND=noninteractive
ARG VERSION

RUN apt-get -y update && apt-get -y install ruby ruby-dev build-essential
RUN gem install --no-ri --no-rdoc fpm pleaserun

WORKDIR /workdir
COPY nanoprobe /workdir
RUN fpm -v $VERSION -s pleaserun -t dir -n nanoprobe /usr/bin/nanoprobe
COPY usr/ /workdir/nanoprobe.dir/usr/
RUN echo "#!/bin/sh\nsh /usr/share/pleaserun/nanoprobe/cleanup.sh\nrm /usr/share/pleaserun/nanoprobe/cleanup.sh\n" > ./nanoprobe.dir/usr/share/pleaserun/nanoprobe/delete.sh
COPY fix.sh /workdir/nanoprobe.dir/usr/share/pleaserun/nanoprobe/
RUN fpm -v $VERSION -s dir -t deb -n nanoprobe --after-install ./nanoprobe.dir/usr/share/pleaserun/nanoprobe/install.sh --after-install ./nanoprobe.dir/usr/share/pleaserun/nanoprobe/fix.sh --before-remove ./nanoprobe.dir/usr/share/pleaserun/nanoprobe/delete.sh nanoprobe=/usr/bin/ ./nanoprobe.dir/usr/share/pleaserun/=/usr/share/pleaserun ./nanoprobe.dir/usr/share/crypto.d=/usr/share/ ./nanoprobe.dir/usr/share/assimilation=/usr/share/ ./nanoprobe.dir/usr/lib/ocf=/usr/lib/

CMD ["/bin/bash"]
