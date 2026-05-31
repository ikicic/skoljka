# Deploying Školjka

## 1. Bootstrap The Host

Clone the repository first, then run from the checkout:

```sh
cd /path/to/skoljka
sudo deploy/bootstrap_ubuntu.sh
```

## 2. Database

Create a database and user:

```sh
sudo -u postgres createuser --pwprompt skoljka
sudo -u postgres createdb --owner skoljka skoljkadb
```

## 3. Application Checkout

Create production settings:

```sh
cp skoljka/config/local.template.py skoljka/config/local.py
# Edit skoljka/config/local.py
```

Set at least `SECRET_KEY`, `DEBUG = False`, `ALLOWED_HOSTS`, database
credentials, email settings, and worker settings. For the worker:

```py
EXTERNAL_PROCESS_MODE = "worker"
EXTERNAL_WORKER_URL = "http://127.0.0.1:8765/run"
EXTERNAL_WORKER_TOKEN = "<long random shared secret>"
```

Apply filesystem permissions:

```sh
sudo ./deploy/set_permissions.sh
```

This keeps source files, `skoljka/config/local.py`, and `private/` unreadable to
Nginx. Nginx gets access only to public `staticfiles/` and `media/`. Parent
directories get execute-only traversal permission so Nginx can reach those
public aliases without being able to list the repository.

## 4. Docker Worker

Start the isolated external-tool worker:

```sh
cd docker
EXTERNAL_WORKER_TOKEN="<same long random shared secret>" make up
make check-tools
make ps
```

The worker mounts `../worker-files` as `/app/worker-files`.
`EXTERNAL_WORKER_TOKEN` must match the value in `skoljka/config/local.py`.

The worker must be running before `./deploy/deploy.sh` can render registration
challenge images when `EXTERNAL_PROCESS_MODE = "worker"`.

## 5. Build And Migrate

Run as the app user:

```sh
./deploy/deploy.sh
```

Import the built-in tag taxonomy:

```sh
./venv/bin/python manage.py import_json data/tags.json
```

This command creates or updates tags by slug, so it is safe to rerun after
pulling changes to `data/tags.json`.

Run permissions again after collecting static files and rendering images:

```sh
sudo ./deploy/set_permissions.sh
```

## 6. Systemd

Install the Gunicorn service:

```sh
sudo deploy/install_systemd.sh
sudo systemctl start skoljka
sudo systemctl status skoljka
```

If transcription API keys are needed, put them in `/etc/skoljka/skoljka.env`:

```sh
MISTRAL_API_KEY=...
ANTHROPIC_API_KEY=...
```

Then restart:

```sh
sudo systemctl restart skoljka
```

## 7. Nginx

Install the Nginx site:

```sh
sudo ./deploy/install_nginx.sh example.com
```

The generated config serves `staticfiles/` and `media/`, and proxies everything
else to Gunicorn on `127.0.0.1:8000`.

The installer refuses to overwrite an existing
`/etc/nginx/sites-available/skoljka.conf`, because Certbot may have added SSL
settings there. Use `--force` only when you intentionally want to replace the
active config:

```sh
sudo ./deploy/install_nginx.sh --force example.com
```

## 8. SSL With Certbot

Once the site works over HTTP, follow these instructions to set up HTTPS.

```sh
sudo certbot --nginx -d example.com -d www.example.com
```

Choose the redirect-to-HTTPS option when Certbot asks. Test renewal:

```sh
sudo certbot renew --dry-run
```

After enabling HTTPS, verify production security settings in
`skoljka/config/local.py`:

```py
DEBUG = False
ALLOWED_HOSTS = ["example.com"]
CSRF_TRUSTED_ORIGINS = ["https://example.com"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
```

Then restart the app:

```sh
sudo systemctl restart skoljka
```

## 9. Release Checklist

For normal releases:

```sh
git pull
./deploy/deploy.sh
./venv/bin/python manage.py import_json data/tags.json
sudo ./deploy/set_permissions.sh
sudo systemctl restart skoljka
cd docker && EXTERNAL_WORKER_TOKEN="<same long random shared secret>" make up
```

Useful logs:

```sh
sudo journalctl -u skoljka -f
sudo tail -f /var/log/nginx/error.log
cd docker && make logs
```
