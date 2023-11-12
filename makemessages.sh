#!/bin/bash

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

cd "$SCRIPTPATH/skoljka"

# TODO: Django 2.0: consider using --add-location=file
OPTIONS="--ignore=settings --ignore=local"
django-admin.py makemessages -l hr $OPTIONS
django-admin.py makemessages -l hr $OPTIONS --ignore=node_modules --ignore=build -d djangojs
