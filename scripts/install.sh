#!/bin/bash
function assert {
    if [[ $1 -ne 0 ]]
    then
        echo "Error!!! Aborting."
        exit 0
    fi
}

echo "Installing packages..."
sudo apt-get install python2.7 python-setuptools wget git-core xclip
assert $?

echo "Downloading django..."
wget http://www.djangoproject.com/download/1.3.1/tarball/ -O Django-1.3.1.tar.gz
assert $?

echo "Making django dir..."
sudo mkdir -p "/usr/local/src/Django-1.3.1"
assert $?

echo "Unzipping django..."
sudo tar -xf "Django-1.3.1.tar.gz" -C "/usr/local/src/"
assert $?

echo "Removing downloaded file..."
rm -rf "Django-1.3.1.tar.gz"
assert $?

echo "Installing django..."
cd "/usr/local/src/Django-1.3.1"
sudo python setup.py install
assert $?

echo "Installing django sentry..."
sudo easy_install -U django-sentry
assert $?

echo -n "Username: "
read username

echo -n "Email: "
read email

read -p "Do you need a ssh key for github [Y/n]? " sshkey
if [[ $sshkey != "n" ]]
then
    echo "Creating ssh-keys..."
    ssh-keygen -t rsa -C $email
    assert $?

    xclip ~/.ssh/id_rsa.pub
    assert $?

    echo "Open https://github.com/account/ssh, press Add another public key"
    echo "    then paste the string from ~/.ssh/id_rsa.pub in the Key field."
    echo "    That value should be in your clipboard."
    read -p "Press Enter to continue..."
else
    echo "Skipping ssh key generation..."
fi

read -p "Do want me to set up git [y/N]? " setup
if [[ $setup != "y" ]]
then
    echo "Skipping git setup!"
    echo "Done!"
    exit 0
fi

echo "Cloning the repository..."
git clone git@github.com:fpavetic/skoljka.git
assert $?

echo "Configuring git..."
git config --global user.name $username
git config --global user.email $email

echo "Done!"
