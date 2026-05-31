#!/usr/bin/env bash

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/.." && pwd)"

# Bootstrap installs a shared read-only toolchain under /usr/local/rustup. The
# rustup shims need RUSTUP_HOME to find it; leave CARGO_HOME unset so each user
# writes registry/cache/build artifacts under their own ~/.cargo.
if [ -d /usr/local/rustup ] && [ -x /usr/local/cargo/bin/rustc ]; then
    export RUSTUP_HOME="${RUSTUP_HOME:-/usr/local/rustup}"
    export PATH="/usr/local/cargo/bin:$PATH"
fi

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "Run as root: sudo $0" >&2
        exit 1
    fi
}

require_repo_root() {
    if [ ! -f "$REPO_ROOT/manage.py" ]; then
        echo "Could not find manage.py at repository root: $REPO_ROOT" >&2
        exit 1
    fi
}
