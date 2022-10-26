#!/bin/bash

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

cd "$SCRIPTPATH/skoljka"

django-admin.py makemessages -l hr --ignore=settings --ignore=local
django-admin.py makemessages -l hr --ignore=settings --ignore=local --ignore=node_modules --ignore=build -d djangojs
