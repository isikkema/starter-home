#!/bin/bash

set -eo pipefail

echo "Installing Incus..."

sudo mkdir -p /etc/apt/keyrings/
sudo wget -O /etc/apt/keyrings/zabbly.asc https://pkgs.zabbly.com/key.asc
sudo tee /etc/apt/sources.list.d/zabbly-incus-stable.sources >/dev/null <<EOF
Enabled: yes
Types: deb
URIs: https://pkgs.zabbly.com/incus/stable
Suites: $(. /etc/os-release && echo ${VERSION_CODENAME})
Components: main
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/zabbly.asc
EOF

sudo apt-get update
sudo apt-get install -y incus ovn-host ovn-central

sudo ovs-vsctl set open_vswitch . external_ids:ovn-remote=unix:/run/ovn/ovnsb_db.sock external_ids:ovn-encap-type=geneve external_ids:ovn-encap-ip=127.0.0.1

sudo systemctl restart ovn-controller
sudo systemctl restart incus

sudo incus admin init --minimal
sudo incus network create starter-uplink ipv4.nat=true ipv6.address=none ipv4.address=10.60.0.1/24 ipv4.dhcp.ranges=10.60.0.100-10.60.0.200 ipv4.ovn.ranges=10.60.0.240-10.60.0.240 ipv4.routes=10.50.0.0/24
sudo incus project set user-1000 features.networks=true restricted.networks.uplinks=starter-uplink

sudo gpasswd --add "$USER" incus
sg incus -c 'incus network create starter-net --type=ovn network=starter-uplink ipv4.address=10.50.0.1/24 ipv4.dhcp=true ipv4.dhcp.ranges=10.50.0.100-10.50.0.200 ipv6.address=none'

sudo nmcli connection modify starter-uplink +ipv4.routes "10.50.0.0/24 10.60.0.240"

echo "Installing uv..."
wget -qO- https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

echo "Installing starter-home..."
uv tool install .

echo "Installed!"
