import shutil

import click

from .files import ROOT
from .incus import delete_instance, new_incus_client

SECRETS = ROOT / "secrets"
LOCAL_BACKUP = ROOT / "host-storage" / "backup"


@click.command()
@click.option("--delete-local-backups", type=bool, default=False)
def delete(delete_local_backups: bool) -> None:
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
        shutil.rmtree(LOCAL_BACKUP)
