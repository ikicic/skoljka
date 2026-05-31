# Školjka

Školjka is a web archive for math competition problems from various sources.
Problems are organized by competition and year, searchable, tagged by topic, and available for reading online or exporting to PDF/LaTeX.
Users can keep track of what they have solved, bookmark or like problems and lists, and write private notes while studying.

## Requirements

- Python 3.13
- Node.js and npm
- PostgreSQL
- `uv` for Python dependency installation
- `xelatex` for PDF export
- A working LaTeX installation for registration challenge image generation

## Setup

```sh
make                 # create venv and install Python deps (uses uv)
npm install          # frontend deps
cp skoljka/config/local.template.py skoljka/config/local.py  # edit DB + SECRET_KEY
./venv/bin/python manage.py migrate
make build
```

Optionally import the sample data:

```sh
./venv/bin/python manage.py import_json data/sample_data.json
```

## Running

```sh
make build                                  # bundle JS/CSS (development)
./venv/bin/python manage.py runserver
```

For production, use the minified bundles:

```sh
make build-prod                             # minified JS + bundled CSS (static/css/main.min.css)
```

Site runs at http://127.0.0.1:8000/.

## Tests And Checks

```sh
./venv/bin/python manage.py check
./venv/bin/python manage.py makemigrations --check --dry-run
make test
```

## Translations

```sh
make makemessages
make compilemessages
```

JavaScript translation messages are extracted through
`scripts/extract-i18n-messages.mjs`, which is called by `make makemessages`.

## Useful Management Commands

```sh
./venv/bin/python manage.py render_registration_challenges
./venv/bin/python manage.py cleanup_transcription
./venv/bin/python manage.py export_archive --source <slug> --output archive.zip
./venv/bin/python manage.py import_archive archive.zip --owner <username>
./venv/bin/python manage.py import_json data/tags.json
```

## Production Notes

See [deploy/README.md](deploy/README.md) for deployment instructions.

Generated browser bundles live under `static/js/` and `static/vendor/` (gitignored).
CSS sources stay in `static/css/`; production serves the bundled `static/css/main.min.css` when `DEBUG=False`.

## License

This project is licensed under the BSD 3-Clause License. See [LICENSE](LICENSE).
