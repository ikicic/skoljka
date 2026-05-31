.PHONY: venv build build-prod frontend-watch typecheck format makemessages makemessages-py generate-i18n-messages makemessages-js compilemessages test

.DEFAULT_GOAL := venv

venv:
	[ -d venv ] || uv venv venv --python=3.13
	uv pip install -r pyproject.toml --python=venv/bin/python

build:
	node esbuild.mjs

build-prod:
	node esbuild.mjs --production

frontend-watch:
	node esbuild.mjs --watch

typecheck:
	npm run typecheck

format:
	. ./venv/bin/activate && find skoljka -name '*.px' -print0 | xargs -0 -n1 sh -c 'echo "$$1"; python -m pythonjsx format "$$1" --in-place --line-width=100 || exit 255' sh

makemessages: makemessages-py makemessages-js

makemessages-py:
	venv/bin/python manage.py makemessages -l hr --ignore=venv/* --ignore=node_modules/* --ignore=staticfiles/* --no-obsolete

generate-i18n-messages:
	node scripts/extract-i18n-messages.mjs

makemessages-js: generate-i18n-messages
	venv/bin/python manage.py makemessages -d djangojs -l hr --extension=ts,tsx --ignore=venv/* --ignore=node_modules/* --ignore=staticfiles/* --ignore=static/js/* --ignore=static/vendor/* --no-obsolete

compilemessages:
	venv/bin/python manage.py compilemessages --ignore=venv/* --ignore=node_modules/* --ignore=staticfiles/*

test:
	venv/bin/python manage.py test skoljka.apps skoljka.tests skoljka.utils
