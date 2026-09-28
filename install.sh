#!/bin/bash

set -eo pipefail

echo "Checking for virtualization..."
sudo apt-get update
sudo apt-get install -y cpu-checker
sudo kvm-ok

echo "Installing Incus..."
sudo apt-get install -y incus util-linux-extra

if command -v docker >/dev/null 2>&1; then
    if [ ! -f /etc/docker/daemon.json ]; then
        echo "Configuring Docker for Incus..."
        sudo mkdir -p /etc/docker
        sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
    "ip-forward-no-drop": true
}
EOF

        if sudo systemctl is-active --quiet docker; then
            sudo systemctl restart docker
        fi
        
        sudo iptables -P FORWARD ACCEPT
    else
        echo "Warning: /etc/docker/daemon.json already exists."
        echo "Docker may interfere with Incus networking."
        echo "Please ensure it is configured with \"ip-forward-no-drop\": true."
    fi
fi

sudo incus admin init --minimal
sudo incus network create starter-net ipv4.address=10.50.0.1/24 ipv4.nat=true ipv6.address=none
sudo gpasswd --add "$USER" incus
sg incus -c 'incus list'
sudo incus profile device remove default eth0 --project "user-$UID"
sudo incus project set "user-$UID" restricted.networks.access=starter-net
sudo incus project set "user-$UID" restricted.devices.proxy=allow
sudo incus profile device add default eth0 --project "user-$UID" nic network=starter-net name=eth0

if sudo ufw status 2>/dev/null | grep -q '^Status: active$'; then
    echo "Allowing starter-home through UFW..."
    
    sudo ufw allow in on starter-net
    sudo ufw route allow in on starter-net
    sudo ufw route allow out on starter-net
fi

echo "Installing uv..."
wget -qO- https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

echo "Installing starter-home..."

uv tool install .

echo "Installed!"
