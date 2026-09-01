import json
import os
import subprocess

import click

from .files import ROOT

INVENTORY = ROOT / "automation" / "inventory" / "virtual-machine.yaml"
CREATE_BACKUP_PLAYBOOK = ROOT / "automation" / "manual-backup.yaml"
LIST_BACKUPS_PLAYBOOK = ROOT / "automation" / "list-backups.yaml"
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
            str(CREATE_BACKUP_PLAYBOOK),
        ],
        env=env,
        cwd=ROOT,
        check=True,
    )


@backup.command("list")
def list_() -> None:
    local_backups, remote_backups = list_backups()

    print("Local:")
    for backup in local_backups:
        print(
            f"{backup['short_id']}  {backup['time']}  {backup['files_changed']:>3} files changed  {backup['total_files_processed']:>3} files total  {backup['data_added']:>11} B added  {backup['total_bytes_processed']:>11} B total"
        )

    print("Remote:")
    for backup in remote_backups:
        print(
            f"{backup['short_id']}  {backup['time']}  {backup['files_changed']:>3} files changed  {backup['total_files_processed']:>3} files total  {backup['data_added']:>11} B added  {backup['total_bytes_processed']:>11} B total"
        )


def list_backups() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ANSIBLE_CONFIG)
    env["ANSIBLE_STDOUT_CALLBACK"] = "json"

    proc = subprocess.run(
        [
            "ansible-playbook",
            "-i",
            str(INVENTORY),
            str(LIST_BACKUPS_PLAYBOOK),
        ],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    out = json.loads(proc.stdout)

    all_backups = []
    for play in out["plays"]:
        for task in play["tasks"]:
            hosts = task.get("hosts")
            if hosts is None:
                continue

            for host in hosts.values():
                facts = host.get("ansible_facts")
                if facts is None:
                    continue

                for location in ("local_backups", "remote_backups"):
                    backups = []
                    verbose_backups = facts.get(location)
                    if verbose_backups is None:
                        continue

                    verbose_backups.sort(
                        key=lambda backup: backup["time"],
                        reverse=True,
                    )

                    for backup in verbose_backups:
                        backups.append(
                            {
                                "time": backup["time"],
                                "short_id": backup["short_id"],
                                "files_changed": backup["summary"]["files_changed"],
                                "total_files_processed": backup["summary"][
                                    "total_files_processed"
                                ],
                                "data_added": backup["summary"]["data_added"],
                                "total_bytes_processed": backup["summary"][
                                    "total_bytes_processed"
                                ],
                            }
                        )

                    all_backups.append(backups)
                    if len(all_backups) == 2:
                        return tuple(all_backups)

    return ([], [])
