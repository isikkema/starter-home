#!/bin/bash

uv tool uninstall starter-home

sudo rm /etc/NetworkManager/conf.d/starter-home-dns.conf
sudo rm /etc/systemd/system/starter-home-dns.service

sudo ufw delete allow in on starter-net
sudo ufw route delete allow in on starter-net
sudo ufw route delete allow out on starter-net

incus delete --force starter-home
sudo incus profile device remove default eth0 --project "user-$UID"
sudo incus network delete starter-net

sudo apt-get remove --purge --autoremove -y incus

if systemctl is-active --quiet NetworkManager; then
    sudo nmcli device delete starter-net
fi

echo -e "\n---\nReboot to complete the uninstall process."
