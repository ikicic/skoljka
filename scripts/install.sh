#!/bin/bash

set -ex

# Run this from the skoljka's (repository) root folder!

# subversion (svn): used to install jquery-star-rating-plugin
sudo apt-get install python-setuptools python-pip mysql-client-core-5.5 mysql-server-5.5 texlive-full memcached subversion libmysqlclient-dev npm nodejs-legacy
pip install -r requirements.txt

# TODO: How to properly add this to requirements.txt?
pip install git+https://github.com/ikicic/django-bootstrap-toolkit

gem install sass
npm install
sudo npm install -g grunt-cli
./node_modules/bower/bin/bower install
grunt

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
git clone https://github.com/petry/django-template-preprocessor.git
cd django-template-preprocessor
python setup.py install
cd ../../..

# Make a copy of local settings
cp -n settings/local.template.py settings/local.py

echo DONE!
