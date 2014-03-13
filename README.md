# Installation

This procedure is based on the following tutorial:
http://michal.karzynski.pl/blog/2013/06/09/django-nginx-gunicorn-virtualenv-supervisor/

1. Go to your projects folder (e.g. `~/projects`). Run:
  ```sh
  sudo apt-get install python-virtualenv
  virtualenv skoljka
  cd skoljka
  ```

2. In current folder, create file `profile` containing:
  ```sh
  export PYTHONPATH=$PWD:$PWD/skoljka:$PYTHONPATH
  export PROD=true

  source bin/activate
  ```

3. Go to virtual env, clone skoljka and run installation script:
  ```sh
  chmod +x profile
  source profile

  git clone git://github.com/ikicic/skoljka
  cd skoljka
  scripts/install.sh
  ```

4. Create an empty `UTF8` database (use your **username**):
  ```sh
  mysql -e "CREATE DATABASE skoljka CHARACTER SET utf8 COLLATE utf8_general_ci;" -u username -p
  ```

5. Fill out `settings/local.py`.

6. Initialize database and build:
  ```sh
  python manage.py syncdb --noinput
  python b.py
  cd ..
  ```

# Configuring gunicorn

You should now be in `~/projects/skoljka/`.

7. Create file `runserver.sh`. (fill out **user** and **group** variables)
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

8. Set up `gunicorn`.
  ```sh
  chmod +x runserver.sh
  pip install gunicorn
  ```


# Configuring supervisor

9. Run following commands:
  ```sh
  sudo apt-get install supervisor
  mkdir -p logs
  touch logs/gunicorn_supervisor.log
  ```

10. Create file `/etc/supervisor/conf.d/skoljka.conf` (use `sudo`, and change these paths)
  ```
  [program:skoljka]
  directory = /home/username/projects/skoljka/
  command = /home/username/projects/skoljka/runserver.sh
  user = username
  stdout_logfile = /home/username/projects/skoljka/logs/gunicorn_supervisor.log
  stderr_logfile = /home/username/projects/skoljka/logs/gunicorn_supervisor.log
  ```

11. Run `skoljka` Django webserver:
  ```sh
  sudo supervisorctl reread
  sudo supervisorctl update
  sudo supervisorctl restart skoljka
  ```

# Configuring nginx

12. Install and start `nginx`:
  ```sh
  sudo apt-get install nginx
  sudo service nginx start
  ```

13. Create `/etc/nginx/sites-available/skoljka` and the symlink `/etc/nginx/sites-enabled/skoljka` to the first file. Use e.g. `8080` as the main port and remember to redirect `/` to the port `8079`. Look at the tutorial for the details.

14. Restart `nginx`
  ```sh
  sudo service nginx restart
  ```

