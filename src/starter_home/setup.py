import json
import os
from getpass import getpass

import click
import psutil

from .files import CUSTOM_CONFIG, ROOT

HOST_STORAGE = ROOT / "host-storage"

LOCAL_BACKUP_ENV = ROOT / "backup" / "local_backup.env"
REMOTE_BACKUP_ENV = ROOT / "backup" / "remote_backup.env"


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

    print("Memory and Disk Size units must be specified GiB or MiB")
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

    if recommended_gib is None:
        mem = input("Memory: ")
    else:
        mem = input(f"Memory [{recommended_gib}GiB]: ")
        if len(mem.strip()) == 0:
            mem = f"{recommended_gib}GiB"

    disk_size = input("Disk Size: ")

    print(f"CPUs: {cpus}")
    print(f"Memory: {mem}")
    print(f"Disk Size: {disk_size}")

    while True:
        answer = input("Does this look right? y/n: ")
        if answer.lower() == "y":
            break
        elif answer.lower() == "n":
            print("Aborting...")
            return

    if not LOCAL_BACKUP_ENV.exists():
        while True:
            local_password = getpass("Password for local backups: ")
            local_password_confirm = getpass("Confirm password: ")

            if local_password_confirm == local_password:
                break

            print("Passwords do not match.")

        with open(LOCAL_BACKUP_ENV, "w") as f:
            _ = f.write(
                f"RESTIC_REPOSITORY=/host-storage/backup\nRESTIC_PASSWORD={local_password}"
            )

    if not REMOTE_BACKUP_ENV.exists():
        print("A remote backup location is highly recommended.")
        print("See the Remote Backups section in the README.")

    with open(CUSTOM_CONFIG, "w") as f:
        json.dump(
            {
                "cpus": cpus,
                "memory": mem,
                "disk_size": disk_size,
                "host-storage": str(HOST_STORAGE),
            },
            f,
            indent=4,
        )
