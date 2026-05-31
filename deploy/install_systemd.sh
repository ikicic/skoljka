#!/usr/bin/env bash
set -euo pipefail

. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_root

APP_USER="${APP_USER:-skoljka}"
APP_PORT="${APP_PORT:-8000}"

install -d /etc/skoljka
if [ ! -f /etc/skoljka/skoljka.env ]; then
    install -m 0600 /dev/null /etc/skoljka/skoljka.env
fi

sed -e "s|__APP_USER__|$APP_USER|g" \
    -e "s|__REPO_ROOT__|$REPO_ROOT|g" \
    -e "s|__APP_PORT__|$APP_PORT|g" \
    "$DEPLOY_DIR/systemd/skoljka.service.template" \
    > /etc/systemd/system/skoljka.service

systemctl daemon-reload
systemctl enable skoljka

echo "Installed /etc/systemd/system/skoljka.service"
echo "Edit /etc/skoljka/skoljka.env if API keys are needed, then run:"
echo "  sudo systemctl start skoljka"
