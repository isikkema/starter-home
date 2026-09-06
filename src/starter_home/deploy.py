import json
import os
import shutil
import subprocess
import sys
from typing import Any

import click
from httpx import Client

from .files import BASE_CONFIG, CUSTOM_CONFIG, ROOT
from .incus import create_instance, get_instance, new_incus_client, start_instance

IMAGE = "images:debian/13/cloud"
IP_ADDRESS = "10.50.0.100"

GENERATED_CONFIG = ROOT / "virtual-machine" / "generated_config.json"

INVENTORY = ROOT / "automation" / "inventory" / "virtual-machine.yaml"
PLAYBOOK = ROOT / "automation" / "setup-server.yaml"
REQUIREMENTS = ROOT / "automation" / "requirements.yml"
ANSIBLE_CONFIG = ROOT / "automation" / "ansible.cfg"

SECRETS = ROOT / "secrets"
HOST_KEY = SECRETS / "ssh_host_ed25519_key"
HOST_KEY_PUBLIC = SECRETS / "ssh_host_ed25519_key.pub"
SSH_KEY = SECRETS / "id_ed25519"
SSH_KEY_PUBLIC = SECRETS / "id_ed25519.pub"

KNOWN_HOSTS = SECRETS / "known_hosts"


@click.command()
def deploy() -> None:
    check_incus()
    incus_config = get_incus_config()

    ensure_host_key()
    ensure_ssh_key()
    ensure_known_hosts()

    ensure_vm_running(incus_config)

    ensure_ansible_dependencies()
    install_services()


def check_incus() -> None:
    if shutil.which("incus") is None:
        print("error: incus is required", file=sys.stderr)
        sys.exit(1)


def get_incus_config() -> dict[str, Any]:
    if GENERATED_CONFIG.exists():
        with open(GENERATED_CONFIG, "r") as f:
            return json.load(f)

    return generate_incus_config()


def generate_incus_config() -> dict[str, Any]:
    if not CUSTOM_CONFIG.exists():
        print("error: starter-home is not set up!", file=sys.stderr)
        sys.exit(1)

    with open(CUSTOM_CONFIG, "r") as f:
        custom_config = json.load(f)

    with open(BASE_CONFIG, "r") as f:
        generated_config = json.load(f)

    generated_config["config"]["limits.cpu"] = str(custom_config["cpus"])
    generated_config["config"]["limits.memory"] = custom_config["memory"]
    generated_config["devices"]["root"]["size"] = custom_config["disk_size"]
    generated_config["devices"]["host-storage"]["source"] = custom_config[
        "host-storage"
    ]

    with open(GENERATED_CONFIG, "w") as f:
        json.dump(generated_config, f, indent=4)

    return generated_config


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


def ensure_vm_running(incus_config: dict[str, Any]) -> None:
    client = new_incus_client()
    vm_exists = check_vm_exists(client)
    if not vm_exists:
        create_instance(client, incus_config)
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

    print(ANSIBLE_CONFIG)
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
