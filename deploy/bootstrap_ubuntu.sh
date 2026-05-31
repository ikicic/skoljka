#!/usr/bin/env bash
set -euo pipefail

. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_root

APP_USER="${APP_USER:-skoljka}"
NODE_MAJOR="${NODE_MAJOR:-22}"
RUST_VERSION="${RUST_VERSION:-1.96.0}"

apt-get update
apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cerbot \
    curl \
    docker-buildx \
    docker-compose \
    docker.io \
    gettext \
    git \
    gnupg \
    nginx \
    postgresql \
    postgresql-contrib \
    python3-certbot-nginx \
    ufw

install -d -m 0755 /etc/apt/keyrings
curl -fsSL "https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key" \
    | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list
apt-get update
apt-get install -y --no-install-recommends nodejs

if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
fi

install_shared_rust() {
    export CARGO_HOME=/usr/local/cargo
    export RUSTUP_HOME=/usr/local/rustup
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --profile minimal --default-toolchain "$RUST_VERSION"
    ln -sf /usr/local/cargo/bin/rustc /usr/local/bin/rustc
    ln -sf /usr/local/cargo/bin/cargo /usr/local/bin/cargo
    ln -sf /usr/local/cargo/bin/rustup /usr/local/bin/rustup
    configure_shared_rust
}

configure_shared_rust() {
    export CARGO_HOME=/usr/local/cargo
    export RUSTUP_HOME=/usr/local/rustup
    /usr/local/cargo/bin/rustup default "$RUST_VERSION"
    chmod -R a+rX /usr/local/rustup
    cat > /etc/profile.d/rust.sh <<'EOF'
export RUSTUP_HOME=/usr/local/rustup
export PATH="/usr/local/cargo/bin:$PATH"
EOF
    chmod 644 /etc/profile.d/rust.sh
    RUSTUP_HOME=/usr/local/rustup /usr/local/cargo/bin/rustc --version
}

installed_rust_version() {
    if [ -x /usr/local/cargo/bin/rustc ]; then
        RUSTUP_HOME=/usr/local/rustup \
            /usr/local/cargo/bin/rustc --version 2>/dev/null | awk '{print $2}'
    fi
}

if [ "$(installed_rust_version)" != "$RUST_VERSION" ]; then
    install_shared_rust
elif [ -d /usr/local/rustup ] && {
    [ ! -f /etc/profile.d/rust.sh ] \
        || grep -q 'CARGO_HOME=/usr/local/cargo' /etc/profile.d/rust.sh
}; then
    configure_shared_rust
fi

if ! id "$APP_USER" >/dev/null 2>&1; then
    useradd --system --create-home --shell /bin/bash "$APP_USER"
fi

usermod -aG docker "$APP_USER"
install -d -o "$APP_USER" -g "$APP_USER" "$REPO_ROOT"
install -d -o "$APP_USER" -g "$APP_USER" /var/log/skoljka

systemctl enable --now postgresql
systemctl enable --now docker
systemctl enable --now nginx

cat <<EOF
Bootstrap complete.

Next steps:
1. Create PostgreSQL DB/user.
2. Create skoljka/config/local.py from local.template.py.
3. Run deploy/set_permissions.sh, deploy/install_systemd.sh, and deploy/install_nginx.sh.
EOF
