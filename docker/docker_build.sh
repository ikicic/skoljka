#!/bin/bash

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

if [ $# -ne 1 ]; then
    echo "Usage: $0 IMAGE"
    exit 1
fi
IMAGE=$1

cd "$SCRIPTPATH/.."

docker build -t $IMAGE -f docker/Dockerfile-16.04 .
