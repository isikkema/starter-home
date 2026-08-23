#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "ansible-core>=2.19,<3",
# ]
# ///

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

INVENTORY = ROOT / "automation" / "inventory" / "virtual-machine.yaml"
PLAYBOOK = ROOT / "automation" / "manual-backup.yaml"
ANSIBLE_CONFIG = ROOT / "automation" / "ansible.cfg"


def main() -> None:
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
