#!/bin/bash

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

set -ex

cd "$SCRIPTPATH/.."

mkdir -p local
mkdir -p local/media
mkdir -p local/media/attachment
mkdir -p local/media/export
mkdir -p local/media/m

# django-template-preprocessor cannot be installed using pip.
mkdir -p local/modules
if [ ! -d local/modules/django-template-preprocessor ]; then
    cd local/modules
    git clone https://github.com/ikicic/django-template-preprocessor.git
    cd django-template-preprocessor
    python setup.py install
    cd ../../..
else
    echo "local/modules/django-template-preprocessor already found, skipping"
fi

# Make a copy of local settings
cp -n skoljka/settings/local.template.py skoljka/settings/local.py
