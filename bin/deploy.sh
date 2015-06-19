#!/usr/bin/env bash

docker pull click2care/mamabear:$1
docker stop mamabear
docker rm mamabear
docker run -d --name=mamabear -p 9055:9055 -v /etc/docker/certs:/etc/docker/certs click2care/mamabear:$1

