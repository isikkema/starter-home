import ipaddress
import json
import os
import shutil
import socket
import subprocess
from getpass import getpass

import click
import psutil

from .files import CUSTOM_CONFIG, LOCAL_BACKUP_ENV, REMOTE_BACKUP_ENV, ROOT, SERVICES

HOST_STORAGE = ROOT / "host-storage"

DNS = "10.50.0.100"
DOMAIN = "~starter.home.arpa"


@click.command()
def setup() -> None:
    if CUSTOM_CONFIG.exists():
        print("starter-home has already been setup!")
        answer = input("Do you want to run setup again? y/N: ")
        if answer != "y":
            return

    match os.cpu_count():
        case None:
            recommended_cpus = None
        case n if n <= 0:
            recommended_cpus = None
        case 1:
            recommended_cpus = 1
        case n if n <= 4:
            recommended_cpus = n - 1
        case n if n <= 8:
            recommended_cpus = n - 2
        case n:
            recommended_cpus = n - 3

    if recommended_cpus is None:
        cpus = int(input("Number of CPUs: "))
    else:
        cpus = input(f"Number of CPUs [{recommended_cpus}]: ")
        if len(cpus.strip()) == 0:
            cpus = recommended_cpus
        else:
            cpus = int(cpus)

    print(
        "Memory and Disk Size must be specified as units of MB, GB, TB, MiB, GiB, or TiB."
    )
    print("Example: 8GiB")

    available_mem: int = psutil.virtual_memory().available
    gib = 1024 * 1024 * 1024
    available_gib = available_mem // gib
    match available_gib:
        case n if n <= 1:
            recommended_gib = None
        case n if n <= 4:
            recommended_gib = available_gib - 1
        case n if n <= 8:
            recommended_gib = available_gib - 2
        case n:
            recommended_gib = available_gib - 3

    while True:
        if recommended_gib is None:
            mem = input("Memory: ")
        else:
            mem = input(f"Memory [{recommended_gib}GiB]: ")
            if len(mem.strip()) == 0:
                mem = f"{recommended_gib}GiB"

        if validate_size(mem):
            break

        print(f'"{mem}" is not a valid size.')

    while True:
        disk_size = input("Disk Size: ").strip()

        if validate_size(disk_size):
            break

        print(f'"{disk_size}" is not a valid size.')

    forwarded_ports: list[dict[str, int]] = []

    print(
        "If you intend to reach the server from any devices other than this computer, port forwarding is required."
    )
    answer = input(
        "Do you want to forward any ports from the host to the server? Y/n: "
    ).strip()
    local_addr = None
    if answer.lower() == "y" or len(answer) == 0:
        recommended_ip = get_local_ip()
        if recommended_ip is None:
            local_ip = input("Host computer's LAN IP: ")
        else:
            local_ip = input(f"Host computer's LAN IP [{recommended_ip}]: ").strip()
            if len(local_ip) == 0:
                local_ip = recommended_ip

        local_addr = ipaddress.IPv4Address(local_ip)
        print(
            "Enter desired forwarded ports in the form <SOURCE_PORT>,<DESTINATION_PORT> or leave blank when finished."
        )
        print("Example: 80,8080")
        while True:
            answer = input("Forward port: ").strip()
            if len(answer) == 0:
                break

            ports = answer.split(",")
            if len(ports) != 2:
                print("Couldn't parse ports.")
                continue

            src_port = int(ports[0])
            dst_port = int(ports[1])

            forwarded_ports.append(
                {
                    "src": src_port,
                    "dst": dst_port,
                }
            )

    if not LOCAL_BACKUP_ENV.exists():
        while True:
            local_password = getpass("Password for local backups: ")
            local_password_confirm = getpass("Confirm password: ")

            if local_password_confirm != local_password:
                print("Passwords do not match.")
                continue

            if len(local_password) == 0:
                print("Password cannot be empty.")
                continue

            if local_password.strip() != local_password:
                print("First or last characters of password cannot be whitespace.")
                continue

            break

        with open(LOCAL_BACKUP_ENV, "w") as f:
            _ = f.write(
                f"RESTIC_REPOSITORY=/host-storage/backup\nRESTIC_PASSWORD={local_password}"
            )

    if not REMOTE_BACKUP_ENV.exists():
        print("A remote backup location is highly recommended.")
        print("See the Remote Backups section in the README.")

    resolve_local = False
    answer = input(
        "Do you want starter-home to attempt to automatically setup split DNS? Y/n: "
    ).strip()
    if answer.lower() == "y" or len(answer) == 0:
        resolve_local = setup_split_dns(local_addr)

    print(f"CPUs: {cpus}")
    print(f"Memory: {mem}")
    print(f"Disk Size: {disk_size}")
    if local_addr is not None:
        print(f"LAN IP: {local_addr.compressed}")
        print("Forwarded Ports:")
        for ports in forwarded_ports:
            print(f"  {ports['src']} => {ports['dst']}")

        print(f"Resolve Local: {resolve_local}")

    while True:
        answer = input("Does this look right? y/n: ")
        if answer.lower() == "y":
            break
        elif answer.lower() == "n":
            print("Aborting...")
            return

    SERVICES.mkdir(mode=0o700, exist_ok=True)
    HOST_STORAGE.mkdir(mode=0o700, exist_ok=True)

    with open(CUSTOM_CONFIG, "w") as f:
        json.dump(
            {
                "cpus": cpus,
                "memory": mem,
                "disk_size": disk_size,
                "host-storage": str(HOST_STORAGE),
                "local_address": local_addr.compressed
                if local_addr is not None
                else None,
                "forwarded_ports": forwarded_ports,
                "resolve_local": resolve_local,
            },
            f,
            indent=4,
        )

    print("Setup complete!")


