#!/bin/bash

# Run this from the skoljka's root folder!

sudo apt-get install python2.7 python-setuptools python-pip mysql-client-core-5.5 mysql-server-5.5 texlive-full memcached
sudo pip install -r requirements.txt

# Configure local folders
mkdir -p local
mkdir -p local/media
mkdir -p local/media/attachment
mkdir -p local/media/export
mkdir -p local/media/m

# django-template-preprocessor cannot be installed using pip.
mkdir -p local/modules
# TODO: do not reinstall (or reinstall...)
cd local/modules
git clone https://github.com/citylive/django-template-preprocessor.git
cd django-template-preprocessor
sudo python setup.py install
cd ../../..

# Make a copy of local settings
cp -n settings/local.template.py settings/local.py

echo
echo ==============================================================
echo Now create an empty database and fill out the settings/local.py
echo After that, run following commands:
echo python manage.py syncdb --noinput
echo python b.py
