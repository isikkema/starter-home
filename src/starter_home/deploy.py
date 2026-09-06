import os
import shutil
import subprocess
import sys

import click
from httpx import Client

from .files import ROOT
from .incus import create_instance, get_instance, new_incus_client, start_instance

IMAGE = "images:debian/13/cloud"
IP_ADDRESS = "10.50.0.100"


INVENTORY = ROOT / "automation" / "inventory" / "virtual-machine.yaml"
PLAYBOOK = ROOT / "automation" / "setup-server.yaml"
REQUIREMENTS = ROOT / "automation" / "requirements.yml"
ANSIBLE_CONFIG = ROOT / "automation" / "ansible.cfg"

HOST_STORAGE = ROOT / "host-storage"

SECRETS = ROOT / "secrets"
HOST_KEY = SECRETS / "ssh_host_ed25519_key"
HOST_KEY_PUBLIC = SECRETS / "ssh_host_ed25519_key.pub"
SSH_KEY = SECRETS / "id_ed25519"
SSH_KEY_PUBLIC = SECRETS / "id_ed25519.pub"

KNOWN_HOSTS = SECRETS / "known_hosts"


@click.command()
def deploy() -> None:
    check_incus()

    ensure_host_key()
    ensure_ssh_key()
    ensure_known_hosts()

    ensure_vm_running()

    ensure_ansible_dependencies()
    install_services()


def check_incus() -> None:
    if shutil.which("incus") is None:
        print("error: incus is required", file=sys.stderr)
        sys.exit(1)


def ensure_host_key() -> None:
    if HOST_KEY.exists():
        if HOST_KEY_PUBLIC.exists():
            return

        pubkey = subprocess.run(
            ["ssh-keygen", "-f", str(HOST_KEY), "-y"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        _ = HOST_KEY_PUBLIC.write_text(pubkey)

        return

    print("Creating host keys")
    _ = subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(HOST_KEY)],
        stdout=subprocess.DEVNULL,
        check=True,
    )


def ensure_ssh_key() -> None:
    if SSH_KEY.exists():
        if SSH_KEY_PUBLIC.exists():
            return

        pubkey = subprocess.run(
            ["ssh-keygen", "-f", str(SSH_KEY), "-y"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        _ = SSH_KEY_PUBLIC.write_text(pubkey)

        return

    print("Creating SSH keys")
    _ = subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(SSH_KEY)],
        stdout=subprocess.DEVNULL,
        check=True,
    )


def ensure_known_hosts() -> None:
    valid = check_known_hosts()
    if not valid:
        create_known_hosts()


def check_known_hosts() -> bool:
    return (
        subprocess.run(
            ["ssh-keygen", "-F", IP_ADDRESS, "-f", str(KNOWN_HOSTS)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def create_known_hosts() -> None:
    print("Creating known hosts")

    host_key = HOST_KEY_PUBLIC.read_text()
    _ = KNOWN_HOSTS.write_text(f"{IP_ADDRESS} {host_key}")

    _ = subprocess.run(
        ["ssh-keygen", "-H", "-f", str(KNOWN_HOSTS)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


def ensure_vm_running() -> None:
    client = new_incus_client()
    vm_exists = check_vm_exists(client)
    if not vm_exists:
        create_instance(client)
    else:
        start_instance(client)


def check_vm_exists(client: Client) -> bool:
    return get_instance(client) is not None


def ensure_ansible_dependencies() -> None:
    _ = subprocess.run(
        ["ansible-galaxy", "collection", "install", "-r", str(REQUIREMENTS)],
        stdout=subprocess.DEVNULL,
        check=True,
    )


def install_services() -> None:
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ANSIBLE_CONFIG)

    print("Installing services into VM")
    _ = subprocess.run(
        [
            "ansible-playbook",
            "-i",
            str(INVENTORY),
            str(PLAYBOOK),
        ],
        env=env,
        cwd=ROOT,
        check=True,
    )
