import os
import subprocess

import click

from .files import ROOT

INVENTORY = ROOT / "automation" / "inventory" / "virtual-machine.yaml"
PLAYBOOK = ROOT / "automation" / "manual-backup.yaml"
ANSIBLE_CONFIG = ROOT / "automation" / "ansible.cfg"


@click.group()
def backup() -> None:
    pass


@backup.command()
def create() -> None:
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ANSIBLE_CONFIG)

    print("Creating backup")
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
