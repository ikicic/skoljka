#!/bin/bash

django-admin.py makemessages -l hr --ignore=settings --ignore=local
django-admin.py makemessages -l hr --ignore=settings --ignore=local --ignore=node_modules --ignore=build -d djangojs
