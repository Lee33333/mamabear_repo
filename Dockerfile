FROM ubuntu:14.04
MAINTAINER Jacob Perkins <jacob@click2care.org>

RUN apt-get update
RUN apt-get install -y python-pip --fix-missing
RUN apt-get install -y libpython2.7-dev
RUN apt-get install -y libmysqlclient-dev

RUN mkdir /etc/mamabear/
COPY mamabear.cfg /etc/mamabear/mamabear.cfg
RUN rm mamabear.cfg

RUN mkdir /var/mamabear/
ADD . /var/mamabear
RUN chmod ugo+x /var/mamabear/mamabear/server.py
EXPOSE 9055

RUN pip install /var/mamabear
CMD ["/var/mamabear/mamabear/server.py", "-c", "/etc/mamabear/mamabear.cfg"]
