# Release Notes

## Školjka v0.12.0

### New features
- [competition] chains can now be restricted to selected teams
- [competition] submission count limit can be customized per-task now
- [competition] optionally make team categories non-configurable by teams themselves
- [competition] optionally hide team categories from teams themselves
- [competition] added a new "teams/participants/competitors" admin page, used to change team categories
- [competition] added `Chain.close_minutes`, used to close the submission for a given chain after a given period of time
- [competition] added an option to show per-category scoreboards
- [userprofile] added a registration challenge to fight spam

### Changes
- [competition] individual (non-team) competitions and courses: adjusted the GUI based on `Competition.max_team_size`
- [competition] removed the confusing angle brackets in "&lt;Write the question/message here&gt;"
- [competition] using "unlock days" and "close days" not only for courses, but depending on the competition/course duration
- [general] improved the design of some forms by utilizing `bootstrap_toolkit`
- [general] added a "courses" link in the main menu, separately list competitions and courses

### Technical
- [competition] added some Cypress tests for competitions
- [competition] courses now use the `/course/<id>/` URL pattern by default
- [competition] courses and competitions URLs are automatically redirected to the correct URL (as returned by `get_absolute_url()`)
- [competition] made the solution help optional in the competition and course help pages
- [competition] split `views.py` into multiple files `views/*.py`
- [posts] changed the prefix of PostsForm to avoid `id` collision

# Installation (Docker)

Note: docker-based installation is work in progress.
The docker files are not optimal nor secure for production.

In the current setup, the container is given read-write access to the repository root folder, because media files are stored in `local/` and similar subfolders.

First, build the image and start the container:
```sh
./docker/build.sh
./docker/run_mount.sh
```

Then, attach to the container:
```sh
docker attach skoljka
```
(This command might look stuck, press enter to see the interactive shell.)

From outside the container, run the following:
```sh
./docker/run_rsync.sh
```

Within the container, run the following:
```sh
cd /app
./docker/build_internal.sh
./docker/setup_internal.sh
```
The default mysql root password is empty.

To run skoljka, run
```sh
cd /app
python2 manage.py runserver 0.0.0.0:8000
```
and open http://localhost:8000/ .
Set `DEBUG` in `settings/local.py` to `True` for CSS and JS files to work.

After closing the container, run the following to resume it:
```sh
docker start skoljka
docker attach skoljka
service mysql start                  # Sometimes fails on the first try.
mysqlcheck --repair --all-databases  # Sometimes needed.
```


# Development environment setup

```sh
# Install outside of the Python environment, to get the newest version.
python3 -m pip install pre-commit
pre-commit install
```


# Installation

This procedure is based on the following tutorial:
http://michal.karzynski.pl/blog/2013/06/09/django-nginx-gunicorn-virtualenv-supervisor/

NOTE: Consider using Docker installation above.
The following installation procedure might be broken.

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
  scripts/install_dependencies.sh
  scripts/setup.sh
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
  python2 build.py
  ```
  You can now use Django test server by running `python2 manage.py runserver`.
  The database is pre-filled with superuser `arhiva` whose password is `a`.
  Note that in `settings/local.py` the variable `DEBUG` is `False` by default, so static files won't be loaded correctly.


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


# Testing

## Unit tests

The syntax to restrict which tests are executed:
```sh
python2 manage.py test --noinput competition.ChainSortingTest.test_custom_ordering
```

## End to end tests (E2E)

To run the E2E tests, first launch the test server in the Docker container:
```sh
python2 manage.py testserver --noinput --traceback --addrport=0.0.0.0:8000 skoljka/userprofile/fixtures/test_userprofiles.json
```

Then, run the tests:
```sh
npx cypress run
```

Or, launch the GUI with:
```sh
npx cypress open
```
