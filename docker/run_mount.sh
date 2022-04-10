#!/bin/bash

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
IMAGE=skoljka:ubuntu16.04
CONTAINER=skoljka

# Map the repo root folder as /app and forward container's port 8000 to host's
# port 8005.
docker run \
    --detach \
    --interactive \
    --tty \
    --name $CONTAINER \
    --mount type=bind,source="${SCRIPTPATH}/../",target=/app \
    --publish 8000:8000 \
    $IMAGE
