#!/bin/bash

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

set -ex

if [ -x "$(command -v sudo)" ]; then
    SUDO=sudo
else
    SUDO=
fi

# subversion (svn): used to install jquery-star-rating-plugin
if [ -x "$(command -v apt-get)" ]; then
    $SUDO apt-get install -y \
        libmysqlclient-dev \
        memcached \
        mysql-client-core-5.7 \
        mysql-server-5.7 \
        nodejs-legacy \
        npm \
        ruby-dev \
        python-pip \
        python-setuptools \
        subversion
    $SUDO apt-get install -y --no-install-recommends texlive-latex-extra
fi
pip install -r requirements.txt

# TODO: How to properly add this to requirements.txt?
pip install git+https://github.com/ikicic/django-bootstrap-toolkit

gem install sass --user-install
