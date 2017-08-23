FROM centos:7
MAINTAINER JJromi <jromi158@gmail.com>

# Install basic packages
RUN yum install wget
RUN yum install make

# Install python3.6 / slick client
RUN yum install https://centos7.iuscommunity.org/ius-release.rpm
RUN yum install python36u
RUN yum install python36u-pip
RUN yum install python36u-devel

# Install jdk
RUN yum install java-1.8.0-openjdk-devel.x86_64


EXPOSE 80

CMD ["python3.6"]