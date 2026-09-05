#!/bin/bash

set -eo pipefail

echo "Installing Incus..."
sudo apt-get update
sudo apt-get install -y incus

sudo incus admin init --minimal
sudo incus network create starter-home-net ipv4.address=10.50.0.1/24 ipv6.address=none
UID="$(id -u)"
sudo incus project set user-$UID restricted.networks.access=starter-home-net
sudo gpasswd --add "$USER" incus

echo "Installing uv..."
wget -qO- https://astral.sh/uv/install.sh | sh

echo "Installing starter-home..."
uv pip install .

echo "Installed!"