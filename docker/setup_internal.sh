#!/bin/bash

SCRIPTDIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

set -ex

service mysql start
mysql -e "CREATE DATABASE IF NOT EXISTS skoljka CHARACTER SET utf8 COLLATE utf8_general_ci;" -u root -p

./node_modules/bower/bin/bower install

# Make the repo root available through `import skoljka`.
# TODO: restructure the repo, create a `skoljka/` folder for the package.
ln -sf /app $(python -c 'import site; print(site.getsitepackages())[0]')/skoljka

python2 manage.py syncdb --noinput
python2 manage.py loaddata folders userprofiles
(cd "$SCRIPTDIR/.." && python2 build.py)
