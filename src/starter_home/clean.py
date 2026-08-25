import glob
import subprocess

import click

from .files import ROOT

SECRETS = ROOT / "secrets"
LOCAL_BACKUP = ROOT / "host-storage" / "backup"


@click.command()
@click.option("--delete-local-backups", type=bool, default=False)
def clean(delete_local_backups: bool) -> None:
    _ = subprocess.run(
        ["sudo", "incus", "stop", "starter-home"],
        stdout=subprocess.DEVNULL,
        check=False,
    )
    _ = subprocess.run(
        ["sudo", "incus", "delete", "starter-home"],
        stdout=subprocess.DEVNULL,
        check=False,
    )

    secrets = glob.glob(str(SECRETS / "*"))
    _ = subprocess.run(["rm"] + secrets, stdout=subprocess.DEVNULL, check=True)

    if delete_local_backups:
        _ = subprocess.run(
            ["rm", "-rf", str(LOCAL_BACKUP)], stdout=subprocess.DEVNULL, check=True
        )
