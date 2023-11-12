#!/bin/bash

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
IMAGE=skoljka:ubuntu16.04
CONTAINER=skoljka

docker run \
    --detach \
    --interactive \
    --tty \
    --name $CONTAINER \
    --publish 8000:8000 \
    $IMAGE
