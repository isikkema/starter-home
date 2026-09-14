#!/bin/bash

set -eo pipefail

echo "Installing Incus..."
sudo apt-get update
sudo apt-get install -y incus ovn-host ovn-central

sudo ovs-vsctl set open_vswitch . external_ids:ovn-remote=unix:/run/ovn/ovnsb_db.sock external_ids:ovn-encap-type=geneve external_ids:ovn-encap-ip=127.0.0.1

sudo systemctl restart ovn-controller
sudo systemctl restart incus

sudo incus admin init --minimal
sudo incus network create starter-uplink ipv4.nat=true ipv6.address=none ipv4.address=10.60.0.1/24 ipv4.dhcp.ranges=10.60.0.100-10.60.0.200 ipv4.ovn.ranges=10.60.0.240-10.60.0.250 ipv4.routes=10.50.0.0/24
sudo gpasswd --add "$USER" incus
sg incus -c 'incus network create starter-net --type=ovn network=starter-uplink ipv4.address=10.50.0.1/24 ipv4.dhcp=true ipv4.dhcp.ranges=10.50.0.100-10.50.0.200 ipv6.address=none'

echo "Installing uv..."
wget -qO- https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

echo "Installing starter-home..."
uv tool install .

echo "Installed!"
