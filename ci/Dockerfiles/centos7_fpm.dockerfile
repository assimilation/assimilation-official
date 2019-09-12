FROM centos:7

ARG VERSION

RUN yum -y groupinstall "Development Tools"
RUN yum -y install ruby ruby-devel
RUN gem install --no-ri --no-rdoc fpm pleaserun

WORKDIR /workdir
COPY nanoprobe /workdir

RUN fpm -v $VERSION -s pleaserun -t dir -n nanoprobe /usr/bin/nanoprobe
RUN echo "#!/bin/sh\nsh /usr/share/pleaserun/nanoprobe/cleanup.sh\nrm /usr/share/pleaserun/nanoprobe/cleanup.sh\n" > ./nanoprobe.dir/usr/share/pleaserun/nanoprobe/delete.sh
RUN fpm -v $VERSION -s dir -t rpm -n nanoprobe --after-install ./nanoprobe.dir/usr/share/pleaserun/nanoprobe/install.sh --before-remove ./nanoprobe.dir/usr/share/pleaserun/nanoprobe/delete.sh nanoprobe=/usr/bin/ ./nanoprobe.dir/usr/share/pleaserun/=/usr/share/pleaserun

CMD ["/bin/bash"]
