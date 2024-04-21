#!/bin/bash

SCRIPTDIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
APPDIR="$SCRIPTDIR/.."

set -ex

cd "$APPDIR"

mkdir -p "local"
mkdir -p "local/media"
mkdir -p "local/media/attachment"
mkdir -p "local/media/export"
mkdir -p "local/media/m"

service mysql start
mysql -e "CREATE DATABASE IF NOT EXISTS skoljka CHARACTER SET utf8 COLLATE utf8_general_ci;" -u root --password=""

npm install
./node_modules/bower/bin/bower install

python2 manage.py syncdb --noinput
python2 manage.py loaddata folders userprofiles
python2 build.py