def validate_size(size: str) -> bool:
    digits = "0123456789"

    num = None
    units = None
    for i in range(len(size)):
        if size[i] in digits:
            continue

        num = size[:i]
        units = size[i:]
        break

    if num is None or units is None:
        return False

    try:
        int(num)
    except ValueError:
        return False

    return units in ["MB", "GB", "TB", "MiB", "GiB", "TiB"]


def get_local_ip() -> str | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("1.1.1.1", 53))

    local_ip, _ = s.getsockname()
    s.close()

    addr = ipaddress.IPv4Address(local_ip)
    if addr in ipaddress.IPv4Network("10.0.0.0/8"):
        return local_ip
    if addr in ipaddress.IPv4Network("172.16.0.0/12"):
        return local_ip
    if addr in ipaddress.IPv4Network("192.168.0.0/16"):
        return local_ip

    return None


def setup_split_dns(addr: ipaddress.IPv4Address | None) -> bool:
    if shutil.which("nmcli") and is_active("NetworkManager"):
        configure_networkmanager()
    elif shutil.which("networkctl") and is_active("systemd-networkd"):
        configure_networkd()
    else:
        print("Could not determine network stack")
        return False

    if addr is not None:
        answer = input(
            f"Do you want to resolve *.starter.home.arpa to {addr.compressed} instead of 10.50.0.100? Y/n: "
        ).strip()
        if answer.lower() == "y" or len(answer) == 0:
            return True

    return False


def is_active(service: str):
    return (
        subprocess.run(
            ["systemctl", "is-active", "--quiet", service], check=False
        ).returncode
        == 0
    )


def configure_networkmanager() -> None:
    subprocess.run(["sudo", "apt-get", "install", "-y", "systemd-resolved"], check=True)

    subprocess.run(
        ["sudo", "tee", "/etc/NetworkManager/conf.d/starter-home-dns.conf"],
        input="""\
[main]
dns=systemd-resolved
""",
        text=True,
        check=True,
    )

    subprocess.run(["sudo", "systemctl", "restart", "NetworkManager"], check=True)

    subprocess.run(
        [
            "sudo",
            "nmcli",
            "connection",
            "modify",
            "starter-net",
            "+ipv4.dns",
            DNS,
            "+ipv4.dns-search",
            DOMAIN,
        ],
        check=True,
    )
    subprocess.run(["sudo", "nmcli", "device", "reapply", "starter-net"], check=True)
    subprocess.run(["sudo", "systemctl", "restart", "systemd-resolved"], check=True)


def configure_networkd() -> None:
    subprocess.run(
        ["sudo", "tee", "/etc/systemd/system/starter-home-dns.service"],
        input="""\
[Unit]
Description=DNS configuration for starter-home
BindsTo=sys-subsystem-net-devices-starter\\x2dnet.device
After=sys-subsystem-net-devices-starter\\x2dnet.device

[Service]
Type=oneshot
ExecStart=/usr/bin/resolvectl dns starter-net 10.50.0.100
ExecStart=/usr/bin/resolvectl domain starter-net ~starter.home.arpa
ExecStopPost=/usr/bin/resolvectl revert starter-net
RemainAfterExit=yes

[Install]
WantedBy=sys-subsystem-net-devices-starter\\x2dnet.device
""",
        text=True,
        check=True,
    )

    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    subprocess.run(
        ["sudo", "systemctl", "enable", "--now", "starter-home-dns.service"], check=True
    )
