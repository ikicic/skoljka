#!/bin/bash

# Run this from the skoljka's (repository) root folder!

# subversion (svn): used to instal jquery-star-rating-plugin
sudo apt-get install python2.7 python-setuptools python-pip mysql-client-core-5.5 mysql-server-5.5 texlive-full memcached subversion
pip install -r requirements.txt

gem install sass

# Make local folders
mkdir -p local
mkdir -p local/media
mkdir -p local/media/attachment
mkdir -p local/media/export
mkdir -p local/media/m

# django-template-preprocessor cannot be installed using pip.
mkdir -p local/modules
# TODO: do not reinstall (or do reinstall if it already exists...)
cd local/modules
git clone https://github.com/citylive/django-template-preprocessor.git
cd django-template-preprocessor
python setup.py install
cd ../../..

# Make a copy of local settings
cp -n settings/local.template.py settings/local.py

echo DONE!
