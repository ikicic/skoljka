#!/bin/bash

SCRIPTDIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
LOCAL="$SCRIPTDIR/../local"

set -ex

cd /app

mkdir -p "$LOCAL"
mkdir -p "$LOCAL/media"
mkdir -p "$LOCAL/media/attachment"
mkdir -p "$LOCAL/media/export"
mkdir -p "$LOCAL/media/m"

# django-template-preprocessor cannot be installed using pip.
mkdir -p "$LOCAL/modules"
if [ ! -d "$LOCAL/modules/django-template-preprocessor" ]; then
    (cd "$LOCAL/modules" && git clone https://github.com/ikicic/django-template-preprocessor.git)
fi
(cd "$LOCAL/modules/django-template-preprocessor" && git pull && python setup.py install)

# Make a copy of local settings
cp -n skoljka/settings/local.template.py skoljka/settings/local.py

set +x

RANDOM_SECRET_KEY=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 64)
sed -i "s/KEY_SHOULD_BE_SOMETHING_COMPLICATED/$RANDOM_SECRET_KEY/" skoljka/settings/local.py

echo "DONE!"
echo "Now run ./docker/setup_internal.sh"
