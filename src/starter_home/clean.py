import glob
import subprocess
import sys

from .files import ROOT

SECRETS = ROOT / "secrets"
LOCAL_BACKUP = ROOT / "host-storage" / "backup"


def main(delete_local_backup: bool) -> None:
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

    if delete_local_backup:
        _ = subprocess.run(
            ["rm", "-rf", str(LOCAL_BACKUP)], stdout=subprocess.DEVNULL, check=True
        )


if __name__ == "__main__":
    delete_local_backup = False
    if sys.argv[1] == "--delete-local-backup":
        delete_local_backup = True

    main(delete_local_backup)
