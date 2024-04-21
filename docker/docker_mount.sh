#!/bin/bash
#
if [ $# -ne 2 ]; then
    echo "Usage:"
    echo "$0 IMAGE CONTAINER"
    exit 1
fi

IMAGE=$1
CONTAINER=$2

docker run \
    --detach \
    --interactive \
    --tty \
    --name $CONTAINER \
    --publish 8000:8000 \
    $IMAGE
