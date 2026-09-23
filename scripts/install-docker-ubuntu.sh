#!/usr/bin/env bash
# Install Docker's official stable Ubuntu packages for this development machine.
# Run through sudo/pkexec, passing the local account that will use Docker.
set -euo pipefail

if [[ $EUID -ne 0 || $# -ne 1 ]]; then
    echo "Usage: sudo bash scripts/install-docker-ubuntu.sh LOCAL_USER" >&2
    exit 2
fi

setup_user="$(id -un -- "$1")"
if [[ "$setup_user" == root ]]; then
    echo "Pass the non-root developer account." >&2
    exit 2
fi

# This setup was reviewed for the repository's Ubuntu 24.04 host.
source /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 24.04 ]]; then
    echo "This installer is for Ubuntu 24.04; review Docker's instructions for this host." >&2
    exit 2
fi

for package in docker.io docker-compose docker-compose-v2 docker-doc docker-buildx \
    podman-docker containerd runc; do
    package_status="$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null || true)"
    if [[ "$package_status" == installed ]]; then
        echo "Existing conflicting package: $package. Review it before replacing anything." >&2
        exit 2
    fi
done

apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl --fail --silent --show-error --location \
    https://download.docker.com/linux/ubuntu/gpg \
    --output /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

setup_arch="$(dpkg --print-architecture)"
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: $setup_arch
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
usermod -aG docker "$setup_user"
docker version
docker compose version
echo "Docker installed. New login sessions for $setup_user will have Docker group access."
