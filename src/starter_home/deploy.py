import os
import shutil
import subprocess
import sys

from .files import ROOT

INSTANCE = "starter-home"
IMAGE = "images:debian/13/cloud"
IP_ADDRESS = "10.56.24.100"

VM_CONFIG = ROOT / "virtual-machine" / "configuration.yaml"

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


def main() -> None:
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
    vm_exists = check_vm_exists()
    if not vm_exists:
        create_vm()
    else:
        start_vm()


def check_vm_exists() -> bool:
    proc = subprocess.run(
        ["sudo", "incus", "info", INSTANCE],
        capture_output=True,
        text=True,
        check=False,
    )

    return proc.returncode == 0 and proc.stdout is not None


def create_vm() -> None:
    config = VM_CONFIG.read_text()

    host_key = ""
    for idx, line in enumerate(HOST_KEY.read_text().strip().splitlines()):
        if idx == 0:
            host_key += line
        else:
            host_key += "\n" + " " * 8 + line

    config = config.replace("${SSH_HOST_PRIVATE_KEY}", host_key)
    config = config.replace(
        "${SSH_HOST_PUBLIC_KEY}", HOST_KEY_PUBLIC.read_text().strip()
    )
    config = config.replace("${SSH_PUBLIC_KEY}", SSH_KEY_PUBLIC.read_text().strip())

    print("Creating VM")
    _ = subprocess.run(
        ["sudo", "incus", "launch", IMAGE, INSTANCE, "--vm"],
        input=config,
        stdout=subprocess.DEVNULL,
        text=True,
        check=True,
    )


def start_vm() -> None:
    state = subprocess.run(
        ["sudo", "incus", "list", INSTANCE, "--format", "csv", "-c", "s"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    if state.lower() != "running":
        print("Starting VM")
        _ = subprocess.run(
            ["sudo", "incus", "start", INSTANCE],
            stdout=subprocess.DEVNULL,
            check=True,
        )


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


if __name__ == "__main__":
    main()
