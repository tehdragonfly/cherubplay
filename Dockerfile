FROM ubuntu:14.04
MAINTAINER Olly Parton <mysticdragonfly@hotmail.co.uk>

RUN apt-get update && apt-get install -y python python2.7-dev python-pip libpq-dev libffi-dev uwsgi uwsgi-plugin-python

COPY . /src

WORKDIR src

RUN pip install -r requirements.txt
RUN python setup.py develop

EXPOSE 8000

ENTRYPOINT ["uwsgi", "--plugins", "python", "--ini-paste", "/etc/cherubplay/production.ini"]
