#!/bin/bash

set -eo pipefail

echo "Installing Incus..."
sudo apt-get update
sudo apt-get install -y incus

sudo incus admin init --minimal
sudo incus network create starter-net ipv4.address=10.50.0.1/24 ipv6.address=none
sudo gpasswd --add "$USER" incus
sg incus -c 'incus list'
sudo incus profile device remove default eth0 --project "user-$UID"
sudo incus project set user-$UID restricted.networks.access=starter-net
sudo incus profile device add default eth0 --project "user-$UID" nic network=starter-net name=eth0

echo "Installing uv..."
wget -qO- https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

echo "Installing starter-home..."
uv tool install .

echo "Installed!"