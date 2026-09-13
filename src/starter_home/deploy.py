import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import click
from fabric import Connection
from httpx import Client
from invoke.runners import Result
from paramiko.ssh_exception import NoValidConnectionsError

from starter_home.backup import get_local_backup_env, get_remote_backup_env
from starter_home.server import server_connect

from .files import (
    BACKUP,
    BASE_CONFIG,
    CUSTOM_CONFIG,
    GENERATED_CONFIG,
    HOST_KEY,
    HOST_KEY_PUBLIC,
    KNOWN_HOSTS,
    REMOTE_BACKUP_ENV,
    SECRETS,
    SERVICES,
    SSH_KEY,
    SSH_KEY_PUBLIC,
)
from .incus import create_instance, get_instance, new_incus_client, start_instance

IMAGE = "images:debian/13/cloud"
IP_ADDRESS = "10.50.0.100"


@click.command()
def deploy() -> None:
    check_incus()
    incus_config = get_incus_config()

    ensure_host_key()
    ensure_ssh_key()
    ensure_known_hosts()

    ensure_vm_running(incus_config)

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
    SECRETS.mkdir(mode=0o700, exist_ok=True)

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


class ServiceFile:
    def __init__(self, service: "Service", path: Path) -> None:
        self.path = path
        self.relative_path = self.path.relative_to(service.path)
        self.hash = hashlib.file_digest(self.path.open("rb"), "sha256").hexdigest()


class Service:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.name = self.path.name

        self.changed = False

        containers = list(self.path.glob("*.container"))
        if (
            len(containers) == 0
            or len(containers) > 1
            or len(containers) == 1
            and containers[0].name != f"{self.name}.container"
        ):
            raise ValueError(
                f"Service {self.name} must container exactly one .container file named {self.name}.container"
            )

        self.files: list[ServiceFile] = []
        for file in self.path.rglob("*"):
            if not file.is_file():
                continue

            self.files.append(ServiceFile(self, file))

    def copy_to_server(self, server: Connection) -> None:
        remote_services_dir = Path(
            f"/home/starter-home/.config/containers/systemd/{self.name}"
        )

        server.run(f"mkdir -p {remote_services_dir}")
        with server.cd(remote_services_dir):
            output: Result = server.run("find -type f -printf '%P\n'", hide=True)

            remote_files = output.stdout.splitlines()
            unnecessary_remote_files = list(
                set(remote_files).difference(str(f.relative_path) for f in self.files)
            )
            for file in unnecessary_remote_files:
                server.run(f"rm {file}", hide=True)
                self.changed = True

            remote_files = list(set(remote_files).difference(unnecessary_remote_files))

            for service_file in self.files:
                copy = False

                output = server.run(
                    f"test -f {service_file.relative_path!s}", hide=True, warn=True
                )
                if output.return_code != 0:
                    copy = True
                else:
                    output = server.run(
                        f"sha256sum {service_file.relative_path!s}", hide=True
                    )
                    remote_hash = output.stdout.split()[0]
                    if remote_hash != service_file.hash:
                        copy = True

                if copy:
                    remote_file = remote_services_dir / service_file.relative_path
                    server.run(f"mkdir -p {remote_file.parent}", hide=True)
                    server.put(
                        str(service_file.path),
                        str(remote_file),
                    )
                    self.changed = True

    def restart_if_changed(self, server: Connection) -> None:
        if not self.changed:
            return

        server.run(
            f"systemctl --user restart {self.name}",
            env={"XDG_RUNTIME_DIR": "/run/user/1000"},
            echo=True,
        )


def wait_for_server() -> Connection:
    waiting = False
    start = time.time()
    while time.time() - start <= 180:
        try:
            server = server_connect()
            server.open()
            return server
        except NoValidConnectionsError:
            if not waiting:
                print("Waiting for server...")
                waiting = True

            time.sleep(5)

    raise TimeoutError("Timed out while trying to connect to server")


