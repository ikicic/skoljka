#!/bin/bash

SCRIPTDIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
SETTINGSDIR="$SCRIPTDIR/../skoljka/settings/"

set -ex

# Make a copy of local settings
if [ ! -f "$SETTINGSDIR/local.py" ]; then
    cp "$SETTINGSDIR/local.template.py" "$SETTINGSDIR/local.py"
fi

set +x

RANDOM_SECRET_KEY=$(LC_CTYPE=C tr -dc A-Za-z0-9 </dev/urandom | head -c 64)
if [ "${#RANDOM_SECRET_KEY}" -ne 64 ]; then
    echo Generating secret key failed.
    exit 1
fi

# https://stackoverflow.com/questions/5694228/sed-in-place-flag-that-works-both-on-mac-bsd-and-linux
sed -i.tmp-bak "s/KEY_SHOULD_BE_SOMETHING_COMPLICATED/$RANDOM_SECRET_KEY/g" "$SETTINGSDIR/local.py"
rm -f "$SETTINGSDIR/local.py.tmp-bak"

echo "Done! $SETTINGSDIR/local.py and the secret key are set."
