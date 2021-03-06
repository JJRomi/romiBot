FROM ubuntu:16.04
MAINTAINER JJromi <jromi158@gmail.com>

RUN apt-get update
RUN apt-get install -y software-properties-common vim
RUN add-apt-repository ppa:jonathonf/python-3.6
RUN apt-get update && \
    apt-get install -y build-essential python3.6 python3.6-dev python3-pip python3.6-venv python3-setuptools && \
    apt-get install -y libxml2-dev libffi-dev libxslt-dev zlib1g-dev && \
    apt-get install -y git && \
    apt-get install -y libmecab-dev && \
    apt-get install -y openjdk-8-jdk && \
	apt-get install -y ant && \
    apt-get install -y automake1.11 &&\
    apt-get install -y curl &&\
    apt-get install -y g++ &&\
    apt-get install -y wget &&\
    apt-get install -y autoconf autogen &&\
    apt-get clean && \
	rm -rf /var/lib/apt/lists/* && \
	rm -rf /var/cache/oracle-jdk8-installer


# update pip
RUN python3.6 -m pip install pip --upgrade
RUN python3.6 -m pip install wheel
RUN python3.6 -m pip install pynacl

# This is in accordance to : https://www.digitalocean.com/community/tutorials/how-to-install-java-with-apt-get-on-ubuntu-16-04
ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64/
RUN export JAVA_HOME

RUN git clone https://github.com/JJRomi/romiBot.git

WORKDIR /romiBot

RUN wget https://bitbucket.org/eunjeon/mecab-ko/downloads/mecab-0.996-ko-0.9.2.tar.gz
RUN tar zxfv mecab-0.996-ko-0.9.2.tar.gz
WORKDIR "/romiBot/mecab-0.996-ko-0.9.2"
RUN ./configure
RUN make
RUN make install

WORKDIR "/romiBot"
RUN wget https://bitbucket.org/eunjeon/mecab-ko-dic/downloads/mecab-ko-dic-2.0.2-20170922.tar.gz
RUN tar zxfv mecab-ko-dic-2.0.2-20170922.tar.gz
WORKDIR "/romiBot/mecab-ko-dic-2.0.2-20170922"
RUN ./configure
RUN make
RUN make install

WORKDIR /romiBot

RUN git clone https://bitbucket.org/eunjeon/mecab-python-0.996.git
WORKDIR "/romiBot/mecab-python-0.996"
RUN python3.6 setup.py install

WORKDIR /romiBot

RUN curl -s https://raw.githubusercontent.com/konlpy/konlpy/master/scripts/mecab.sh | bash
RUN pip3 install -r requirements.txt

EXPOSE 80

CMD ["/usr/local/bin/gunicorn",  "chatbot:app"]