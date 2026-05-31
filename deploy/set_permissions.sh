#!/usr/bin/env bash
set -euo pipefail

. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_root
require_repo_root

WEB_USER="${WEB_USER:-www-data}"

# Nginx must be able to traverse the path to reach public aliases. This grants
# execute-only access on parent directories, not read/list access.
path="$REPO_ROOT"
while [ "$path" != "/" ]; do
    chmod o+x "$path"
    path="$(dirname "$path")"
done

# Keep sensitive paths private to their owner. These operations intentionally
# avoid touching owner bits, so tracked executable flags remain unchanged.
if [ -f "$REPO_ROOT/skoljka/config/local.py" ]; then
    chmod go-rwx "$REPO_ROOT/skoljka/config/local.py"
fi

if [ -d "$REPO_ROOT/.git" ]; then
    chmod -R go-rwx "$REPO_ROOT/.git"
fi

if [ -d "$REPO_ROOT/private" ]; then
    chmod -R go-rwx "$REPO_ROOT/private"
fi

# Let Nginx read only public files. Keep owner permissions as they are.
for public_dir in "$REPO_ROOT/staticfiles" "$REPO_ROOT/media"; do
    if [ -d "$public_dir" ]; then
        chgrp -R "$WEB_USER" "$public_dir"
        find "$public_dir" -type d -exec chmod g+rx,o+rx {} +
        find "$public_dir" -type f -exec chmod g+r,o+r {} +
    fi
done

echo "Applied public/private permissions for $REPO_ROOT"
