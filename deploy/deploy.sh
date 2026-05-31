#!/usr/bin/env bash
set -euo pipefail

. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_repo_root

cd "$REPO_ROOT"

set -x

mkdir -p media private/transcription worker-files
make
npm ci
make build-prod
./venv/bin/python manage.py check --deploy
./venv/bin/python manage.py migrate --noinput
./venv/bin/python manage.py collectstatic --noinput
make compilemessages
./venv/bin/python manage.py render_registration_challenges
