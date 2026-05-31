#!/usr/bin/env bash
set -euo pipefail

. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_root

FORCE=0
if [ "${1:-}" = "--force" ]; then
    FORCE=1
    shift
fi

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
    echo "Usage: sudo $0 [--force] DOMAIN [APP_PORT]" >&2
    exit 1
fi

APP_PORT="${2:-8000}"
NGINX_SITE="/etc/nginx/sites-available/skoljka.conf"

if [ -e "$NGINX_SITE" ] && [ "$FORCE" -ne 1 ]; then
    echo "$NGINX_SITE already exists; refusing to overwrite it." >&2
    echo "Edit it manually, or rerun with --force if you intentionally want to replace it." >&2
    exit 1
fi

sed -e "s|__DOMAIN__|$DOMAIN|g" \
    -e "s|__APP_PORT__|$APP_PORT|g" \
    -e "s|__REPO_ROOT__|$REPO_ROOT|g" \
    "$DEPLOY_DIR/nginx/skoljka.conf.template" \
    > "$NGINX_SITE"

ln -sf "$NGINX_SITE" /etc/nginx/sites-enabled/skoljka.conf
nginx -t
systemctl reload nginx

echo "Installed Nginx site for $DOMAIN."
