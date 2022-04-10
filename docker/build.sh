#!/bin/bash

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
IMAGE=skoljka:ubuntu16.04

cd "$SCRIPTPATH/.."

docker build -t $IMAGE -f docker/Dockerfile-16.04 .
