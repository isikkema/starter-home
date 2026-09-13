import shutil

import click

from .files import ROOT
from .incus import delete_instance, new_incus_client

SECRETS = ROOT / "secrets"
LOCAL_BACKUP = ROOT / "host-storage" / "backup"


@click.command()
@click.option("--delete-local-backups", type=bool, is_flag=True, default=False)
def delete(delete_local_backups: bool) -> None:
    answer = input(
        "This will delete the starter-home VM and everything on it.\nAre you sure? y/N: "
    )
    if answer.lower() != "y":
        print("Aborted.")
        return

    client = new_incus_client()
    delete_instance(client)

    for item in SECRETS.iterdir():
        if item.name == ".gitkeep":
            continue

        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    if delete_local_backups:
        answer = input(
            "WARNING: This will delete ALL local backups!\nAre you REALLY sure? yes/no: "
        )
        if answer.lower() != "yes":
            print("Aborted.")
            return

        shutil.rmtree(LOCAL_BACKUP)
