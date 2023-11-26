#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: ./run_rsync.sh CONTAINER"
    exit 1
fi

set -e

CONTAINER=$1

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
REPOSITORY_ROOT="$SCRIPTPATH/.."
cd $REPOSITORY_ROOT

# We copy the node_modules from the host because `npm install` does not seem to
# work in the container.
while true; do
    rsync -arvm \
        --exclude=*.pyc \
        --exclude=*.swp \
        --exclude=*~ \
        --exclude=.DS_Store \
        --exclude=.git \
        --exclude=bower_components  \
        --exclude=build \
        --exclude=cypress \
        --exclude=local/ \
        -e 'docker exec -i' \
        . \
        $CONTAINER:/app/
    sleep 5
done