def install_services() -> None:
    SERVICES.mkdir(mode=0o755, exist_ok=True)

    services = [Service(dir) for dir in SERVICES.iterdir() if dir.is_dir()]

    if len(services) == 0:
        print("WARNING: No services to deploy.")

    server = wait_for_server()

    server.run("sudo apt-get install -y podman restic", echo=True)
    server.run("sudo loginctl enable-linger starter-home", echo=True)

    server.run("sudo mkdir -p /vm-storage", echo=True)
    server.run("sudo chown starter-home:starter-home /vm-storage", echo=True)

    # TODO: Handle changed or deleted directories
    for service in services:
        print(f"Checking {service.name} definition...")
        service.copy_to_server(server)
        if service.changed:
            print("Updated.")
        else:
            print("No change.")

    server.run(
        "systemctl --user daemon-reload",
        env={"XDG_RUNTIME_DIR": "/run/user/1000"},
        echo=True,
    )

    before_volumes: set[str] = set(
        server.run(
            "podman volume ls --format '{{ .Name }}'", hide=True
        ).stdout.splitlines()
    )

    server.run(
        "systemctl --user restart --all '*-volume.service'",
        env={"XDG_RUNTIME_DIR": "/run/user/1000"},
        echo=True,
    )

    after_volumes: set[str] = set(
        server.run(
            "podman volume ls --format '{{ .Name }}'", hide=True
        ).stdout.splitlines()
    )

    restore_volumes = after_volumes - before_volumes

    server.run("mkdir -p /home/starter-home/backup", echo=True)
    backup_files = BACKUP.glob("*")
    for file in backup_files:
        server.put(f"{file!s}", "/home/starter-home/backup/")

    local_backup_env = get_local_backup_env()

    output: Result = server.run(
        "restic cat config",
        env=local_backup_env,
        hide=True,
        warn=True,
    )

    local_restore = False
    if output.return_code == 0:
        output = server.run(
            "restic snapshots --json --latest 1",
            env=local_backup_env,
            hide=True,
        )

        if len(json.loads(output.stdout)) > 0:
            local_restore = True
    elif output.return_code == 10:
        server.run(
            "restic init",
            env=local_backup_env,
            echo=True,
        )
    else:
        print(output.stderr)
        raise RuntimeError("Failed to initialize local backup")

    if local_restore and len(restore_volumes) > 0:
        server.run(
            "restic restore latest --target /home/starter-home/local_restore",
            env=local_backup_env,
            echo=True,
        )

        for volume in restore_volumes:
            output = server.run(
                f"podman volume import {volume} /home/starter-home/local_restore/{volume}.tar",
                echo=True,
            )

        server.run("rm -rf /home/starter-home/local_restore", echo=True)

    if REMOTE_BACKUP_ENV.exists():
        remote_backup_env = get_remote_backup_env()

        output = server.run(
            "restic cat config",
            env=remote_backup_env,
            hide=True,
            warn=True,
        )

        remote_restore = False
        if output.return_code == 0:
            output = server.run(
                "restic snapshots --json --latest 1",
                env=remote_backup_env,
                hide=True,
            )

            if len(json.loads(output.stdout)) > 0:
                remote_restore = True
        elif output.return_code == 10:
            server.run(
                "restic init",
                env=remote_backup_env,
                echo=True,
            )
        else:
            print(output.stderr)
            raise RuntimeError("Failed to initialize remote backup")

        if remote_restore and not local_restore and len(restore_volumes) > 0:
            server.run(
                "restic restore latest --target /home/starter-home/remote_restore",
                env=remote_backup_env,
                echo=True,
            )

            for volume in restore_volumes:
                output = server.run(
                    f"podman volume import {volume} /home/starter-home/remote_restore/{volume}.tar",
                    echo=True,
                )

            server.run("rm -rf /home/starter-home/remote_restore", echo=True)

    server.run(
        "systemctl --user restart *-build.service",
        env={"XDG_RUNTIME_DIR": "/run/user/1000"},
        echo=True,
    )

    for service in services:
        service.restart_if_changed(server)

    server.run("mkdir -p /home/starter-home/.config/systemd/user", echo=True)
    server.run(
        "mv /home/starter-home/backup/*.{service,timer} /home/starter-home/.config/systemd/user/",
        echo=True,
    )

    server.run(
        "systemctl --user daemon-reload",
        env={"XDG_RUNTIME_DIR": "/run/user/1000"},
        echo=True,
    )

    server.run(
        "systemctl --user enable {local,remote}-backup.timer",
        env={"XDG_RUNTIME_DIR": "/run/user/1000"},
        echo=True,
    )
    server.run(
        "systemctl --user start {local,remote}-backup.timer",
        env={"XDG_RUNTIME_DIR": "/run/user/1000"},
        echo=True,
    )
