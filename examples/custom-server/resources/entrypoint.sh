#!/bin/sh
set -eu

if [ ! -f /etc/ssh/ssh_host_ed25519_key ]; then
    ssh-keygen -A
fi

mkdir -p /home/server/.ssh
cp /bootstrap/authorized_keys /home/server/.ssh/authorized_keys
chown -R server:server /home/server/.ssh
chmod 0700 /home/server/.ssh
chmod 0600 /home/server/.ssh/authorized_keys

exec /usr/sbin/sshd -D -e
