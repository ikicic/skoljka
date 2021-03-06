# Installation

This procedure is based on the following tutorial:
http://michal.karzynski.pl/blog/2013/06/09/django-nginx-gunicorn-virtualenv-supervisor/

1. Go to your projects folder (e.g. `~/projects`). Create and go to a virtual environment:
  ```sh
  sudo apt-get install gettext git python2.7-dev python-virtualenv
  virtualenv -p `which python2` skoljka
  cd skoljka
  echo -e "export PYTHONPATH=\$PWD:\$PWD/skoljka:\$PYTHONPATH\nexport PROD=true\n\nsource bin/activate" > profile
  source profile
  ```

2. Clone skoljka and run the installation script:
  ```sh
  git clone https://github.com/ikicic/skoljka.git
  cd skoljka
  scripts/install.sh
  ```

3. Create an empty `UTF8` database (use your **username**):
  ```sh
  mysql -e "CREATE DATABASE skoljka CHARACTER SET utf8 COLLATE utf8_general_ci;" -u username -p
  ```

4. Fill out `settings/local.py`, at least the fields marked as `REQUIRED`.

5. Initialize database and build:
  ```sh
  python2 manage.py syncdb --noinput
  python2 manage.py loaddata folders userprofiles
  python2 b.py
  ```
  You can now use Django test server by running `python2 manage.py runserver`. The database is pre-filled with superuser `arhiva` whose password is `a`. Note that by default, `DEBUG` is `False`, so static files won't be loaded correctly.

# Configuring gunicorn

The following three sections are used only for running in the release mode.

You should now be in `~/projects/skoljka/skoljka/`.

1. Run `cd ..` to move to `~/projects/skoljka/`.

2. Create file `runserver.sh`. (fill out **user** and **group** variables)
  ```sh
  #!/bin/bash
  set -e

  PORT=8079       # Internal port for non-static files
  LOGFILE=logs/skoljka.log
  NUM_WORKERS=3

  # user/group to run as
  USER=""
  GROUP=""

  source profile

  exec gunicorn skoljka.wsgi:application -w $NUM_WORKERS \
    --user=$USER --group=$GROUP --log-level=debug \
    --log-file=$LOGFILE -b localhost:$PORT
  ```

3. Set up `gunicorn`.
  ```sh
  chmod +x runserver.sh
  mkdir -p logs
  pip install gunicorn
  ```


# Configuring supervisor

1. Run the following commands:
  ```sh
  sudo apt-get install supervisor
  touch logs/gunicorn_supervisor.log
  ```

2. Create file `/etc/supervisor/conf.d/skoljka.conf` (use `sudo`, and change these paths)
  ```
  [program:skoljka]
  directory = /home/username/projects/skoljka/
  command = /home/username/projects/skoljka/runserver.sh
  user = username
  stdout_logfile = /home/username/projects/skoljka/logs/gunicorn_supervisor.log
  stderr_logfile = /home/username/projects/skoljka/logs/gunicorn_supervisor.log
  ```

3. Run `skoljka` Django webserver:
  ```sh
  sudo supervisorctl reread
  sudo supervisorctl update
  sudo supervisorctl restart skoljka
  ```

# Configuring nginx

4. Install and start `nginx`:
  ```sh
  sudo apt-get install nginx
  sudo service nginx start
  ```

5. Create `/etc/nginx/sites-available/skoljka` and the symlink `/etc/nginx/sites-enabled/skoljka` to the first file. Use e.g. `8080` as the main port and remember to redirect `/` to the port `8079`. Look at the tutorial for the details.

6. Restart `nginx`
  ```sh
  sudo service nginx restart
  ```

