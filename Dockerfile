FROM centos:7
MAINTAINER JJromi <jromi158@gmail.com>

# Install basic packages
RUN yum install wget -y
RUN yum install make -y

# Install python3.6 / slick client
RUN yum install https://centos7.iuscommunity.org/ius-release.rpm -y
RUN yum install python36u -y
RUN yum install python36u-pip -y
RUN yum install python36u-devel -y

# Install jdk
RUN yum install java-1.8.0-openjdk-devel.x86_64 -y

# Install KoNLPy
RUN yum install gcc-c++ -y

RUN pip3.6 install konlpy
RUN yum install curl -y
RUN yum install bash -y
RUN curl -s https://raw.githubusercontent.com/konlpy/konlpy/master/scripts/mecab.sh

# Install git
RUN yum install git -y


EXPOSE 80

CMD ["python3.6"]